"""Visual theme: one stylesheet for the whole Streamlit app. Colours meet WCAG AA contrast on their backgrounds."""

from pathlib import Path

LOGO_PATH = Path(__file__).resolve().parent / "logo.svg"
LOGO_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 34 34">'
            '<circle cx="17" cy="17" r="14" fill="none" stroke="#1747b8" stroke-width="3"/>'
            '<path d="M9.5 17.5l5 5 10-11" fill="none" stroke="#0b1f3a" stroke-width="3.2" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')

CSS = """
<style>
:root{--ink:#0f1b2d;--muted:#4a5870;--line:#d5dce8;--navy:#0b1f3a;--navy2:#1b3358;--blue:#1747b8;--blue-dark:#0f379a;
--tint:#eef3fc;--ok:#0e6b3a;--okbg:#e3f5eb;--bad:#9b1c1c;--badbg:#fde8e8;--warn:#7a4b00;--warnbg:#fff1d6;--info:#1b3a6b;--infobg:#e3ecfb}
#MainMenu,footer,[data-testid="stDeployButton"]{visibility:hidden}
.block-container{max-width:1180px;padding-top:2.2rem;padding-bottom:3rem}
h1,h2,h3{letter-spacing:-.015em;color:var(--ink)}
[data-testid="stSidebar"]{border-right:1px solid var(--line)}
[data-testid="stSidebar"] .al-side{background:var(--tint);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:10px;font-size:.88rem;color:var(--ink)}
.al-side b{display:block;margin-bottom:4px}
.al-side .row{display:flex;justify-content:space-between;gap:8px;padding:2px 0}
.stButton>button,.stDownloadButton>button{border-radius:10px;font-weight:650;min-height:2.7rem}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:var(--blue);border-color:var(--blue);color:#fff}
.stButton>button[kind="primary"]:hover{background:var(--blue-dark);border-color:var(--blue-dark)}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px}

.al-hero{background:linear-gradient(135deg,#0b1f3a 0%,#14336b 55%,#1747b8 100%);color:#fff;border-radius:20px;padding:54px 48px 46px;margin-bottom:22px;position:relative;overflow:hidden}
.al-hero:after{content:"";position:absolute;right:-90px;top:-90px;width:340px;height:340px;border-radius:50%;border:48px solid rgba(255,255,255,.07)}
.al-eyebrow{display:inline-block;background:rgba(255,255,255,.14);color:#e6eeff;border-radius:99px;padding:5px 14px;font-size:.84rem;font-weight:600;margin-bottom:18px}
.al-hero h1{color:#fff;font-size:2.6rem;line-height:1.12;margin:0 0 14px;max-width:900px}
.al-hero p{color:#d6e2fb;font-size:1.12rem;max-width:700px;margin:0 0 6px}
.al-trust{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:6px 0 26px}
.al-stat{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.al-stat .n{font-size:2rem;font-weight:780;letter-spacing:-.03em;color:var(--navy)}
.al-stat .l{color:var(--muted);font-size:.9rem}
.al-section{margin:30px 0 10px}
.al-section h2{font-size:1.55rem;margin:0 0 4px}
.al-section p{color:var(--muted);margin:0}
.al-grid{display:grid;gap:14px}
.al-grid.c2{grid-template-columns:repeat(2,1fr)}.al-grid.c3{grid-template-columns:repeat(3,1fr)}.al-grid.c4{grid-template-columns:repeat(4,1fr)}
.al-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px 22px;box-shadow:0 1px 2px rgba(15,27,45,.05)}
.al-card h3{font-size:1.05rem;margin:0 0 6px}
.al-card p{color:var(--muted);margin:0;font-size:.95rem}
.al-ico{width:42px;height:42px;border-radius:11px;background:var(--tint);color:var(--blue);display:grid;place-items:center;font-weight:800;font-size:1.05rem;margin-bottom:12px}
.al-tl{list-style:none;margin:8px 0 16px;padding:0 0 0 18px;border-left:3px solid var(--line)}
.al-tl li{position:relative;margin:0 0 10px;padding:6px 10px;background:#fff;border:1px solid var(--line);border-radius:10px}
.al-tl li::before{content:"";position:absolute;left:-26px;top:14px;width:11px;height:11px;border-radius:50%;background:var(--line)}
.al-tl li.al-tl-commit::before{background:var(--ok)}.al-tl li.al-tl-rollback::before{background:var(--bad)}
.al-tl li.al-tl-escalate::before{background:var(--warn)}.al-tl li.al-tl-perceive::before,.al-tl li.al-tl-stop::before{background:var(--info)}
.al-tl code{font-size:.8rem}.al-tl-n{float:right;font-size:.8rem;color:#3b475c;font-weight:700}.al-tl-d{font-size:.85rem;color:#3b475c;margin-top:2px}
.al-h2{font-size:1.3rem;font-weight:700;color:var(--ink);margin:22px 0 8px;padding:0;line-height:1.3}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#4a5568 !important;opacity:1 !important}
.al-navsec{font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#4a5568;margin:14px 0 2px 4px}
.al-term{background:#0d1117;color:#d6deeb;border-radius:12px;padding:0 0 10px;font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;max-height:460px;overflow:auto;border:1px solid #30363d;margin:6px 0 14px}
.al-term-h{background:#161b22;color:#9aa4b2;padding:7px 12px;border-bottom:1px solid #30363d;border-radius:12px 12px 0 0;margin-bottom:6px;position:sticky;top:0}
.al-term-h span{display:inline-block;width:10px;height:10px;border-radius:50%;background:#ff5f56;margin-right:5px}
.al-term-h span:nth-child(2){background:#ffbd2e}.al-term-h span:nth-child(3){background:#27c93f;margin-right:10px}
.al-term-l{padding:0 12px;white-space:pre-wrap;word-break:break-word}.al-term-l .t{color:#8b949e}.al-term-l .p{display:inline-block;min-width:66px;color:#79c0ff;font-weight:700}
.al-term-l.ok .p{color:#56d364}.al-term-l.bad .p{color:#ff7b72}.al-term-l.warn .p{color:#e3b341}.al-term-l.dim{color:#9aa4b2}
.al-term .cur{color:#56d364;animation:al-blink 1s steps(1) infinite}@keyframes al-blink{50%{opacity:0}}
@media (prefers-reduced-motion:reduce){.al-term .cur{animation:none}}
.al-code{font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#f6f8fb;border:1px solid var(--line);border-radius:10px;padding:8px 0;max-height:360px;overflow:auto;margin:6px 0 10px}
.al-code div{white-space:pre;padding:0 12px 0 0;color:#1f2a3d}.al-code .ln{display:inline-block;width:64px;color:#4a5568;user-select:none}
.al-code div.chg{background:#fff4d6;font-weight:600}.al-code div.chg .ln{color:#7a4b00}
.al-crumbs{font-size:.85rem;color:#3b475c;margin:2px 0 6px}
.al-notice{border-radius:10px;padding:12px 16px;margin:6px 0 12px;line-height:1.5}
.al-notice.warn{background:#fff4d6;color:#3d2a00;border:1px solid #d9a63a}
.al-notice.info{background:#e8f0fd;color:#13294b;border:1px solid #9db8e8}
.al-note{background:#fff;border-left:4px solid var(--blue);border-radius:8px;padding:12px 16px;color:var(--ink);margin:10px 0}
.al-foot{color:var(--muted);font-size:.85rem;margin-top:28px;border-top:1px solid var(--line);padding-top:14px}

.al-head{margin-bottom:18px}
.al-head .eyebrow{color:var(--blue-dark);font-weight:700;font-size:.84rem;letter-spacing:.04em;text-transform:uppercase}
.al-head h1{font-size:2rem;margin:2px 0 4px}
.al-head p{color:var(--muted);margin:0;max-width:760px}
.al-steps{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px;padding:0;list-style:none}
.al-steps li{display:flex;align-items:center;gap:8px;padding:5px 12px 5px 6px;border-radius:99px;color:var(--muted);font-size:.88rem;font-weight:600;background:#fff;border:1px solid var(--line)}
.al-steps .n{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:.76rem;border:2px solid #6b7a94;color:var(--muted)}
.al-steps li.done{color:var(--ok)}.al-steps li.done .n{background:var(--ok);border-color:var(--ok);color:#fff}
.al-steps li.cur{background:var(--tint);color:var(--blue-dark);border-color:var(--blue)}.al-steps li.cur .n{background:var(--blue);border-color:var(--blue);color:#fff}
.al-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:8px 0 14px}
.al-metric{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.al-metric .v{font-size:1.9rem;font-weight:780;letter-spacing:-.03em}
.al-metric .l{color:var(--muted);font-size:.86rem}
.al-metric.good .v{color:var(--ok)}.al-metric.bad .v{color:var(--bad)}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.78rem;font-weight:700;border:1px solid var(--line);background:#fff;color:var(--ink);margin-right:6px}
.badge.critical,.badge.bad{background:var(--badbg);color:var(--bad);border-color:#f1b5b5}
.badge.serious,.badge.warn{background:var(--warnbg);color:var(--warn);border-color:#ecc986}
.badge.moderate,.badge.info{background:var(--infobg);color:var(--info);border-color:#b9cbef}
.badge.minor,.badge.neutral{background:#eef0f4;color:#3b475c}
.badge.ok{background:var(--okbg);color:var(--ok);border-color:#a9dcc0}
.al-diff{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:.85rem;border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:8px 0}
.al-diff div{padding:5px 12px;white-space:pre-wrap;word-break:break-word}
.al-diff .add{background:var(--okbg);color:#0b4d29}.al-diff .del{background:var(--badbg);color:#7a1515}
.al-diff .ctx{background:#f6f8fb;color:#33405a}.al-diff .meta{background:#eaeff8;color:#4a5870}
.al-banner{border-radius:12px;padding:14px 18px;margin:6px 0 16px;font-weight:550}
.al-banner.verified{background:var(--okbg);color:#0b4d29;border:1px solid #a9dcc0}
.al-banner.rejected{background:var(--infobg);color:var(--info);border:1px solid #b9cbef}
.al-banner.rolled_back{background:var(--badbg);color:#7a1515;border:1px solid #f1b5b5}
@media (max-width:900px){.al-trust,.al-grid.c4{grid-template-columns:repeat(2,1fr)}.al-grid.c3,.al-grid.c2{grid-template-columns:1fr}.al-hero{padding:34px 24px}.al-hero h1{font-size:2rem}}
@media (max-width:520px){.al-trust,.al-grid.c4{grid-template-columns:1fr}}
</style>
"""
