#!/usr/bin/env python3
"""Directive 17 static site builder.

Zero dependencies. Reads content/ and writes the finished site into docs/
(which GitHub Pages serves). Run:  python3 build.py

Content lives in:
  content/site.json        - all page copy: nav, pillars, why/philosophy/future/build pages
  content/companies.json   - portfolio companies (name, group, logo, one_liner, url)
  content/pages/*.md       - long-form pages (Joel's Directive)
  content/posts/*.md       - blog posts, filename: YYYY-MM-DD-slug.md with frontmatter
  content/images/          - logos and images (copied to the site as-is)
"""
import json, re, shutil, html
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs"

site = json.loads((CONTENT / "site.json").read_text())
companies = json.loads((CONTENT / "companies.json").read_text())

# ---------------------------------------------------------------- markdown
def md_inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s

def md_to_html(text):
    out, para, lst = [], [], None
    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para = []
    def flush_list():
        nonlocal lst
        if lst:
            tag = lst["tag"]
            items = "".join(f"<li>{md_inline(i)}</li>" for i in lst["items"])
            out.append(f"<{tag}>{items}</{tag}>")
            lst = None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush_para(); flush_list(); continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush_para(); flush_list()
            n = len(m.group(1))
            out.append(f"<h{n}>{md_inline(m.group(2))}</h{n}>")
            continue
        if s == "---":
            flush_para(); flush_list(); out.append("<hr>"); continue
        if s.startswith(">"):
            flush_para(); flush_list()
            out.append(f"<blockquote><p>{md_inline(s[1:].strip())}</p></blockquote>")
            continue
        m = re.match(r"^[-*]\s+(.*)", s)
        if m:
            flush_para()
            if not lst or lst["tag"] != "ul": flush_list(); lst = {"tag": "ul", "items": []}
            lst["items"].append(m.group(1)); continue
        m = re.match(r"^\d+\.\s+(.*)", s)
        if m:
            flush_para()
            if not lst or lst["tag"] != "ol": flush_list(); lst = {"tag": "ol", "items": []}
            lst["items"].append(m.group(1)); continue
        para.append(s)
    flush_para(); flush_list()
    return "\n".join(out)

def parse_post(path):
    raw = path.read_text()
    meta = {}
    body = raw
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        for ln in fm.strip().splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip()
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
    return {
        "title": meta.get("title", slug.replace("-", " ").title()),
        "date": meta.get("date", ""),
        "excerpt": meta.get("excerpt", ""),
        "slug": slug,
        "html": md_to_html(body.strip()),
    }

def fmt_date(d):
    try:
        from datetime import date
        y, m, dd = map(int, d.split("-"))
        return date(y, m, dd).strftime("%B %-d, %Y")
    except Exception:
        return d

