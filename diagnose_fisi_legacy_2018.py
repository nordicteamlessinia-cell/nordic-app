import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

COMMITTEES = [
    "trentino",
    "alto-adige",
    "veneto",
    "alpi-centrali",
    "alpi-occidentali",
    "friuli-venezia-giulia",
    "appennino-emiliano",
    "appennino-toscano",
    "abruzzo",
    "lazio-sardegna",
    "umbro-marchigiano",
    "campano",
    "calabro-lucano",
    "pugliese",
    "siculo",
    "ligure",
    "asiva",
]

YEAR = 2018
HEADERS = {"User-Agent": "Mozilla/5.0 NordicHub-Legacy-Diagnostic/1.0"}
session = requests.Session()
session.headers.update(HEADERS)

FONDO_TERMS = (
    "SCI DI FONDO", "FONDO", "CROSS COUNTRY", "LANGLAUF",
    "SKIROLL", "ROLLER SKI", "ROLLERSKI",
)
BAD_TERMS = (
    "SCI ALPINO", "SLALOM", "GIGANTE", "SUPER G", "BIATHLON",
    "SNOWBOARD", "FREESTYLE", "COMBINATA NORDICA", "SALTO",
    "SCI ALPINISMO", "SCIALPINISMO",
)

def is_fondo_text(text: str) -> bool:
    u = (text or "").upper()
    return any(k in u for k in FONDO_TERMS) and not any(k in u for k in BAD_TERMS)

def fetch(url, timeout=25):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r

def sitemap_urls(base):
    found = set()
    candidates = [
        urljoin(base, "wp-sitemap.xml"),
        urljoin(base, "sitemap_index.xml"),
    ]
    for sm in candidates:
        try:
            r = fetch(sm)
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "xml")
        locs = [x.get_text(strip=True) for x in soup.find_all("loc")]
        nested = [u for u in locs if u.endswith(".xml")]
        if nested:
            for child in nested:
                try:
                    cr = fetch(child)
                    cs = BeautifulSoup(cr.text, "xml")
                    for loc in cs.find_all("loc"):
                        u = loc.get_text(strip=True)
                        if f"/{YEAR}/" in u:
                            found.add(u)
                except Exception:
                    pass
        else:
            for u in locs:
                if f"/{YEAR}/" in u:
                    found.add(u)
        if found:
            break
    return found

def rest_posts(base):
    found = set()
    api = urljoin(base, "wp-json/wp/v2/posts")
    params = {
        "after": f"{YEAR}-01-01T00:00:00",
        "before": f"{YEAR}-12-31T23:59:59",
        "per_page": 100,
        "page": 1,
        "_fields": "link,title,content",
    }
    while True:
        try:
            r = session.get(api, params=params, timeout=25)
            if r.status_code in (400, 404):
                break
            r.raise_for_status()
            rows = r.json()
        except Exception:
            break
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            text = " ".join([
                str(row.get("title", {}).get("rendered", "")),
                str(row.get("content", {}).get("rendered", "")),
            ])
            if is_fondo_text(BeautifulSoup(text, "html.parser").get_text(" ", strip=True)):
                link = row.get("link")
                if link:
                    found.add(link)
        total_pages = int(r.headers.get("X-WP-TotalPages", "1") or "1")
        if params["page"] >= total_pages:
            break
        params["page"] += 1
        time.sleep(0.1)
    return found

def inspect_post(url):
    try:
        r = fetch(url)
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    if not is_fondo_text(text):
        return None
    pdfs = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        label = a.get_text(" ", strip=True)
        probe = f"{label} {href}"
        if ".pdf" in href.lower() and (
            is_fondo_text(probe)
            or "CLASSIF" in probe.upper()
            or "RISULT" in probe.upper()
        ):
            pdfs.add(href)
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    return title, sorted(pdfs)

def main():
    total_posts = 0
    total_pdfs = 0
    for slug in COMMITTEES:
        base = f"https://comitati.fisi.org/{slug}/"
        urls = set()
        sm = sitemap_urls(base)
        rest = rest_posts(base)
        urls.update(sm)
        urls.update(rest)

        fondo_posts = []
        pdfs = set()
        for u in sorted(urls):
            info = inspect_post(u)
            if not info:
                continue
            title, found_pdfs = info
            fondo_posts.append((u, title))
            pdfs.update(found_pdfs)

        total_posts += len(fondo_posts)
        total_pdfs += len(pdfs)

        print(f"\n=== {slug} ===", flush=True)
        print(f"URL 2018 trovati: {len(urls)}", flush=True)
        print(f"Post/pagine pertinenti al fondo: {len(fondo_posts)}", flush=True)
        print(f"PDF classifiche candidati: {len(pdfs)}", flush=True)
        for u, title in fondo_posts[:8]:
            print(f"  POST {title[:110]} | {u}", flush=True)
        for p in sorted(pdfs)[:12]:
            print(f"  PDF  {p}", flush=True)

    print("\n==============================", flush=True)
    print(f"Totale post/pagine fondo 2018: {total_posts}", flush=True)
    print(f"Totale PDF candidati 2018: {total_pdfs}", flush=True)

if __name__ == "__main__":
    main()
