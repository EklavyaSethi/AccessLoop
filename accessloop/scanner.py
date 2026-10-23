"""Runs the actual axe-core browser engine, with zero CDN dependency at runtime."""
from __future__ import annotations
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
import atexit
import mimetypes
import threading
from .htmlsource import Doc, scan_copy
from .models import ScanResult

ROOT = Path(__file__).resolve().parent.parent
AXE_PATH = Path(os.environ.get('ACCESSLOOP_AXE_PATH', str(ROOT / 'node_modules/axe-core/axe.min.js')))
TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22a', 'wcag22aa']
BEST_PRACTICE_TAGS = TAGS + ['best-practice']


class ScanError(RuntimeError):
    pass


ASSET_ORIGIN = 'http://accessloop.local/'
ASSET_TYPES = {'.css', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.otf'}
MAX_ASSET_BYTES = 5 * 1024 * 1024


def _local_asset(url: str, assets_dir: Path | None) -> Path | None:
    """Map http://accessloop.local/<path> to a file inside assets_dir (style sheets, images, fonts only)."""
    if assets_dir is None or not url.startswith(ASSET_ORIGIN):
        return None
    rel = url[len(ASSET_ORIGIN):].split('?', 1)[0].split('#', 1)[0]
    try:
        from urllib.parse import unquote
        target = (assets_dir / unquote(rel)).resolve()
        root = assets_dir.resolve()
    except (OSError, ValueError):
        return None
    if root not in target.parents or target.suffix.lower() not in ASSET_TYPES or not target.is_file() \
            or target.stat().st_size > MAX_ASSET_BYTES:
        return None
    return target


def _router(assets_dir: Path | None, blocked: list[str]):
    def handle(route) -> None:
        """Nothing leaves the machine. The page's own style sheets, images and fonts can be served from its folder
        (when one is given); a navigation (meta refresh, frame src) gets "204 No Content", which browsers treat as
        'stay on this page'; every other request is aborted and recorded, so the report can list what did not load."""
        try:
            url = route.request.url
            local = _local_asset(url, assets_dir)
            if local is not None:
                ctype = mimetypes.guess_type(local.name)[0] or 'application/octet-stream'
                route.fulfill(status=200, body=local.read_bytes(), headers={'Content-Type': ctype})
                return
            shown = url[len(ASSET_ORIGIN):] if url.startswith(ASSET_ORIGIN) else url
            if route.request.is_navigation_request():
                blocked.append(f'navigation (stayed on page): {shown[:200]}')
                route.fulfill(status=204, body='')
            else:
                blocked.append(f'{route.request.resource_type}: {shown[:200]}')
                route.abort()
        except Exception:  # noqa: BLE001 - the request may already be gone
            pass
    return handle


class _Browser(threading.local):
    """One headless Chromium per thread, reused across scans (a fresh, isolated context for every scan)."""
    playwright = None
    browser = None

    def get(self):
        if self.browser is not None and self.browser.is_connected():
            return self.browser
        self.close()
        launch_args = {'headless': True}
        # Optional override for environments with a system Chromium installation.
        if os.getenv('ACCESSLOOP_CHROMIUM_EXECUTABLE'):
            launch_args['executable_path'] = os.environ['ACCESSLOOP_CHROMIUM_EXECUTABLE']
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(**launch_args)
        _OPEN.append(self)
        return self.browser

    def close(self) -> None:
        for closer in (getattr(self.browser, 'close', None), getattr(self.playwright, 'stop', None)):
            try:
                if closer:
                    closer()
            except Exception:  # noqa: BLE001
                pass
        self.browser = self.playwright = None


_OPEN: list = []
_LOCAL = _Browser()


@atexit.register
def _shutdown() -> None:
    for b in list(_OPEN):
        b.close()


_JS = """async ([tags, wanted]) => {
    const res = await window.axe.run(document, {
        runOnly: { type: 'tag', values: tags },
        iframes: false,   // frame contents are never loaded (all requests are blocked)
        rules: { 'frame-tested': { enabled: false }, 'frame-focusable-content': { enabled: false } },
        resultTypes: ['violations', 'incomplete', 'passes']
    });
    // What a screen reader would announce for an element: name, role and the states that matter.
    const canAnnounce = !!(axe.setup && axe.utils && axe.utils.getNodeFromTree && axe.commons);
    if (canAnnounce) axe.setup(document);
    const announce = (el) => {
        if (!canAnnounce || /^(HTML|BODY|HEAD)$/i.test(el.tagName)) return null;
        try {
            const v = axe.utils.getNodeFromTree(el);
            if (!v) return null;
            let name = ''; try { name = axe.commons.text.accessibleTextVirtual(v) || ''; } catch (e) {}
            let role = null; try { role = axe.commons.aria.getRole(v); } catch (e) {}
            const states = [];
            const t = (el.getAttribute('type') || '').toLowerCase();
            if (t === 'checkbox' || t === 'radio' || el.hasAttribute('aria-checked'))
                states.push((el.checked || el.getAttribute('aria-checked') === 'true') ? 'checked' : 'not checked');
            if (el.hasAttribute('aria-expanded')) states.push(el.getAttribute('aria-expanded') === 'true' ? 'expanded' : 'collapsed');
            if (el.required || el.getAttribute('aria-required') === 'true') states.push('required');
            if (el.disabled || el.getAttribute('aria-disabled') === 'true') states.push('dimmed');
            if (el.getAttribute('aria-invalid') === 'true') states.push('invalid');
            if (el.getAttribute('aria-hidden') === 'true') states.push('hidden from screen readers');
            const level = el.getAttribute('aria-level') || ((/^h([1-6])$/i.exec(el.tagName) || [])[1]);
            if (role === 'heading' && level) states.push('level ' + level);
            return { name: String(name).trim().slice(0, 160), role, states };
        } catch (e) { return null; }
    };
    for (const v of res.violations.concat(res.incomplete)) {
        for (const n of v.nodes) {
            let uid = null, el = null;
            try {
                const sel = Array.isArray(n.target) ? n.target[0] : null;
                el = typeof sel === 'string' ? document.querySelector(sel) : null;
                if (el) uid = el.getAttribute('data-al-uid');
            } catch (e) { uid = null; }
            n.uid = uid;
            n.announce = el ? announce(el) : null;
        }
    }
    const extra = {};
    for (const u of wanted) {
        const el = document.querySelector('[data-al-uid="' + u + '"]');
        if (el) extra[u] = announce(el);
    }
    if (canAnnounce && axe.teardown) axe.teardown();
    res.announced = extra;
    res.engine = { axe: axe.version || 'unknown' };
    return res;
}"""


# ---- AccessLoop's own browser checks (beyond axe): small screens, text spacing, keyboard focus, open states ----------
CUSTOM_RULES = {
    'al-reflow': {'title': 'Content must reflow at 320 CSS pixels without horizontal scrolling', 'wcag': ['1.4.10'],
                  'level': 'AA', 'impact': 'serious'},
    'al-text-spacing': {'title': 'Text must not be cut off when users increase text spacing', 'wcag': ['1.4.12'],
                        'level': 'AA', 'impact': 'serious'},
    'al-focus-visible': {'title': 'Keyboard focus must be visible', 'wcag': ['2.4.7'], 'level': 'AA', 'impact': 'serious'},
    'al-forced-colors': {'title': 'Controls must stay visible in Windows high-contrast (forced colours) mode', 'wcag': ['1.4.11'],
                         'level': 'AA', 'impact': 'moderate'},
}

_UID = """(el) => { const u = el.closest('[data-al-uid]'); return u ? u.getAttribute('data-al-uid') : null; }"""

_REFLOW_JS = """() => {
  const uid = %s;
  const out = [];
  const vw = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth <= vw + 2) return out;
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.right <= vw + 2) continue;
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed' || cs.visibility === 'hidden') continue;
    if ([...el.children].some(c => c.getBoundingClientRect().right > vw + 2)) continue;  // report the deepest
    if (el.closest('table, pre, code, [role=application], svg, canvas, video, iframe')) continue;  // 1.4.10 exceptions
    out.push({uid: uid(el), html: el.outerHTML.slice(0, 200), extra: Math.round(r.right - vw)});
    if (out.length >= 15) break;
  }
  return out;
}""" % _UID

_SPACING_JS = """() => {
  const uid = %s;
  const st = document.createElement('style');
  st.textContent = '* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; } ' +
                   'p { margin-bottom: 2em !important; }';
  document.head.appendChild(st);
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(el);
    const clipY = (cs.overflowY === 'hidden' || cs.overflow === 'hidden') && el.scrollHeight > el.clientHeight + 2;
    const clipX = (cs.overflowX === 'hidden' || cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 2;
    if (clipY || clipX) out.push({uid: uid(el), html: el.outerHTML.slice(0, 200)});
    if (out.length >= 15) break;
  }
  st.remove();
  return out;
}""" % _UID

_FOCUS_STYLE_JS = """() => {
  const sel = 'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), ' +
              'textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"]), [contenteditable=""], [contenteditable=true]';
  const look = (el) => { const c = getComputedStyle(el); return [c.outlineStyle, c.outlineWidth, c.outlineColor, c.boxShadow,
      c.borderTopColor, c.borderBottomColor, c.borderBottomWidth, c.backgroundColor, c.color, c.textDecorationLine].join('|'); };
  if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
  const base = {};
  for (const el of document.querySelectorAll(sel)) {
    const u = el.getAttribute('data-al-uid');
    if (u && el.getClientRects().length) base[u] = look(el);
  }
  window.__alLook = look;
  return base;
}"""

_ACTIVE_JS = """() => { const el = document.activeElement; if (!el || el === document.body) return null;
  const u = el.getAttribute('data-al-uid'); return u ? [u, window.__alLook(el), el.outerHTML.slice(0, 200)] : null; }"""

_OPEN_JS = """() => { let n = 0;
  for (const d of document.querySelectorAll('details:not([open])')) { d.setAttribute('open', ''); n++; }
  for (const d of document.querySelectorAll('dialog:not([open])')) { d.setAttribute('open', ''); n++; }
  return n; }"""

_FORCED_JS = """() => {
  const uid = %s;
  const out = [];
  for (const el of document.querySelectorAll('a[href], button, [role=button], [role=link], [role=img]')) {
    if (!el.getClientRects().length || (el.innerText || '').trim()) continue;
    const hasSvg = el.querySelector('svg, img[src]');
    const bg = getComputedStyle(el).backgroundImage;
    if (!hasSvg && bg && bg !== 'none' && !/gradient/.test(bg)) out.push({uid: uid(el), html: el.outerHTML.slice(0, 200)});
    if (out.length >= 15) break;
  }
  return out;
}""" % _UID


def _custom(rule: str, nodes: list[dict], why: str) -> dict:
    info = CUSTOM_RULES[rule]
    return {'id': rule, 'impact': info['impact'], 'help': info['title'], 'description': why,
            'nodes': [{'target': [f'[data-al-uid="{n["uid"]}"]'] if n.get('uid') else ['html'], 'uid': n.get('uid'),
                       'html': n.get('html', ''), 'failureSummary': why + (f' (overflows by {n["extra"]} px)' if n.get('extra') else '')}
                      for n in nodes]}


def _extended(page, best_practice: bool) -> tuple[list, list]:
    """Run AccessLoop's own checks; returns (violations, needs-review) in axe's result shape."""
    violations, reviews = [], []
    # keyboard focus visibility, at desktop width, by really pressing Tab
    base = page.evaluate(_FOCUS_STYLE_JS)
    missing, seen = [], set()
    for _ in range(min(len(base), 80)):
        page.keyboard.press('Tab')
        got = page.evaluate(_ACTIVE_JS)
        if not got or got[0] in seen:
            if got is None:
                continue
            break
        seen.add(got[0])
        if got[0] in base and base[got[0]] == got[1]:
            missing.append({'uid': got[0], 'html': got[2]})
    if missing:
        violations.append(_custom('al-focus-visible', missing[:20], 'Nothing visibly changes when this control receives keyboard focus.'))
    # forced colours (Windows high-contrast): background-image-only controls disappear
    page.emulate_media(forced_colors='active')
    forced = page.evaluate(_FORCED_JS)
    page.emulate_media(forced_colors='none')
    if forced:
        reviews.append(_custom('al-forced-colors', forced, 'This control shows no text and relies on a background image, '
                               'which forced-colours mode removes.'))
    # small screen: reflow and text spacing at 320 CSS pixels (= 1280 px at 400% zoom)
    page.set_viewport_size({'width': 320, 'height': 800})
    reflow = page.evaluate(_REFLOW_JS)
    spacing = page.evaluate(_SPACING_JS)
    if reflow:
        reviews.append(_custom('al-reflow', reflow, 'At 320 CSS pixels wide this element runs off the screen, so users must '
                               'scroll sideways.'))
    if spacing:
        violations.append(_custom('al-text-spacing', spacing, 'With increased line, letter and word spacing the text in '
                                  'this element is cut off.'))
    page.set_viewport_size({'width': 1280, 'height': 900})
    return violations, reviews


def scan_html(html: str, best_practice: bool = False, assets_dir: Path | None = None,
              announce_uids: tuple[int, ...] = (), extended: bool = False) -> ScanResult:
    """Scan with the WCAG A/AA rules; best_practice=True also runs axe's best-practice rules.

    Nothing on the page ever runs (see htmlsource.scan_copy). assets_dir, when given, is the folder the page's own
    relative style sheets, images and fonts are loaded from; nothing outside it can be read. announce_uids asks for
    what a screen reader would announce for those elements (used to show a fix's effect)."""
    if not AXE_PATH.is_file():
        raise ScanError('axe-core not installed. Run `npm install` in the project directory first.')
    blocked: list[str] = []
    for attempt in (1, 2):           # a crashed or closed browser is relaunched once
        try:
            browser = _LOCAL.get()
            context = browser.new_context(service_workers='block')
            try:
                context.route('**/*', _router(Path(assets_dir) if assets_dir else None, blocked))
                page = context.new_page()
                page.set_viewport_size({'width': 1280, 'height': 900})
                page.set_default_timeout(10000)
                # Tag every start tag with data-al-uid so each finding maps to an exact source element.
                copy = scan_copy(Doc(html), ASSET_ORIGIN if assets_dir else None)
                page.set_content(copy, wait_until='load', timeout=15000)
                # Injected through the DevTools protocol, which the page's script-blocking policy does not apply to.
                page.evaluate(_axe_source() + '\n;0')
                if extended:
                    page.evaluate(_OPEN_JS)        # closed <details> and <dialog> are scanned in their open state too
                data = page.evaluate(_JS, [BEST_PRACTICE_TAGS if best_practice else TAGS,
                                           [str(u) for u in announce_uids]])
                if extended:
                    more_v, more_r = _extended(page, best_practice)
                    data['violations'] = data.get('violations', []) + more_v
                    data['incomplete'] = data.get('incomplete', []) + more_r
                data['engine'] = {**data.get('engine', {}), 'browser': f'Chromium {browser.version}'}
                data['blocked'] = sorted(set(blocked))
                return ScanResult.from_axe(data)
            finally:
                context.close()
        except ScanError:
            raise
        except Exception as error:
            _LOCAL.close()
            if attempt == 2:
                raise ScanError(f'Browser scan failed: {error}') from error
    raise ScanError('Browser scan failed.')


_AXE_CACHE: dict = {}


def _axe_source() -> str:
    key = (str(AXE_PATH), AXE_PATH.stat().st_mtime)
    if key not in _AXE_CACHE:
        _AXE_CACHE.clear()
        _AXE_CACHE[key] = AXE_PATH.read_text(encoding='utf-8')
    return _AXE_CACHE[key]


def screenshot(html: str, assets_dir: Path | None = None, highlight_uids: tuple[int, ...] = (), width: int = 1280,
               max_height: int = 6000) -> bytes:
    """A PNG of the page as the sandbox renders it (scripts never run), with changed elements outlined."""
    for attempt in (1, 2):
        try:
            browser = _LOCAL.get()
            context = browser.new_context(service_workers='block', viewport={'width': width, 'height': 900})
            try:
                context.route('**/*', _router(Path(assets_dir) if assets_dir else None, []))
                page = context.new_page()
                page.set_content(scan_copy(Doc(html), ASSET_ORIGIN if assets_dir else None), wait_until='load', timeout=15000)
                if highlight_uids:
                    css = ', '.join(f'[data-al-uid="{int(u)}"]' for u in highlight_uids)
                    page.evaluate("""(css) => { const s = document.createElement('style');
                        s.textContent = css + ' { outline: 4px solid #e11d48 !important; outline-offset: 2px !important; }';
                        document.head.appendChild(s); }""", css)
                height = min(max_height, page.evaluate('document.documentElement.scrollHeight'))
                return page.screenshot(clip={'x': 0, 'y': 0, 'width': width, 'height': max(height, 200)}, full_page=True)
            finally:
                context.close()
        except Exception as error:  # noqa: BLE001
            _LOCAL.close()
            if attempt == 2:
                raise ScanError(f'Screenshot failed: {error}') from error
    raise ScanError('Screenshot failed.')