# ---------------------------------------------------------------- css
CSS = """
:root{--bg:#FBF7EC;--panel:#F4EEDD;--ink:#23392C;--deep:#203C2D;--muted:#71806B;
--line:#E6DEC7;--ghost:#EDE5CE;--accent:#D98B33;
--serif:'Source Serif 4',Georgia,'Times New Roman',serif;
--sans:'Helvetica Neue',Helvetica,Arial,sans-serif;
--ease:cubic-bezier(.22,.61,.21,1)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--serif);font-size:17.5px;
line-height:1.7;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit;text-decoration:none}
img{max-width:100%}
::selection{background:var(--deep);color:var(--bg)}
a:focus-visible,button:focus-visible,[role=button]:focus-visible{
outline:2px solid var(--accent);outline-offset:3px;border-radius:2px}
/* reading progress */
.progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent);
z-index:120;transition:width .1s linear}
.wrap{max-width:1500px;margin:0 auto;padding:0 clamp(28px,5vw,76px)}
/* film grain */
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:90;opacity:.045;
background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E")}
/* ---------- header ---------- */
header{position:sticky;top:0;z-index:10;background:rgba(251,247,236,.9);
backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.nav{display:flex;align-items:center;justify-content:space-between;gap:16px;height:74px}
.logo{display:flex;align-items:center;gap:12px;font-family:var(--serif);font-weight:700;
font-size:1.2rem;color:var(--deep)}
.logo img{height:38px;width:38px;object-fit:contain;transition:transform .6s var(--ease)}
.logo:hover img{transform:rotate(180deg)}
.menu-btn{display:flex;flex-direction:column;gap:6px;background:none;border:none;
cursor:pointer;padding:12px 4px}
.menu-btn span{display:block;width:28px;height:2px;background:var(--deep);border-radius:2px;
transition:transform .3s var(--ease),width .3s var(--ease)}
.menu-btn:hover span:nth-child(1){width:20px}
.menu-btn:hover span:nth-child(3){width:24px}
/* ---------- menu overlay ---------- */
.menu-overlay{position:fixed;inset:0;background:var(--deep);z-index:100;
display:flex;flex-direction:column;justify-content:center;padding:0 max(9vw,36px);
visibility:hidden;opacity:0;transition:opacity .4s var(--ease),visibility .4s}
.menu-overlay.open{visibility:visible;opacity:1}
.menu-overlay .m-label{font-family:var(--sans);font-size:.72rem;font-weight:700;
text-transform:uppercase;letter-spacing:.22em;color:var(--accent);margin-bottom:30px}
.menu-overlay a.m-link{font-family:var(--serif);font-size:clamp(1.5rem,4.2vw,2.5rem);
color:#F5F1E2;padding:10px 0;letter-spacing:-.01em;line-height:1.2;width:fit-content;
position:relative;opacity:0;transform:translateY(26px);
transition:opacity .5s var(--ease),transform .5s var(--ease),color .2s}
.menu-overlay.open a.m-link{opacity:1;transform:none;transition-delay:calc(.06s*var(--i))}
.menu-overlay a.m-link::after{content:"";position:absolute;left:0;bottom:6px;height:1px;
width:0;background:var(--accent);transition:width .35s var(--ease)}
.menu-overlay a.m-link:hover{color:var(--accent)}
.menu-overlay a.m-link:hover::after{width:100%}
.menu-overlay a.m-link.active{color:var(--accent)}
.m-foot{position:absolute;bottom:34px;left:max(9vw,36px);font-family:var(--sans);
font-size:.78rem;letter-spacing:.06em;color:#8FA08A}
.m-foot a{color:#D8DDCF}.m-foot a:hover{color:var(--accent)}
.menu-close{position:absolute;top:24px;right:max(9vw,36px);background:none;border:none;
cursor:pointer;color:#F5F1E2;font-size:2.3rem;line-height:1;font-family:var(--serif);
transition:transform .4s var(--ease),color .2s}
.menu-close:hover{color:var(--accent);transform:rotate(90deg)}
/* ---------- load + scroll animations ---------- */
@keyframes wordUp{to{opacity:1;transform:none}}
.w{display:inline-block;opacity:0;transform:translateY(.55em);
animation:wordUp .75s var(--ease) forwards;animation-delay:var(--d,0s)}
@keyframes fadeUp{to{opacity:1;transform:none}}
.fade{opacity:0;transform:translateY(22px);animation:fadeUp .8s var(--ease) forwards;
animation-delay:var(--d,0s)}
.js .reveal{opacity:0;transform:translateY(30px);
transition:opacity .8s var(--ease),transform .8s var(--ease);transition-delay:var(--d,0s)}
.js .reveal.in{opacity:1;transform:none}
@keyframes ensoIn{from{opacity:0;transform:scale(.9) rotate(-10deg)}to{opacity:1;transform:none}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-14px)}}
.hero-enso img{opacity:0;animation:ensoIn 1.1s var(--ease) .45s forwards}
.hero-enso.floaty img{animation:ensoIn 1.1s var(--ease) .45s forwards,
float 7s ease-in-out 1.8s infinite}
@media(prefers-reduced-motion:reduce){
.w,.fade,.hero-enso img{animation:none!important;opacity:1!important;transform:none!important}
.js .reveal{opacity:1;transform:none;transition:none}
*{scroll-behavior:auto!important}}
/* ---------- hero ---------- */
.hero{padding:110px 0 90px}
.hero-home{min-height:calc(100vh - 75px);display:flex;align-items:center;padding:40px 0 110px;
position:relative}
/* intro curtain (homepage, once per session) */
#intro{position:fixed;inset:0;background:var(--deep);z-index:200;display:flex;
align-items:center;justify-content:center;animation:introLift .9s var(--ease) 2s forwards}
@keyframes introLift{to{transform:translateY(-101%)}}
#intro .intro-inner{text-align:center}
#intro img{width:clamp(90px,12vw,140px);opacity:0;
animation:introEnso 1.25s var(--ease) .15s forwards}
@keyframes introEnso{from{opacity:0;transform:scale(.5) rotate(-170deg)}
to{opacity:1;transform:none}}
#intro .intro-name{font-family:var(--sans);font-size:.78rem;font-weight:700;
text-transform:uppercase;color:#F5F1E2;margin-top:26px;opacity:0;letter-spacing:.6em;
animation:introName 1s var(--ease) .55s forwards}
@keyframes introName{from{opacity:0;letter-spacing:.6em}to{opacity:1;letter-spacing:.3em}}
.skip-intro #intro{display:none}
.skip-intro body{--hd:0s!important}
.hero-home .w{animation-delay:calc(var(--d) + var(--hd,0s))}
.hero-home .fade{animation-delay:calc(var(--d) + var(--hd,0s))}
.hero-home .hero-enso img{animation-delay:calc(.45s + var(--hd,0s))}
.hero-home .hero-enso.floaty img{animation-delay:calc(.45s + var(--hd,0s)),calc(1.8s + var(--hd,0s))}
/* pillar ticker (homepage) */
.ticker{position:absolute;bottom:0;left:0;right:0;overflow:hidden;
border-top:1px solid var(--line);padding:22px 0;opacity:0;
animation:fadeUp .9s var(--ease) forwards;animation-delay:calc(1.3s + var(--hd,0s))}
.ticker-track{display:flex;align-items:center;gap:64px;width:max-content;
animation:tickerScroll 30s linear infinite}
@keyframes tickerScroll{to{transform:translateX(calc(-100%/3))}}
.ticker span{font-family:var(--sans);font-size:.74rem;font-weight:600;white-space:nowrap;
text-transform:uppercase;letter-spacing:.22em;color:var(--muted)}
.ticker .tsep{color:var(--accent);font-size:.9rem;letter-spacing:0}
@media(prefers-reduced-motion:reduce){#intro{display:none}
.ticker-track{animation:none}.ticker{animation:none;opacity:1}}
.hero-flex{display:flex;align-items:center;gap:64px;justify-content:space-between;width:100%}
.hero-enso{flex:0 0 auto;width:min(320px,30vw)}
.kicker{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.24em;color:var(--accent);margin-bottom:26px;display:flex;align-items:center;gap:16px}
h1.display{font-family:var(--serif);font-weight:700;letter-spacing:-.02em;
font-size:clamp(2.9rem,7vw,6.4rem);line-height:1.04;max-width:16ch;color:var(--deep)}
.sub{color:var(--muted);font-size:clamp(1.15rem,1.6vw,1.45rem);max-width:46ch;margin-top:30px}
/* ---------- editorial building blocks ---------- */
section{padding:90px 0}
.rule{border:none;border-top:1px solid var(--line)}

/* scroll cue on homepage hero */
.scrollcue{position:absolute;left:0;right:0;margin:0 auto;width:max-content;bottom:86px;
display:flex;flex-direction:column;align-items:center;gap:10px;background:none;border:none;
cursor:pointer;opacity:0;animation:fadeUp .9s var(--ease) forwards;
animation-delay:calc(1.55s + var(--hd,0s))}
.scrollcue .sc-label{font-family:var(--sans);font-size:.68rem;font-weight:700;
text-transform:uppercase;letter-spacing:.22em;color:var(--muted);transition:color .2s}
.scrollcue:hover .sc-label{color:var(--accent)}
.scrollcue .sc-arrow{width:34px;height:34px;border:1px solid var(--line);border-radius:50%;
display:flex;align-items:center;justify-content:center;color:var(--accent);font-size:.95rem;
animation:nudge 1.9s var(--ease) infinite;transition:border-color .2s}
.scrollcue:hover .sc-arrow{border-color:var(--accent)}
@keyframes nudge{0%,100%{transform:translateY(0)}50%{transform:translateY(6px)}}
@media(prefers-reduced-motion:reduce){.scrollcue .sc-arrow{animation:none}}
@media(max-width:860px){.scrollcue{bottom:74px;gap:8px}
.scrollcue .sc-label{font-size:.6rem;letter-spacing:.16em;white-space:nowrap}
.scrollcue .sc-arrow{width:30px;height:30px}}
/* founder note framing */
.note-open{padding:96px 0 8px;border-top:1px solid var(--line)}
.note-byline{display:flex;align-items:center;gap:13px}
.note-byline img{width:44px;height:44px;object-fit:contain}
.note-byline .nb-name{font-family:var(--serif);font-size:1.05rem;color:var(--deep);
font-weight:700;line-height:1.3}
.note-byline .nb-role{font-family:var(--sans);font-size:.68rem;font-weight:600;
text-transform:uppercase;letter-spacing:.18em;color:var(--muted)}
/* Joel's Directive — editorial chapters */
.jd-lede{font-family:var(--serif);font-weight:700;color:var(--accent);
font-size:clamp(1.5rem,3vw,2.5rem);line-height:1.2;letter-spacing:-.01em;
max-width:24ch;margin-top:38px}
.longform{max-width:64ch;font-size:1.07rem;line-height:1.75}
.longform p{margin:0 0 18px}
.longform p>strong:only-child{display:inline-block;font-size:1.3em;line-height:1.35;
color:var(--deep);margin:8px 0}
.longform blockquote{border-left:3px solid var(--accent);padding:8px 0 8px 26px;
margin:30px 0;font-family:var(--serif);font-size:1.4rem;font-style:italic;
color:var(--deep);line-height:1.45}
.longform blockquote p{margin:0}
.ch-eyebrow{font-family:var(--sans);font-size:.72rem;font-weight:700;
text-transform:uppercase;letter-spacing:.22em;color:var(--muted);
display:flex;align-items:center;gap:14px}
.read-time{font-family:var(--sans);font-size:.72rem;font-weight:600;
letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-top:14px}
.chapter{padding:72px 0;border-top:1px solid var(--line)}
.ch-grid{display:grid;grid-template-columns:minmax(220px,340px) 1fr;
gap:clamp(32px,5vw,90px);align-items:start}
.ch-side{position:sticky;top:110px}
.ch-num{font-family:var(--serif);font-weight:700;font-size:clamp(3.2rem,6vw,5rem);
color:var(--ghost);line-height:1}
.ch-title{font-family:var(--serif);font-size:clamp(1.5rem,2.3vw,2.1rem);
color:var(--deep);margin-top:12px;letter-spacing:-.01em;max-width:14ch;line-height:1.25}
.jd-end{text-align:center;padding:80px 0 100px;border-top:1px solid var(--line)}
.jd-end img{width:56px;opacity:.9}
.jd-end .m-label-line{font-family:var(--sans);font-size:.72rem;font-weight:700;
text-transform:uppercase;letter-spacing:.3em;color:var(--muted);margin-top:20px}
@media(max-width:860px){.ch-grid{grid-template-columns:1fr;gap:22px}
.ch-side{position:static;display:flex;align-items:baseline;gap:16px}
.ch-num{font-size:2.4rem}.ch-title{margin-top:0}}
.sec-label{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.24em;color:var(--accent);margin-bottom:34px}
.statement{font-family:var(--serif);color:var(--deep);letter-spacing:-.015em;
font-size:clamp(2.1rem,5.2vw,4rem);line-height:1.12;max-width:22ch}
.statement .accent{font-style:italic;color:var(--accent)}
.muted-line{font-family:var(--serif);font-size:clamp(1.25rem,2.6vw,1.7rem);
color:var(--muted);margin-bottom:18px}
.split{display:grid;grid-template-columns:200px 1fr;gap:48px;align-items:start}
.split .side{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.2em;color:var(--muted);padding-top:10px;position:sticky;top:110px}
.bigtext p{font-size:clamp(1.15rem,2vw,1.4rem);line-height:1.75;color:var(--ink);
margin-bottom:26px;max-width:56ch}
.bigtext p strong{color:var(--deep)}
/* belief rows */
.belief-row{display:grid;grid-template-columns:150px 1fr;gap:36px;align-items:baseline;
padding:38px 0;border-bottom:1px solid var(--line)}
.belief-row:first-of-type{border-top:1px solid var(--line)}
.belief-row .gnum{font-family:var(--serif);font-weight:700;font-size:clamp(3rem,6vw,4.6rem);
line-height:1;color:var(--ghost)}
.belief-row .btext{font-family:var(--serif);font-size:clamp(1.6rem,3.8vw,2.8rem);
line-height:1.25;color:var(--deep);letter-spacing:-.01em}
.belief-row .btext em{font-style:italic;color:var(--accent)}
/* question split */
.qgrid{display:grid;grid-template-columns:1fr 1fr;gap:48px;margin:64px 0}
.qgrid .q{font-family:var(--serif);font-size:clamp(1.5rem,3vw,2.2rem);line-height:1.3;
letter-spacing:-.01em}
.qgrid .q1{color:var(--deep)}
.qgrid .q2{color:var(--muted);font-style:italic}
.answer{font-family:var(--serif);font-size:clamp(1.3rem,2.4vw,1.7rem);color:var(--deep);
border-left:3px solid var(--accent);padding-left:26px;max-width:44ch}
/* pillars */
.pillars{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}
.pillar{background:var(--panel);padding:34px 26px;border-radius:12px;
transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.pillar:hover{transform:translateY(-6px);box-shadow:0 14px 30px rgba(32,60,45,.1)}
.pillar .num{font-family:var(--sans);font-size:.7rem;font-weight:700;color:var(--accent);
letter-spacing:.18em;margin-bottom:16px}
.pillar h3{font-family:var(--serif);font-size:1.3rem;color:var(--deep);margin-bottom:10px}
.pillar p{color:var(--muted);font-size:.95rem;line-height:1.55}
/* dark section (human test) */
.dark{background:var(--deep);color:#EFEDE0;position:relative;overflow:hidden;
padding:120px 0}
.dark .sec-label{color:var(--accent)}
.dark .big-q{font-family:var(--serif);font-style:italic;font-weight:700;
font-size:clamp(2rem,5vw,3.6rem);line-height:1.15;letter-spacing:-.015em;color:#F7F3E6;
max-width:20ch}
.dark .after{color:#9FB09A;font-size:1.15rem;margin-top:36px;max-width:42ch}
.dark .watermark{position:absolute;right:-140px;top:50%;transform:translateY(-50%);
width:520px;opacity:.14;pointer-events:none}
/* the way rows */
.way-row{display:grid;grid-template-columns:1fr 1.4fr;gap:40px;align-items:baseline;
padding:36px 0;border-bottom:1px solid var(--line)}
.way-row:first-of-type{border-top:1px solid var(--line)}
.way-row .no{font-family:var(--serif);font-size:clamp(1.05rem,2vw,1.3rem);
color:var(--muted);text-decoration:line-through;text-decoration-color:var(--accent);
text-decoration-thickness:1.5px}
.way-row .yes{font-family:var(--serif);font-size:clamp(1.6rem,3.4vw,2.4rem);
line-height:1.2;color:var(--deep);letter-spacing:-.01em}
.closing{font-family:var(--serif);font-style:italic;text-align:center;
font-size:clamp(1.25rem,2.6vw,1.8rem);line-height:1.9;color:var(--deep);max-width:34ch;
margin:0 auto}
.closing .dot{color:var(--accent)}
/* domain pills */
.domains{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 48px}
.domains span{font-family:var(--sans);font-size:.8rem;font-weight:600;letter-spacing:.08em;
text-transform:uppercase;border:1px solid var(--line);border-radius:999px;padding:12px 22px;
color:var(--deep);background:var(--panel);transition:all .3s var(--ease)}
.domains span:hover{background:var(--deep);color:var(--bg);border-color:var(--deep);
transform:translateY(-3px)}
/* company cards */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:26px}
.card{display:block;text-align:center}
.tile{border-radius:14px;height:112px;display:flex;align-items:center;justify-content:center;
padding:18px;transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.card:hover .tile{transform:translateY(-6px) scale(1.02);box-shadow:0 16px 32px rgba(32,60,45,.16)}
.tile-dark{background:var(--deep)}
.tile-light{background:#FDFBF3;border:1px solid var(--line)}
.tile img{max-width:calc(82% * var(--ls,1));max-height:calc(74px * var(--ls,1));object-fit:contain}
.card h3{font-family:var(--sans);font-size:.86rem;font-weight:600;color:var(--ink);
margin-top:14px;line-height:1.35}
.card p{color:var(--muted);font-size:.85rem;margin-top:6px}
.group-label{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.2em;color:var(--accent);margin:64px 0 30px;display:flex;align-items:center;gap:18px}
.group-label::after{content:"";flex:1;height:1px;background:var(--line)}
.group-label:first-of-type{margin-top:0}
.deck-tag{font-family:var(--sans);font-size:.66rem;font-weight:700;letter-spacing:.16em;
text-transform:uppercase;color:var(--accent);margin-top:8px}
/* buttons */
.btn{display:inline-flex;align-items:center;gap:10px;font-family:var(--sans);font-size:.76rem;
font-weight:700;text-transform:uppercase;letter-spacing:.16em;background:var(--deep);
color:var(--bg);padding:16px 32px;border-radius:8px;transition:all .3s var(--ease)}
.btn .arr{transition:transform .3s var(--ease)}
.btn:hover{background:#2C5240;transform:translateY(-2px);box-shadow:0 10px 24px rgba(32,60,45,.2)}
.btn:hover .arr{transform:translateX(5px)}
.btn-ghost{background:transparent;color:var(--deep);border:1px solid var(--deep)}
.btn-ghost:hover{background:var(--deep);color:var(--bg)}
/* blog accordion */
.acc{border-bottom:1px solid var(--line)}
.acc:first-of-type{border-top:1px solid var(--line)}
.acc-head{display:flex;align-items:center;gap:18px;width:100%;padding:30px 0;cursor:pointer;
background:none;border:none;text-align:left;font:inherit;color:inherit}
.acc-head .meta{flex:1;min-width:0}
.acc-head .date{font-family:var(--sans);font-size:.7rem;font-weight:600;color:var(--muted);
text-transform:uppercase;letter-spacing:.18em}
.acc-head h3{font-family:var(--serif);font-size:clamp(1.25rem,2.7vw,1.7rem);color:var(--deep);
margin-top:8px;letter-spacing:-.01em;transition:color .2s;line-height:1.3}
.acc-head:hover h3{color:var(--accent)}
.chev{flex:0 0 auto;width:36px;height:36px;border:1px solid var(--line);border-radius:50%;
display:flex;align-items:center;justify-content:center;color:var(--muted);
transition:transform .4s var(--ease),color .2s,border-color .2s;font-size:.95rem}
.acc.open .chev{transform:rotate(45deg);color:var(--accent);border-color:var(--accent)}
.share-btn{flex:0 0 auto;font-family:var(--sans);font-size:.66rem;font-weight:700;
text-transform:uppercase;letter-spacing:.14em;color:var(--muted);background:none;
border:1px solid var(--line);border-radius:999px;padding:10px 16px;cursor:pointer;
transition:all .25s var(--ease);white-space:nowrap}
.share-btn:hover{color:var(--bg);border-color:var(--deep);background:var(--deep)}
.acc-body{display:grid;grid-template-rows:0fr;transition:grid-template-rows .55s var(--ease)}
.acc.open .acc-body{grid-template-rows:1fr}
.acc-inner{overflow:hidden;min-height:0;max-width:68ch}
.acc-inner-pad{padding:8px 0 48px}
.acc-inner p{margin:0 0 20px}
.acc-inner h2{font-family:var(--serif);font-size:1.5rem;color:var(--deep);margin:44px 0 16px}
.acc-inner strong{color:var(--deep)}
.acc-inner em{color:var(--muted)}
.acc-inner ul,.acc-inner ol{margin:0 0 20px 24px}
.acc-inner blockquote{border-left:3px solid var(--accent);padding:6px 0 6px 24px;margin:28px 0;
font-size:1.25rem;line-height:1.5;color:var(--deep);font-style:italic}
.acc-inner blockquote p{margin:0}
/* prose (long-form pages/posts) */
.prose{max-width:66ch;padding:70px 0 110px}
.prose h1{font-family:var(--serif);font-size:clamp(2.2rem,5vw,3.4rem);color:var(--deep);
letter-spacing:-.02em;line-height:1.08;margin-bottom:34px}
.prose h2{font-family:var(--serif);font-size:1.65rem;color:var(--deep);margin:52px 0 18px}
.prose p{margin:0 0 20px}
.prose p>strong:only-child{display:block;font-size:1.25em;line-height:1.4;color:var(--deep)}
.prose>p:first-of-type>strong:only-child{font-size:1.5em;letter-spacing:-.01em}
.prose ul,.prose ol{margin:0 0 20px 24px}
.prose li{margin-bottom:10px}
.prose strong{color:var(--deep)}
.prose a{color:var(--accent)}
.prose em{color:var(--muted)}
.prose blockquote{border-left:3px solid var(--accent);padding:6px 0 6px 26px;margin:30px 0;
font-size:1.3rem;line-height:1.5;color:var(--deep);font-style:italic}
.prose blockquote p{margin:0}
.prose hr{border:none;border-top:1px solid var(--line);margin:44px 0}
.prose .date{font-family:var(--sans);font-size:.7rem;font-weight:700;color:var(--accent);
text-transform:uppercase;letter-spacing:.2em;margin-bottom:20px}
/* ---------- responsive ---------- */
@media(max-width:820px){
.hero{padding:70px 0 60px}section{padding:64px 0}
.hero-flex{flex-direction:column-reverse;align-items:flex-start;gap:38px}
.hero-enso{width:132px}
.split{grid-template-columns:1fr;gap:18px}
.split .side{position:static}
.qgrid{grid-template-columns:1fr;gap:26px;margin:44px 0}
.belief-row{grid-template-columns:74px 1fr;gap:20px;padding:30px 0}
.way-row{grid-template-columns:1fr;gap:10px;padding:28px 0}
.dark{padding:80px 0}
.dark .watermark{width:340px;right:-120px}
}
"""

