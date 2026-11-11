#!/usr/bin/env python3
"""Directive 17 static site builder — 2026 redesign (v16).

Zero dependencies. Reads content/ and theme/ and writes the finished site into docs/
(which GitHub Pages serves). Run:  python3 build.py

Words live in content/:
  content/site.json        - page copy: tagline, nav, pillars, why/philosophy/future/build/companies/blog pages
  content/seo.json         - page titles and search/share descriptions
  content/companies.json   - portfolio: name, group, logo + logo sizes, website, dark/light logo tile
  content/companies/*.md   - each company's overview, one paragraph per blank-line-separated block
  content/pages/founders-note.md - the founder's note (also opens in place on the home page)
  content/posts/*.md       - blog posts, filename YYYY-MM-DD-slug.md with frontmatter (title, date, excerpt)
  content/images/          - logos and images (copied to the site as-is)
  content/decks/           - encrypted investor decks (see tools/encrypt_deck.py)
The look lives in theme/: site.css, site.js and fonts/ (copied to docs/assets/).
"""
import json, re, shutil, html, hashlib
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
THEME = ROOT / "theme"
OUT = ROOT / "docs"


def versioned(name):
    """/assets/<name>?v=<fingerprint of the file>. When the look changes, every page points at a new address, so a phone
    that reloads gets the new stylesheet/script at once instead of a saved copy (GitHub Pages lets browsers keep files
    for 10 minutes). Line endings are ignored, so a Windows checkout builds the same pages."""
    data = (THEME / name).read_bytes().replace(b"\r\n", b"\n")
    return f"/assets/{name}?v={hashlib.sha256(data).hexdigest()[:10]}"


CSS_URL, JS_URL = versioned("site.css"), versioned("site.js")


def read(p):
    return Path(p).read_text(encoding="utf-8")


def write(p, s):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


site = json.loads(read(CONTENT / "site.json"))
seo = json.loads(read(CONTENT / "seo.json"))
companies = json.loads(read(CONTENT / "companies.json"))
URL = f"https://{site['domain']}"
EMAIL = site["contact_email"]
esc = html.escape          # text and attributes (escapes quotes too)


def tx(s):                 # text where quotes are left as typed
    return html.escape(s, quote=False)


def wbr(s):                # allow long slash-joined titles to wrap after each slash
    return s.replace("/", "/<wbr>")


