"""Minimal stand-in for the streamlit module so the page code can be smoke-tested without installing Streamlit.

It records what pages render and lets a test script button clicks. It does NOT prove the look or the real Streamlit API;
tests/test_streamlit_ui.py also runs Streamlit's own AppTest when Streamlit is installed.
"""
from __future__ import annotations
import sys
import types
from unittest.mock import MagicMock


class StopScript(Exception):
    pass


_ROUTES: dict = {}


class _Ctx(MagicMock):
    """A `with` block or column. Widget calls on it (col.button(...)) go to the same stand-in as st.button(...)."""

    def __getattr__(self, name):
        if name in _ROUTES:
            return _ROUTES[name]
        return super().__getattr__(name)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def install(clicks: set[str] | None = None, uploads: dict | None = None, inputs: dict | None = None) -> types.ModuleType:
    clicks = clicks if clicks is not None else set()
    mod = types.ModuleType('streamlit')
    mod.__path__ = []
    mod.session_state = type('SS', (dict,), {'__getattr__': lambda s, k: s[k], '__setattr__': lambda s, k, v: s.__setitem__(k, v)})()
    mod.rendered = []
    mod.errors = []
    ctx = lambda *a, **k: _Ctx()  # noqa: E731

    def record(kind):
        def fn(*a, **k):
            mod.rendered.append((kind, a, k))
            if kind == 'error':
                mod.errors.append(a[0] if a else '')
        return fn

    def button(label, key=None, **k):
        mod.rendered.append(('button', (label,), {'key': key}))
        hit = (key in clicks) or (label in clicks)
        return hit

    def columns(spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Ctx() for _ in range(n)]

    def tabs(labels, **k):
        return [_Ctx() for _ in labels]

    def selectbox(label, options, index=0, format_func=str, **k):
        options = list(options)
        if inputs and label in inputs:
            return inputs[label]
        for o in options:
            format_func(o)  # exercise the formatter
        return options[index] if options else None

    def text_input(label, value='', **k):
        return (inputs or {}).get(label, value)

    def stop():
        raise StopScript()

    def rerun():
        raise StopScript()

    for name in ('markdown', 'write', 'caption', 'code', 'dataframe', 'bar_chart', 'metric', 'info', 'success', 'warning', 'toast',
                 'subheader', 'header', 'title', 'page_link', 'download_button', 'set_page_config', 'logo', 'divider', 'json', 'text'):
        setattr(mod, name, record(name))
    mod.error = record('error')
    mod.button = button
    mod.columns = columns
    mod.tabs = tabs
    mod.selectbox = selectbox
    mod.toggle = lambda label, value=False, **k: (inputs or {}).get(label, value)
    mod.radio = lambda label, options, index=0, **k: (inputs or {}).get(label, list(options)[index])
    mod.text_input = text_input
    mod.number_input = lambda label, min_value=None, max_value=None, value=0, **k: (inputs or {}).get(label, value)
    mod.empty = lambda: types.SimpleNamespace(markdown=record('markdown'))
    mod.multiselect = lambda label, options, default=None, **k: (inputs or {}).get(label, list(default if default is not None else []))
    mod.checkbox = lambda label, **k: (inputs or {}).get(label, False)
    mod.text_area = lambda label, **k: (inputs or {}).get(label, '')
    mod.file_uploader = lambda label, **k: (uploads or {}).get(label)
    mod.container = ctx
    mod.popover = ctx
    mod.progress = lambda *a, **k: type('Bar', (), {'progress': lambda self, *a, **k: None})()
    mod.expander = ctx
    mod.spinner = ctx
    mod.sidebar = _Ctx()
    mod.stop = stop
    mod.rerun = rerun
    mod.Page = lambda *a, **k: types.SimpleNamespace(args=a, kwargs=k, run=lambda: None)
    mod.navigation = lambda pages, **k: types.SimpleNamespace(run=lambda: None, pages=pages)
    mod.column_config = types.SimpleNamespace(LinkColumn=lambda *a, **k: ('link', a, k))
    comp = types.ModuleType('streamlit.components')
    comp.__path__ = []
    v1 = types.ModuleType('streamlit.components.v1')
    v1.html = record('components.html')
    comp.v1 = v1
    mod.components = comp
    _ROUTES.clear()
    _ROUTES.update({k: getattr(mod, k) for k in ('number_input', 'button', 'download_button', 'text_input', 'selectbox', 'radio', 'toggle', 'multiselect', 'checkbox',
                                                 'text_area', 'file_uploader', 'markdown', 'write', 'caption', 'metric', 'info', 'success',
                                                 'warning', 'error', 'code', 'dataframe', 'subheader')})
    sys.modules['streamlit'] = mod
    sys.modules['streamlit.components'] = comp
    sys.modules['streamlit.components.v1'] = v1
    for name in [m for m in sys.modules if m.startswith('streamlit_ui')]:
        del sys.modules[name]
    return mod