# ---------------------------------------------------------------- js
SHARED_JS = """
document.documentElement.classList.add('js');
(function() {
  var btn = document.getElementById('menu-btn');
  var menu = document.getElementById('menu');
  var close = document.getElementById('menu-close');
  function setOpen(open) {
    menu.classList.toggle('open', open);
    menu.setAttribute('aria-hidden', String(!open));
    btn.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  }
  btn.addEventListener('click', function() { setOpen(true); });
  close.addEventListener('click', function() { setOpen(false); });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') setOpen(false);
  });
})();
(function() {
  var els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) {
    els.forEach(function(el){ el.classList.add('in'); });
    return;
  }
  var io = new IntersectionObserver(function(entries) {
    entries.forEach(function(en) {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    });
  }, {threshold: 0.12, rootMargin: '0px 0px -40px 0px'});
  els.forEach(function(el){ io.observe(el); });
})();
(function() {
  var intro = document.getElementById('intro');
  if (intro) setTimeout(function(){ intro.remove(); }, 3200);
  var pe = document.querySelector('.hero-enso.floaty');
  if (pe && window.matchMedia('(pointer:fine)').matches
        && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.addEventListener('mousemove', function(e) {
      var x = (e.clientX / window.innerWidth - .5) * 24;
      var y = (e.clientY / window.innerHeight - .5) * 18;
      pe.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
    }, {passive: true});
  }
})();
"""

