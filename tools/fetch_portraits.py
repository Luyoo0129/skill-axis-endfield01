# -*- coding: utf-8 -*-
"""从 endfield.wiki.gg 抓取干员头像，供连携技图标使用。

产出：
    data/portraits/<中文名>.png    （统一缩放到 256x256，保留透明）
    data/portraits/index.json      （中文名 -> 文件 / 英文名）

用法：
    python tools/fetch_portraits.py            增量
    python tools/fetch_portraits.py --force    全部重下
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

API = "https://endfield.wiki.gg/api.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(BASE, "data", "icons")
OUT_DIR = os.path.join(BASE, "data", "portraits")
TARGET = 256


def api(**params):
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def operators():
    with open(os.path.join(ICON_DIR, "index.json"), encoding="utf-8") as f:
        entries = json.load(f)
    seen = {}
    for e in entries:
        seen.setdefault(e["cn"], e["en"])
    return seen


def resolve(filenames):
    urls = {}
    items = list(filenames)
    for i in range(0, len(items), 40):
        chunk = items[i:i + 40]
        titles = "|".join("File:" + f for f in chunk)
        d = api(action="query", titles=titles, prop="imageinfo", iiprop="url|size")
        for page in d.get("query", {}).get("pages", {}).values():
            info = page.get("imageinfo")
            if info:
                urls[page["title"][5:]] = info[0]["url"]
        time.sleep(0.1)
    return urls


def safe_name(text):
    bad = '\\/:*?"<>|'
    return "".join("_" if ch in bad else ch for ch in text).strip() or "unknown"


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)
    ops = operators()
    print("干员数:", len(ops))

    wanted = {f"{en} icon.png": cn for cn, en in ops.items()}
    print("解析头像地址…")
    urls = resolve(wanted.keys())
    print("找到地址:", len(urls), "/", len(wanted))

    ok = skip = fail = 0
    manifest = []
    for filename, cn in sorted(wanted.items(), key=lambda kv: kv[1]):
        url = urls.get(filename)
        out = os.path.join(OUT_DIR, safe_name(cn) + ".png")
        if not url:
            print("  [缺]", cn, filename)
            fail += 1
            continue
        if os.path.exists(out) and not force:
            skip += 1
            manifest.append({"cn": cn, "en": ops[cn], "file": os.path.basename(out)})
            continue
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Referer": "https://endfield.wiki.gg/"})
            with urllib.request.urlopen(req, timeout=60) as r:
                blob = r.read()
            im = Image.open(io.BytesIO(blob)).convert("RGBA")
            im.thumbnail((TARGET, TARGET), Image.LANCZOS)
            im.save(out)
            ok += 1
            manifest.append({"cn": cn, "en": ops[cn], "file": os.path.basename(out)})
        except Exception as e:
            print("  [失败]", cn, e)
            fail += 1

    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"下载 {ok}，跳过 {skip}，失败 {fail}")
    print("目录:", OUT_DIR)
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
