# Aarón Ayllón Benítez — career archive

A small static site: a short landing page plus detail pages (Experience, Projects, Achievements, Research, Education, About),
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
  `role`, optional `official` / `summary`, `bullets` (may be empty), and `projects` ids that become chips linking to `/projects/`).
  `early: true` styles a role as early career; `glance: false` keeps it off the landing-page career card (the Experience
  page still lists it). The home and Experience intros state the number of positions: update them when adding one.
* **A project** — add an item to a group in `content/projects.json`. Set `short` (landing card), `body`, `points`,
  `metric`, `links`, and optionally `pubs` (publication ids) and `role` (experience id).
  To show it on the landing page, add its id to `projects.featured` in `content/home.json`.
* **A publication** — add it to `publications` in `content/research.json`, newest year first (journals, preprints,
  conference talks and posters all live there). `featured: true` puts it on the landing page and must match
  `research.featured` in `content/home.json`.
* **A service or community role** — add an entry to `service` in `content/research.json` (`date` as `"YYYY"`, `"YYYY-MM"`
  or a range `"YYYY/YYYY"`, `title`, `text`); it appears under "Service & community" on `/research/`.
* **A certification or course** — add an object to `certifications` in `content/education.json` (`date` as `"YYYY"` or `"YYYY-MM"`, `title`, `issuer`, `kind`; optional `url` links the credential, optional `credential` = `{id, url, site}` prints the verification code with a link to the verifier; `featured: true` also lists it on the landing page). Newest first on the page; input order breaks ties within the same month.
* **An achievement** — `content/achievements.json`. `impact` (business results) and `recognition` (talks, podcasts, debates,
  competitions, science communication) are lists of entries with a `date` as `"YYYY"` or `"YYYY-MM"` (shown as "Nov 2026",
  localised per language; a bare year sorts after the months of that year). Order in the file does not matter: pages sort
  newest first. `impact` entries take an optional `link` (`page` + `anchor`); `recognition` entries take a `kind` from `kinds`.
  Recognition entries of kind `talk` or `podcast` also feed the "Speaking & media" card on `/research/`.
* **Grants** — `grants` in `content/education.json`, each with a `date` (`"YYYY"` or `"YYYY-MM"`), `title` and `text`; newest first on the page.
* **Degrees, skills, principles** — the matching arrays in `education.json`, `about.json`.

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

