# -*- coding: utf-8 -*-
"""从 endfield.wiki.gg 抓取干员技能图标，生成 data/icons/ 图标库。

用法：
    python tools/fetch_icons.py           增量下载（已存在的不重复下）
    python tools/fetch_icons.py --force   全部重下

产出：
    data/icons/<中文名>_技能.png
    data/icons/<中文名>_连携.png
    data/icons/<中文名>_终结.png
    data/icons/index.json   图标清单（供程序里的图标库面板使用）
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://endfield.wiki.gg/api.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "data", "icons")

KINDS = {
    "skill": "技能",
    "combo": "连携",
    "ult": "终结",
}


def api(**params):
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def operator_titles():
    titles, cont = [], {}
    while True:
        params = dict(action="query", list="categorymembers",
                      cmtitle="Category:Operators", cmlimit=500, cmnamespace=0)
        params.update(cont)
        data = api(**params)
        titles += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        if "continue" in data:
            cont = data["continue"]
        else:
            return titles


def parse_operator(title):
    try:
        data = api(action="parse", page=title, prop="wikitext", redirects=1)
    except Exception:
        return None
    wt = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wt:
        return None
    cn = title
    m = re.search(r"\|\s*cnname\s*=\s*([^\n|]+)", wt)
    if m:
        cn = m.group(1).strip()
    rarity = 0
    m = re.search(r"\|\s*rarity\s*=\s*(\d)", wt)
    if m:
        rarity = int(m.group(1))
    cls = ""
    m = re.search(r"\|\s*class\s*=\s*([^\n|]+)", wt)
    if m:
        cls = m.group(1).strip()
    element = ""
    m = re.search(r"\|\s*element\s*=\s*([^\n|]+)", wt)
    if m:
        element = m.group(1).strip()
    skills = []
    for block in re.finditer(r"\{\{Combat skill\s*\n(.*?)\n\}\}", wt, re.S):
        body = block.group(1)
        nm = re.search(r"\|\s*name\s*=\s*([^\n|]+)", body)
        ic = re.search(r"\|\s*icon\s*=\s*([^\n|]+)", body)
        name = nm.group(1).strip() if nm else ""
        icon = ic.group(1).strip() if ic else ""
        icon = icon.replace("[[", "").replace("]]", "").split("|")[0].strip()
        skills.append((name, icon))
    return cn, rarity, cls, element, skills


def kind_of(icon):
    low = icon.lower()
    for key in ("skill", "combo", "ult"):
        if low.startswith(key):
            return key
    return None


def resolve_urls(filenames):
    """批量把 File:xxx 换成真实图片 URL。"""
    urls = {}
    for i in range(0, len(filenames), 40):
        chunk = filenames[i:i + 40]
        titles = "|".join("File:" + f for f in chunk)
        data = api(action="query", titles=titles, prop="imageinfo", iiprop="url")
        for page in data.get("query", {}).get("pages", {}).values():
            info = page.get("imageinfo")
            if info:
                urls[page["title"][5:]] = info[0]["url"]
        time.sleep(0.1)
    return urls


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "https://endfield.wiki.gg/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        blob = r.read()
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)
    return len(blob)


def safe_name(text):
    bad = '\\/:*?"<>|'
    return "".join("_" if ch in bad else ch for ch in text).strip() or "unknown"


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[1/4] 读取干员列表…")
    titles = operator_titles()
    print("      干员数:", len(titles))

    print("[2/4] 解析技能图标引用…")
    entries = []
    for idx, title in enumerate(titles, 1):
        parsed = parse_operator(title)
        if not parsed:
            continue
        cn, rarity, cls, element, skills = parsed
        for skill_name, icon in skills:
            kind = kind_of(icon)
            if not kind:
                continue
            entries.append({
                "en": title,
                "cn": cn,
                "rarity": rarity,
                "class": cls,
                "element": element,
                "kind": kind,
                "kind_cn": KINDS[kind],
                "skill": skill_name,
                "icon": icon + ".png",
            })
        if idx % 10 == 0:
            print(f"      {idx}/{len(titles)}")
        time.sleep(0.05)
    print("      图标条目:", len(entries))

    print("[3/4] 解析图片地址…")
    files = sorted({e["icon"] for e in entries})
    urls = resolve_urls(files)
    print("      可下载:", len(urls), "/", len(files))

    print("[4/4] 下载图片…")
    used = {}
    manifest = []
    ok = skip = fail = 0
    for e in entries:
        url = urls.get(e["icon"])
        if not url:
            fail += 1
            continue
        base = f"{safe_name(e['cn'])}_{e['kind_cn']}"
        n = used.get(base, 0)
        used[base] = n + 1
        filename = base + ("" if n == 0 else str(n + 1)) + ".png"
        path = os.path.join(OUT_DIR, filename)
        if not force and os.path.exists(path):
            skip += 1
        else:
            try:
                download(url, path)
                ok += 1
            except Exception:
                fail += 1
                continue
        manifest.append({
            "file": filename,
            "cn": e["cn"],
            "en": e["en"],
            "rarity": e["rarity"],
            "class": e["class"],
            "element": e["element"],
            "kind": e["kind"],
            "kind_cn": e["kind_cn"],
            "skill": e["skill"],
        })

    manifest.sort(key=lambda m: (m["cn"], m["kind"]))
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"      下载 {ok} 张，跳过 {skip} 张，失败 {fail} 张")
    print("      图标库:", OUT_DIR)
    print("      清单条目:", len(manifest))
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
