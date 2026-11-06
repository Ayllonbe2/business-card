#!/usr/bin/env python3
"""Static site generator for the career archive (Python standard library only).

    python build.py            validate content, render public/, check links
    python build.py --check    validate content and rendering without writing public/

Content lives in content/*.json. Every user-visible string is a {"en", "es", "fr"} object and the build
fails when a language is missing. Output: public/ (English at /, Spanish at /es/, French at /fr/).
"""
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, STATIC, OUT = ROOT / "content", ROOT / "static", ROOT / "public"
LANGS = ("en", "es", "fr")
LANG_NAMES = {"en": "English", "es": "Español", "fr": "Français"}
OG_LOCALE = {"en": "en_US", "es": "es_ES", "fr": "fr_FR"}
PAGES = ("", "experience", "projects", "research", "education", "about")

ICONS = {
    "eye": '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    "chart": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="m19 9-5 5-4-4-3 3"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
    "network": '<rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/>',
    "briefcase": '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "flask": '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "linkedin": '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/>',
    "scholar": '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "mic": '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
    "pen": '<path d="M12 20h9"/><path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z"/>',
    "menu": '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
}


class BuildError(Exception):
    pass


# ------------------------------------------------------------------------------ content + validation
def load(name):
    return json.loads((CONTENT / f"{name}.json").read_text(encoding="utf-8"))