def img_size(path):
    """(width, height) of a PNG or WebP file, read from its header (no dependencies)."""
    import struct
    d = Path(path).read_bytes()[:40]
    if d[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", d[16:24])
    if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
        kind = d[12:16]
        if kind == b"VP8X":
            return (1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little"))
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", d[26:30]); return (w & 0x3FFF, h & 0x3FFF)
        if kind == b"VP8L":
            b0 = int.from_bytes(d[21:25], "little"); return ((b0 & 0x3FFF) + 1, ((b0 >> 14) & 0x3FFF) + 1)
    return (1, 1)


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
        # numbered lines ("1. Collecting Limes.") stay as ordinary paragraphs, exactly as typed
        para.append(s)
    flush_para(); flush_list()
    return "\n".join(out)


def parse_post(path):
    raw = read(path)
    meta, body = {}, raw
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        for ln in fm.strip().splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip()
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
    title = meta.get("title", slug.replace("-", " ").title())
    body = body.strip()
    # a bold first line that only repeats the title is not shown twice
    m = re.match(r"^\*\*(.+?)\*\*[ \t]*(\n|$)", body)
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    if m and norm(m.group(1)) == norm(title):
        body = body[m.end():].strip()
    html_body = md_to_html(body)
    return {
        "title": title,
        "date": meta.get("date", ""),
        "excerpt": meta.get("excerpt", ""),
        "order": int(meta.get("order", "0") or 0),
        "slug": slug,
        "html": html_body,
        "words": len(re.sub(r"<[^>]+>", " ", html_body).split()),
    }


def as_date(d):
    y, m, dd = map(int, d.split("-"))
    return date(y, m, dd)


def long_date(d):          # November 9, 2026
    x = as_date(d); return f"{x:%B} {x.day}, {x.year}"


def minutes(n_words):
    return max(1, round(n_words / 200))


def words(text, cls="w", fmt=lambda w: w):
    """Headline words that rise one by one (each in its own span)."""
    return " ".join(f'<span class="{cls}" style="--i:{i}"><span>{fmt(esc(w))}</span></span>'
                    for i, w in enumerate(text.split()))


def ld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


def crumbs(*items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}


HOME_CRUMB = ("Home", URL + "/")
FOUNDER = {"@type": "Person", "@id": URL + "/#founder", "name": "Joel Shapiro", "url": URL + "/founders-note.html"}
PUBLISHER = {"@type": "Organization", "@id": URL + "/#organization", "name": site["name"],
             "logo": {"@type": "ImageObject", "url": URL + "/images/logos/enso.png"}}
ORG = {"@context": "https://schema.org", "@type": "Organization", "@id": URL + "/#organization",
       "name": site["name"], "alternateName": [site["name"].replace(" ", "")], "url": URL + "/",
       "logo": URL + "/images/logos/enso.png", "description": seo["org_description"],
       "slogan": site["tagline"], "email": EMAIL,
       "founder": {"@type": "Person", "@id": URL + "/#founder", "name": "Joel Shapiro",
                   "url": URL + "/founders-note.html", "jobTitle": "Founder"},
       "sameAs": [site["linkedin"]]}
BLOG = site["blog_page"]

# shown when JavaScript is off: everything visible, menu laid out flat
NOSCRIPT = ('<noscript><style>.w>span,.lw>span,.fade,.rv,.way .yes{opacity:1!important;transform:none!important;filter:none!important}'
            '.burger,.circle .spin,.circle .spark,.mcopy,.iris .icue{display:none}.bar{position:absolute;color:var(--bg)}'
            '.menu{position:static;display:block;opacity:1;visibility:visible;padding:calc(var(--barH) + 4px) var(--gut) 14px}'
            '.circle{width:auto;aspect-ratio:auto;display:flex;flex-wrap:wrap;align-items:center;gap:4px 22px}'
            '.circle a.item,.circle a.item.r,.circle a.item.l{position:static;transform:none;font-size:1.05rem;padding:6px 0}'
            '.circle a.item span{opacity:1;animation:none}.circle .ctr{position:static;transform:none;opacity:1}'
            '.circle .ctr a.contact{font-size:1.05rem;padding:.2em .7em .26em}.iris{height:auto}.iris .stick{position:relative}'
            '.orb{height:auto;display:flex;flex-wrap:wrap;gap:14px;margin-top:24px}.orb .core,.orb .tracks,.orb .readout{display:none}'
            '.pl{position:static;width:auto}.pl .disc{width:104px;height:104px}</style></noscript>')

# the circular menu: six items placed every 60 degrees around the enso
NAV_STYLES = ["--i:0;--ux:0.0000;--uy:-0.4625", "--i:1;--ax:0.4005;--uy:-0.2312", "--i:2;--ax:0.4005;--uy:0.2312",
              "--i:3;--ux:0.0000;--uy:0.4625", "--i:4;--ax:0.4005;--uy:0.2312", "--i:5;--ax:0.4005;--uy:-0.2313"]
ENSO_HD = img_size(CONTENT / "images" / "logos" / "enso-hd.webp")

# the opening curtain on the home page: forest green, the enso turns in and the name settles under it, then it lifts away.
# Shown once per browser session (not on a link straight to a section, not with reduced motion, never without JavaScript).
INTRO_HEAD = ("<script>try{var h=document.documentElement;if(!sessionStorage.getItem('d17i')&&!location.hash&&"
              "!matchMedia('(prefers-reduced-motion: reduce)').matches)h.classList.add('intro-on');"
              "sessionStorage.setItem('d17i','1')}catch(e){}</script>\n")
INTRO_HTML = ('<div id="intro" aria-hidden="true"><div class="intro-in">'
              f'<img src="/images/logos/enso-hd.webp" alt="" width="{ENSO_HD[0]}" height="{ENSO_HD[1]}">'
              f'<div class="intro-name">{esc(site["name"])}</div></div></div>\n')


def nav(prefix, current):
    n = len(site["nav"])
    items = []
    for i, it in enumerate(site["nav"]):
        deg = round(360 * i / n)
        cls = "c" if deg in (0, 180) else ("r" if deg < 180 else "l")
        if n == 6:
            style = NAV_STYLES[i]
        else:
            import math
            a = math.radians(deg); ux, uy = 0.4625 * math.sin(a), -0.4625 * math.cos(a)
            style = (f"--i:{i};--ux:{ux:.4f};--uy:{uy:.4f}" if cls == "c" else f"--i:{i};--ax:{abs(ux):.4f};--uy:{uy:.4f}")
        cur = it["href"] == current
        items.append(f'<a class="item {cls}{" cur" if cur else ""}" href="{prefix}{it["href"].lstrip("/")}" data-deg="{deg}"'
                     f'{" aria-current=" + chr(34) + "page" + chr(34) if cur else ""} style="{style}"><span>{esc(it["label"])}</span></a>')
    return ('<nav class="menu" id="menu" aria-label="Site menu"><div class="circle" id="circle">'
            f'<div class="spin" id="spin"><img src="/images/logos/enso-hd.webp" alt="" width="{ENSO_HD[0]}" height="{ENSO_HD[1]}" decoding="async" fetchpriority="low"></div>'
            '<span class="spark" id="spark"></span>' + "".join(items) +
            f'<div class="ctr"><a class="contact" href="mailto:{EMAIL}">Contact</a></div></div>'
            f'<div class="mcopy">{esc(site["name"])} &copy; {date.today().year}</div></nav>')


def page(path, data_page, title, desc, body, current="", og_type="website", lds=(), head_extra="", ring=False,
         dark_top=False, intro=False):
    """A full page. path is relative to the site root (e.g. 'blog/x.html').
    dark_top: the page opens on a forest section, so the top bar starts light-on-dark (no flash, no reliance on the script).
    intro: the opening curtain (home page, first visit in a session)."""
    depth = path.count("/")
    prefix = "/" if path == "404.html" else "../" * depth
    canon = URL + "/" + re.sub(r"(^|/)index\.html$", r"\1", path)
    t, d = esc(title), esc(desc)
    head = (
        "<!DOCTYPE html>\n<html lang=\"en\"" + (' class="ondark"' if dark_top else "") + ">\n<head>"
        + ('<base href="/">' if path == "404.html" else "") + "\n"
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        + (INTRO_HEAD if intro else "") +
        f"<title>{t}</title>\n<meta name=\"description\" content=\"{d}\">\n<meta name=\"theme-color\" content=\"#FBF7EC\">\n"
        f'<link rel="canonical" href="{canon}">\n<meta property="og:type" content="{og_type}">\n'
        f'<meta property="og:site_name" content="{esc(site["name"])}">\n<meta property="og:title" content="{t}">\n'
        f'<meta property="og:description" content="{d}">\n<meta property="og:url" content="{canon}">\n'
        f'<meta property="og:image" content="{URL}/images/og-card.png">\n<meta property="og:image:alt" content="{esc(seo["og_image_alt"])}">\n'
        '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="{t}">\n'
        f'<meta name="twitter:description" content="{d}">\n<meta name="twitter:image" content="{URL}/images/og-card.png">\n'
        '<link rel="icon" type="image/png" href="/images/logos/enso.png">\n<link rel="apple-touch-icon" href="/images/apple-touch-icon.png">\n'
        f'<link rel="alternate" type="application/rss+xml" title="{esc(BLOG["title"] + " — " + site["name"])}" href="{URL}/blog/feed.xml">\n'
        + head_extra +
        '<link rel="stylesheet" href="' + CSS_URL + '">\n' + NOSCRIPT + "\n" + ld(ORG) + "".join(ld(x) for x in lds) + "\n</head>\n")
    chrome = (
        f'<body data-page="{data_page}">\n' + (INTRO_HTML if intro else "")
        + '<a class="skip" href="#main">Skip to content</a>\n'
        + ('<header class="bar inv" id="bar">\n' if dark_top else '<header class="bar" id="bar">\n') +
        f'  <a class="brand" href="{prefix}index.html" aria-label="{esc(site["name"])} home"><img id="navEnso" src="/images/logos/enso-sm.webp" alt="" width="36" height="36"><span>{esc(site["name"])}</span></a>\n'
        '  <button class="burger" id="menuBtn" aria-label="Open menu" aria-expanded="false" aria-controls="menu"><span></span></button>\n'
        "</header>\n" + nav(prefix, current) + "\n"
        + ('<button class="ring" id="ring" aria-label="Back to top"><img class="ghost-e" src="/images/logos/enso-sm.webp" alt=""><img id="ringImg" src="/images/logos/enso-sm.webp" alt=""></button>\n'
           if ring else "\n")
        + '<main id="main">\n')
    goat = (f'<script data-goatcounter="https://{site["goatcounter"]}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
            if site.get("goatcounter") else "")
    write(OUT / path, head + chrome + body + "</main>\n\n<script src=\"" + JS_URL + "\"></script>\n" + goat + "</body>\n</html>")


def pmeta(key, **kw):
    e = seo["pages"][key]
    return e.get("title", "").format(**kw), e.get("description", "").format(**kw)


# ================================================================ build
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
shutil.copytree(CONTENT / "images", OUT / "images", dirs_exist_ok=True)
shutil.copytree(THEME, OUT / "assets", dirs_exist_ok=True)
write(OUT / ".nojekyll", "")
if site.get("domain") and site.get("live"):
    write(OUT / "CNAME", site["domain"])

# newest first; for posts on the same date, a higher frontmatter "order" comes first, then filename
posts = sorted((parse_post(p) for p in sorted((CONTENT / "posts").glob("*.md"))),
               key=lambda x: (x["date"], x["order"]), reverse=True)

# ---------------- the founder's note (its own page, and the home-page card that opens it in place)
fn_src = read(CONTENT / "pages" / "founders-note.md")
fn_title = next(l[2:].strip() for l in fn_src.splitlines() if l.startswith("# "))
fn_body = re.sub(r"^#\s+.*\n", "", fn_src, count=1)
fn_lede_m = re.search(r"^\*\*(.+?)\*\*\s*$", fn_body, flags=re.M)
fn_lede = fn_lede_m.group(1) if fn_lede_m else ""
if fn_lede_m:
    fn_body = fn_body.replace(fn_lede_m.group(0), "", 1)
fn_body = fn_body.replace("<!--more-->", "")
fn_minutes = minutes(len(fn_body.split()))
fn_prose = md_to_html(fn_body.strip())
FN_URL = URL + "/founders-note.html"
FN_ENDMARK = (f'<img src="/images/logos/enso-sm.webp" alt=""><button class="share" type="button" data-share="{FN_URL}" '
              f'data-title="{esc(fn_title)}">Share this post</button>')


def endmark(url, title, rv=True):
    return (f'<div class="endmark{" rv" if rv else ""}"><img src="/images/logos/enso-sm.webp" alt="">'
            f'<button class="share" type="button" data-share="{url}" data-title="{esc(title)}">Share this post</button></div>')


# ---------------- home
_feat = (site.get("featured_post") or "").strip()
newest = next((x for x in posts if x["slug"] == _feat), None) if _feat else None
newest = newest or (posts[0] if posts else None)
tw = site["tagline"].split()
hero_h = " ".join(f'<span class="lw" style="--i:{i}"><span>{esc(w)}</span></span>' for i, w in enumerate(tw[:-2]))
hero_h += ' <span class="s2">' + " ".join(f'<span class="lw" style="--i:{i + len(tw) - 2}"><span>{esc(w)}</span></span>'
                                        for i, w in enumerate(tw[-2:])) + "</span>"
newpost = ""
if newest:
    newpost = (f'\n  <a class="newpost" href="blog/{newest["slug"]}.html">\n'
               f'    <span class="tag"><i></i>New post &middot; {esc(BLOG["kicker"])}</span>\n'
               f'    <span><span class="np-title">{esc(newest["title"])}</span><span class="np-ex">{esc(newest["excerpt"])}</span></span>\n'
               f'    <span class="when">{long_date(newest["date"])}<b>Read &rarr;</b></span>\n  </a>')
home = f"""
<section class="iris" id="iris"><div class="stick" id="irisStick">
  <canvas class="skyc" aria-hidden="true"></canvas>
  <div class="ens" id="ens"><img src="/images/logos/enso-hd.webp" alt="" width="{ENSO_HD[0]}" height="{ENSO_HD[1]}" fetchpriority="high"></div>
  <div class="hc"><h1 id="heroH">{hero_h}</h1></div>
  <p class="sub" id="heroSub">{esc(site["subline"])}</p>
  <button class="icue" id="cue" type="button" aria-label="Scroll down"><svg viewBox="0 0 16 16"><path d="M8 2.5v10M3.5 8.5 8 13l4.5-4.5"/></svg></button>
</div></section>

<section class="notesec"><div class="wrap">
  <a class="note-card" href="founders-note.html" data-go="founders-note" aria-expanded="false">
    <img class="ns" src="/images/logos/enso-md.webp" alt="">
    <div><div class="label">{esc(site["home_note"]["label"])}</div><h2>{esc(fn_title)}</h2><p>{esc(fn_lede)}</p>
      <span class="readnote">{esc(site["home_note"]["link"])}</span><span class="readmeta">Joel Shapiro &middot; {fn_minutes} min read</span></div>
  </a>
  <div class="note-full" id="note-full"><div class="nf-in"><div class="nf-body"><div class="prose">{fn_prose}</div><div class="endmark">{FN_ENDMARK}</div></div></div></div>{newpost}
</div></section>
"""
t, d = pmeta("home")
page("index.html", "home", t, d, home, intro=True,
     lds=[{"@context": "https://schema.org", "@type": "WebSite", "@id": URL + "/#website", "name": site["name"],
           "alternateName": [site["name"].replace(" ", "")], "url": URL + "/", "inLanguage": "en",
           "publisher": {"@id": URL + "/#organization"}}],
     head_extra='<link rel="preload" as="image" href="/images/logos/enso-hd.webp" fetchpriority="high">\n')

# ---------------- founder's note page
fn_body_html = f"""
<article class="article"><div class="wrap">
  <div class="head"><a class="back" href="index.html">&larr; Home</a>
  <h1>{words(fn_title)}</h1>
  <div class="byline fade" style="--d:.6s"><img src="/images/logos/enso-sm.webp" alt=""><span>Joel Shapiro <span class="sep">&middot;</span> Founder <span class="sep">&middot;</span> {fn_minutes} min read</span><button class="share" type="button" data-share="{FN_URL}" data-title="{esc(fn_title)}">Share</button></div></div>
  <div class="prose"><p class="lede-p">{esc(fn_lede)}</p>{fn_prose}</div>
  {endmark(FN_URL, fn_title)}
{"  "}
</div></article>
"""
_, d = pmeta("note", title=fn_title, lede=fn_lede)
page("founders-note.html", "note", fn_title, d, fn_body_html, og_type="article", ring=True,
     lds=[{"@context": "https://schema.org", "@type": "Article", "headline": fn_title, "description": fn_lede,
           "author": FOUNDER, "publisher": PUBLISHER, "image": URL + "/images/og-card.png", "inLanguage": "en",
           "about": {"@id": URL + "/#organization"}, "isPartOf": {"@id": URL + "/#website"},
           "mainEntityOfPage": FN_URL, "url": FN_URL},
          crumbs(HOME_CRUMB, (seo["pages"]["note"]["crumb"], FN_URL))])

# ---------------- why
W_ = site["why_page"]
why = f"""
<div class="hero"><div class="wrap">
  <div class="label tl fade" style="--d:.05s">{esc(W_["kicker"])}</div>
  <div class="muted-line fade" style="--d:.25s;margin-top:22px">{esc(W_["line1"])}</div>
  <h1 class="display">{words(W_["line2"])}</h1>
</div></div>
<section style="padding-top:0"><div class="wrap">
  <div class="why-cols bigtext">{"".join(f"<p>{esc(p)}</p>" for p in W_["paragraphs"])}</div>
</div></section>
<section style="padding-top:0"><div class="wrap">
  <div class="label tl rv">{esc(W_["belief_label"])}</div>
  <h2 class="h2 rv" style="margin:14px 0 calc(30px + .32em);max-width:24ch"><span class="stroke">{esc(W_["belief_intro"])}<svg viewBox="0 0 100 10" preserveAspectRatio="none"><path pathLength="1" d="M2 6 C 25 2, 55 9, 98 4"/></svg></span></h2>
  {"".join(f'<div class="belief rv"><div class="g">{i + 1:02d}</div><div class="btext">{esc(b)}</div></div>' for i, b in enumerate(W_["beliefs"]))}
</div></section>
"""
t, d = pmeta("why")
page("why.html", "why", t, d, why, current="/why.html", lds=[crumbs(HOME_CRUMB, (seo["pages"]["why"]["crumb"], URL + "/why.html"))])

# ---------------- philosophy
P_ = site["philosophy_page"]
STRIKE = '<svg viewBox="0 0 100 10" preserveAspectRatio="none"><path pathLength="1" d="M1 6 C 30 3, 60 8, 99 4"/></svg>'
_q = P_["human_test"]["question"]
_qw = _q.rsplit(" ", 1)          # the last word is set in italics: "...life better?"
_qlast = re.match(r"^(\w+)(.*)$", _qw[1])
big_q = f'&ldquo;{esc(_qw[0])} <em>{esc(_qlast.group(1))}</em>{esc(_qlast.group(2))}&rdquo;'
closing = " ".join(f"<span>{esc(s.strip())}</span>" for s in re.findall(r"[^.]+\.", P_["way"]["closing"]))
phil = f"""
<div class="hero"><div class="wrap">
  <div class="label tl fade" style="--d:.05s">{esc(P_["kicker"])}</div>
  <h1 class="h1" style="margin-top:20px;max-width:18ch">{words(P_["opening"])}</h1>
  <div class="qgrid"><div class="q fade" style="--d:1.1s">{esc(P_["q1"])}</div><div class="q q2 fade" style="--d:1.4s">{esc(P_["q2"])}</div></div>
  <div class="answer fade" style="--d:1.8s">{esc(P_["answer"])}</div>
</div></div>
<section style="padding-top:10px"><div class="wrap">
  <div class="label tl rv">{esc(P_["pillars_label"])}</div>
  <h2 class="h2 rv" style="margin-top:14px">{esc(P_["pillars_intro"])}</h2>
  <div class="five">{"".join(f'<div class="c rv" style="--d:{i * 0.08:.2f}s"><span class="n">{esc(p["num"])}</span><h3>{esc(p["title"])}</h3><p>{esc(p["body"])}</p></div>' for i, p in enumerate(site["home_pillars"]))}</div>
</div></section>
<section class="dark test"><canvas class="skyc" aria-hidden="true"></canvas><img class="wm" src="/images/logos/enso-hd.webp" alt="" loading="lazy" decoding="async"><div class="wrap" style="position:relative">
  <div class="label tl rv">{esc(P_["human_test"]["label"])}</div>
  <p style="color:var(--sageOnDark);font-size:1.02rem;margin-top:18px">{esc(P_["human_test"]["intro"])}</p>
  <div class="big-q rv" style="--d:.15s">{big_q}</div>
  <p class="after">{esc(P_["human_test"]["after"])}</p>
</div></section>
<section><div class="wrap">
  <div class="label tl rv">{esc(P_["way"]["label"])}</div>
  <h2 class="h1 rv" style="margin:14px 0 26px">{esc(P_["way"]["lede"])}</h2>
  {"".join(f'<div class="way rv"><div class="no"><span class="nt">{esc(a)}</span>{STRIKE}</div><div class="yes">{esc(b)}</div></div>' for a, b in P_["way"]["pairs"])}
  <p class="closing" style="margin-top:52px">{closing}</p>
</div></section>
"""
t, d = pmeta("philosophy")
page("philosophy.html", "philosophy", t, d, phil, current="/philosophy.html",
     lds=[crumbs(HOME_CRUMB, (seo["pages"]["philosophy"]["crumb"], URL + "/philosophy.html"))])

# ---------------- future
F_ = site["future_page"]
_rot = ["-3deg", "2deg", "-1.5deg", "3deg", "-2deg", "1.5deg"]
future = f"""
<div class="hero"><div class="wrap">
  <div class="label tl fade" style="--d:.05s">{esc(F_["kicker"])}</div>
  <div class="muted-line fade" style="--d:.25s;margin-top:22px">{esc(F_["old_q"])}</div>
  <h1 class="display" style="max-width:13ch">{words(F_["new_q"])}</h1>
</div></div>
<section class="dark future-dk"><canvas class="skyc" aria-hidden="true"></canvas><div class="wrap">
  <div class="stamps rv">{"".join(f'<span class="stamp" style="--i:{i};--r:{_rot[i % len(_rot)]}">{esc(x)}</span>' for i, x in enumerate(F_["domains"]))}</div>
  <div class="bigtext"><p style="max-width:104ch;text-wrap:balance">{esc(F_["body"])}</p></div>
  <a class="btn rv" style="margin-top:22px" href="build.html">Build with us <span class="arr">&rarr;</span></a>
</div></section>
"""
t, d = pmeta("future")
page("future.html", "future", t, d, future, current="/future.html",
     lds=[crumbs(HOME_CRUMB, (seo["pages"]["future"]["crumb"], URL + "/future.html"))])

# ---------------- build with us
B_ = site["build_page"]
LI_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.07 2.07 0 1 1 0-4.13 2.07 2.07 0 0 1 0 4.13zM7.12 20.45H3.55V9h3.57v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.22.79 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>')
build = f"""
<div class="hero build dark"><canvas class="skyc" aria-hidden="true"></canvas><div class="wrap">
  <div><div class="label tl fade" style="--d:.05s">{esc(B_["kicker"])}</div>
  <h1 class="display" style="margin-top:20px">{words(B_["headline"])}</h1>
  <p class="lede fade" style="--d:.8s;margin-top:20px">{esc(B_["body"])}</p>
  <div class="actions fade" style="--d:1s"><a class="btn" href="mailto:{EMAIL}">{esc(B_["button"])} <span class="arr">&rarr;</span></a>
    <a class="icon" href="{site["linkedin"]}" target="_blank" rel="noopener" aria-label="{esc(site["name"])} on LinkedIn">{LI_SVG}</a></div>
  <p class="em fade" style="--d:1.2s">{EMAIL}</p></div>
  <div class="enso-wrap breathe"><img class="paint go" src="/images/logos/enso-hd.webp" alt="" width="{ENSO_HD[0]}" height="{ENSO_HD[1]}"></div>
</div></div>
"""
t, d = pmeta("build", email=EMAIL)
page("build.html", "build", t, d, build, current="/build.html", dark_top=True,
     lds=[crumbs(HOME_CRUMB, (seo["pages"]["build"]["crumb"], URL + "/build.html"))])

# ---------------- companies (orbit + list + overview drawer) and one page per company
for c in companies:
    f = CONTENT / "companies" / f'{c["slug"]}.md'
    c["paras"] = [b.strip() for b in re.split(r"\n\s*\n", read(f)) if b.strip()] if f.exists() else []
    c["show"] = c.get("overview_name") or c["name"]          # how the company is named on its page and in lists
    c["dark"] = c.get("overview_logo_bg") == "dark"
groups = []
for c in companies:
    if c["group"] not in groups:
        groups.append(c["group"])
CP = site["companies_page"]
orbit = [c for c in companies if c["group"] == groups[0]]


def first_sentence(text, min_len=80):
    """The opening sentence for search/share previews; a very short opener takes the next sentence too."""
    out = ""
    for s in re.findall(r".+?[.!?](?=\s|$)", text) or [text]:
        out = (out + " " + s.strip()).strip()
        if len(out) >= min_len:
            break
    return out


def site_label(url):
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


pls = "".join(
    f'<a class="pl" href="companies/{c["slug"]}.html" data-slug="{c["slug"]}" data-name="{esc(c["show"])}" data-group="{esc(c["group"])}">'
    f'<span class="disc"><img src="/images/{c["logo"]}" alt="{esc(c["show"])} logo" style="width:{c.get("orbit_logo_width", "60%")}" decoding="async"></span>'
    f'<span class="nm">{esc(c["name"])}</span></a>' for c in orbit)
coindex = "".join(
    f'<div><h2 class="label">{esc(g)} <b>{sum(1 for c in companies if c["group"] == g):02d}</b></h2><ul>'
    + "".join(f'<li><a href="companies/{c["slug"]}.html">{esc(c["show"])}<span aria-hidden="true">&rarr;</span></a></li>'
              for c in companies if c["group"] == g) + "</ul></div>" for g in groups)


def nx_link(c, prev_c, next_c):
    return (f'<div class="nx"><a href="companies/{prev_c["slug"]}.html" data-go="{prev_c["slug"]}">&larr; {esc(prev_c["show"])}</a>'
            f'<a href="companies/{next_c["slug"]}.html" data-go="{next_c["slug"]}">{esc(next_c["show"])} &rarr;</a></div>')


templates = ""
for i, c in enumerate(orbit):
    pc, nc = orbit[i - 1], orbit[(i + 1) % len(orbit)]
    templates += (f'<template id="ov-{c["slug"]}"><div class="dh"><span class="label">{esc(c["group"])}</span>'
                  '<button type="button" data-close>Close &times;</button></div><div class="db">'
                  f'<div class="lg{" dk" if c["dark"] else ""}"><img data-src="/images/{c["logo"]}" alt="{esc(c["show"])} logo" style="width:{c.get("drawer_logo_width", "50%")}"></div>'
                  f'<h2>{esc(c["show"])}</h2>' + "".join(f"<p>{esc(p, quote=False)}</p>" for p in c["paras"])
                  + nx_link(c, pc, nc) + "</div></template>")
cos = f"""
<section class="dark cos"><canvas class="skyc" aria-hidden="true"></canvas><div class="wrap">
  <div class="cohead fade" style="--d:.05s"><div class="label tl">{esc(CP["kicker"])}</div><a class="tolist" href="#all-companies">{esc(CP["list_link"])} <span aria-hidden="true">&darr;</span></a></div>
  <h1 class="display" style="margin-top:18px;font-size:clamp(2.1rem,4.4vw,4.4rem)">{words(CP["headline"])}</h1>
  <div class="orb" id="orb">
    <svg class="tracks" aria-hidden="true"><ellipse id="trIn"/></svg>
    <div class="core" id="core"><img src="/images/logos/enso-hd.webp" alt="" decoding="async"></div>
    <div class="readout" id="readout" aria-hidden="true"><span class="cg" id="coreG"></span><span class="cn" id="coreN"></span></div>
    <div class="ph" id="phI"><span class="label">{esc(groups[0])}</span><b>{len(orbit):02d}</b></div>
    <div class="cap" id="capI" aria-hidden="true"></div>
    {pls}
  </div>
  <div class="coindex" id="all-companies" aria-label="All companies">{coindex}</div>
</div></section>
<div class="scrim" id="scrim"></div><aside class="drawer" id="drawer" aria-hidden="true" aria-label="Company overview"></aside>
{templates}
"""


def join_names(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


co_desc = seo["pages"]["companies"]["description_intro"] + "".join(
    f' {g}: {join_names([c["show"] for c in companies if c["group"] == g])}.' for g in groups)
page("companies.html", "companies", seo["pages"]["companies"]["title"], co_desc, cos, current="/companies.html", dark_top=True,
     lds=[{"@context": "https://schema.org", "@type": "ItemList", "name": g,
           "numberOfItems": sum(1 for c in companies if c["group"] == g),
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": c["show"], "url": f'{URL}/companies/{c["slug"]}.html'}
                               for i, c in enumerate([c for c in companies if c["group"] == g])]} for g in groups]
         + [crumbs(HOME_CRUMB, (seo["pages"]["companies"]["crumb"], URL + "/companies.html"))])

with_pages = [c for c in companies if c["paras"]]
for i, c in enumerate(with_pages):
    nc = with_pages[(i + 1) % len(with_pages)]
    cu = f'{URL}/companies/{c["slug"]}.html'
    site_link = (f'\n      <a class="ov-site rv" href="{c["website"]}" target="_blank" rel="noopener">Visit {site_label(c["website"])} &#8599;</a>'
                 if c.get("website") else "\n      ")
    body = f"""<div class="ov-page"><div class="wrap">
  <a class="back fade" style="--d:0s" href="../companies.html">&larr; All companies</a>
  <div class="ov-grid">
    <div class="ov-left"><div class="ov-logo{" dk" if c["dark"] else ""} fade" style="--d:.05s"><img src="/images/{c["logo"]}" alt="{esc(c["show"])} logo" style="width:{c.get("page_logo_width", "240px")};height:auto" loading="lazy" decoding="async"></div>
      <h1 class="ov-name">{words(c["show"])}</h1></div>
    <div class="ov-body">{"".join(f"<p>{esc(p, quote=False)}</p>" for p in c["paras"])}{site_link}</div>
  </div>
  <a class="next rv" href="{nc["slug"]}.html"><div><div class="label" style="margin-bottom:14px">Next company</div><div class="big">{esc(nc["show"])} &rarr;</div></div>
    <div class="nt{" dk" if nc["dark"] else ""}"><img src="/images/{nc["logo"]}" alt="{esc(nc["show"])} logo" style="width:{nc.get("thumb_logo_width", "80px")};height:auto" loading="lazy" decoding="async"></div></a>
</div></div>
"""
    about = {"@type": "Organization", "name": c["show"], "description": " ".join(c["paras"])}
    if c.get("website"):
        about["url"] = c["website"]
    title = seo["company_title"].format(name=c["show"])
    page(f'companies/{c["slug"]}.html', "company", title, first_sentence(c["paras"][0]), body, current="/companies.html",
         lds=[{"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": cu, "about": about,
               "isPartOf": {"@type": "WebSite", "@id": URL + "/#website", "name": site["name"], "url": URL + "/"}},
              crumbs(HOME_CRUMB, (seo["pages"]["companies"]["crumb"], URL + "/companies.html"), (c["show"], cu))])

# ---------------- blog index
rows, month = [], None
for p in posts:
    m = f'{as_date(p["date"]):%B} {as_date(p["date"]).year}'
    if m != month:
        rows.append(f'<div class="month rv">{m}</div>'); month = m
    rows.append(f'<a class="prow rv" href="{p["slug"]}.html" data-slug="{p["slug"]}"><div class="d">{as_date(p["date"]):%B} {as_date(p["date"]).day}</div>'
                f'<div><h3>{wbr(tx(p["title"]))}</h3><p>{esc(p["excerpt"])}</p></div><div class="m">{minutes(p["words"])} MIN</div></a>')
blog = f"""
<div class="hero"><div class="wrap">
  <div class="label tl fade" style="--d:.05s">{tx(BLOG["kicker"])}</div>
  <h1 class="display" style="margin-top:20px;font-size:clamp(2.1rem,4.9vw,5rem);max-width:14ch">{words(BLOG["title"])}</h1>
  <p class="lede fade" style="--d:1s;margin-top:18px;font-style:italic">{esc(BLOG["tagline"])}</p>
</div></div>
<section style="padding-top:0"><div class="wrap"><div class="posts">
{"".join(rows)}
</div></div></section>
"""
BLOG_URL = URL + "/blog/"
page("blog/index.html", "blog", seo["pages"]["blog"]["title"],
     seo["pages"]["blog"]["description"].format(blog_title=BLOG["title"], blog_tagline=BLOG["tagline"]), blog, current="/blog/",
     lds=[{"@context": "https://schema.org", "@type": "Blog", "@id": BLOG_URL + "#blog", "name": BLOG["title"],
           "description": seo["pages"]["blog"]["description"].format(blog_title=BLOG["title"], blog_tagline=BLOG["tagline"]),
           "url": BLOG_URL, "inLanguage": "en", "author": FOUNDER, "publisher": PUBLISHER,
           "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": f'{BLOG_URL}{p["slug"]}.html', "datePublished": p["date"]} for p in posts]},
          crumbs(HOME_CRUMB, (seo["pages"]["blog"]["crumb"], BLOG_URL))])