FITHEAD_JS = """
(function(){
  var el = document.querySelector('.note-head');
  if (!el) return;
  var CAP = 76;
  function fit(){
    if (window.innerWidth < 861) {
      el.style.whiteSpace = '';
      el.style.fontSize = '';
      el.style.maxWidth = '';
      return;
    }
    el.style.maxWidth = 'none';
    el.style.whiteSpace = 'nowrap';
    el.style.fontSize = CAP + 'px';
    var p = el.parentElement, cs = getComputedStyle(p);
    var avail = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    var w = el.scrollWidth;
    if (w > avail) el.style.fontSize = Math.floor(CAP * (avail / w) * 0.985) + 'px';
  }
  fit();
  window.addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
})();
"""

CLIMAX_JS = """
(function(){
  var body = document.getElementById('teaser-body');
  var climax = document.getElementById('climax');
  var cont = document.getElementById('continue-wrap');
  if (!climax || !cont) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function maxSize(){ return window.innerWidth < 700 ? 2.1 : 3.4; }
  function minSize(){ return window.innerWidth < 700 ? 1.25 : 1.4; }
  function upd(){
    if (reduce) {
      climax.style.fontSize = maxSize() + 'rem';
      cont.style.opacity = 1; cont.style.transform = 'none';
      if (body) body.style.opacity = 1;
      return;
    }
    var vh = window.innerHeight || 800;
    var pageTop = climax.getBoundingClientRect().top + window.scrollY;
    var s0 = pageTop - vh * 1.45;
    var s1 = document.documentElement.scrollHeight - vh;
    var p = (s1 - s0) > 40 ? (window.scrollY - s0) / (s1 - s0) : 1;
    p = p < 0 ? 0 : (p > 1 ? 1 : p);
    var mn = minSize(), mx = maxSize();
    climax.style.fontSize = (mn + (mx - mn) * p).toFixed(3) + 'rem';
    if (body) body.style.opacity = (1 - 0.82 * p).toFixed(3);
    var cp = (p - 0.52) / 0.33;
    cp = cp < 0 ? 0 : (cp > 1 ? 1 : cp);
    cont.style.opacity = cp.toFixed(3);
    cont.style.transform = 'translateY(' + ((1 - cp) * 20).toFixed(1) + 'px)';
  }
  upd();
  window.addEventListener('scroll', upd, {passive:true});
  window.addEventListener('resize', upd, {passive:true});
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(upd);
})();
"""

SCROLLCUE_JS = """
(function(){
  var c = document.getElementById('scrollcue');
  if (!c) return;
  c.addEventListener('click', function(){
    var t = document.getElementById('founder-note');
    if (t) t.scrollIntoView({behavior:'smooth', block:'start'});
  });
})();
"""

PROGRESS_JS = """
(function() {
  var bar = document.createElement('div');
  bar.className = 'progress';
  document.body.appendChild(bar);
  function upd() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
  }
  window.addEventListener('scroll', upd, {passive: true});
  window.addEventListener('resize', upd, {passive: true});
  upd();
})();
"""

INTRO_SCRIPT = """<script>
try{if(sessionStorage.getItem('d17i')){document.documentElement.classList.add('skip-intro')}
else{sessionStorage.setItem('d17i','1')}}catch(e){}
</script>"""

BLOG_JS = """
(function() {
  document.querySelectorAll('.acc-head').forEach(function(h){
    function toggle(){
      var acc = h.parentElement;
      acc.classList.toggle('open');
      h.setAttribute('aria-expanded', acc.classList.contains('open'));
    }
    h.addEventListener('click', function(e){
      if (e.target.closest('.share-btn')) return;
      toggle();
    });
    h.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  });
  document.querySelectorAll('.share-btn').forEach(function(b){
    b.addEventListener('click', function(e){
      e.stopPropagation();
      var url = new URL(b.dataset.slug + '.html', location.href).href;
      var done = function(msg){
        var old = b.textContent; b.textContent = msg;
        setTimeout(function(){ b.textContent = old; }, 1800);
      };
      if (navigator.share) {
        navigator.share({title: b.dataset.title, url: url}).catch(function(){});
      } else if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function(){ done('Link copied!'); },
          function(){ window.prompt('Copy this link:', url); });
      } else {
        window.prompt('Copy this link:', url);
      }
    });
  });
  function openFromHash() {
    if (!location.hash) return;
    var t = document.getElementById(location.hash.slice(1));
    if (t && t.classList.contains('acc')) {
      t.classList.add('open');
      t.querySelector('.acc-head').setAttribute('aria-expanded', 'true');
      setTimeout(function(){ t.scrollIntoView({behavior:'smooth', block:'start'}); }, 80);
    }
  }
  openFromHash();
  window.addEventListener('hashchange', openFromHash);
})();
"""

# ---------------------------------------------------------------- helpers
def words(text, start=0.15, step=0.07):
    """Split text into word spans with staggered rise-in delays."""
    out = []
    for i, w in enumerate(text.split()):
        out.append(f'<span class="w" style="--d:{start + i*step:.2f}s">{html.escape(w)}</span>')
    return " ".join(out)

def rev(inner, delay=0.0, tag="div", cls="", style=""):
    d = f"--d:{delay:.2f}s;" if delay else ""
    return f'<{tag} class="reveal {cls}" style="{d}{style}">{inner}</{tag}>'

def page(title, body, active="", depth=0, extra_js="", intro=False, path="", desc=None, jsonld=None):
    p = "../" * depth
    links = [("Home", f"{p}index.html", active == "")]
    links += [(n["label"], f'{p}{n["href"].lstrip("/")}', n["label"] == active) for n in site["nav"]]
    nav = "".join(
        f'<a href="{href}" class="m-link {"active" if act else ""}" style="--i:{i}">{label}</a>'
        for i, (label, href, act) in enumerate(links))
    intro_head = INTRO_SCRIPT if intro else ""
    intro_html = ("""<div id="intro"><div class="intro-inner">
<img src="images/logos/enso.webp" alt="">
<div class="intro-name">Directive 17</div>
</div></div>""" if intro else "")
    body_attr = ' style="--hd:2.2s"' if intro else ""
    d = desc or site["subline"]  # noqa: shadow ok
    url = f"https://{site['domain']}/{path}"
    analytics = (f'<script data-goatcounter="https://{site["goatcounter"]}.goatcounter.com/count" '
                 f'async src="//gc.zgo.at/count.js"></script>') if site.get("goatcounter") else ""
    org_ld = {
        "@context": "https://schema.org", "@type": "Organization",
        "name": "Directive 17", "url": f"https://{site['domain']}/",
        "logo": f"https://{site['domain']}/images/logos/enso.png",
        "description": site["subline"],
        "email": site["contact_email"],
        "founder": {"@type": "Person", "name": "Joel Shapiro"},
    }
    blocks = [org_ld] + ([jsonld] if jsonld else [])
    ld = "".join('<script type="application/ld+json">' + json.dumps(b) + '</script>'
                 for b in blocks)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(d)}">
