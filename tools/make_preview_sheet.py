# -*- coding: utf-8 -*-
"""生成图标样式样张，供确认。

输出 preview/sample_icons.png
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from app.iconart import compose  # noqa: E402

ICON_DIR = os.path.join(BASE, "data", "icons")
OUT = os.path.join(BASE, "preview", "sample_icons.png")

BG = (13, 17, 23)
ROW_BG = (22, 27, 34)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)
ACCENT = (240, 180, 41)

KIND_LABEL = {"skill": "技能", "combo": "连携", "ult": "终结技"}
KIND_ORDER = ("skill", "combo", "ult")


def font(size):
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf"):
        p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def load_manifest():
    with open(os.path.join(ICON_DIR, "index.json"), encoding="utf-8") as f:
        return json.load(f)


ELEMENT_ORDER = ("Physical", "Electric", "Cryo", "Heat", "Nature")
ELEMENT_CN = {
    "Physical": "物理",
    "Electric": "电磁",
    "Cryo": "寒冷",
    "Heat": "灼热",
    "Nature": "自然",
}


def pick_operators(entries):
    """每种元素挑一个干员，要求技能/连携/终结三张齐全。"""
    by_op = {}
    for e in entries:
        by_op.setdefault(e["cn"], {})[e["kind"]] = e
    by_elem = {}
    for cn, kinds in by_op.items():
        if not all(k in kinds for k in KIND_ORDER):
            continue
        el = kinds["skill"].get("element", "")
        if el and el not in by_elem:
            by_elem[el] = (cn, kinds)
    ordered = [(el, by_elem[el]) for el in ELEMENT_ORDER if el in by_elem]
    for el, v in by_elem.items():
        if el not in ELEMENT_ORDER:
            ordered.append((el, v))
    return ordered


def main():
    from app.iconart import ELEMENT_RGB, SECTOR_DIM

    entries = load_manifest()
    ops = pick_operators(entries)

    big = 96
    smalls = (48, 32, 24)
    pad = 28
    label_w = 200
    cell_w = big + 34
    width = pad * 2 + label_w + cell_w * len(KIND_ORDER) + 190
    row_h = big + 56
    height = pad * 2 + 96 + row_h * len(ops)

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)

    f_title = font(24)
    f_sub = font(14)
    f_row = font(17)
    f_small = font(12)

    d.text((pad, pad), "技能图标样式样张", fill=TEXT, font=f_title)
    d.text((pad, pad + 34),
           "正圆 · 透明圆外 · 暗色底 · 底部 120° 扇形=元素色 · 白色符号在上层",
           fill=MUTED, font=f_sub)
    d.text((pad, pad + 56),
           "终结技：整个圆为纯元素色。连携技：与技能完全同款。",
           fill=MUTED, font=f_sub)

    y = pad + 96
    # 表头
    for i, kind in enumerate(KIND_ORDER):
        x = pad + label_w + i * cell_w + cell_w // 2
        d.text((x, y), KIND_LABEL[kind], fill=ACCENT, font=f_row, anchor="mb")
    xs = pad + label_w + len(KIND_ORDER) * cell_w + 10
    d.text((xs, y), "小尺寸", fill=ACCENT, font=f_row, anchor="mb")

    y += 20
    for elem, (cn, kinds) in ops:
        d.rectangle([pad - 8, y - 8, width - pad + 8, y + row_h - 20], fill=ROW_BG)

        d.text((pad, y + 16), cn, fill=TEXT, font=f_row)
        rgb = ELEMENT_RGB.get(elem, (150, 150, 150))
        d.text((pad, y + 44),
               "%s %s · %s★" % (ELEMENT_CN.get(elem, elem), elem, kinds["skill"].get("rarity")),
               fill=MUTED, font=f_small)
        d.rectangle([pad, y + 66, pad + 18, y + 80], fill=rgb)
        d.text((pad + 24, y + 66), "#%02x%02x%02x" % rgb, fill=MUTED, font=f_small)

        for i, kind in enumerate(KIND_ORDER):
            entry = kinds[kind]
            glyph = os.path.join(ICON_DIR, entry["file"])
            icon = compose(glyph, big, elem, kind)
            x = pad + label_w + i * cell_w
            img.paste(icon, (x, y), icon)

        # 小尺寸行
        glyph = os.path.join(ICON_DIR, kinds["skill"]["file"])
        sx = xs
        for s in smalls:
            icon = compose(glyph, s, elem, "skill")
            img.paste(icon, (sx, y + (big - s) // 2), icon)
            sx += s + 14

        y += row_h

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("saved", OUT, img.size)
    print("  压暗系数 SECTOR_DIM =", SECTOR_DIM)
    for elem, (cn, kinds) in ops:
        print("  干员:", cn, "/ 元素:", elem, "/ 稀有度:", kinds["skill"].get("rarity"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