# ---------------- one page per post
for i, p in enumerate(posts):
    pu = f'{BLOG_URL}{p["slug"]}.html'
    older = posts[i + 1] if i + 1 < len(posts) else None
    newer = posts[i - 1] if i > 0 else None
    pn = ""
    if older or newer:
        pn = ('<div class="pn">'
              + (f'<a href="{older["slug"]}.html"><small>&larr; Previous</small><b>{wbr(md_inline(older["title"]))}</b></a>' if older else "<span></span>")
              + (f'<a class="r" href="{newer["slug"]}.html"><small>Next &rarr;</small><b>{wbr(md_inline(newer["title"]))}</b></a>' if newer else "")
              + "</div>")
    body = f"""
<article class="article"><div class="wrap">
  <div class="head"><a class="back" href="index.html">&larr; All posts</a>
  <h1>{words(p["title"], fmt=wbr)}</h1>
  <div class="byline fade" style="--d:.6s"><img src="/images/logos/enso-sm.webp" alt=""><span>{long_date(p["date"])} <span class="sep">&middot;</span> {minutes(p["words"])} min read</span><button class="share" type="button" data-share="{pu}" data-title="{esc(p["title"])}">Share</button></div></div>
  <div class="prose">{p["html"]}</div>
  {endmark(pu, p["title"])}
  {pn}
</div></article>
"""
    page(f'blog/{p["slug"]}.html', "post", seo["post_title"].format(title=p["title"]), p["excerpt"], body,
         current="/blog/", og_type="article", ring=True,
         lds=[{"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "datePublished": p["date"],
               "description": p["excerpt"], "author": FOUNDER, "publisher": PUBLISHER, "image": URL + "/images/og-card.png",
               "inLanguage": "en", "wordCount": p["words"], "isPartOf": {"@id": BLOG_URL + "#blog"},
               "mainEntityOfPage": pu, "url": pu},
              crumbs(HOME_CRUMB, (seo["pages"]["blog"]["crumb"], BLOG_URL), (p["title"], pu))])

