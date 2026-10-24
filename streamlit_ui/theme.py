"""Visual theme: one stylesheet for the whole Streamlit app. Colours meet WCAG AA contrast on their backgrounds."""

from pathlib import Path

LOGO_PATH = Path(__file__).resolve().parent / "logo.svg"
LOGO_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 34 34">'
            '<circle cx="17" cy="17" r="14" fill="none" stroke="#244dc5" stroke-width="3"/>'
            '<path d="M9.5 17.5l5 5 10-11" fill="none" stroke="#132843" stroke-width="3.2" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')

CSS = """
<style>
/* ---- AccessLoop design system: editorial minimalism. Neutral surfaces, thin borders, colour only for actions and
   status. Every text colour below is at least 4.5:1 on its background (checked by python -m accessloop.selfcheck). */
:root{
--canvas:#f6f7f9;--surface:#ffffff;--ink:#18202b;--ink2:#2b3442;--muted:#5b6370;--line:#e4e7ec;--line2:#d3d8e0;
--navy:#132843;--navy2:#1d3a62;--blue:#244dc5;--blue-dark:#1c3d9e;--tint:#eef2fd;
--ok:#14683b;--okbg:#e8f5ee;--bad:#a12626;--badbg:#fbeceb;--warn:#7a4a00;--warnbg:#fdf3e1;--info:#1f3d7a;--infobg:#edf2fc;
--serif:"Iowan Old Style","Charter","Source Serif Pro","Source Serif 4",Georgia,"Times New Roman",serif;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
--r:14px;--r-sm:10px;--ease:cubic-bezier(.2,.7,.2,1)}
#MainMenu,footer,[data-testid="stDeployButton"]{visibility:hidden}
[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1240px;padding-top:2.4rem;padding-bottom:3rem}
h1,h2,h3{color:var(--ink);letter-spacing:-.01em}
.al-hero h1,.al-head h1,.al-h2,.al-panel h2,.al-panel h3,.al-card h3,.al-section h2,.al-panel .big,.al-strip .n,.al-metric .v,.al-stat .n,.al-brand .w{font-family:var(--serif)!important;font-weight:400!important}
.al-panel .big b{font-weight:600!important}
.stButton>button[kind="primary"] p,.stDownloadButton>button[kind="primary"] p,.stFormSubmitButton>button[kind="primary"] p{color:#fff!important}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"]{height:auto;min-height:2.2rem}
code{font-family:var(--mono)}
[data-testid="stMarkdownContainer"],[data-testid="stCaptionContainer"],.al-rows .sub,.al-crumbs,.al-note{overflow-wrap:anywhere}

/* ---- sidebar: white, narrow, quiet ---- */
[data-testid="stSidebar"]{background:var(--surface);border-right:1px solid var(--line)}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:.4rem}
.al-brand{display:flex;align-items:center;gap:10px;padding:2px 4px 14px;margin-bottom:6px;border-bottom:1px solid var(--line)}
.al-brand .w{font-family:var(--serif);font-size:1.45rem;color:var(--ink);letter-spacing:-.01em;line-height:1}
.al-brand .s{display:block;font-size:.72rem;color:var(--muted);letter-spacing:.04em;margin-top:4px}
.al-navsec{font-size:.68rem;font-weight:650;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin:16px 0 4px 6px}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]{border-radius:8px;padding:4px 8px;transition:background .18s var(--ease),color .18s var(--ease)}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover{background:#f1f3f6}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p{font-size:.92rem;color:var(--ink2)}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] span[data-testid="stIconMaterial"]{color:var(--muted);font-size:1.15rem}
[data-testid="stSidebar"] .al-side{background:var(--canvas);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px 14px;margin-top:14px;font-size:.86rem;color:var(--ink)}
.al-side b{display:block;margin-bottom:6px;font-weight:600}
.al-side .row{display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-top:1px solid var(--line)}
.al-side .row span:first-child{color:var(--muted)}

/* ---- controls ---- */
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:var(--r-sm);font-weight:600;min-height:2.6rem;
 border:1px solid var(--line2);background:var(--surface);color:var(--ink);transition:background .18s var(--ease),border-color .18s var(--ease),box-shadow .18s var(--ease),transform .08s}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:#aeb6c3;background:#fafbfc;color:var(--ink)}
.stButton>button:active,.stDownloadButton>button:active{transform:translateY(1px)}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:var(--navy);border-color:var(--navy);color:#fff}
.stButton>button[kind="primary"]:hover,.stDownloadButton>button[kind="primary"]:hover{background:var(--navy2);border-color:var(--navy2);color:#fff}
.stButton>button:disabled{background:#eef0f3;color:#5b6370;border-color:var(--line)}
button:focus-visible,a:focus-visible,[tabindex]:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--blue)!important;outline-offset:2px}
a[data-testid="stPageLink-NavLink"]{transition:background .18s var(--ease)}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:var(--r);border-color:var(--line)!important;background:var(--surface)}
[data-testid="stExpander"] details{border-radius:var(--r-sm);border-color:var(--line);background:var(--surface)}
[data-testid="stExpander"] summary:hover{background:#fafbfc}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:var(--r-sm)}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--muted)!important;opacity:1!important}

/* ---- page header ---- */
.al-head{margin:0 0 22px}
.al-head .eyebrow{color:var(--muted);font-weight:600;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase}
.al-head h1{padding:0!important;font-size:2.55rem;line-height:1.1;margin:6px 0 8px;letter-spacing:-.015em}
.al-head p{color:var(--muted);margin:0;max-width:760px;font-size:1.02rem;line-height:1.55}
.al-steps{display:flex;gap:0;flex-wrap:wrap;margin:0 0 26px;padding:0;list-style:none;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--surface);width:max-content;max-width:100%;overflow:hidden}
.al-steps li{display:flex;align-items:center;gap:8px;padding:8px 16px;color:var(--muted);font-size:.85rem;font-weight:550;border-right:1px solid var(--line)}
.al-steps li:last-child{border-right:0}
.al-steps .n{width:20px;height:20px;border-radius:50%;display:grid;place-items:center;font-size:.72rem;border:1px solid var(--line2);color:var(--muted)}
.al-steps li.done{color:var(--ok)}.al-steps li.done .n{background:var(--okbg);border-color:#9fd2b5;color:var(--ok)}
.al-steps li.cur{background:var(--tint);color:var(--blue-dark)}.al-steps li.cur .n{background:var(--blue);border-color:var(--blue);color:#fff}
.al-h2{font-family:var(--serif);font-weight:400;font-size:1.55rem;color:var(--ink);margin:30px 0 10px;padding:0;line-height:1.25}

/* ---- metrics: one surface, fine vertical rules ---- */
.al-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:8px 0 18px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.al-metric{padding:18px 22px;border-right:1px solid var(--line)}
.al-metric:last-child{border-right:0}
.al-metric .v{font-family:var(--serif);font-size:2.1rem;line-height:1.1;color:var(--ink);letter-spacing:-.02em}
.al-metric .l{color:var(--muted);font-size:.82rem;margin-top:4px}
.al-metric .v.long{font-size:1.3rem;line-height:1.3;overflow-wrap:anywhere}.al-metric.good .v{color:var(--ok)}.al-metric.bad .v{color:var(--bad)}

/* ---- status labels (text always says the status; colour only supports it) ---- */
.badge{display:inline-block;padding:2px 9px;border-radius:6px;font-size:.75rem;font-weight:600;border:1px solid var(--line);background:var(--surface);color:var(--ink2);margin-right:6px;letter-spacing:.01em}
.badge.critical,.badge.bad{background:var(--badbg);color:var(--bad);border-color:#efc4c1}
.badge.serious,.badge.warn{background:var(--warnbg);color:var(--warn);border-color:#ecd09c}
.badge.moderate,.badge.info{background:var(--infobg);color:var(--info);border-color:#c5d3f1}
.badge.minor,.badge.neutral{background:#f1f3f6;color:#3d4552}
.badge.ok{background:var(--okbg);color:var(--ok);border-color:#a9d6bc}

/* ---- code and diffs: neutral panel, restrained add/remove ---- */
.al-diff{font-family:var(--mono);font-size:.84rem;border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden;margin:10px 0;background:#fbfbfc}
.al-diff div{padding:5px 14px;white-space:pre-wrap;word-break:break-word}
.al-diff .add{background:#eaf6ef;color:#0f5530}.al-diff .del{background:#fbeeee;color:#8a1c1c}
.al-diff .ctx{background:#fbfbfc;color:#3d4552}.al-diff .meta{background:#f1f3f6;color:var(--muted)}
.al-code{font:12.5px/1.55 var(--mono);background:#fbfbfc;border:1px solid var(--line);border-radius:var(--r-sm);padding:8px 0;max-height:360px;overflow:auto;margin:6px 0 10px}
.al-code div{white-space:pre;padding:0 12px 0 0;color:#232b38}.al-code .ln{display:inline-block;width:64px;color:var(--muted);user-select:none}
.al-code div.chg{background:#fdf3e1;font-weight:600}.al-code div.chg .ln{color:#7a4a00}
.al-crumbs{font-size:.84rem;color:var(--muted);margin:2px 0 8px}

/* ---- notices and banners ---- */
.al-notice{border-radius:var(--r-sm);padding:12px 16px;margin:6px 0 14px;line-height:1.5}
.al-notice.warn{background:var(--warnbg);color:#3d2a00;border:1px solid #e3c27e}
.al-notice.info{background:var(--infobg);color:#13294b;border:1px solid #c5d3f1}
.al-note{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px 16px;color:var(--ink2);margin:10px 0;font-size:.92rem}
.al-banner{border-radius:var(--r-sm);padding:14px 18px;margin:6px 0 16px;font-weight:550}
.al-banner.verified{background:var(--okbg);color:#0f5530;border:1px solid #a9d6bc}
.al-banner.rejected{background:var(--infobg);color:var(--info);border:1px solid #c5d3f1}
.al-banner.rolled_back{background:var(--badbg);color:#7c1717;border:1px solid #efc4c1}
.al-foot{color:var(--muted);font-size:.82rem;margin-top:40px;border-top:1px solid var(--line);padding-top:16px}

/* ---- home: editorial hero, metric strip, asymmetric grid ---- */
.al-hero{padding:34px 0 30px;margin:0 0 6px}
.al-kicker{font-size:.72rem;font-weight:650;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:18px}
.al-hero h1{padding:0!important;font-size:3.6rem;line-height:1.04;letter-spacing:-.025em;color:var(--ink);margin:0 0 18px;max-width:900px}
.al-hero h1 em{font-style:normal;color:var(--muted)}
.al-hero p{color:var(--muted);font-size:1.12rem;line-height:1.6;max-width:640px;margin:0}
.al-strip{display:grid;grid-template-columns:repeat(4,1fr);background:var(--surface);border:1px solid var(--line);border-radius:var(--r);margin:26px 0 22px;overflow:hidden}
.al-strip>div{padding:22px 26px;border-right:1px solid var(--line)}
.al-strip>div:last-child{border-right:0}
.al-strip .n{font-family:var(--serif);font-size:2.6rem;line-height:1;color:var(--ink);letter-spacing:-.02em}
.al-strip .l{color:var(--muted);font-size:.84rem;margin-top:8px;line-height:1.4}
.al-board{display:grid;grid-template-columns:1.55fr 1fr;gap:18px;margin:0 0 18px}
.al-board.b3{grid-template-columns:1fr 1fr 1fr}
.al-panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:24px 26px;transition:border-color .2s var(--ease)}
.al-panel:hover{border-color:var(--line2)}
.al-panel .cap{font-size:.72rem;font-weight:650;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
.al-panel h2,.al-panel h3{font-family:var(--serif);font-weight:400;color:var(--ink);margin:0 0 10px;line-height:1.25}
.al-panel h2{font-size:1.75rem}.al-panel h2.sm{font-size:1.3rem}.al-panel h3{font-size:1.3rem}
.al-panel p{color:var(--muted);margin:0;font-size:.95rem;line-height:1.55}
.al-panel .big{font-family:var(--serif);font-size:1.6rem;line-height:1.35;color:var(--ink);margin:2px 0 14px}
.al-panel .big b{font-weight:600}
.al-flow{list-style:none;margin:6px 0 0;padding:0}
.al-flow li{display:grid;grid-template-columns:30px 1fr;gap:12px;padding:10px 0;border-top:1px solid var(--line);align-items:start}
.al-flow li:first-child{border-top:0}
.al-flow .dot{width:26px;height:26px;border-radius:50%;border:1px solid var(--line2);display:grid;place-items:center;font-size:.75rem;color:var(--muted);background:var(--surface)}
.al-flow li.done .dot{background:var(--okbg);border-color:#a9d6bc;color:var(--ok)}
.al-flow li.cur .dot{background:var(--navy);border-color:var(--navy);color:#fff}
.al-flow b{display:block;color:var(--ink);font-weight:600;font-size:.95rem}
.al-flow span.d{color:var(--muted);font-size:.86rem}
.al-flow .st{font-size:.75rem;font-weight:600;color:var(--blue-dark);margin-left:8px}.al-flow .st.ok{color:var(--ok)}
.al-rows{list-style:none;margin:4px 0 0;padding:0}
.al-rows li{display:flex;justify-content:space-between;gap:14px;padding:11px 0;border-top:1px solid var(--line);font-size:.9rem}
.al-rows li:first-child{border-top:0}
.al-rows .txt{flex:1;min-width:0}.al-rows .what{color:var(--ink);font-weight:550}.al-rows .sub{display:block;color:var(--muted);font-size:.8rem;font-weight:400;margin-top:2px}
.al-rows .when{color:var(--muted);font-size:.8rem;white-space:nowrap;text-align:right}
.al-bar{height:6px;border-radius:99px;background:#eceff3;overflow:hidden;margin:8px 0 4px}
.al-bar span{display:block;height:100%;background:var(--navy)}

/* ---- older blocks still used on some pages ---- */
.al-section{margin:34px 0 12px}.al-section h2{font-family:var(--serif);font-weight:400;font-size:1.7rem;margin:0 0 4px}.al-section p{color:var(--muted);margin:0}
.al-grid{display:grid;gap:16px}.al-grid.c2{grid-template-columns:repeat(2,1fr)}.al-grid.c3{grid-template-columns:repeat(3,1fr)}.al-grid.c4{grid-template-columns:repeat(4,1fr)}
.al-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:22px 24px;transition:border-color .2s var(--ease)}
.al-card:hover{border-color:var(--line2)}
.al-card h3{font-family:var(--serif);font-weight:400;font-size:1.25rem;margin:0 0 8px}
.al-card p{color:var(--muted);margin:0;font-size:.93rem;line-height:1.55}
.al-ico{width:30px;height:30px;border-radius:50%;border:1px solid var(--line2);color:var(--ink);display:grid;place-items:center;font-size:.8rem;margin-bottom:14px}
.al-trust{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin:6px 0 26px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.al-stat{padding:18px 22px;border-right:1px solid var(--line)}.al-stat:last-child{border-right:0}
.al-stat .n{font-family:var(--serif);font-size:2rem;color:var(--ink)}.al-stat .l{color:var(--muted);font-size:.86rem}

/* ---- agent timeline and console ---- */
.al-tl{list-style:none;margin:8px 0 16px;padding:0 0 0 18px;border-left:1px solid var(--line2)}
.al-tl li{position:relative;margin:0 0 8px;padding:8px 12px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm)}
.al-tl li::before{content:"";position:absolute;left:-24px;top:15px;width:11px;height:11px;border-radius:50%;background:var(--line2);border:2px solid var(--canvas)}
.al-tl li.al-tl-commit::before{background:var(--ok)}.al-tl li.al-tl-rollback::before{background:var(--bad)}
.al-tl li.al-tl-escalate::before{background:#b07400}.al-tl li.al-tl-perceive::before,.al-tl li.al-tl-stop::before{background:var(--info)}
.al-tl code{font-size:.8rem}.al-tl-n{float:right;font-size:.8rem;color:#3d4552;font-weight:600}.al-tl-d{font-size:.85rem;color:#3d4552;margin-top:2px}
.al-term{background:#111720;color:#d6deeb;border-radius:var(--r);padding:0 0 10px;font:12.5px/1.6 var(--mono);max-height:460px;overflow:auto;border:1px solid #232c38;margin:6px 0 14px}
.al-term-h{background:#161d27;color:#9aa4b2;padding:8px 14px;border-bottom:1px solid #232c38;border-radius:var(--r) var(--r) 0 0;margin-bottom:6px;position:sticky;top:0}
.al-term-h span{display:inline-block;width:9px;height:9px;border-radius:50%;background:#3a4452;margin-right:5px}
.al-term-l{padding:0 14px;white-space:pre-wrap;word-break:break-word}.al-term-l .t{color:#8b949e}.al-term-l .p{display:inline-block;min-width:66px;color:#8fb8ff;font-weight:600}
.al-term-l.ok .p{color:#6fd38a}.al-term-l.bad .p{color:#ff8a80}.al-term-l.warn .p{color:#e8c06a}.al-term-l.dim{color:#9aa4b2}
.al-term .cur{color:#6fd38a;animation:al-blink 1s steps(1) infinite}@keyframes al-blink{50%{opacity:0}}


/* ---- data visuals: severity bars, checklist progress ---- */
.al-sevbox{margin:8px 0 18px}
.al-sevbox .key{float:right;text-transform:none;letter-spacing:0;font-weight:500;color:var(--muted)}
.al-sevbox .key i{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 5px 0 12px;vertical-align:-1px}
.al-sevbox .key i.k0,.al-sev .b0{background:#cfd5de}.al-sevbox .key i.k1,.al-sev .b1{background:var(--navy)}
.al-sev{display:grid;grid-template-columns:110px 1fr 130px;gap:16px;align-items:center;padding:9px 0;border-top:1px solid var(--line)}
.al-sev:first-of-type{border-top:0}
.al-sev .bars div{height:8px;border-radius:99px;margin:3px 0;min-width:2px;transition:width .5s var(--ease)}
.al-sev .nums{text-align:right;font-size:.88rem}.al-sev .nums b{font-family:var(--serif);font-weight:400;font-size:1.1rem;color:var(--ink);display:block}
.al-sev .nums span{color:var(--muted);font-size:.8rem}
.al-cl{grid-template-columns:1fr 1.2fr}
.al-ringbox{display:flex;gap:24px;align-items:center}.al-ringbox svg{flex:none;width:132px;height:132px}
.al-ring{transition:stroke-dasharray .6s var(--ease)}
.al-pbar{padding:8px 0;border-top:1px solid var(--line)}.al-pbar:first-of-type{border-top:0}
.al-pbar .top{display:flex;justify-content:space-between;font-size:.9rem}.al-pbar .top b{color:var(--ink);font-weight:600}.al-pbar .top span{color:var(--muted)}
.al-pbar p{font-size:.8rem!important;margin:0!important}
.al-focus{margin:6px 0 12px;background:linear-gradient(180deg,#fff,#fbfcfd)}
.al-focus h2{font-size:2rem!important}
.al-step{border:1px solid var(--line);border-radius:var(--r-sm);padding:12px 16px;margin:0 0 10px;background:var(--surface);color:var(--ink2);line-height:1.55}
.al-step.ok{background:#f6fbf8;border-color:#cfe8da}
.al-step .lbl{display:block;font-size:.7rem;font-weight:650;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:3px}
@media (max-width:700px){.al-sev{grid-template-columns:90px 1fr 90px;gap:10px}.al-ringbox{flex-direction:column;align-items:flex-start}}

/* ---- motion: hover/focus transitions only (no entrance animation: content is fully visible from the first paint) ---- */
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}

/* ---- responsive ---- */
@media (max-width:1024px){.al-board,.al-board.b3{grid-template-columns:1fr}.al-hero h1{font-size:2.9rem}}
@media (max-width:900px){.al-strip,.al-trust,.al-grid.c4{grid-template-columns:repeat(2,1fr)}.al-strip>div:nth-child(2),.al-stat:nth-child(2){border-right:0}
 .al-strip>div:nth-child(-n+2){border-bottom:1px solid var(--line)}.al-grid.c3,.al-grid.c2{grid-template-columns:1fr}}
@media (max-width:560px){.al-strip,.al-trust,.al-grid.c4{grid-template-columns:1fr}.al-strip>div{border-right:0;border-bottom:1px solid var(--line)}
 .al-hero h1{font-size:2.2rem}.al-head h1{font-size:2rem}.al-steps{width:auto}.al-steps li{padding:6px 10px}.al-panel{padding:18px}}
</style>
"""