<meta name="theme-color" content="#FBF7EC">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Directive 17">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(d)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://{site['domain']}/images/og-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(d)}">
<meta name="twitter:image" content="https://{site['domain']}/images/og-card.png">
<link rel="icon" type="image/png" href="{p}images/logos/enso.png">
<link rel="apple-touch-icon" href="{p}images/apple-touch-icon.png">
<link rel="preload" as="image" href="{p}images/logos/enso-md.webp">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..700&display=swap" rel="stylesheet">
{ld}{intro_head}<style>{CSS}</style>
</head>
<body{body_attr}>
{intro_html}
<header><div class="wrap nav">
<a class="logo" href="{p}index.html"><img src="{p}images/logos/enso-sm.webp" width="38" height="38" alt="Directive 17 enso logo">Directive 17</a>
<button class="menu-btn" id="menu-btn" aria-label="Open menu" aria-expanded="false">
<span></span><span></span><span></span>
</button>
</div></header>
<nav class="menu-overlay" id="menu" aria-hidden="true">
<button class="menu-close" id="menu-close" aria-label="Close menu">&times;</button>
<div class="m-label">Directive 17</div>
{nav}
<div class="m-foot">Directive 17 &copy; 2026</div>
</nav>
{body}
<script>{SHARED_JS}{extra_js}</script>
{analytics}</body>
</html>"""

# optical size normalization: multiplier on each logo so all marks read the same weight
LOGO_SCALE = {
    "Pivt": 0.68, "Mythogenic": 0.82, "Caviar and Corndogs": 0.88,
    "Vector": 1.12, "Twelve92": 0.95, "HumanOS": 0.92,
    "Epirus": 0.72, "Advocate": 0.72, "LARX": 0.8, "General Fusion": 0.82,
    "Colossal Laboratories & Biosciences": 0.95,
}

def company_card(c, depth=0, delay=0.0):
    p = "../" * depth
    dark = "Proprietary" in c.get("group", "Proprietary")
    tile_cls = "tile-dark" if dark else "tile-light"
    ls = LOGO_SCALE.get(c["name"], 1.0)
    ls_attr = f' style="--ls:{ls}"' if ls != 1.0 else ""
    logo = (f'<img src="{p}images/{c["logo"]}"{ls_attr} loading="lazy" decoding="async" alt="{html.escape(c["name"])} logo">'
            if c.get("logo") else f'<span style="font-family:var(--serif);font-size:1.4rem;'
            f'color:{"#FBF7EC" if dark else "var(--deep)"}">{html.escape(c["name"][0])}</span>')
    if c.get("deck"):
        liner_extra = '<p class="deck-tag">Investor deck &rarr;</p>'
        inner_link = f'{p}decks/{c["deck"]}.html'
        liner = (f'<p>{html.escape(c["one_liner"])}</p>' if c.get("one_liner") else "") + liner_extra
        inner = f'<div class="tile {tile_cls}">{logo}</div><h3>{html.escape(c["name"])}</h3>{liner}'
        return f'<a class="card" href="{inner_link}">{inner}</a>'
    liner = f'<p>{html.escape(c["one_liner"])}</p>' if c.get("one_liner") else ""
    inner = f'<div class="tile {tile_cls}">{logo}</div><h3>{html.escape(c["name"])}</h3>{liner}'
    d = f' style="--d:{delay:.2f}s"' if delay else ""
    if c.get("url"):
        return f'<a class="card reveal" href="{c["url"]}" target="_blank" rel="noopener"{d}>{inner}</a>'
    return f'<div class="card reveal"{d}>{inner}</div>'

# ---------------------------------------------------------------- build
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
(OUT / "blog").mkdir()
if (CONTENT / "images").exists():
    shutil.copytree(CONTENT / "images", OUT / "images", dirs_exist_ok=True)
(OUT / ".nojekyll").write_text("")
if site.get("domain") and site.get("live"):
    (OUT / "CNAME").write_text(site["domain"])

posts = sorted((parse_post(p) for p in (CONTENT / "posts").glob("*.md")),
               key=lambda x: x["date"], reverse=True)

# ---------------- Founder's note: homepage teaser + full page
jd_src = (CONTENT / "pages" / "joels-directive.md").read_text()
jd_body = re.sub(r"^#\s+.*\n", "", jd_src, count=1)
jd_lede_m = re.search(r"^\*\*(.+?)\*\*\s*$", jd_body, flags=re.M)
jd_lede = jd_lede_m.group(1) if jd_lede_m else ""
if jd_lede_m:
    jd_body = jd_body.replace(jd_lede_m.group(0), "", 1)
jd_minutes = max(1, round(len(jd_body.split()) / 200))
jd_parts = re.split(r"^##\s+(.*)$", jd_body, flags=re.M)
jd_intro_full = jd_parts[0].replace("<!--more-->", "")
jd_chapters = [(jd_parts[i], jd_parts[i + 1]) for i in range(1, len(jd_parts), 2)]

# teaser = intro up to the <!--more--> marker; its final paragraph is the climax line
teaser_md = jd_parts[0].split("<!--more-->", 1)[0]
teaser_paras = [p.strip() for p in teaser_md.strip().split("\n\n") if p.strip()]
climax_line = teaser_paras[-1] if teaser_paras else ""
teaser_rest = "\n\n".join(teaser_paras[:-1])

ch_html = "".join(f"""
<section class="chapter"><div class="wrap ch-grid">
<div class="ch-side reveal"><div class="ch-num">{i+1:02d}</div>
<h2 class="ch-title">{md_inline(t)}</h2></div>
<div class="ch-body longform">{md_to_html(body)}</div>
</div></section>""" for i, (t, body) in enumerate(jd_chapters))

note_head = f"""
<div class="note-open" id="founder-note"><div class="wrap">
<div class="kicker reveal">A Note from the Founder</div>
<h2 class="display reveal note-head" style="max-width:19ch;font-size:clamp(2.1rem,5vw,4rem)">{html.escape(jd_lede)}</h2>
</div></div>"""

byline = f"""<div class="ch-side reveal"><div class="note-byline">
<img src="images/logos/enso-sm.webp" width="44" height="44" loading="lazy" alt="">
<div><div class="nb-name">Joel Shapiro</div>
<div class="nb-role">Founder</div></div>
</div>
<div class="read-time">{jd_minutes} min read</div></div>"""

# --- homepage teaser
founder_note = f"""{note_head}
<section class="jd-intro" style="padding-top:56px;padding-bottom:32vh">
<div class="wrap ch-grid">
{byline}
<div>
<div class="longform teaser-body" id="teaser-body">{md_to_html(teaser_rest)}</div>
<div class="climax" id="climax">{md_inline(climax_line)}</div>
<div class="continue-wrap" id="continue-wrap">
<a class="btn" href="founders-note.html">Continue reading <span class="arr">&rarr;</span></a>
</div>
</div>
</div>
</section>"""

# --- full note page
full_note = f"""
<div class="hero" style="padding-bottom:56px"><div class="wrap">
<div class="kicker fade" style="--d:.05s">A Note from the Founder</div>
<h1 class="display note-head" style="max-width:19ch;font-size:clamp(2.1rem,5vw,4rem)">{words(jd_lede, .25, .07)}</h1>
</div></div>
<section class="jd-intro" style="padding-top:56px;border-top:1px solid var(--line)">
<div class="wrap ch-grid">
{byline}
<div class="longform">{md_to_html(jd_intro_full)}</div>
</div>
</section>
{ch_html}
<div class="jd-end reveal"><div class="wrap">
<img src="images/logos/enso-sm.webp" width="56" height="55" loading="lazy" alt="">
<div class="m-label-line">Directive 17</div>
</div></div>"""

(OUT / "founders-note.html").write_text(
    page(f"A Note from the Founder — {site['name']}", full_note, "", 0,
         extra_js=FITHEAD_JS + PROGRESS_JS, path="founders-note.html",
         desc="Stop watching. Start creating. A note from Joel Shapiro."))

# legacy link -> full note page
(OUT / "joels-directive.html").write_text(
    '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    '<title>A Note from the Founder \u2014 Directive 17</title>'
    '<link rel="canonical" href="https://directive17.com/founders-note.html">'
    '<meta http-equiv="refresh" content="0; url=founders-note.html">'
    '<script>location.replace("founders-note.html")</script></head>'
    '<body style="background:#FBF7EC"></body></html>')

# ---------------- home: hero only, animated, intro curtain + pillar ticker
tick_set = "".join(
    f'<span>{html.escape(p["title"])}</span><span class="tsep">&#10022;</span>'
    for p in site["home_pillars"])
home = f"""
<div class="hero hero-home"><div class="wrap hero-flex">
<div>
<div class="kicker fade" style="--d:.05s">Directive 17</div>
<h1 class="display">{words(site['tagline'], .25, .09)}</h1>
<p class="sub fade" style="--d:.95s">{html.escape(site['subline'])}</p>
</div>
<div class="hero-enso floaty"><img src="images/logos/enso-md.webp" width="640" height="629" alt="Directive 17 enso"></div>
</div>
<button class="scrollcue" id="scrollcue" aria-label="Scroll to the note from the founder">
<span class="sc-label">A note from the founder</span>
<span class="sc-arrow">&darr;</span>
</button>
<div class="ticker"><div class="ticker-track">{tick_set}{tick_set}{tick_set}</div></div>
</div>
{founder_note}"""


# ---------------- why
wp = site["why_page"]
belief_rows = "".join(
    rev(f'<div class="gnum">0{i+1}</div><div class="btext">{html.escape(b)}</div>',
        delay=0.05 * (i % 3), tag="div", cls="belief-row")
    for i, b in enumerate(wp["beliefs"]))
paras = "".join(f"<p>{html.escape(t)}</p>" for t in wp["paragraphs"])
why = f"""
<div class="hero"><div class="wrap">
<div class="kicker fade" style="--d:.05s">{html.escape(wp['kicker'])}</div>
<div class="muted-line fade" style="--d:.2s">{html.escape(wp['line1'])}</div>
<h1 class="display">{words(wp['line2'], .4, .09)}</h1>
</div></div>
<div class="wrap"><hr class="rule"></div>
<section><div class="wrap">
<div class="split">
<div class="side reveal">The starting point</div>
<div class="bigtext reveal" style="--d:.1s">{paras}</div>
</div>
</div></section>
<section style="padding-top:0"><div class="wrap">
<div class="sec-label reveal">{html.escape(wp['belief_label'])}</div>
{rev(f'<div class="statement">{html.escape(wp["belief_intro"])}</div>', .05)}
<div style="height:56px"></div>
{belief_rows}
</div></section>"""
(OUT / "why.html").write_text(page(f"Why — {site['name']}", why, "Why", path="why.html",
    desc="Most organizations begin with markets. We begin with people."))

# ---------------- philosophy
pp = site["philosophy_page"]
pillars = "".join(
    rev(f'<div class="num">{p["num"]}</div><h3>{html.escape(p["title"])}</h3>'
        f'<p>{html.escape(p["body"])}</p>', delay=0.07 * i, tag="div", cls="pillar")
    for i, p in enumerate(site["home_pillars"]))
way_rows = "".join(
    rev(f'<div class="no">{html.escape(no)}</div><div class="yes">{html.escape(yes)}</div>',
        delay=0.06 * i, tag="div", cls="way-row")
    for i, (no, yes) in enumerate(pp["way"]["pairs"]))
closing_html = html.escape(pp["way"]["closing"]).replace(". ", '.<span class="dot"> &middot; </span>')
philosophy = f"""
<div class="hero"><div class="wrap">
<div class="kicker fade" style="--d:.05s">{html.escape(pp['kicker'])}</div>
<h1 class="display" style="max-width:20ch">{words(pp['opening'], .25, .07)}</h1>
<div class="qgrid">
<div class="q q1 fade" style="--d:1.1s">{html.escape(pp['q1'])}</div>
<div class="q q2 fade" style="--d:1.35s">{html.escape(pp['q2'])}</div>
</div>
<div class="answer fade" style="--d:1.6s">{html.escape(pp['answer'])}</div>
</div></div>
<div class="wrap"><hr class="rule"></div>
<section><div class="wrap">
<div class="sec-label reveal">{html.escape(pp['pillars_label'])}</div>
{rev(f'<div class="statement" style="font-size:clamp(1.6rem,3.2vw,2.4rem)">{html.escape(pp["pillars_intro"])}</div>', .05)}
<div style="height:48px"></div>
<div class="pillars">{pillars}</div>
</div></section>
<div class="dark">
<img class="watermark" src="images/logos/enso-md.webp" loading="lazy" alt="">
<div class="wrap">
<div class="sec-label reveal">{html.escape(pp['human_test']['label'])}</div>
{rev(f'<p style="color:#9FB09A;font-size:1.1rem;margin-bottom:30px">{html.escape(pp["human_test"]["intro"])}</p>', .05, tag="div")}
{rev(f'<div class="big-q">&ldquo;{html.escape(pp["human_test"]["question"])}&rdquo;</div>', .15)}
{rev(f'<p class="after">{html.escape(pp["human_test"]["after"])}</p>', .3, tag="div")}
</div></div>
<section><div class="wrap">
<div class="sec-label reveal">{html.escape(pp['way']['label'])}</div>
{rev(f'<div class="statement" style="font-size:clamp(1.6rem,3.2vw,2.4rem)">{html.escape(pp["way"]["lede"])}</div>', .05)}
<div style="height:48px"></div>
{way_rows}
<div style="height:80px"></div>
{rev(f'<div class="closing">{closing_html}</div>', .1)}
</div></section>"""
(OUT / "philosophy.html").write_text(page(f"Philosophy — {site['name']}", philosophy, "Philosophy",
    path="philosophy.html", desc="The Five Pillars, the Human Test, and the Directive 17 Way."))

# ---------------- future
fp = site["future_page"]
pills = "".join(
    f'<span class="reveal" style="--d:{.06*i:.2f}s">{html.escape(d)}</span>'
    for i, d in enumerate(fp["domains"]))
future = f"""
<div class="hero" style="padding-bottom:56px"><div class="wrap">
<div class="kicker fade" style="--d:.05s">{html.escape(fp['kicker'])}</div>
<div class="muted-line fade" style="--d:.2s">{html.escape(fp['old_q'])}</div>
<h1 class="display" style="max-width:15ch">{words(fp['new_q'], .4, .09)}</h1>
</div></div>
<div class="wrap"><hr class="rule"></div>
<section style="padding-top:56px"><div class="wrap">
<div class="domains">{pills}</div>
{rev(f'<div class="bigtext"><p style="max-width:52ch">{html.escape(fp["body"])}</p></div>', .1)}
<div style="height:24px"></div>
{rev(f'<a class="btn" href="build.html">Build with us <span class="arr">&rarr;</span></a>', .2, tag="div")}
</div></section>"""
(OUT / "future.html").write_text(page(f"Future — {site['name']}", future, "Future", path="future.html",
    desc="The better question is: what future is worth building?"))

# ---------------- companies
groups = []
for c in companies:
    g = c.get("group", "Portfolio")
    if g not in groups:
        groups.append(g)
sections = ""
for g in groups:
    cards = "".join(company_card(c, delay=0.05 * (i % 6))
                    for i, c in enumerate([c for c in companies if c.get("group", "Portfolio") == g]))
    sections += f'<div class="group-label reveal">{html.escape(g)}</div><div class="grid">{cards}</div>'
companies_body = f"""
<div class="hero" style="padding-bottom:70px"><div class="wrap">
<div class="kicker fade" style="--d:.05s">Our Companies</div>
<h1 class="display" style="max-width:20ch">{words('Different companies. One philosophy.', .25, .08)}</h1>
</div></div>
<section style="padding-top:20px"><div class="wrap">{sections}</div></section>"""
(OUT / "companies.html").write_text(page(f"Companies — {site['name']}", companies_body, "Companies",
    path="companies.html", desc="Different companies. One philosophy."))

(OUT / "index.html").write_text(
    page(f"{site['name']} — {site['tagline']}", home, "", 0, intro=True,
         extra_js=SCROLLCUE_JS + FITHEAD_JS + CLIMAX_JS + PROGRESS_JS))

# ---------------- blog index (accordion)
rows = "".join(f"""
<article class="acc reveal" id="{p['slug']}" style="--d:{.06*i:.2f}s">
<div class="acc-head" role="button" tabindex="0" aria-expanded="false">
<div class="meta"><div class="date">{fmt_date(p['date'])}</div>
<h3>{html.escape(p['title'])}</h3></div>
<button class="share-btn" data-slug="{p['slug']}" data-title="{html.escape(p['title'], quote=True)}">Share</button>
<div class="chev">+</div>
</div>
<div class="acc-body"><div class="acc-inner"><div class="acc-inner-pad">{p['html']}</div></div></div>
</article>""" for i, p in enumerate(posts))
if not posts:
    rows = '<p style="color:var(--muted);font-size:1.1rem">New posts coming soon.</p>'
blog_body = f"""
<div class="hero" style="padding-bottom:70px"><div class="wrap">
<div class="kicker fade" style="--d:.05s">Joel's Blog</div>
<h1 class="display" style="max-width:19ch">{words("Joel's Tales from Weird Side", .25, .085)}</h1>
<p class="sub fade" style="--d:1.05s">I wish I was making this shit up!</p>
</div></div>
<section style="padding-top:20px"><div class="wrap">{rows}</div></section>"""
(OUT / "blog" / "index.html").write_text(
    page(f"Joel's Tales from Weird Side — {site['name']}", blog_body, "Joel's Blog", 1,
         extra_js=BLOG_JS + PROGRESS_JS, path="blog/",
         desc="I wish I was making this shit up!"))

# ---------------- individual post pages (own URL, own preview, crawlable text)
for p in posts:
    art_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["title"],
        "datePublished": p["date"],
        "description": p["excerpt"],
        "author": {"@type": "Person", "name": "Joel Shapiro"},
        "publisher": {"@type": "Organization", "name": "Directive 17",
                      "logo": {"@type": "ImageObject",
                               "url": f"https://{site['domain']}/images/logos/enso.png"}},
        "mainEntityOfPage": f"https://{site['domain']}/blog/{p['slug']}.html",
        "url": f"https://{site['domain']}/blog/{p['slug']}.html",
    }
    words_ct = max(1, round(len(re.sub(r"<[^>]+>", " ", p["html"]).split()) / 200))
    post_body = f"""
