"""Builds a local Sea of Thieves reference board from the community wiki (seaofthieves.wiki.gg).

python fetch_refs.py <out_dir> [max_total]
Images are fetched at up to 1280 px wide through the MediaWiki API, one folder per topic.
For study only: nothing here is to be imported into the game. An index.csv records each source page.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://seaofthieves.wiki.gg/api.php"
UA = {"User-Agent": "BrinewakeRefBoard/1.0 (personal art reference; low rate)"}
OUT = sys.argv[1]
MAX_TOTAL = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

CATEGORIES = {            # folder -> (wiki categories, cap)
    "Islands_Locations": (["Location images"], 700),
    "Screenshots": (["Screenshots"], 500),
    "Concept_Art": (["Concept art"], 300),
    "Maps_Charts": (["Map images", "Chart images"], 250),
    "UI_Icons": (["Icon images", "Commendation images", "Achievement images"], 350),
    "UI_Parchment_Posters": (["Parchment Images", "Poster images"], 150),
    "Props": (["Prop images", "Barrel images", "Crate images", "Chest images"], 300),
    "Pirates_Outfits": (["Pirate images", "Outfit images"], 150),
}
SEARCHES = {              # folder -> (search terms in the File namespace, cap per term)
    "UI_Menus": (["menu", "screen", "HUD", "interface", "ship selection", "pirate generator", "lobby", "emporium"], 60),
    "Outposts": (["outpost", "tavern", "dock", "shipwright", "order of souls", "weaponsmith"], 60),
    "Rocks_Terrain": (["rock", "cliff", "cave", "beach", "island", "waterfall", "peak", "cove"], 60),
    "Ocean_Weather": (["ocean", "sea", "storm", "waves", "sunset", "fog", "shores of gold", "devil's roar"], 50),
    "Ships": (["sloop", "brigantine", "galleon", "sail", "hull", "figurehead"], 50),
}


def api(params):
    params = dict(params, format="json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(2 + attempt * 3)
    return {}


def pages(base):
    """Yields (title, url, description page) for a generator query, following continuation."""
    cont = {}
    while True:
        d = api(dict(base, prop="imageinfo", iiprop="url|size|mime", iiurlwidth=1280, **cont))
        for p in (d.get("query", {}).get("pages", {}) or {}).values():
            info = (p.get("imageinfo") or [{}])[0]
            if info.get("mime") in ("image/png", "image/jpeg", "image/webp") and min(info.get("width", 0), info.get("height", 0)) >= 200:
                yield p["title"], info.get("thumburl") or info.get("url"), info.get("descriptionurl", "")
        if "continue" not in d:
            return
        cont = d["continue"]
        time.sleep(0.25)


def subcats(cat):
    d = api({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat, "cmtype": "subcat", "cmlimit": 200})
    return [m["title"][9:] for m in d.get("query", {}).get("categorymembers", [])]


def download(job):
    folder, title, url, _ = job
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', title[5:])[:120]
    path = os.path.join(OUT, folder, name)
    if os.path.exists(path):
        return True
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
        time.sleep(0.15)
        return True
    except Exception:
        return False


jobs, seen = [], set()
for folder, (cats, cap) in CATEGORIES.items():
    os.makedirs(os.path.join(OUT, folder), exist_ok=True)
    n = 0
    todo = list(cats)
    for c in cats:
        todo += subcats(c)[:25]
    for c in todo:
        for title, url, src in pages({"action": "query", "generator": "categorymembers", "gcmtitle": "Category:" + c,
                                      "gcmtype": "file", "gcmlimit": 100}):
            if title not in seen and url and n < cap:
                seen.add(title)
                jobs.append((folder, title, url, src))
                n += 1
        if n >= cap:
            break
    print(folder, n, flush=True)
for folder, (terms, cap) in SEARCHES.items():
    os.makedirs(os.path.join(OUT, folder), exist_ok=True)
    n = 0
    for term in terms:
        k = 0
        for title, url, src in pages({"action": "query", "generator": "search", "gsrsearch": term, "gsrnamespace": 6, "gsrlimit": 50}):
            if title not in seen and url and k < cap:
                seen.add(title)
                jobs.append((folder, title, url, src))
                k += 1
                n += 1
            if k >= cap:
                break
    print(folder, n, flush=True)
jobs = jobs[:MAX_TOTAL] if len(jobs) > MAX_TOTAL else jobs
with open(os.path.join(OUT, "index.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["folder", "file", "source_page"])
    for folder, title, url, src in jobs:
        w.writerow([folder, title, src])
with open(os.path.join(OUT, "README.txt"), "w", encoding="utf-8") as f:
    f.write("Sea of Thieves reference board for Brinewake.\n"
            "Source: seaofthieves.wiki.gg (community wiki), fetched through its public API. Game imagery belongs to Rare / Microsoft.\n"
            "Use: look, study shapes, colour and layout. Do not import, trace or ship any of these files.\n"
            "index.csv lists the wiki page for every file.\n")
print("queued", len(jobs), flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:
    done = sum(1 for ok in pool.map(download, jobs) if ok)
print("downloaded", done, "of", len(jobs), flush=True)
