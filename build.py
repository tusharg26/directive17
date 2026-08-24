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
--serif:Georgia,'Times New Roman',serif;
--sans:'Helvetica Neue',Helvetica,Arial,sans-serif;
--ease:cubic-bezier(.22,.61,.21,1)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--serif);font-size:17.5px;
line-height:1.7;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit;text-decoration:none}
img{max-width:100%}
::selection{background:var(--deep);color:var(--bg)}
.wrap{max-width:1100px;margin:0 auto;padding:0 28px}
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
.hero-home{min-height:calc(100vh - 75px);display:flex;align-items:center;padding:40px 0}
.hero-flex{display:flex;align-items:center;gap:64px;justify-content:space-between;width:100%}
.hero-enso{flex:0 0 auto;width:min(320px,30vw)}
.kicker{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.24em;color:var(--accent);margin-bottom:26px}
h1.display{font-family:var(--serif);font-weight:700;letter-spacing:-.015em;
font-size:clamp(2.6rem,6vw,4.6rem);line-height:1.06;max-width:16ch;color:var(--deep)}
.sub{color:var(--muted);font-size:1.22rem;max-width:46ch;margin-top:28px}
/* ---------- editorial building blocks ---------- */
section{padding:90px 0}
.rule{border:none;border-top:1px solid var(--line)}
.sec-label{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.24em;color:var(--accent);margin-bottom:34px}
.statement{font-family:var(--serif);color:var(--deep);letter-spacing:-.015em;
font-size:clamp(2rem,4.8vw,3.4rem);line-height:1.15;max-width:22ch}
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
.belief-row .btext{font-family:var(--serif);font-size:clamp(1.5rem,3.4vw,2.3rem);
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
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:22px}
.card{display:block;text-align:center}
.tile{border-radius:14px;height:112px;display:flex;align-items:center;justify-content:center;
padding:18px;transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.card:hover .tile{transform:translateY(-6px) scale(1.02);box-shadow:0 16px 32px rgba(32,60,45,.16)}
.tile-dark{background:var(--deep)}
.tile-light{background:#FDFBF3;border:1px solid var(--line)}
.tile img{max-width:82%;max-height:74px;object-fit:contain}
.card h3{font-family:var(--sans);font-size:.86rem;font-weight:600;color:var(--ink);
margin-top:14px;line-height:1.35}
.card p{color:var(--muted);font-size:.85rem;margin-top:6px}
.group-label{font-family:var(--sans);font-size:.72rem;font-weight:700;text-transform:uppercase;
letter-spacing:.2em;color:var(--accent);margin:64px 0 30px;display:flex;align-items:center;gap:18px}
.group-label::after{content:"";flex:1;height:1px;background:var(--line)}
.group-label:first-of-type{margin-top:0}
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
"""

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
      var url = location.origin + location.pathname + '#' + b.dataset.slug;
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

def page(title, body, active="", depth=0, extra_js=""):
    p = "../" * depth
    links = [("Home", f"{p}index.html", active == "")]
    links += [(n["label"], f'{p}{n["href"].lstrip("/")}', n["label"] == active) for n in site["nav"]]
    nav = "".join(
        f'<a href="{href}" class="m-link {"active" if act else ""}" style="--i:{i}">{label}</a>'
        for i, (label, href, act) in enumerate(links))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(site['subline'])}">
<link rel="icon" type="image/png" href="{p}images/logos/enso.png">
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap nav">
<a class="logo" href="{p}index.html"><img src="{p}images/logos/enso.png" alt="Directive 17 enso logo">Directive 17</a>
<button class="menu-btn" id="menu-btn" aria-label="Open menu" aria-expanded="false">
<span></span><span></span><span></span>
</button>
</div></header>
<nav class="menu-overlay" id="menu" aria-hidden="true">
<button class="menu-close" id="menu-close" aria-label="Close menu">&times;</button>
<div class="m-label">Directive 17</div>
{nav}
<div class="m-foot"><a href="mailto:{site['contact_email']}">{site['contact_email']}</a>
&nbsp;&middot;&nbsp; Directive 17 &copy; 2026</div>
</nav>
{body}
<script>{SHARED_JS}{extra_js}</script>
</body>
</html>"""

def company_card(c, depth=0, delay=0.0):
    p = "../" * depth
    dark = "Proprietary" in c.get("group", "Proprietary")
    tile_cls = "tile-dark" if dark else "tile-light"
    logo = (f'<img src="{p}images/{c["logo"]}" alt="{html.escape(c["name"])} logo">'
            if c.get("logo") else f'<span style="font-family:var(--serif);font-size:1.4rem;'
            f'color:{"#FBF7EC" if dark else "var(--deep)"}">{html.escape(c["name"][0])}</span>')
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
if site.get("domain"):
    (OUT / "CNAME").write_text(site["domain"])

posts = sorted((parse_post(p) for p in (CONTENT / "posts").glob("*.md")),
               key=lambda x: x["date"], reverse=True)

# ---------------- home: hero only, animated
home = f"""
<div class="hero hero-home"><div class="wrap hero-flex">
<div>
<div class="kicker fade" style="--d:.05s">Directive 17</div>
<h1 class="display">{words(site['tagline'], .25, .09)}</h1>
<p class="sub fade" style="--d:.95s">{html.escape(site['subline'])}</p>
</div>
<div class="hero-enso floaty"><img src="images/logos/enso.png" alt="Directive 17 enso"></div>
</div></div>"""
(OUT / "index.html").write_text(page(f"{site['name']} — {site['tagline']}", home, "", 0))

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
(OUT / "why.html").write_text(page(f"Why — {site['name']}", why, "Why"))

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
<img class="watermark" src="images/logos/enso.png" alt="">
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
(OUT / "philosophy.html").write_text(page(f"Philosophy — {site['name']}", philosophy, "Philosophy"))

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
(OUT / "future.html").write_text(page(f"Future — {site['name']}", future, "Future"))

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
(OUT / "companies.html").write_text(page(f"Companies — {site['name']}", companies_body, "Companies"))

# ---------------- long-form markdown pages (Joel's Directive)
page_titles = {"joels-directive": "Joel's Directive"}
for stem, label in page_titles.items():
    src = CONTENT / "pages" / f"{stem}.md"
    if src.exists():
        body = (f'<div class="wrap"><article class="prose">'
                f'<div class="kicker fade" style="--d:.05s">{label}</div>'
                f'{md_to_html(src.read_text())}</article></div>')
        (OUT / f"{stem}.html").write_text(
            page(f"{label} — {site['name']}", body, label))

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
<h1 class="display">{words('Question more. Build more.', .25, .09)}</h1>
</div></div>
<section style="padding-top:20px"><div class="wrap">{rows}</div></section>"""
(OUT / "blog" / "index.html").write_text(
    page(f"Joel's Blog — {site['name']}", blog_body, "Joel's Blog", 1, extra_js=BLOG_JS))

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
<div class="hero-enso floaty"><img src="images/logos/enso.png" alt="Directive 17 enso"></div>
</div></div>"""
(OUT / "build.html").write_text(page(f"Build With Us — {site['name']}", build_body, "Build With Us"))

print(f"Built {len(list(OUT.rglob('*.html')))} pages, {len(posts)} posts, {len(companies)} companies -> docs/")