<div class="hero" style="padding-bottom:52px"><div class="wrap">
<div class="kicker fade" style="--d:.05s">{fmt_date(p['date'])}</div>
<h1 class="display note-head" style="max-width:20ch;font-size:clamp(2rem,4.4vw,3.4rem)">{words(p['title'], .25, .07)}</h1>
</div></div>
<section class="jd-intro" style="padding-top:52px;border-top:1px solid var(--line)">
<div class="wrap ch-grid">
<div class="ch-side reveal"><div class="note-byline">
<img src="../images/logos/enso-sm.webp" width="44" height="44" loading="lazy" alt="">
<div><div class="nb-name">Joel Shapiro</div>
<div class="nb-role">Joel's Blog</div></div>
</div>
<div class="read-time">{words_ct} min read</div></div>
<div class="longform">{p['html']}</div>
</div>
</section>
<div class="jd-end reveal"><div class="wrap">
<img src="../images/logos/enso-sm.webp" width="56" height="55" loading="lazy" alt="">
<div class="m-label-line"><a href="index.html">&larr; All posts</a></div>
</div></div>"""
    (OUT / "blog" / f"{p['slug']}.html").write_text(
        page(f"{p['title']} — Joel's Blog — {site['name']}", post_body, "Joel's Blog", 1,
             extra_js=FITHEAD_JS + PROGRESS_JS, path=f"blog/{p['slug']}.html",
             desc=p["excerpt"], jsonld=art_ld))

# ---------------- build with us
bp = site["build_page"]
build_body = f"""
<div class="hero hero-home"><div class="wrap hero-flex">
<div>
<div class="kicker fade" style="--d:.05s">Build With Us</div>
<h1 class="display">{words(bp['headline'], .25, .1)}</h1>
<p class="sub fade" style="--d:.7s">{html.escape(bp['body'])}</p>
<p class="fade" style="--d:.95s;margin-top:40px">
<a class="btn" href="mailto:{site['contact_email']}">{html.escape(bp['button'])} <span class="arr">&rarr;</span></a></p>
<p class="fade" style="--d:1.15s;margin-top:18px;font-family:var(--sans);font-size:.85rem;color:var(--muted)">{site['contact_email']}</p>
</div>
<div class="hero-enso floaty"><img src="images/logos/enso-md.webp" width="640" height="629" alt="Directive 17 enso"></div>
</div></div>"""
(OUT / "build.html").write_text(page(f"Build With Us — {site['name']}", build_body, "Build With Us",
    path="build.html", desc="The future is built by people who believe it can be better."))

# ---------------- password-protected deck viewers
DECK_CSS = """
:root{--bg:#FBF7EC;--deep:#203C2D;--accent:#D98B33;--line:#3A5344;--cream:#F5F1E2;
--serif:'Source Serif 4',Georgia,serif;--sans:'Helvetica Neue',Helvetica,Arial,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--deep);color:var(--cream);font-family:var(--serif);min-height:100vh}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;
padding:18px clamp(20px,3vw,44px);border-bottom:1px solid var(--line)}
.topbar .brand{display:flex;align-items:center;gap:12px;font-weight:700;font-size:1.05rem;
color:var(--cream)}
.topbar .brand img{height:32px;width:32px}
.topbar .dtitle{font-family:var(--sans);font-size:.72rem;font-weight:700;
text-transform:uppercase;letter-spacing:.18em;color:#8FA08A;text-align:center}
.topbar .count{font-family:var(--sans);font-size:.78rem;font-weight:600;color:#8FA08A;
min-width:70px;text-align:right}
/* gate */
.gate{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
background:var(--deep);z-index:50;padding:24px}
.gate-card{text-align:center;max-width:420px;width:100%}
.gate-card img{width:84px;margin-bottom:26px}
.gate-card h1{font-size:clamp(1.5rem,3vw,2rem);margin-bottom:8px;letter-spacing:-.01em}
.gate-card .glabel{font-family:var(--sans);font-size:.7rem;font-weight:700;
text-transform:uppercase;letter-spacing:.22em;color:var(--accent);margin-bottom:30px}
.gate-card input{width:100%;background:#1A3226;border:1px solid var(--line);border-radius:8px;
color:var(--cream);font-family:var(--sans);font-size:1rem;padding:15px 18px;outline:none;
text-align:center;letter-spacing:.08em;transition:border-color .2s}
.gate-card input:focus{border-color:var(--accent)}
.gate-card button{margin-top:14px;width:100%;background:var(--accent);border:none;
border-radius:8px;color:#1A2E22;font-family:var(--sans);font-size:.8rem;font-weight:700;
text-transform:uppercase;letter-spacing:.16em;padding:15px;cursor:pointer;transition:filter .15s}
.gate-card button:hover{filter:brightness(1.08)}
.gate-card .err{font-family:var(--sans);font-size:.82rem;color:#E2907B;margin-top:14px;
min-height:1.2em}
.gate-card .note{font-family:var(--sans);font-size:.72rem;color:#8FA08A;margin-top:22px}
@keyframes shake{20%,60%{transform:translateX(-7px)}40%,80%{transform:translateX(7px)}}
.shake{animation:shake .4s}
/* stage */
.viewer{display:none}
.viewer.on{display:block}
.stage{position:relative;display:flex;align-items:center;justify-content:center;
height:calc(100vh - 130px);padding:20px clamp(56px,6vw,90px)}
.stage img{max-width:100%;max-height:100%;border-radius:6px;
box-shadow:0 20px 60px rgba(0,0,0,.35)}
.arrow{position:absolute;top:50%;transform:translateY(-50%);background:rgba(245,241,226,.08);
border:1px solid var(--line);color:var(--cream);width:46px;height:46px;border-radius:50%;
cursor:pointer;font-size:1.15rem;font-family:var(--sans);transition:background .15s;z-index:5}
.arrow:hover{background:rgba(245,241,226,.18)}
.arrow.prev{left:clamp(8px,1.5vw,24px)}.arrow.next{right:clamp(8px,1.5vw,24px)}
.arrow:disabled{opacity:.25;cursor:default}
.bottom{display:flex;align-items:center;justify-content:center;gap:20px;
padding:0 20px 18px;font-family:var(--sans);font-size:.7rem;font-weight:600;
text-transform:uppercase;letter-spacing:.18em;color:#8FA08A}
.loading{position:absolute;inset:0;display:none;align-items:center;justify-content:center;
color:#8FA08A;font-family:var(--sans);font-size:.8rem;letter-spacing:.14em}
.loading.on{display:flex}
@media(max-width:640px){.stage{padding:12px 8px;height:calc(100vh - 150px)}
.arrow{width:38px;height:38px}.topbar .dtitle{display:none}}
"""

def deck_js(slug, meta):
    sizes = meta["sizes"]
    return """
const META = {salt:'%s', iterations:%d, sizes:%s, pack:'%s.pack'};
const offsets = []; let acc = 0;
for (const s of META.sizes) { offsets.push(acc); acc += s; }
const TOTAL = META.sizes.length;
let key = null, cur = 1, packBuf = null, noRange = false;
const cache = new Map();
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));

async function deriveKey(pw) {
  const km = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw),
    'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    {name:'PBKDF2', salt:b64(META.salt), iterations:META.iterations, hash:'SHA-256'},
    km, {name:'AES-GCM', length:256}, false, ['decrypt']);
}
async function sliceFor(n) {
  const start = offsets[n-1], end = start + META.sizes[n-1] - 1;
  if (packBuf) return packBuf.slice(start, end + 1);
  if (!noRange) {
    try {
      const r = await fetch(META.pack, {headers:{Range:'bytes='+start+'-'+end}});
      if (r.status === 206) {
        const buf = await r.arrayBuffer();
        if (buf.byteLength === META.sizes[n-1]) return buf;
      }
      noRange = true;
    } catch (e) { noRange = true; }
  }
  const full = await fetch(META.pack);
  packBuf = await full.arrayBuffer();
  return packBuf.slice(start, end + 1);
}
async function slideURL(n) {
  if (cache.has(n)) return cache.get(n);
  const blob = await sliceFor(n);
  const iv = new Uint8Array(blob.slice(0, 12));
  const pt = await crypto.subtle.decrypt({name:'AES-GCM', iv}, key, blob.slice(12));
  const url = URL.createObjectURL(new Blob([pt], {type:'image/jpeg'}));
  cache.set(n, url);
  return url;
}
async function show(n) {
  if (n < 1 || n > TOTAL) return;
  cur = n;
  document.getElementById('loading').classList.add('on');
  const url = await slideURL(n);
  const img = document.getElementById('slide');
  img.src = url;
  document.getElementById('loading').classList.remove('on');
  document.getElementById('count').textContent = n + ' / ' + TOTAL;
  document.getElementById('prev').disabled = (n === 1);
  document.getElementById('next').disabled = (n === TOTAL);
  if (n < TOTAL) slideURL(n + 1);
}
async function unlock() {
  const pw = document.getElementById('pw').value;
  const btn = document.getElementById('go');
  const err = document.getElementById('err');
  if (!pw) return;
  btn.textContent = 'Unlocking\\u2026'; err.textContent = '';
  try {
    key = await deriveKey(pw);
    await slideURL(1);
    document.getElementById('gate').style.display = 'none';
    document.querySelector('.viewer').classList.add('on');
    show(1);
  } catch (e) {
    key = null;
    err.textContent = 'Incorrect password.';
    const card = document.querySelector('.gate-card');
    card.classList.remove('shake'); void card.offsetWidth; card.classList.add('shake');
  }
  btn.textContent = 'View deck';
}
document.getElementById('go').addEventListener('click', unlock);
document.getElementById('pw').addEventListener('keydown', e => {
  if (e.key === 'Enter') unlock();
});
document.getElementById('prev').addEventListener('click', () => show(cur - 1));
document.getElementById('next').addEventListener('click', () => show(cur + 1));
document.addEventListener('keydown', e => {
  if (!key) return;
  if (e.key === 'ArrowRight' || e.key === ' ') show(cur + 1);
  if (e.key === 'ArrowLeft') show(cur - 1);
});
let tx = null;
document.addEventListener('touchstart', e => { tx = e.touches[0].clientX; }, {passive:true});
document.addEventListener('touchend', e => {
  if (tx === null || !key) return;
  const dx = e.changedTouches[0].clientX - tx;
  if (dx < -50) show(cur + 1);
  if (dx > 50) show(cur - 1);
  tx = null;
}, {passive:true});
""" % (meta["salt"], meta["iterations"], json.dumps(sizes), slug)

decks_src = CONTENT / "decks"
if decks_src.exists():
    (OUT / "decks").mkdir(exist_ok=True)
    for packf in sorted(decks_src.glob("*.pack")):
        slug = packf.stem
        meta = json.loads((decks_src / f"{slug}.json").read_text())
        shutil.copy(packf, OUT / "decks" / packf.name)
        title = meta["title"]
        viewer = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — Investor Deck — Directive 17</title>
<meta name="robots" content="noindex,nofollow">
<link rel="icon" type="image/png" href="../images/logos/enso.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700&display=swap" rel="stylesheet">
<style>{DECK_CSS}</style>
</head>
<body>
<div class="topbar">
<a class="brand" href="../companies.html"><img src="../images/logos/enso.webp" alt="">Directive 17</a>
<div class="dtitle">{html.escape(title)} &middot; Investor Deck</div>
<div class="count" id="count"></div>
</div>
<div class="gate" id="gate">
<div class="gate-card">
<img src="../images/logos/enso.webp" alt="">
<div class="glabel">Confidential &middot; Investor Deck</div>
<h1>{html.escape(title)}</h1>
<input type="password" id="pw" placeholder="Password" autocomplete="off" autofocus>
<button id="go">View deck</button>
<div class="err" id="err"></div>
<div class="note">This deck is confidential. Please do not distribute.<br>
Need access? <span style="color:var(--cream)">{site['contact_email']}</span></div>
</div>
</div>
<div class="viewer">
<div class="stage">
<button class="arrow prev" id="prev" aria-label="Previous slide">&larr;</button>
<img id="slide" alt="{html.escape(title)} slide">
<div class="loading" id="loading">DECRYPTING&hellip;</div>
<button class="arrow next" id="next" aria-label="Next slide">&rarr;</button>
</div>
<div class="bottom">Confidential &mdash; do not distribute</div>
</div>
<script>{deck_js(slug, meta)}</script>
</body>
</html>"""
        (OUT / "decks" / f"{slug}.html").write_text(viewer)

