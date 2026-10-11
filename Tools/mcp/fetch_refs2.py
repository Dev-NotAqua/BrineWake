"""Second pass for the reference board: every large wiki image (mostly in-game screenshots), sorted into topic folders by file name.

python fetch_refs2.py <out_dir> [max_total]
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
MAX_TOTAL = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
TOPICS = [("UI_Menus", r"menu|screen|hud|interface|lobby|emporium|ui_|_ui|banner|tab"),
          ("Outposts", r"outpost|tavern|dock|shipwright|shop|weaponsmith|order_of_souls|merrick|seapost"),
          ("Ships", r"sloop|brigantine|galleon|ship|sail|hull|figurehead|cannon"),
          ("Ocean_Weather", r"ocean|sea_|storm|wave|sunset|fog|sky|kraken|megalodon"),
          ("Rocks_Terrain", r"rock|cliff|cave|beach|waterfall|peak|cove|reef|fort|isle|island|key|bay|crag|haven|hideaway")]


def api(params):
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(dict(params, format="json")), headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(2 + attempt * 3)
    return {}


have = set()
for root, _, files in os.walk(OUT):
    have.update(files)
jobs, cont = [], {}
while len(jobs) < MAX_TOTAL:
    d = api(dict({"action": "query", "generator": "allimages", "gaisort": "name", "gaiminsize": 350000, "gailimit": 100,
                  "prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 1280}, **cont))
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/png", "image/jpeg", "image/webp") or info.get("width", 0) < 900:
            continue
        name = re.sub(r'[^A-Za-z0-9._-]+', '_', p["title"][5:])[:120]
        if name in have:
            continue
        low = name.lower()
        folder = next((f for f, pat in TOPICS if re.search(pat, low)), "Misc_Large")
        jobs.append((folder, name, info.get("thumburl") or info.get("url"), info.get("descriptionurl", "")))
    if "continue" not in d:
        break
    cont = d["continue"]
    time.sleep(0.25)
jobs = jobs[:MAX_TOTAL]
print("queued", len(jobs), flush=True)


def download(job):
    folder, name, url, _ = job
    os.makedirs(os.path.join(OUT, folder), exist_ok=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        with open(os.path.join(OUT, folder, name), "wb") as f:
            f.write(data)
        time.sleep(0.15)
        return True
    except Exception:
        return False


with open(os.path.join(OUT, "index.csv"), "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for folder, name, url, src in jobs:
        w.writerow([folder, name, src])
with ThreadPoolExecutor(max_workers=4) as pool:
    done = sum(1 for ok in pool.map(download, jobs) if ok)
print("downloaded", done, "of", len(jobs), flush=True)
