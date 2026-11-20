"""Openly licensed archive images, each with its licence and credit recorded.

  docuframe archive find "boston molasses 1919"     # Wikimedia Commons, newest licence data
  docuframe archive fetch --project P               # download photos.json entries that have no file yet
  docuframe archive credits --project P             # credits.md for the description

photos.json entries say where an image comes from:
  {"id": "P01", "commons": "File:Example.jpg"}
  {"id": "P02", "url": "https://...", "license": "Public domain", "credit": "...", "source": "<record page>"}
Allowed in a commercial film: public domain, CC0, CC BY, CC BY-SA (share-alike is noted in the credits).
Refused: non-commercial (NC) and no-derivatives (ND) licences, unless you pass --allow-restricted.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

FREE = ("public domain", "pd", "cc0", "cc by", "cc-by", "no restrictions", "no known copyright")
RESTRICTED = ("nc", "nd", "noncommercial", "non-commercial", "noderiv", "all rights reserved")


def commercial_ok(licence: str) -> bool:
    words = re.split(r"[^a-z0-9]+", (licence or "").lower())
    text = " ".join(words)
    if any(r in words for r in ("nc", "nd")) or any(r in text for r in RESTRICTED[2:]):
        return False
    return any(f in text for f in FREE)


class Commons:
    """A small client for the Wikimedia Commons API (read only, polite: identifies itself, backs off)."""
    endpoint = "https://commons.wikimedia.org/w/api.php"
    agent = "docuframe/0.1 (https://github.com/moiensaboohi/docuframe)"

    def _get(self, **query):
        query.setdefault("format", "json")
        query.setdefault("formatversion", "2")
        address = f"{self.endpoint}?{urllib.parse.urlencode(query)}"
        wait = 1.5
        while True:
            try:
                req = urllib.request.Request(address, headers={"User-Agent": self.agent})
                with urllib.request.urlopen(req, timeout=40) as resp:
                    return json.load(resp)
            except OSError as err:
                if wait > 12:
                    raise SystemExit(f"Wikimedia Commons did not answer ({err}). Check your connection and try again.") from None
                time.sleep(wait)
                wait *= 2

    @staticmethod
    def _text(field):
        return html.unescape(re.sub(r"<.*?>", "", (field or {}).get("value", "") or "")).strip()

    def files(self, titles):
        data = self._get(action="query", titles="|".join(titles), prop="imageinfo",
                         iiprop="url|size|extmetadata", iiurlwidth=3200)
        found = []
        for page in data.get("query", {}).get("pages", []):
            info = (page.get("imageinfo") or [None])[0]
            if not info:
                continue
            meta = info.get("extmetadata", {})
            licence = self._text(meta.get("LicenseShortName")) or self._text(meta.get("UsageTerms"))
            found.append({
                "title": page["title"], "download": info.get("thumburl") or info["url"],
                "size": (info.get("width"), info.get("height")), "license": licence,
                "license_url": self._text(meta.get("LicenseUrl")),
                "credit": self._text(meta.get("Artist")) or self._text(meta.get("Credit")),
                "source": info.get("descriptionurl"), "license_ok": commercial_ok(licence),
            })
        return found

    def search(self, words, limit):
        hits = self._get(action="query", list="search", srsearch=words, srnamespace=6, srlimit=limit)
        titles = [h["title"] for h in hits.get("query", {}).get("search", [])]
        return self.files(titles) if titles else []


def download(address, target: pathlib.Path):
    req = urllib.request.Request(address, headers={"User-Agent": Commons.agent})
    with urllib.request.urlopen(req, timeout=120) as resp, open(target, "wb") as out:
        while True:
            block = resp.read(1 << 16)
            if not block:
                break
            out.write(block)


def suffix_of(address, default=".jpg"):
    return pathlib.Path(urllib.parse.urlparse(address).path).suffix.lower() or default


def find(words, limit):
    results = Commons().search(words, limit)
    if not results:
        print("No results. Search with the archive's own words: the place, the year, the event.")
    for r in results:
        verdict = "usable    " if r["license_ok"] else "not usable"
        w, h = r["size"]
        print(f"{verdict}  {r['title']}  ({r['license'] or 'licence unknown'}, {w}x{h})")


def fetch(project: pathlib.Path, allow_restricted=False):
    listing = project / "photos.json"
    spec = json.loads(listing.read_text(encoding="utf-8"))
    store = project / "assets" / "photos"
    store.mkdir(parents=True, exist_ok=True)
    pending = [p for p in spec.get("photos", []) if not (p.get("file") and (store / p["file"]).exists())]
    by_title = {}
    titles = [p["commons"] for p in pending if p.get("commons")]
    for start in range(0, len(titles), 40):
        for r in Commons().files(titles[start:start + 40]):
            by_title[r["title"].replace("_", " ")] = r
    for p in pending:
        if p.get("commons"):
            r = by_title.get(p["commons"].replace("_", " "))
            if r is None:
                print(f"{p['id']}: {p['commons']} is not on Commons (check the exact file name).")
                continue
            p.update(license=r["license"], license_url=r["license_url"], credit=r["credit"], source=r["source"], license_ok=r["license_ok"])
            if not (r["license_ok"] or allow_restricted):
                print(f"{p['id']}: not downloaded — its licence ({r['license']}) does not allow commercial use.")
                continue
            p["file"] = p["id"] + suffix_of(r["download"])
            download(r["download"], store / p["file"])
        elif p.get("url"):
            p["file"] = p["id"] + suffix_of(p["url"])
            download(p["url"], store / p["file"])
            p.setdefault("license_ok", commercial_ok(p.get("license", "")))
        else:
            continue
        print(f"{p['id']}: {p['file']}  [{p.get('license') or 'licence missing — add it to photos.json'}]")
    listing.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def credits(project: pathlib.Path):
    spec = json.loads((project / "photos.json").read_text(encoding="utf-8"))
    rows = []
    for p in spec.get("photos", []):
        lic = p.get("license") or "licence not recorded"
        share = " — share-alike" if re.search(r"\bsa\b", lic.lower()) else ""
        where = f" ({p['source']})" if p.get("source") else ""
        rows.append(f"- {p.get('what') or p['id']}: {p.get('credit') or 'unknown author'}, {lic}{share}{where}")
    (project / "credits.md").write_text("# Image credits\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"credits.md: {len(rows)} images")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["find", "fetch", "credits", "search", "get"])
    ap.add_argument("words", nargs="?", default="")
    ap.add_argument("--project")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--allow-restricted", action="store_true")
    a = ap.parse_args(argv)
    if a.action in ("find", "search"):
        return find(a.words, a.limit)
    if not a.project:
        raise SystemExit("Add --project <folder>.")
    project = pathlib.Path(a.project).resolve()
    return fetch(project, a.allow_restricted) if a.action in ("fetch", "get") else credits(project)