# ---------------- 404 (root-relative links: GitHub Pages serves this at any path)
nf_body = f"""
<div class="hero hero-home"><div class="wrap hero-flex">
<div>
<div class="kicker fade" style="--d:.05s">404</div>
<h1 class="display">{words("This page doesn't exist.", .2, .08)}</h1>
<p class="sub fade" style="--d:.8s">The future does. Let's get you back to it.</p>
<p class="fade" style="--d:1s;margin-top:36px"><a class="btn" href="/">Back home <span class="arr">&rarr;</span></a></p>
</div>
<div class="hero-enso floaty"><img src="/images/logos/enso.webp" alt="Directive 17 enso"></div>
</div></div>"""
nf = page(f"Not Found — {site['name']}", nf_body, "", 0, path="404.html",
          desc="This page doesn't exist. The future does.")
nf = nf.replace('href="images/', 'href="/images/').replace('src="images/', 'src="/images/')
nf = nf.replace('href="index.html"', 'href="/"')
for _n in site["nav"]:
    _h = _n["href"].lstrip("/")
    nf = nf.replace(f'href="{_h}"', f'href="/{_h}"')
(OUT / "404.html").write_text(nf)

# ---------------- crawler files: sitemap, robots (AI bots welcome), llms.txt
from datetime import date as _date
_today = _date.today().isoformat()
_urls = ["", "why.html", "philosophy.html", "companies.html", "future.html",
         "build.html", "founders-note.html", "blog/"] + [f"blog/{p['slug']}.html" for p in posts]
