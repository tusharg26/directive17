# Directive 17 — directive17.com

The official Directive 17 website. Live at https://directive17.com via GitHub Pages.

## How it works

- **The words live in `content/`** — no coding needed to update anything:
  - `content/site.json` — page copy: tagline, nav, pillars, and the Why / Philosophy / Future /
    Build With Us / Companies / blog headings; also the contact email and LinkedIn link
  - `content/seo.json` — page titles and the descriptions search engines and link previews show
  - `content/companies.json` — portfolio companies: name, group, logo (and its size on the
    Companies page, in the overview panel, on its own page and as a "next company" thumbnail),
    website, and `overview_logo_bg: "dark"` for logos that need a dark tile
  - `content/companies/<slug>.md` — each company's overview, one paragraph per block
  - `content/pages/founders-note.md` — the founder's note (its own page, and it unfolds in place
    on the home page)
  - `content/posts/*.md` — blog posts, one file each, named `YYYY-MM-DD-slug.md`
  - `content/images/logos/` — company logos and the enso mark
- **`theme/`** is the look: `site.css`, `site.js` and the font files (copied to `docs/assets/`).
- **`build.py`** turns content + theme into the finished site. Run `python3 build.py` (no dependencies).
- **`docs/`** is the generated output that GitHub Pages serves. Never edit it by hand —
  edit `content/`, rebuild, and commit both.

## Publishing an update

1. Edit files in `content/` (or ask Claude to)
2. `python3 build.py`
3. Commit and push `content/` + `docs/` — the live site updates in ~1 minute

## Adding a blog post

Create `content/posts/2026-09-01-my-title.md`:

```
---
title: My Title
date: 2026-09-01
excerpt: One or two lines shown in the blog list, on the home page and in link previews.
---

Post body in markdown...
```

Then rebuild and push. The build adds the post page, puts it at the top of the blog list and in
the home page's "New post" row (unless `featured_post` in site.json names another post), links it
from the previous post, and updates the RSS feed (`blog/feed.xml`), `sitemap.xml` and `llms.txt`.
