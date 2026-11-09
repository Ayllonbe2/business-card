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
python build.py --pending  # also list achievement strings that still lack an es/fr translation
python -m http.server 8000 --directory public   # preview at http://localhost:8000
```

The build fails if any string is missing a language (achievement entries are the exception, see below), if markup inside a string is unbalanced, if an entry points to
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
* **An achievement** — add an object to `items` in `content/achievements.json` (see *Achievements log* below).
* **Grants** — `grants` in `content/education.json`, each with a `date` (`"YYYY"` or `"YYYY-MM"`), `title` and `text`; newest first on the page.
* **A talk or podcast** — add an entry to `talks` in `content/research.json` (`date` as `"YYYY"` or `"YYYY-MM"`, `text`); it feeds the
  "Speaking & media" card of `/research/`. Log it in the achievements log as well if it deserves its own entry.
* **Degrees, skills, principles** — the matching arrays in `education.json`, `about.json`.

## Achievements log

`content/achievements.json` is the place to record every result as it happens. The landing page shows the newest
`featured` ones (as many as `achievements.limit` in `content/home.json`); `/achievements/` lists all of them by year.
Entries are sorted by `date`, newest first; entries with the same date keep their order in the file.

```json
{
  "id": "short-kebab-id",
  "date": "2026-09",
  "until": "present",
  "type": "impact",
  "title":  { "en": "What happened", "es": "…", "fr": "…" },
  "body":   { "en": "Context and your part in it", "es": "…", "fr": "…" },
  "metric": { "en": "The number that matters", "es": "…", "fr": "…" },
  "role": "basf-head",
  "projects": ["cv-mlops"],
  "pubs": ["gsan-nar"],
  "links": [{ "label": { "en": "Press", "es": "Prensa", "fr": "Presse" }, "url": "https://…" }],
  "featured": true
}
```

* Required: `id` (unique, lowercase, hyphens), `date` (`YYYY` or `YYYY-MM`), `type` (one of `types` in the same file:
  `impact`, `leadership`, `research`, `recognition`, `venture`), `title`. Everything else is optional.
* `until` (`YYYY`, `YYYY-MM` or `"present"`) turns the date into a range such as “2022 – Present”.
* `role`, `projects` and `pubs` must be existing ids; they become chips linking to those pages. A typo fails the build,
  and so does any unknown field name.
* **Translations are optional here**: only `en` is required. A missing `es` / `fr` falls back to the English text
  (marked `lang="en"`) and is listed by `python build.py --pending`, so you can log a result in one minute and translate later.
  Everywhere else on the site all three languages remain mandatory.
* Each entry is linkable as `/achievements/#a-<id>` (it is highlighted when opened that way).

Strings that contain `<` are treated as HTML (`<strong>`, `<em>`, `<a href=…>`); plain strings are escaped.
Set `base_url` in `content/site.json` to enable canonical/hreflang tags, `sitemap.xml` and `robots.txt`.

## Typography helper

`static/assets/site.js` glues the last two words of each text block (no lonely last word) and keeps separators
such as “—”, “·”, “:” attached to the preceding word. It contains no dictionary: the language is part of the URL.

## Deploy (GitHub → Cloudflare)

* **Production:** every push to `main` is built and published by Cloudflare Workers Builds. `public/` is not in git,
  so `wrangler.jsonc` carries `build.command = "python3 build.py"`: wrangler generates the site itself before it
  uploads it, and no dashboard setting is needed. In the dashboard (Workers & Pages → `business-card` → Settings →
  Build) leave **Build command** empty (a second `build.py` run would only repeat the first) and keep
  **Deploy command** `npx wrangler deploy`.
* **Previews:** pushes to any other branch are uploaded as a preview version (`npx wrangler versions upload`),
  which runs the same build command.
* **Only one Cloudflare project should be connected to this repo.** If the repo also appears under *Workers & Pages →
  Pages* (`*.pages.dev`), disconnect that one: it is a second, unrelated deployment of the same repository.
* **Reproduce a Cloudflare build locally** from a clean clone: `npx wrangler deploy --dry-run`
  (fails with “assets.directory … does not exist” if the build step is missing).
* **CI:** `.github/workflows/build.yml` runs `python build.py` on every push and pull request, so a broken
  translation or link is caught before it reaches production. The built site is attached to the run as a download.
* **If the Cloudflare build image has no Python:** remove `public/` from `.gitignore`, run `python build.py` locally
  and commit `public/`; Cloudflare will then just publish the committed files.