_sm = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in _urls:
    pri = "1.0" if u == "" else ("0.8" if u.startswith("blog") else "0.7")
    _sm.append(f"<url><loc>https://{site['domain']}/{u}</loc>"
               f"<lastmod>{_today}</lastmod><priority>{pri}</priority></url>")
_sm.append("</urlset>")
(OUT / "sitemap.xml").write_text("\n".join(_sm))

# AI crawlers are explicitly welcomed; the confidential deck viewers are not indexed
_ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User",
            "Claude-SearchBot", "anthropic-ai", "PerplexityBot", "Perplexity-User",
            "Google-Extended", "Applebot-Extended", "CCBot", "Bytespider", "meta-externalagent"]
_rb = ["# Directive 17 — all crawlers welcome, including AI assistants",
       "User-agent: *", "Allow: /", "Disallow: /decks/", ""]
for bot in _ai_bots:
    _rb += [f"User-agent: {bot}", "Allow: /", "Disallow: /decks/", ""]
_rb.append(f"Sitemap: https://{site['domain']}/sitemap.xml")
(OUT / "robots.txt").write_text("\n".join(_rb))

_ll = [f"# Directive 17", "", f"> {site['subline']} {site['tagline']}", "",
       "Directive 17 is an early-stage venture firm founded by Joel Shapiro. Every company "
       "begins with one question: how will this make someone's life better? Only then do we "
       "ask whether it can become a great business.", "",
       "## Pages", ""]
_ll += [f"- [Why We Exist](https://{site['domain']}/why.html): Most organizations begin with markets. We begin with people.",
        f"- [Philosophy](https://{site['domain']}/philosophy.html): The Five Pillars — happiness, health, trust, connection, human potential — and the Human Test.",
        f"- [Companies](https://{site['domain']}/companies.html): Portfolio companies. Different companies. One philosophy.",
        f"- [The Future We See](https://{site['domain']}/future.html): What future is worth building?",
        f"- [Build With Us](https://{site['domain']}/build.html): Contact — {site['contact_email']}",
        f"- [A Note from the Founder](https://{site['domain']}/founders-note.html): Joel Shapiro on creating rather than consuming.",
        "", "## Joel's Blog", ""]
_ll += [f"- [{p['title']}](https://{site['domain']}/blog/{p['slug']}.html): {p['excerpt']}" for p in posts]
(OUT / "llms.txt").write_text("\n".join(_ll) + "\n")

print(f"Built {len(list(OUT.rglob('*.html')))} pages, {len(posts)} posts, {len(companies)} companies -> docs/")
