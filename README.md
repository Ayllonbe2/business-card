# Aarón Ayllón Benítez — career archive

A small static site: a short landing page plus detail pages (Experience, Projects, Research, Education, About),
published in English (`/`), Spanish (`/es/`) and French (`/fr/`). Deployed as Cloudflare static assets from `public/`.

## Layout

| Path | What it is |
| --- | --- |
| `content/*.json` | All the content. Every user-visible string is `{"en": …, "es": …, "fr": …}`. |
| `static/` | Copied as-is into `public/` (CSS, JS, photo, CV PDF, logos, favicon). |
| `build.py` | The generator (Python standard library only). |
| `public/` | Generated output. Git-ignored: GitHub Actions and Cloudflare run `build.py` themselves. |
| `wrangler.jsonc` | Cloudflare config (`assets.directory = public`, custom 404 page). |

## Build

```
python build.py          # validate content, render public/, check every internal link and anchor
python build.py --check  # same, without writing public/
python -m http.server 8000 --directory public   # preview at http://localhost:8000
```

The build fails if any string is missing a language, if markup inside a string is unbalanced, if an entry points to
an unknown project/publication/role, or if an internal link or `#anchor` does not resolve.

## Adding content

* **A role** — add an object to `roles` in `content/experience.json` (`id`, `dates`, `company` as `"Company — City"`,
  `role`, optional `official` / `summary`, `bullets`, and `projects` ids that become chips linking to `/projects/`).
* **A project** — add an item to a group in `content/projects.json`. Set `short` (landing card), `body`, `points`,
  `metric`, `links`, and optionally `pubs` (publication ids) and `role` (experience id).
  To show it on the landing page, add its id to `projects.featured` in `content/home.json`.
* **A publication** — add it to `publications` in `content/research.json`. `featured: true` puts it on the landing page and
  must match `research.featured` in `content/home.json`.
* **A certification or course** — add an object to `certifications` in `content/education.json` (`year`, `title`, `issuer`, `kind`; optional `url` links the credential; `featured: true` also lists it on the landing page). Newest year first on the page.
* **Talks, grants, degrees, skills, principles** — the matching arrays in `research.json`, `education.json`, `about.json`.

Strings that contain `<` are treated as HTML (`<strong>`, `<em>`, `<a href=…>`); plain strings are escaped.
Set `base_url` in `content/site.json` to enable canonical/hreflang tags, `sitemap.xml` and `robots.txt`.

## Typography helper

`static/assets/site.js` glues the last two words of each text block (no lonely last word) and keeps separators
such as “—”, “·”, “:” attached to the preceding word. It contains no dictionary: the language is part of the URL.

## Deploy (GitHub → Cloudflare)

* **Production:** every push to `main` is built and published by Cloudflare Workers Builds.
  In the Cloudflare dashboard (Workers & Pages → `business-card` → Settings → Build) set
  **Build command** `python3 build.py` and keep **Deploy command** `npx wrangler deploy`.
* **Previews:** pushes to any other branch are uploaded as a preview version (`npx wrangler versions upload`).
* **CI:** `.github/workflows/build.yml` runs `python build.py` on every push and pull request, so a broken
  translation or link is caught before it reaches production. The built site is attached to the run as a download.
* **If the Cloudflare build image has no Python:** remove `public/` from `.gitignore`, run `python build.py` locally
  and commit `public/`; Cloudflare will then just publish the committed files.

