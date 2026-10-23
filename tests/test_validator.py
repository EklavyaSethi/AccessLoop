import pytest
from accessloop.workflow import WorkflowError, validate_source

PAGE = '<!doctype html><html lang="en"><head><title>t</title></head><body>{}</body></html>'

REFUSED = [
    '<script>alert(1)</script>', '<svg><script>alert(1)</script></svg>', '<base href="https://evil.example/">',
    '<img src="x.png" onerror="alert(1)" alt="">', '<a href="javascript:alert(1)">x</a>',
    '<a href="  jav&#x09;ascript:alert(1)">x</a>', '<a href="JaVaScRiPt:alert(1)">x</a>',
    '<iframe srcdoc="&lt;script&gt;alert(1)&lt;/script&gt;" title="x"></iframe>',
    '<iframe src="data:text/html,&lt;script&gt;alert(1)&lt;/script&gt;" title="x"></iframe>',
    '<object data="data:image/svg+xml,&lt;svg onload=alert(1)&gt;"></object>',
    '<form action="javascript:alert(1)"><button>Go</button></form>',
    '<button formaction="javascript:alert(1)">Go</button>', '<svg><a xlink:href="javascript:alert(1)">x</a></svg>',
    '<meta http-equiv="refresh" content="0; url=javascript:alert(1)">', '<frameset></frameset>',
]
ALLOWED = [
    '<iframe src="map.html" title="Branch map"></iframe>', '<object data="chart.svg" type="image/svg+xml">Chart</object>',
    '<a href="/statements">Statements</a>', '<img src="data:image/png;base64,iVBORw0KGgo=" alt="dot">',
    '<meta http-equiv="refresh" content="600; url=/logout">', '<p>Use javascript: links? No.</p>',
]


def test_active_content_is_refused():
    for snippet in REFUSED:
        with pytest.raises(WorkflowError):
            validate_source(PAGE.format(snippet))


def test_static_content_is_allowed():
    for snippet in ALLOWED:
        validate_source(PAGE.format(snippet))


def test_scripts_allowed_mode_accepts_but_never_runs_them():
    page = PAGE.format('<script>document.title="RAN"</script><p onclick="x()">Hi</p>')
    with pytest.raises(WorkflowError):
        validate_source(page)
    validate_source(page, allow_scripts=True)


def test_url_allow_list():
    for bad in ('<a href="file:///etc/passwd">x</a>', '<a href="ftp://x.example/">x</a>', '<img src="data:text/plain,hi" alt="">',
                '<iframe src="data:image/png;base64,AAAA" title="x"></iframe>', '<img srcset="a.png 1x, javascript:x() 2x" alt="">',
                '<a href="jav&#x09;ascript&colon;alert(1)">x</a>'):
        with pytest.raises(WorkflowError):
            validate_source(PAGE.format(bad))
    for ok in ('<a href="https://bank.example/rates">x</a>', '<a href="mailto:help@bank.example">x</a>', '<a href="tel:+911800">x</a>',
               '<a href="#main">x</a>', '<a href="../rates.html?x=1">x</a>', '<img srcset="a.png 1x, b.png 2x" alt="">',
               '<img src="data:image/png;base64,AAAA" alt="">'):
        validate_source(PAGE.format(ok))
