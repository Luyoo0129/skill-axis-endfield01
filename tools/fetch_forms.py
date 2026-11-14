# -*- coding: utf-8 -*-
"""把多段技能的第二段图标抓下来，并补进 data/icons/index.json。

规则：第 1 段沿用已有文件（干员_种类.png），第 2 段存成 干员_种类2.png。
目前只有「诀」在 wiki 上有第二套图标（Skill/Combo/Ult-Arcane2）。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://endfield.wiki.gg/api.php"
UA = "skill-axis/1.0 (local tool)"

# 干员 -> {kind: [第2段 wiki 图标名]}
SECOND = {
    "诀": {"skill": "Skill-Arcane2", "combo": "Combo-Arcane2", "ult": "Ult-Arcane2"},
}
KIND_CN = {"skill": "技能", "combo": "连携", "ult": "终结"}


def api(**params):
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def file_url(name):
    d = api(action="query", titles="File:" + name, prop="imageinfo", iiprop="url")
    for page in d.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo")
        if info:
            return info[0]["url"]
    return None


def download(url, path):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": "https://endfield.wiki.gg/"})
    with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    root = os.path.join(BASE, "data", "icons")
    idx_path = os.path.join(root, "index.json")
    with open(idx_path, encoding="utf-8") as f:
        manifest = json.load(f)

    by_key = {}
    for e in manifest:
        by_key[(e.get("cn"), e.get("kind"))] = e

    added = 0
    for cn, per in SECOND.items():
        for kind, icon_name in per.items():
            base = by_key.get((cn, kind))
            if not base:
                print("跳过（没有第 1 段条目）:", cn, kind)
                continue
            rel = "%s_%s2.png" % (cn, KIND_CN[kind])
            path = os.path.join(root, rel)
            if not os.path.isfile(path):
                url = file_url(icon_name + ".png")
                if not url:
                    print("找不到图:", icon_name)
                    continue
                download(url, path)
                time.sleep(0.2)
                print("下载:", rel, "<-", icon_name)

            # 补 index 条目（stage=2），保留原条目的属性
            entry = dict(base)
            entry["file"] = rel
            entry["stage"] = 2
            entry["icon"] = icon_name
            if not any(x.get("cn") == cn and x.get("kind") == kind
                       and x.get("file") == rel for x in manifest):
                manifest.append(entry)
                added += 1

    # 去重：同一 (干员, 种类, 文件) 只留一条（以前重复跑会追加出重复段）
    deduped = []
    seen_files = set()
    for e in manifest:
        key = (e.get("cn", ""), e.get("kind", ""), e.get("file", ""))
        if key in seen_files:
            continue
        seen_files.add(key)
        deduped.append(e)
    manifest = deduped

    # 同一 (干员, 种类) 的多张图标按出现顺序重新编号 1..N（幂等）
    counts = {}
    for e in manifest:
        key = (e.get("cn", ""), e.get("kind", ""))
        counts[key] = counts.get(key, 0) + 1
        e["stage"] = counts[key]
    manifest.sort(key=lambda m: (m.get("cn", ""), m.get("kind", ""),
                                 int(m.get("stage", 1))))

    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("index 条目:", len(manifest), " 新增:", added)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
