# Adding a fix template

AccessLoop's 85 fix types are small Python functions, one per kind of problem. Adding one takes three pieces: the
function, a sample page that shows the problem, and a test. The engine does the rest: finding the element, showing the
diff, asking for approval, re-scanning, rolling back and logging are shared by every template.

## 1. Write the function

Templates live in `accessloop/fixers.py` and `accessloop/fixers_extra.py`. Register one with the `@fixer` decorator,
naming the axe rule (or rules) it fixes and its mode:

- `auto`: the fix needs no words from a person (for example, linking a label that sits right next to its field);
- `input`: a person must type something (alt text, a page title); the template returns the questions, never a guess;
- `mixed`: automatic when the page already holds the answer, otherwise it asks.

The example below is a simplified version of the real `frame-title` template (a new template would name a rule that
has none yet):

```python
from .fixers import Draft, fixer, clean_text, _text_field, _tag_focus
from .htmlsource import Edit


@fixer('frame-title', mode='input')
def frame_title(doc, el, finding, language, values):
    """`doc` is the parsed page, `el` the exact element axe flagged, `values` what the person typed (None at first)."""
    fld = _text_field('title', 'Frame title', 'Say what the frame contains, e.g. "Branch locator map".')
    if values is None:                                   # first call: ask, change nothing
        return Draft(focus=_tag_focus(el), explanation='Frames need a title that says what they contain.',
                     mode='input', fields=(fld,), preview='title="…"')
    text = clean_text(values.get('title'), 3, 120, 'Frame title')     # refuses markup, control characters, bad length
    at = el.start_end - 1                                # just before the start tag's closing ">"
    return Draft([Edit(at, at, f' title="{text}"')], _tag_focus(el), 'Add the frame title you typed.',
                 f'Reviewer-provided title: "{text}"')
```

Rules every template follows:

- **Edit by offset, never by re-writing the page.** An `Edit(start, end, text)` replaces exactly those characters of the
  source; everything else stays byte for byte. Offsets come from `doc` (`el.start`, `el.start_end`, `el.end_start`).
- **Return `None` when unsure.** The finding then goes to the manual review queue with guidance, which is better than a
  plausible wrong fix.
- **Never invent words.** Anything a person must know (what an image shows, what a button does) is a field.
- **Set `risk='medium'`** for changes to structure or behaviour (roles, tab order, heading levels). The agent's default
  policy only applies low-risk fixes on its own.
- **New files** (for example a captions file) go in `Draft.files`; only safe relative paths are written.

## 2. Add a sample page

Put a page that shows the problem in `examples/samples/` (or extend an existing gallery page) and add a case to `CASES`
in `accessloop/sample_suite.py`. The suite applies the template in a real browser and prints how many templates it has
proven (currently 88 of 88).

## 3. Add a test, then run everything

```bash
python -m pytest -q                       # unit tests, including your new one
python -m accessloop.sample_suite         # every template proven in a real browser
python -m accessloop.catalog              # regenerates docs/ISSUE_CATALOG.md: the rule now shows as "fixed"
```

A test fails if axe adds a rule nobody has classified, so the catalogue never silently goes stale. You do not need to
touch verification: every fix, including yours, is kept only if the targeted problem is gone, no other rule got worse
and the element itself passes; otherwise it is rolled back automatically.