# old link: Joel's Directive became a blog post
write(OUT / "joels-directive.html",
      '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
      '<title>Stop Watching. Start F@cking Creating. — Directive 17</title>'
      '<link rel="canonical" href="https://directive17.com/blog/stop-watching-start-creating.html">'
      '<meta http-equiv="refresh" content="0; url=blog/stop-watching-start-creating.html">'
      '<script>location.replace("blog/stop-watching-start-creating.html")</script></head>'
      '<body style="background:#FBF7EC"></body></html>')

# ---------------- 404 (root-relative links: GitHub Pages serves it at any path)
NF = site["notfound_page"]
nf = f"""
<div class="hero"><div class="wrap">
  <div class="label tl fade" style="--d:.05s">{esc(NF["kicker"])}</div>
  <h1 class="display" style="margin-top:20px;max-width:14ch">{words(NF["headline"])}</h1>
  <p class="lede fade" style="--d:.8s;margin-top:20px">{tx(NF["body"])}</p>
  <p class="fade" style="--d:1s;margin-top:26px"><a class="btn" href="/">{esc(NF["button"])} <span class="arr">&rarr;</span></a></p>
</div></div>
"""
t, d = pmeta("404")
page("404.html", "404", t, d, nf)

# ---------------- RSS feed
def xml(s):
    return html.escape(str(s), quote=True).replace("&#x27;", "'")


