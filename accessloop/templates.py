"""Fixes that land in the template file a developer edits, not in generated HTML.

Server-side templates (Jinja, Django, Thymeleaf, JSP, Handlebars, ERB, Blade, Twig ...) render HTML. AccessLoop scans
and fixes the rendered page as usual, then carries each verified edit back into the template: an edit is anchored to the
nearest element whose markup appears exactly once in the template, and is only transferred if the template text there
is identical to the rendered text the edit relies on. Anything that cannot be carried over safely (markup produced by a
loop or an expression) is reported as a manual change with the exact before/after.

For Jinja templates AccessLoop can render the template itself (with a JSON context) and re-scan the rendered result of
the fixed template, so the template fix is verified end to end. For other engines, provide a rendered sample page.

Client-side frameworks (React, Angular, Vue) compile components in JavaScript; mapping into those sources needs their
compilers and is not part of this module.
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

from .htmlsource import Doc, Edit, apply_edits
from .workflow import Workflow, approve_all, read_source


class TemplateError(ValueError):
    pass


def render_jinja(template: str, context: dict, search_path: Path | None = None) -> str:
    try:
        import jinja2
    except ImportError as error:  # pragma: no cover
        raise TemplateError('Rendering Jinja templates needs the jinja2 package.') from error
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(search_path)) if search_path else None,
                             autoescape=True, undefined=jinja2.StrictUndefined)
    try:
        return env.from_string(template).render(**context)
    except jinja2.TemplateError as error:
        raise TemplateError(f'The template did not render: {error}') from error


def map_edits(rendered: str, template: str, edits: list[Edit]) -> tuple[list[Edit], list[Edit]]:
    """Carry edits made on `rendered` into `template`. Returns (template edits, edits that could not be carried)."""
    doc = Doc(rendered)
    mapped, failed = [], []
    for e in sorted(edits, key=lambda x: (x.start, x.end)):
        anchors = sorted((el for el in doc.elements if el.start <= e.start), key=lambda el: -el.start)
        done = False
        for el in anchors[:40]:
            tag = rendered[el.start:el.start_end]
            if template.count(tag) != 1:
                continue
            t0 = template.index(tag)
            span = rendered[el.start:e.end]
            if template[t0:t0 + len(span)] != span:        # the template differs between the anchor and the edit
                continue
            off = e.start - el.start
            mapped.append(Edit(t0 + off, t0 + off + (e.end - e.start), e.text))
            done = True
            break
        if not done:
            # second strategy: the text right around the edit, if it occurs exactly once in the template
            for width in (80, 50, 30, 18, 12, 8):
                left = rendered[max(0, e.start - width):e.start]
                mid = rendered[e.start:e.end]
                right = rendered[e.end:e.end + width]
                needle = left + mid + right
                if len(left) < 6 or template.count(needle) != 1:
                    continue
                t0 = template.index(needle) + len(left)
                mapped.append(Edit(t0, t0 + len(mid), e.text))
                done = True
                break
        if not done:
            failed.append(e)
    return mapped, failed


def fix_template(template_path: Path, rendered: str | None = None, context: dict | None = None, reviewer: str = '',
                 best_practice: bool = True, language: str = 'en', values_for=None) -> dict:
    """Scan the rendered page, apply the approved fixes there (each verified), then carry them into the template."""
    template = read_source(template_path)
    if rendered is None:
        if context is None:
            raise TemplateError('Give a rendered sample page, or a JSON context to render this Jinja template.')
        rendered = render_jinja(template, context, template_path.parent)
    with tempfile.TemporaryDirectory() as tmp:
        engine = Workflow(Path(tmp))
        engine.load(rendered, allow_scripts=True, assets_dir=template_path.parent)
        before = engine.scan(language=language, best_practice=best_practice)
        outcomes = approve_all(engine, values_for or (lambda p: None), reviewer=reviewer or 'template fix', language=language)
        ops = engine.changes()
        audit = (Path(tmp) / 'audit.jsonl').read_text(encoding='utf-8')
        after_rendered = engine.current_html
        after_scan = engine.current_scan
    # replay every verified change, in order, on the template
    current_rendered, current_template = rendered, template
    carried, manual = [], []
    for op in ops:
        edits = [Edit(s, e, t) for s, e, t, _old in op['edits']]
        t_edits, failed = map_edits(current_rendered, current_template, edits)
        if failed:
            manual.append({'rule': op['rule'], 'selector': op['selector'],
                           'changes': [{'before': current_rendered[f.start:f.end] or '(insert)', 'after': f.text,
                                        'context': current_rendered[max(0, f.start - 60):f.end + 60]} for f in failed]})
        if t_edits:
            current_template = apply_edits(current_template, t_edits)
            carried.append({'rule': op['rule'], 'selector': op['selector'], 'edits': len(t_edits)})
        current_rendered = apply_edits(current_rendered, edits)
    result = {'template': current_template, 'carried': carried, 'manual': manual, 'outcomes': outcomes, 'audit': audit,
              'violations_before': len(before.findings), 'violations_after_rendered': len(after_scan.findings),
              'rendered_after': after_rendered}
    if context is not None:
        # end-to-end check: render the FIXED template and scan what it produces
        from .scanner import scan_html
        re_rendered = render_jinja(current_template, context, template_path.parent)
        check = scan_html(re_rendered, best_practice=best_practice, assets_dir=template_path.parent)
        result['violations_after_template'] = len(check.findings)
        result['template_verified'] = len(check.findings) <= len(after_scan.findings)
    return result


def load_context(path: str | None) -> dict | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding='utf-8'))