class _Balance(HTMLParser):
    VOID = {"br", "hr", "img", "input", "meta", "link", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.error = [], None

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.error = self.error or f"unexpected </{tag}> (open: {self.stack[-1:] or 'none'})"
        else:
            self.stack.pop()


def check_markup(s, where):
    if "<" not in s:
        return
    p = _Balance()
    p.feed(s)
    p.close()
    if p.error or p.stack:
        raise BuildError(f"{where}: unbalanced markup ({p.error or 'unclosed ' + str(p.stack)}): {s[:80]!r}")
    if re.search(r"&(?!(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)", s):
        raise BuildError(f"{where}: bare '&' inside markup: {s[:80]!r}")


def validate(obj, where):
    """Every {"en","es","fr"} object must carry all three non-empty strings, with balanced markup."""
    if isinstance(obj, dict):
        keys = set(obj)
        if keys and keys <= set(LANGS):
            missing = [l for l in LANGS if not (isinstance(obj.get(l), str) and obj[l].strip())]
            if missing:
                raise BuildError(f"{where}: missing language(s) {missing} (have {sorted(keys)})")
            for l in LANGS:
                check_markup(obj[l], f"{where}.{l}")
            return
        for k, v in obj.items():
            validate(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            validate(v, f"{where}[{i}]")


# ------------------------------------------------------------------------------ small helpers
def t(v, lang):
    return v[lang] if isinstance(v, dict) and "en" in v else v


def rich(v, lang):
    """Content strings that contain markup are trusted HTML; plain strings are escaped."""
    s = t(v, lang)
    return s if "<" in s else html.escape(s, quote=False)


def plain(v, lang):
    return re.sub(r"<[^>]+>", "", t(v, lang))


def attr(s):
    return html.escape(s, quote=True)


def icon(name, size=22):
    return f'<svg class="i" viewBox="0 0 24 24" width="{size}" height="{size}" aria-hidden="true">{ICONS[name]}</svg>'


def url(lang, page="", anchor=""):
    base = ("" if lang == "en" else f"/{lang}") + "/"
    path = base + (f"{page}/" if page else "")
    return path + (f"#{anchor}" if anchor else "")


def split_company(s):
    parts = re.split(r"\s+—\s+", s, maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 else (s, "")


class Site:
    def __init__(self):
        self.site = load("site")
        self.home = load("home")
        self.exp = load("experience")
        self.proj = load("projects")
        self.res = load("research")
        self.edu = load("education")
        self.about = load("about")
        for name, data in (("site", self.site), ("home", self.home), ("experience", self.exp), ("projects", self.proj),
                           ("research", self.res), ("education", self.edu), ("about", self.about)):
            validate(data, name)
        self.projects = {i["id"]: i for g in self.proj["groups"] for i in g["items"]}
        self.pubs = {p["id"]: p for p in self.res["publications"]}
        self.roles = {r["id"]: r for r in self.exp["roles"]}
        self.nav = {n["id"]: n["label"] for n in self.site["nav"]}
        self.ui = self.site["ui"]
        self._check_refs()

    def _check_refs(self):
        for r in self.exp["roles"]:
            for pid in r.get("projects", []):
                if pid not in self.projects:
                    raise BuildError(f"experience role {r['id']}: unknown project '{pid}'")
        for p in self.projects.values():
            if p.get("role") and p["role"] not in self.roles:
                raise BuildError(f"project {p['id']}: unknown role '{p['role']}'")
            for pb in p.get("pubs", []):
                if pb not in self.pubs:
                    raise BuildError(f"project {p['id']}: unknown publication '{pb}'")
        for pid in self.home["projects"]["featured"]:
            if pid not in self.projects:
                raise BuildError(f"home featured project '{pid}' not found")
        for pb in self.home["research"]["featured"]:
            if pb not in self.pubs:
                raise BuildError(f"home featured publication '{pb}' not found")
        flagged = {p["id"] for p in self.res["publications"] if p.get("featured")}
        if flagged != set(self.home["research"]["featured"]):
            raise BuildError("research 'featured' flags and home.research.featured differ")


# ------------------------------------------------------------------------------ shared chrome
def layout(S, lang, page, title, description, main):
    site, ui = S.site, S.ui
    base = site.get("base_url", "").rstrip("/")
    head_extra = []
    if base:
        head_extra.append(f'<link rel="canonical" href="{base}{url(lang, page)}">')
        for l in LANGS:
            head_extra.append(f'<link rel="alternate" hreflang="{l}" href="{base}{url(l, page)}">')
        head_extra.append(f'<link rel="alternate" hreflang="x-default" href="{base}{url("en", page)}">')
        head_extra.append(f'<meta property="og:url" content="{base}{url(lang, page)}">')
    page_cur, lang_cur = ' aria-current="page"', ' aria-current="true"'
    nav_items = "".join(
        f'<li><a href="{url(lang, n["id"])}"{page_cur if n["id"] == page else ""}>{rich(n["label"], lang)}</a></li>'
        for n in site["nav"]
    )
    switch = "".join(
        f'<a class="lang-btn" href="{url(l, page)}" lang="{l}" hreflang="{l}" aria-label="{LANG_NAMES[l]}"'
        f'{lang_cur if l == lang else ""}>{l.upper()}</a>'
        for l in LANGS
    )
    foot_nav = "".join(f'<a href="{url(lang, n["id"])}">{rich(n["label"], lang)}</a>' for n in site["nav"])
    desc = attr(description)
    extra = "".join(f"  {h}\n" for h in head_extra)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <meta name="description" content="{desc}" />
  <meta name="theme-color" content="#1F3A5F" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{attr(title)}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:locale" content="{OG_LOCALE[lang]}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
{extra}  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;1,400&amp;family=Plus+Jakarta+Sans:wght@600;700&amp;display=swap" />
  <link rel="stylesheet" href="/assets/site.css" />
  <script src="/assets/site.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#main">{rich(ui["skip"], lang)}</a>
  <nav class="nav" aria-label="{attr(plain(ui["primary_nav"], lang))}">
    <div class="container nav-inner">
      <a class="brand" href="{url(lang)}">{html.escape(site["name"])}</a>
      <ul class="nav-links" id="navLinks">{nav_items}</ul>
      <div class="nav-actions">
        <div class="lang-switch" role="group" aria-label="{attr(plain(ui["language"], lang))}">{switch}</div>
        <button type="button" class="nav-toggle" aria-label="{attr(plain(ui["toggle_nav"], lang))}" aria-expanded="false" aria-controls="navLinks">{icon("menu", 20)}</button>
      </div>
    </div>
  </nav>

  <main id="main">
{main}
  </main>

  <footer class="footer">
    <div class="container">
      <nav class="foot-nav" aria-label="{attr(plain(ui["footer_nav"], lang))}">{foot_nav}</nav>
      <p class="foot-contact">
        <a href="mailto:{attr(site["email"])}">{html.escape(site["email"])}</a>
        <span class="foot-loc">{rich(site["location"], lang)}</span>
      </p>
      <p>{rich(site["footer_rights"], lang)}</p>
    </div>
  </footer>
</body>
</html>
"""


def page_head(S, lang, page, intro):
    return f"""    <header class="page-head">
      <div class="container">
        <h1>{rich(S.nav[page], lang)}</h1>
        <p>{rich(intro, lang)}</p>
      </div>
    </header>"""


def wrap_body(inner):
    return f'    <div class="page-body">\n      <div class="container">\n{inner}\n      </div>\n    </div>'


def more_link(lang, page, label, anchor=""):
    return f'<a class="more-link" href="{url(lang, page, anchor)}">{rich(label, lang)}</a>'


def data_table(lang, caption, cols, rows, foot=None):
    """cols: [(label T, css class)]; rows: lists of cell HTML in column order; foot: (label T, value)."""
    def cls(c):
        return f' class="{c}"' if c else ""
    labels = [attr(plain(c[0], lang)) for c in cols]
    head = "".join(f'<th scope="col"{cls(c[1])}>{rich(c[0], lang)}</th>' for c in cols)
    body = chr(10).join(
        "              <tr>" + "".join(f'<td{cls(c[1])} data-label="{lab}">{cell}</td>' for c, lab, cell in zip(cols, labels, row)) + "</tr>"
        for row in rows
    )
    tfoot = ""
    if foot:
        tfoot = (f'{chr(10)}            <tfoot><tr><th scope="row" colspan="{len(cols) - 1}">{rich(foot[0], lang)}</th>'
                 f'<td class="num" data-label="{labels[-1]}">{foot[1]}</td></tr></tfoot>')
    return (f'<div class="card table-card">{chr(10)}          <table class="data-table">{chr(10)}'
            f'            <caption class="sr-only">{rich(caption, lang)}</caption>{chr(10)}'
            f'            <thead><tr>{head}</tr></thead>{chr(10)}            <tbody>{chr(10)}{body}{chr(10)}            </tbody>{tfoot}{chr(10)}'
            f'          </table>{chr(10)}        </div>')


# ------------------------------------------------------------------------------ landing page
def cert_items(S):
    """Certifications and courses, newest first (input order kept within a year)."""
    return sorted(S.edu["certifications"], key=lambda c: -int(c["year"]))


def cert_title(c, lang):
    title = rich(c["title"], lang)
    if c.get("url"):
        return f'<a href="{attr(c["url"])}" target="_blank" rel="noopener">{title}</a>'
    return title


def project_card(S, lang, p, link_to_detail=True):
    metric = f'\n            <span class="pf-metric">{rich(p["metric"], lang)}</span>' if p.get("metric") else ""
    return f"""          <article class="card pf-card">
            <div class="pf-top">
              <span class="pf-icon">{icon(p["icon"])}</span>
              <span class="badge-type">{rich(p["badge"], lang)}</span>
            </div>
            <h3><a href="{url(lang, "projects", p["id"])}">{rich(p["title"], lang)}</a></h3>
            <p class="card-text short">{rich(p["short"], lang)}</p>{metric}
          </article>"""


def render_home(S, lang):
    H, ui = S.home, S.ui
    hero, site = H["hero"], S.site
    impact = "".join(
        f"""        <div class="tile{" tile-lead" if i == 0 else " tile-wide" if i == 1 else ""}">
          <div class="impact-num">{rich(x["num"], lang)}</div>
          <div class="impact-cap">{rich(x["caption"], lang)}</div>
        </div>
"""
        for i, x in enumerate(H["impact"])
    )
    career = "".join(
        f"""            <div class="glance-row">
              <div class="glance-when">{rich(r["dates"], lang)}</div>
              <div class="glance-what"><strong>{rich(r["role"], lang)}</strong><span>{html.escape(split_company(t(r["company"], lang))[0])}</span></div>
            </div>
"""
        for r in S.exp["roles"]
    )
    degrees = "".join(
        f"""            <div class="glance-row">
              <div class="glance-when">{d["years"]}</div>
              <div class="glance-what"><strong>{rich(d["title"], lang)}</strong><span>{rich(d["inst"], lang)}</span></div>
            </div>
"""
        for d in S.edu["degrees"]
    )
    cards = "\n".join(project_card(S, lang, S.projects[pid]) for pid in H["projects"]["featured"])
    feat = "".join(
        f"""            <div class="glance-row">
              <div class="glance-when">{p["year"]}</div>
              <div class="glance-what"><strong>{rich(p["title"], lang)}</strong><span>{html.escape(p["venue"])}</span></div>
            </div>
"""
        for p in sorted((S.pubs[i] for i in H["research"]["featured"]), key=lambda x: -x["year"])
    )
    principles = "\n".join(
        f"""        <article class="card lead-card compact"><h3>{rich(x["title"], lang)}</h3></article>"""
        for x in S.about["principles"]
    )
    cert_rows = "".join(
        f"""            <div class="glance-row">
              <div class="glance-when">{c["year"]}</div>
              <div class="glance-what"><strong>{rich(c["title"], lang)}</strong><span>{rich(c["issuer"], lang)}</span></div>
            </div>
"""
        for c in cert_items(S) if c.get("featured")
    )
    cert_block = f'            <div class="glance-label">{rich(S.edu["certifications_title"], lang)}</div>' + chr(10) + cert_rows if cert_rows else ""
    main = f"""    <header class="hero" id="home">
      <div class="container hero-grid">
        <div class="hero-copy">
          <h1>{rich(hero["title"], lang)}</h1>
          <p class="hero-sub">{rich(hero["subtitle"], lang)}</p>
          <p class="hero-tagline">{rich(hero["tagline"], lang)}</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="/{attr(site["links"]["cv"])}" target="_blank" rel="noopener">{icon("download", 18)}<span>{rich(ui["download_cv"], lang)}</span></a>
            <a class="icon-btn" href="{attr(site["links"]["linkedin"])}" target="_blank" rel="noopener noreferrer" title="LinkedIn" aria-label="LinkedIn">{icon("linkedin", 19)}</a>
            <a class="icon-btn" href="{attr(site["links"]["scholar"])}" target="_blank" rel="noopener noreferrer" title="Google Scholar" aria-label="Google Scholar">{icon("scholar", 19)}</a>
          </div>
        </div>
        <div class="hero-photo">
          <div class="photo-frame">
            <img src="/Aaron_sin_fondo.png" alt="{attr(site["name"])}" width="646" height="948" decoding="async" fetchpriority="high" />
          </div>
        </div>
      </div>
    </header>

    <section class="impact" id="impact">
      <div class="container">
        <div class="bento">
{impact}        </div>
      </div>
    </section>

    <section class="section" id="about">
      <div class="container">
        <div class="section-head section-head--row">
          <div class="lead-text">
            <h2 class="section-title">{rich(S.about["summary_title"], lang)}</h2>
            <p class="section-intro">{rich(H["about"]["text"], lang)}</p>
          </div>
          {more_link(lang, "about", H["about"]["cta"])}
        </div>
      </div>
    </section>

    <section class="section section-tint" id="experience">
      <div class="container split">
        <div>
          <h2 class="section-title">{rich(S.nav["experience"], lang)}</h2>
          <p class="section-intro">{rich(H["experience"]["text"], lang)}</p>
          <p class="cta-row">{more_link(lang, "experience", H["experience"]["cta"])}</p>
        </div>
        <div class="card glance">
{career}        </div>
      </div>
    </section>

    <section class="section" id="projects">
      <div class="container">
        <div class="section-head section-head--row">
          <div class="lead-text">
            <h2 class="section-title">{rich(S.nav["projects"], lang)}</h2>
            <p class="section-intro">{rich(H["projects"]["text"], lang)}</p>
          </div>
          {more_link(lang, "projects", H["projects"]["cta"])}
        </div>
        <div class="grid-cards">
{cards}
        </div>
      </div>
    </section>

    <section class="section section-tint" id="research">
      <div class="container split">
        <div>
          <h2 class="section-title">{rich(S.nav["research"], lang)}</h2>
          <p class="section-intro">{rich(H["research"]["text"], lang)}</p>
          <p class="section-intro"><strong>{rich(ui["present_stats"], lang)}</strong></p>
          <p class="cta-row">{more_link(lang, "research", H["research"]["cta"])}</p>
        </div>
        <div class="card glance">
{feat}        </div>
      </div>
    </section>

    <section class="section" id="education">
      <div class="container split">
        <div>
          <h2 class="section-title">{rich(S.nav["education"], lang)}</h2>
          <p class="section-intro">{rich(H["education"]["text"], lang)}</p>
          <p class="cta-row">{more_link(lang, "education", H["education"]["cta"])}</p>
        </div>
        <div class="card glance">
{degrees}{cert_block}        </div>
      </div>
    </section>

    <section class="section section-tint" id="leadership">
      <div class="container">
        <div class="section-head section-head--row">
          <div class="lead-text">
            <h2 class="section-title">{rich(H["leadership"]["title"], lang)}</h2>
            <p class="section-intro">{rich(H["leadership"]["text"], lang)}</p>
          </div>
          {more_link(lang, "about", H["leadership"]["cta"], "leadership")}
        </div>
        <div class="grid-3 lead-grid">
{principles}
        </div>
      </div>
    </section>"""
    return H["meta"]["title"][lang], H["meta"]["description"][lang], main


# ------------------------------------------------------------------------------ detail pages
def render_experience(S, lang):
    items = []
    for r in S.exp["roles"]:
        company, loc = split_company(t(r["company"], lang))
        loc_html = f'<span class="role-loc">{html.escape(loc)}</span>' if loc else ""
        official = f'\n            <div class="role-official">{rich(r["official"], lang)}</div>' if r.get("official") else ""
        summary = f'\n            <p class="role-summary">{rich(r["summary"], lang)}</p>' if r.get("summary") else ""
        bullets = "\n".join(f"              <li>{rich(b, lang)}</li>" for b in r["bullets"])
        chips = ""
        if r.get("projects"):
            links = "".join(
                f'<a class="chip" href="{url(lang, "projects", pid)}">{rich(S.projects[pid]["title"], lang)}</a>' for pid in r["projects"]
            )
            chips = f'\n            <div class="chips"><span class="label">{rich(S.ui["related_projects"], lang)}</span>{links}</div>'
        items.append(f"""        <li id="{r["id"]}"{' class="early-role"' if r.get("early") else ""}>
          <div class="role-meta">
            <span class="role-dates">{rich(r["dates"], lang)}</span>
            <h3>{rich(r["role"], lang)}</h3>
            <div class="role-company">{html.escape(company)}{loc_html}</div>{official}
          </div>
          <div class="role-body">{summary}
            <ul class="points">
{bullets}
            </ul>{chips}
          </div>
        </li>""")
    inner = '        <ul class="timeline">\n' + "\n".join(items) + "\n        </ul>"
    main = page_head(S, lang, "experience", S.exp["intro"]) + "\n" + wrap_body(inner)
    return f"{plain(S.nav['experience'], lang)} · {S.site['name']}", plain(S.exp["intro"], lang), main


def project_article(S, lang, p):
    body = "".join(f"<p>{rich(x, lang)}</p>" for x in p["body"])
    points = ""
    if p.get("points"):
        points = '\n          <ul class="points">\n' + "\n".join(f"            <li>{rich(x, lang)}</li>" for x in p["points"]) + "\n          </ul>"
    sub = ""
    if p.get("subtitle"):
        dates = f'<span class="role-dates">{rich(p["dates"], lang)}</span>' if p.get("dates") else ""
        sub = f'\n          <div class="proj-sub">{rich(p["subtitle"], lang)}{dates}</div>'
    access = ""
    foot_links = [f'<a href="{attr(l["url"])}" target="_blank" rel="noopener">{rich(l["label"], lang)}</a>' for l in p.get("links", [])]
    if p.get("access"):
        access = f'\n          <p class="venture-access">{"".join(foot_links)}<span>{rich(p["access"], lang)}</span></p>'
        foot_links = []
    metric = f'\n          <span class="pf-metric">{rich(p["metric"], lang)}</span>' if p.get("metric") else ""
    foot = list(foot_links)
    if p.get("pubs"):
        def pub_label(pb):
            return pb["venue"] if str(pb["year"]) in pb["venue"] else f'{pb["venue"]}, {pb["year"]}'
        pubs = " · ".join(
            f'<a href="{url(lang, "research", "pub-" + pid)}" title="{attr(plain(S.pubs[pid]["title"], lang))}">{html.escape(pub_label(S.pubs[pid]))}</a>'
            for pid in p["pubs"]
        )
        foot.append(f'<span><span class="label">{rich(S.ui["related_pubs"], lang)}:</span> {pubs}</span>')
    if p.get("role"):
        foot.append(f'<a href="{url(lang, "experience", p["role"])}">{rich(S.ui["role_details"], lang)} →</a>')
    foot_html = f'\n          <div class="proj-foot">{"".join(foot)}</div>' if foot else ""
    return f"""        <article class="card proj" id="{p["id"]}">
          <div class="pf-top">
            <span class="pf-icon">{icon(p["icon"])}</span>
            <span class="badge-type">{rich(p["badge"], lang)}</span>
          </div>
          <h3>{rich(p["title"], lang)}</h3>{sub}
          <div class="proj-body">{body}</div>{points}{access}
          <div class="proj-end">{metric}{foot_html}
          </div>
        </article>"""


def render_projects(S, lang):
    groups = []
    for g in S.proj["groups"]:
        intro = f'\n        <p class="group-intro">{rich(g["intro"], lang)}</p>' if g.get("intro") else ""
        note = f'\n        <p class="group-note">{rich(g["note"], lang)}</p>' if g.get("note") else ""
        two = " two" if len(g["items"]) > 1 else ""
        arts = "\n".join(project_article(S, lang, i) for i in g["items"])
        groups.append(f"""      <section class="proj-group" id="{g["id"]}">
        <h2>{rich(g["title"], lang)}</h2>{intro}{note}
        <div class="proj-list{two}">
{arts}
        </div>
      </section>""")
    main = page_head(S, lang, "projects", S.proj["intro"]) + "\n" + wrap_body("\n".join(groups))
    return f"{plain(S.nav['projects'], lang)} · {S.site['name']}", plain(S.proj["intro"], lang), main


def render_research(S, lang):
    R = S.res
    pubs = []
    for p in R["publications"]:
        place = f'&nbsp;· {html.escape(p["place"])}' if p.get("place") else ""
        links = "".join(f'<a href="{attr(l["url"])}" target="_blank" rel="noopener">{rich(l["label"], lang)}</a>' for l in p["links"])
        pubs.append(f"""            <li class="pub-item" id="pub-{p["id"]}">
              <div class="pub-venue"><strong>{html.escape(p["venue"])}</strong>&nbsp;· <span class="pub-year">{p["year"]}</span>{place}&nbsp;· <em>{rich(p["badge"], lang)}</em></div>
              <h4 class="pub-title">{rich(p["title"], lang)}</h4>
              <div class="pub-authors">{p["authors"]}</div>
              <p class="pub-desc">{rich(p["desc"], lang)}</p>
              <div class="pub-links">{links}</div>
            </li>""")
    talks = "\n".join(f'              <li><span class="talk-year">{x["year"]}</span>{rich(x["text"], lang)}</li>' for x in R["talks"])
    scholar = S.site["links"]["scholar"]
    pr = R["peer_review"]
    pc = pr["columns"]
    peer_table = data_table(
        lang, pr["title"],
        [(pc["venue"], "c-main"), (pc["role"], ""), (pc["place"], ""), (pc["year"], "num")],
        [[html.escape(r["venue"]), rich(r["role"], lang), rich(r["place"], lang) if r.get("place") else "", r["year"]] for r in pr["rows"]],
    )
    inner = f"""        <div class="research-main">
          <div class="card panel">
            <div class="panel-head"><h2 class="panel-title">{rich(R["publications_title"], lang)}</h2></div>
            <ol class="pub-list">
{chr(10).join(pubs)}
            </ol>
            <div class="panel-foot">
              <a class="btn btn-secondary" href="{attr(scholar)}" target="_blank" rel="noopener">{icon("scholar", 18)}<span>{rich(R["scholar_cta"], lang)}</span></a>
            </div>
          </div>
          <div class="micro-stack">
            <div class="card micro">
              <div class="micro-head"><span class="micro-icon">{icon("mic", 16)}</span><h2>{rich(R["talks_title"], lang)}</h2></div>
              <ul>
{talks}
              </ul>
            </div>
            <div class="card micro">
              <div class="micro-head"><span class="micro-icon">{icon("pen", 16)}</span><h2>{rich(R["editorial_title"], lang)}</h2></div>
              <p>{rich(R["editorial"], lang)}</p>
            </div>
          </div>
        </div>
        <section class="block">
          <h2 class="block-title">{rich(pr["title"], lang)}</h2>
          {peer_table}
        </section>"""
    main = page_head(S, lang, "research", R["intro"]) + "\n" + wrap_body(inner)
    return f"{plain(S.nav['research'], lang)} · {S.site['name']}", plain(R["intro"], lang), main


def render_education(S, lang):
    E = S.edu
    degrees = "\n".join(
        f"""          <article class="card edu-card">
            <img src="/{attr(d["logo"])}" alt="{attr(d["alt"])}" class="edu-logo" loading="lazy" width="130" height="38" />
            <div class="edu-years">{d["years"]}</div>
            <h3>{rich(d["title"], lang)}</h3>
            <p>{rich(d["inst"], lang)}</p>
          </article>"""
        for d in E["degrees"]
    )
    grants = "\n".join(
        f"""            <div class="entry">
              <div class="entry-year">{g["year"]}</div>
              <div><h3>{rich(g["title"], lang)}</h3><p>{rich(g["text"], lang)}</p></div>
            </div>"""
        for g in E["grants"]
    )
    langs = "\n".join(
        f"""          <div class="card lang-item">
            <div class="lang-name">{rich(x["name"], lang)}</div>
            <div class="lang-level">{rich(x["level"], lang)}</div>
          </div>"""
        for x in E["languages"]
    )
    certs = "\n".join(
        f"""            <div class="entry">
              <div class="entry-year">{c["year"]}</div>
              <div><h3>{cert_title(c, lang)}</h3><p>{rich(c["issuer"], lang)} · {rich(c["kind"], lang)}</p></div>
            </div>"""
        for c in cert_items(S)
    )
    td = E["teaching_detail"]
    courses, sup = td["courses"], td["supervision"]
    cc, sc = courses["columns"], sup["columns"]
    courses_table = data_table(
        lang, courses["title"],
        [(cc["course"], "c-main"), (cc["lead"], ""), (cc["level"], ""), (cc["years"], "num"), (cc["hours"], "num")],
        [[rich(r["course"], lang), html.escape(r["lead"]), rich(r["level"], lang), r["years"], str(r["hours"])] for r in courses["rows"]],
        foot=(courses["total_label"], str(courses["total"])),
    )
    supervision_table = data_table(
        lang, sup["title"],
        [(sc["what"], "c-main"), (sc["first"], ""), (sc["level"], ""), (sc["year"], "num"), (sc["months"], "num")],
        [[rich(r["what"], lang), html.escape(r["first"]) if r["first"] else "", rich(r["level"], lang), str(r["year"]), str(r["months"])] for r in sup["rows"]],
    )
    inner = f"""        <section class="block">
          <h2 class="block-title">{rich(E["degrees_title"], lang)}</h2>
          <div class="grid-4">
{degrees}
          </div>
        </section>
        <section class="block">
          <h2 class="block-title">{rich(E["certifications_title"], lang)}</h2>
          <div class="card pad">
{certs}
          </div>
        </section>
        <section class="block">
          <h2 class="block-title">{rich(E["grants_title"], lang)}</h2>
          <div class="card pad">
{grants}
          </div>
        </section>
        <section class="block">
          <h2 class="block-title">{rich(E["teaching_title"], lang)}</h2>
          <div class="card text-card"><p>{rich(E["teaching"], lang)}</p></div>
          <h3 class="sub-block-title">{rich(courses["title"], lang)}</h3>
          {courses_table}
          <h3 class="sub-block-title">{rich(sup["title"], lang)}</h3>
          {supervision_table}
        </section>
        <section class="block">
          <h2 class="block-title">{rich(E["languages_title"], lang)}</h2>
          <div class="lang-row">
{langs}
          </div>
        </section>"""
    main = page_head(S, lang, "education", E["intro"]) + "\n" + wrap_body(inner)
    return f"{plain(S.nav['education'], lang)} · {S.site['name']}", plain(E["intro"], lang), main


def render_about(S, lang):
    A, site = S.about, S.site
    summary = "".join(f"<p>{rich(p, lang)}</p>" for p in A["summary"])
    skills = "\n".join(
        f"""            <div class="skill-row">
              <div class="skill-label">{rich(s["label"], lang)}</div>
              <div class="skill-list">{rich(s["list"], lang)}</div>
            </div>"""
        for s in A["skills"]
    )
    principles = "\n".join(
        f"""            <article class="card lead-card"><h3>{rich(x["title"], lang)}</h3><p>{rich(x["text"], lang)}</p></article>"""
        for x in A["principles"]
    )
    inner = f"""        <section class="block">
          <h2 class="block-title">{rich(A["summary_title"], lang)}</h2>
          <div class="summary-cols">{summary}</div>
        </section>
        <section class="block">
          <h2 class="block-title">{rich(A["skills_title"], lang)}</h2>
          <div class="card skills">
{skills}
          </div>
        </section>
        <section class="block" id="leadership">
          <h2 class="block-title">{rich(A["leadership_title"], lang)}</h2>
          <p class="block-intro">{rich(A["leadership_intro"], lang)}</p>
          <div class="grid-3 lead-grid">
{principles}
          </div>
        </section>
        <section class="block">
          <h2 class="block-title">{rich(S.ui["contact"], lang)}</h2>
          <div class="card contact-card">
            <a class="mail" href="mailto:{attr(site["email"])}">{html.escape(site["email"])}</a>
            <a class="btn btn-primary" href="/{attr(site["links"]["cv"])}" target="_blank" rel="noopener">{icon("download", 18)}<span>{rich(S.ui["download_cv"], lang)}</span></a>
            <a class="icon-btn" href="{attr(site["links"]["linkedin"])}" target="_blank" rel="noopener noreferrer" title="LinkedIn" aria-label="LinkedIn">{icon("linkedin", 19)}</a>
            <a class="icon-btn" href="{attr(site["links"]["scholar"])}" target="_blank" rel="noopener noreferrer" title="Google Scholar" aria-label="Google Scholar">{icon("scholar", 19)}</a>
          </div>
        </section>"""
    main = page_head(S, lang, "about", A["intro"]) + "\n" + wrap_body(inner)
    return f"{plain(S.nav['about'], lang)} · {site['name']}", plain(A["intro"], lang), main


RENDER = {
    "": render_home, "experience": render_experience, "projects": render_projects,
    "research": render_research, "education": render_education, "about": render_about,
}


def render_404(S):
    ui = S.ui
    rows = "".join(
        f'<p><a href="{url(l)}" hreflang="{l}" lang="{l}">{rich(ui["back_home"], l)}</a> — {rich(ui["not_found_text"], l)}</p>' for l in LANGS
    )
    main = f"""    <header class="page-head">
      <div class="container">
        <h1>404</h1>
        <p>{rich(ui["not_found_title"], "en")}</p>
      </div>
    </header>
    <div class="page-body"><div class="container stack">{rows}</div></div>"""
    return layout(S, "en", "", f"404 · {S.site['name']}", plain(ui["not_found_text"], "en"), main)


# ------------------------------------------------------------------------------ output + checks
def write_page(out_root, lang, page, text):
    parts = ([] if lang == "en" else [lang]) + ([page] if page else [])
    target = out_root.joinpath(*parts, "index.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def check_links(out_root):
    """Every internal href/src must resolve to a file in the output, and every #anchor to an id in that page."""
    ids, refs = {}, []
    for f in out_root.rglob("*.html"):
        s = f.read_text(encoding="utf-8")
        ids[f] = set(re.findall(r'\bid="([^"]+)"', s))
        for m in re.finditer(r'(?:href|src)="(/[^"#]*)(#[^"]*)?"', s):
            if not m.group(1).startswith("//"):
                refs.append((f, m.group(1), (m.group(2) or "")[1:]))
    problems = []
    for f, path, anchor in refs:
        target = out_root / path.lstrip("/")
        if path.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            problems.append(f"{f.relative_to(out_root)}: broken link {path}")
        elif anchor and target.suffix == ".html" and anchor not in ids.get(target, set()):
            problems.append(f"{f.relative_to(out_root)}: missing anchor {path}#{anchor}")
    return sorted(set(problems))


def build(write=True):
    S = Site()
    tmp = ROOT / ".build-tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    try:
        shutil.copytree(STATIC, tmp, dirs_exist_ok=True)
        count = 0
        for lang in LANGS:
            for page in PAGES:
                title, description, main = RENDER[page](S, lang)
                write_page(tmp, lang, page, layout(S, lang, page, title, description, main))
                count += 1
        (tmp / "404.html").write_text(render_404(S), encoding="utf-8", newline="\n")
        base = S.site.get("base_url", "").rstrip("/")
        if base:
            urls = [f"{base}{url(l, p)}" for l in LANGS for p in PAGES]
            (tmp / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8", newline="\n")
            (tmp / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8", newline="\n")
        problems = check_links(tmp)
        if problems:
            raise BuildError("link check failed:\n  " + "\n  ".join(problems))
        if write:
            if OUT.exists():
                shutil.rmtree(OUT)
            shutil.move(str(tmp), str(OUT))
        print(f"OK: {count} pages + 404 ({len(LANGS)} languages){' -> ' + str(OUT) if write else ' (check only)'}"
              + ("" if base else "; base_url not set: no canonical/hreflang/sitemap"))
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


if __name__ == "__main__":
    try:
        build(write="--check" not in sys.argv)
    except BuildError as e:
        print(f"BUILD FAILED: {e}", file=sys.stderr)
        sys.exit(1)
