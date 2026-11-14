# -*- coding: utf-8 -*-
"""生成连携图标样张。

输出 preview/sample_combo.png
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from app.iconart import ELEMENT_CN, compose_combo  # noqa: E402

ICON_DIR = os.path.join(BASE, "data", "icons")
PORTRAIT_DIR = os.path.join(BASE, "data", "portraits")
OUT = os.path.join(BASE, "preview", "sample_combo.png")

BG = (13, 17, 23)
ROW_BG = (22, 27, 34)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)

SIZES = (96, 64, 40)


def font(size):
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf"):
        p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def main():
    with open(os.path.join(ICON_DIR, "index.json"), encoding="utf-8") as f:
        entries = json.load(f)

    by_op = {}
    for e in entries:
        by_op.setdefault(e["cn"], {})[e["kind"]] = e

    picks = []
    for cn, kinds in by_op.items():
        if "combo" not in kinds:
            continue
        portrait = os.path.join(PORTRAIT_DIR, cn + ".png")
        if not os.path.isfile(portrait):
            continue
        picks.append((cn, kinds["combo"], portrait))
        if len(picks) >= 6:
            break

    pad = 28
    label_w = 150
    cell_w = 130
    row_h = 124
    width = pad * 2 + label_w + cell_w * len(picks)
    height = pad * 2 + 92 + row_h

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    f_title = font(23)
    f_sub = font(13)
    f_row = font(15)
    f_small = font(12)

    d.text((pad, pad), "连携技图标 · 立绘 + 右下角小图标", fill=TEXT, font=f_title)
    d.text((pad, pad + 34),
           "大盘：干员立绘填满圆 · 白色外环　｜　右下角：连携技能小图标（约 36%）",
           fill=MUTED, font=f_sub)

    y = pad + 92
    d.rectangle([pad - 8, y - 10, width - pad + 8, y + row_h - 6], fill=ROW_BG)

    for i, (cn, entry, portrait) in enumerate(picks):
        elem = entry.get("element", "")
        x = pad + label_w + i * cell_w
        icon = compose_combo(portrait, os.path.join(ICON_DIR, entry["file"]),
                             96, elem)
        img.paste(icon, (x, y), icon)
        d.text((x + 48, y + 100), cn, fill=TEXT, font=f_row, anchor="mt")
        d.text((x + 48, y + 118), ELEMENT_CN.get(elem, elem), fill=MUTED,
               font=f_small, anchor="mt")

    # 小尺寸预览
    y2 = y + row_h
    d.text((pad, y2 + 6), "小尺寸", fill=MUTED, font=f_small)
    sx = pad + label_w
    for s in (48, 36, 28, 22):
        cn, entry, portrait = picks[1]
        icon = compose_combo(portrait, os.path.join(ICON_DIR, entry["file"]),
                             s, entry.get("element", ""))
        img.paste(icon, (sx, y2 + 22), icon)
        sx += s + 16

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("saved", OUT, img.size)
    for cn, entry, _ in picks:
        print("  ", cn, entry.get("element"), entry["file"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