def rfc822(d):
    return as_date(d).strftime("%a, %d %b %Y") + " 12:00:00 GMT"


TODAY = date.today().isoformat()
items = "\n".join(f'<item><title>{xml(p["title"])}</title><link>{BLOG_URL}{p["slug"]}.html</link>'
                  f'<guid isPermaLink="true">{BLOG_URL}{p["slug"]}.html</guid><pubDate>{rfc822(p["date"])}</pubDate>'
                  f'<description>{xml(p["excerpt"])}</description></item>' for p in posts)
blog_desc = seo["pages"]["blog"]["description"].format(blog_title=BLOG["title"], blog_tagline=BLOG["tagline"])
write(OUT / "blog" / "feed.xml",
      '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
      f'<title>{xml(BLOG["title"])} — {xml(site["name"])}</title>\n<link>{BLOG_URL}</link>\n'
      f'<atom:link href="{BLOG_URL}feed.xml" rel="self" type="application/rss+xml"/>\n<description>{xml(blog_desc)}</description>\n'
      f'<language>en</language>\n<lastBuildDate>{rfc822(TODAY)}</lastBuildDate>\n{items}\n</channel>\n</rss>\n')

# ---------------- crawler files: sitemap, robots (AI bots welcome), llms.txt
_urls = ["", "why.html", "philosophy.html", "companies.html", "future.html", "build.html", "blog/"] \
        + [f"blog/{p['slug']}.html" for p in posts] + [f"companies/{c['slug']}.html" for c in with_pages] + ["founders-note.html"]
_sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in _urls:
    pri = "1.0" if u == "" else ("0.8" if u.startswith("blog") else "0.7")
    _sm.append(f"<url><loc>{URL}/{u}</loc><lastmod>{TODAY}</lastmod><priority>{pri}</priority></url>")
_sm.append("</urlset>")
write(OUT / "sitemap.xml", "\n".join(_sm) + "\n")

# AI crawlers are explicitly welcomed; the confidential deck viewers are not indexed
_ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User",
            "Claude-SearchBot", "anthropic-ai", "PerplexityBot", "Perplexity-User",
            "Google-Extended", "Applebot-Extended", "CCBot", "Bytespider", "meta-externalagent"]
_rb = ["# Directive 17 — all crawlers welcome, including AI assistants",
       "User-agent: *", "Allow: /", "Disallow: /decks/", ""]
for bot in _ai_bots:
    _rb += [f"User-agent: {bot}", "Allow: /", "Disallow: /decks/", ""]
_rb.append(f"Sitemap: {URL}/sitemap.xml")
write(OUT / "robots.txt", "\n".join(_rb))

_ll = ["# Directive 17", "", f"> {site['subline']} {site['tagline']}", "",
       "Directive 17 is a venture firm founded by Joel Shapiro. Every company "
       "begins with one question: how will this make someone's life better? Only then do we "
       "ask whether it can become a great business.", "",
       "## Pages", ""]
