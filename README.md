# Directive 17 — directive17.com

The official Directive 17 website. Live at https://directive17.com via GitHub Pages.

## How it works

- **All content lives in `content/`** — no coding needed to update anything:
  - `content/site.json` — ALL page copy: tagline, nav, pillars, and the full structured
    copy for the Why / Philosophy / Future / Build With Us pages
  - `content/companies.json` — portfolio companies (name, group, logo, one-liner, url)
  - `content/pages/*.md` — long-form pages (Joel's Directive)
  - `content/posts/*.md` — blog posts, one file each, named `YYYY-MM-DD-slug.md`
  - `content/images/logos/` — company logos and the enso mark
- **`build.py`** turns content into the finished site. Run `python3 build.py` (no dependencies).
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
excerpt: One or two lines shown in the blog list and homepage.
---

Post body in markdown...
```

Then rebuild and push. Posts appear newest-first, collapsed to titles, with share links.
