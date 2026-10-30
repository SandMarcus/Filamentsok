"""Søkemotoroptimalisering: canonical, Open Graph, strukturerte data, robots.txt og sitemap.xml.
Adressen hentes fra config/site.json («url»). Ren Python, ingen avhengigheter."""
import html
import json
from pathlib import Path

# side -> (adresse på siden, beskrivelse brukes fra <meta name="description"> i selve siden)
PAGES = {
    "index.html": "/",
    "guide/index.html": "/guide/",
    "funksjoner/index.html": "/funksjoner/",
    "partner/index.html": "/partner/",
    "3d-print/index.html": "/3d-print/",
}
PRIORITY = {"/": "1.0", "/guide/": "0.8", "/funksjoner/": "0.5", "/partner/": "0.4", "/3d-print/": "0.5"}


def site_config(root):
    p = Path(root) / "config" / "site.json"
    cfg = {"url": "", "google_verification": ""}
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    cfg["url"] = (cfg.get("url") or "").rstrip("/")
    return cfg


def _meta(page, name):
    import re
    m = re.search(r'<meta name="%s" content="([^"]*)"' % name, page)
    return html.unescape(m.group(1)) if m else ""


def _title(page):
    import re
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def _jsonld(path, title, desc, url, base):
    data = []
    if path == "/":
        data.append({"@context": "https://schema.org", "@type": "WebSite", "name": "Filamentsøk.no", "url": url,
                     "inLanguage": "nb-NO", "description": desc})
    elif path == "/3d-print/":
        data.append({"@context": "https://schema.org", "@type": "Service", "name": "3D-printtjeneste", "serviceType": "3D-printing på bestilling",
                     "url": url, "description": desc, "areaServed": "NO", "provider": {"@type": "Organization", "name": "Filamentsøk.no", "url": base}})
    elif path == "/guide/":
        data.append({"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url, "description": desc, "inLanguage": "nb-NO"})
    return "".join('<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>\n" for d in data)


def inject_seo(page, path, cfg):
    """Legger canonical, Open Graph, Twitter-kort og strukturerte data i <head>. Uten adresse i config gjøres ingenting."""
    base = cfg.get("url")
    if not base or 'rel="canonical"' in page:
        return page
    url = base + path
    title, desc = _title(page), _meta(page, "description")
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    tags = f'<link rel="canonical" href="{esc(url)}">\n'
    if cfg.get("google_verification"):
        tags += f'<meta name="google-site-verification" content="{esc(cfg["google_verification"])}">\n'
    tags += (f'<meta property="og:type" content="website">\n<meta property="og:site_name" content="Filamentsøk.no">\n'
             f'<meta property="og:locale" content="nb_NO">\n<meta property="og:title" content="{esc(title)}">\n'
             f'<meta property="og:description" content="{esc(desc)}">\n<meta property="og:url" content="{esc(url)}">\n'
             f'<meta property="og:image" content="{esc(base)}/icon-512.png">\n<meta name="twitter:card" content="summary">\n')
    tags += _jsonld(path, title, desc, url, base)
    return page.replace("</head>", tags + "</head>", 1)


def write_files(out, cfg, lastmod, exists):
    """robots.txt og sitemap.xml i byggmappen. `exists(side)` sier om siden er med i bygget."""
    base = cfg.get("url")
    if not base:
        return
    urls = "".join(f"  <url><loc>{html.escape(base + p)}</loc><lastmod>{lastmod}</lastmod><priority>{PRIORITY[p]}</priority></url>\n"
                   for page, p in PAGES.items() if exists(page))
    (Path(out) / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n", encoding="utf-8")
    (Path(out) / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