_ll += [f"- [Why We Exist]({URL}/why.html): Most organizations begin with markets. We begin with people.",
        f"- [Philosophy]({URL}/philosophy.html): The Five Pillars — happiness, health, trust, connection, human potential — and the Human Test.",
        f"- [Companies]({URL}/companies.html): Portfolio companies. Different companies. One philosophy.",
        f"- [The Future We See]({URL}/future.html): What future is worth building?",
        f"- [Build With Us]({URL}/build.html): Contact — {EMAIL}",
        f"- [A Note from the Founder]({URL}/founders-note.html): Joel Shapiro on why Directive 17 exists and what it invests in.",
        "", "## Companies", ""]
_ll += [f"- [{c['show']}]({URL}/companies/{c['slug']}.html): {c['paras'][0]}" for c in with_pages]
_ll += ["", "## Joel's Blog", ""]
_ll += [f"- [{p['title']}]({URL}/blog/{p['slug']}.html): {p['excerpt']}" for p in posts]
write(OUT / "llms.txt", "\n".join(_ll) + "\n")

# ---------------- password-protected deck viewers (unchanged from the previous builder)
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
        meta = json.loads((decks_src / f"{slug}.json").read_text(encoding="utf-8"))
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
        write(OUT / "decks" / f"{slug}.html", viewer)


print(f"Built {len(list(OUT.rglob('*.html')))} pages, {len(posts)} posts, {len(companies)} companies -> docs/")
