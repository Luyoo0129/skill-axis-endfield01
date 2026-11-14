# -*- coding: utf-8 -*-
"""方案 B（横向流水线）排版修订版。

输出 preview/overlay_b_refined.png
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PIL import Image, ImageDraw  # noqa: E402

from app import fonts, theme  # noqa: E402
from app.iconart import ELEMENT_RGB  # noqa: E402
from app.icons import IconStore  # noqa: E402

OUT = os.path.join(BASE, "preview", "overlay_b_refined.png")
icons = IconStore(BASE)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


with open(os.path.join(BASE, "data", "icons", "index.json"), encoding="utf-8") as f:
    manifest = json.load(f)
by_op = {}
for e in manifest:
    by_op.setdefault(e["cn"], {})[e["kind"]] = e

SEQUENCE = []
for op, kind, key in [("佩丽卡", "skill", "1"), ("管理员", "combo", "E"),
                      ("陈千语", "skill", "3"), ("余烬", "ult", "长按4"),
                      ("佩丽卡", "ult", "长按1"), ("管理员", "skill", "2")]:
    e = by_op.get(op, {}).get(kind)
    if e:
        SEQUENCE.append({"op": op, "icon": e["file"], "key": key,
                         "element": e.get("element", ""),
                         "label": {"skill": "技能", "combo": "连携",
                                   "ult": "终结"}[kind]})
INDEX = 2


def render(k=1.15, boost=1.2):
    W, H = int(480 * k), int(392 * k)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def S(v):
        return int(round(v * k))

    def F(size):
        return max(8, int(round(size * k * boost)))

    def shape(box, r=12, fill=None, outline=None, width=1, alpha=255):
        d.rounded_rectangle([S(box[0]), S(box[1]), S(box[2]), S(box[3])],
                            radius=S(r),
                            fill=(rgb(fill) + (int(alpha),)) if fill else None,
                            outline=(rgb(outline) + (int(alpha),)) if outline else None,
                            width=max(1, S(width)))

    def text(x, y, s, size, color, anchor="la", bold=False, max_w=None,
             alpha=255):
        if not s:
            return 0
        if max_w is not None:
            s = fonts.pil_fit(s, F(size), S(max_w), bold)
            if not s:
                return 0
        d.text((S(x), S(y)), s, font=fonts.pil_font(F(size), bold),
               fill=(rgb(color) + (int(alpha),)),
               anchor={"la": "la", "lm": "lm", "mm": "mm", "rm": "rm",
                       "ra": "ra"}.get(anchor, "la"))
        return fonts.pil_text_width(s, F(size), bold) / k

    def icon(name, cx, cy, size, alpha=255):
        im = icons.render_pil(name, S(size))
        if im is None:
            return
        if alpha < 255:
            im = im.copy()
            r, g, b, a = im.split()
            a = a.point(lambda v: int(v * alpha / 255))
            im = Image.merge("RGBA", (r, g, b, a))
        img.alpha_composite(im, (S(cx) - im.width // 2, S(cy) - im.height // 2))

    # ---------- 外框 + 顶栏 ----------
    shape((1, 1, 480 - 1, 392 - 1), r=14, fill=theme.BG, outline=theme.BORDER,
          width=2)
    d.ellipse([S(444), S(8), S(470), S(34)], fill=rgb(theme.PANEL_2) + (255,),
              outline=rgb(theme.BORDER) + (255,), width=S(1))
    text(457, 21, "✕", theme.F_SMALL, theme.TEXT_DIM, anchor="mm", bold=True)
    text(16, 14, "示例编队", theme.F_BODY, theme.TEXT, bold=True, max_w=300)
    text(436, 14, "第 1 轮", theme.F_TINY, theme.TEXT_MUTED, anchor="rm")

    badge = "充能轴 1/2"
    bw = fonts.pil_text_width(badge, F(theme.F_TINY), True) / k + 22
    shape((16, 34, 16 + bw, 58), r=6, fill=theme.PANEL_2, outline=theme.CHARGE,
          width=2)
    text(16 + bw / 2, 46, badge, theme.F_TINY, theme.CHARGE, anchor="mm",
         bold=True)
    text(480 - 16, 46, "充能 · 第一轮", theme.F_TINY, theme.TEXT_MUTED,
         anchor="rm", max_w=220)
    d.line([S(16), S(66), S(480 - 16), S(66)], fill=rgb(theme.BORDER) + (255,),
           width=S(1))

    # ---------- 流水线：固定槽宽，等距排列 ----------
    SLOTS = 5
    GAP = 8
    SW = (480 - 28 - GAP * (SLOTS - 1)) / SLOTS       # 单槽宽
    start = max(0, min(INDEX - 2, len(SEQUENCE) - SLOTS))
    shown = SEQUENCE[start:start + SLOTS]

    y_box = 80
    box_h = 118
    for i, s in enumerate(shown):
        idx = start + i
        cx = 14 + i * (SW + GAP) + SW / 2
        cur = idx == INDEX
        past = idx < INDEX

        if cur:
            shape((14 + i * (SW + GAP), y_box,
                   14 + i * (SW + GAP) + SW, y_box + box_h),
                  r=10, fill=theme.PANEL_2, outline=theme.ACCENT, width=2)
        elif not past:
            shape((14 + i * (SW + GAP), y_box,
                   14 + i * (SW + GAP) + SW, y_box + box_h),
                  r=10, fill=theme.PANEL, outline=theme.BORDER, width=1)

        size = 62 if cur else 44
        cy = 130 if cur else 126
        icon(s["icon"], cx, cy, size, alpha=255 if not past else 95)

        if past:
            # 勾画在图标右上角，不压图案
            bx, by = cx + size / 2 - 4, cy - size / 2 - 2
            d.ellipse([S(bx - 9), S(by - 9), S(bx + 9), S(by + 9)],
                      fill=rgb(theme.PANEL) + (255,),
                      outline=rgb(theme.GREEN) + (255,), width=S(1))
            text(bx, by, "✓", theme.F_TINY, theme.GREEN, anchor="mm", bold=True)

        # 键位（统一基线，居中）+ 干员名（统一基线，居中，限制宽度）
        key_col = theme.ACCENT if cur else (theme.TEXT_MUTED if past else theme.TEXT)
        text(cx, 178, s["key"], theme.F_SMALL, key_col, anchor="mm", bold=True,
             alpha=255 if not past else 150)
        text(cx, 194, s["op"], theme.F_TINY, theme.TEXT_DIM, anchor="mm",
             max_w=SW - 6, alpha=255 if not past else 150)

    # ---------- 现在按 ----------
    d.line([S(16), S(210), S(480 - 16), S(210)], fill=rgb(theme.BORDER) + (255,),
           width=S(1))

    cur = SEQUENCE[INDEX]
    accent = "#%02x%02x%02x" % ELEMENT_RGB.get(cur["element"], (150, 150, 150))

    text(16, 230, "现在按", theme.F_TINY, theme.TEXT_MUTED)
    shape((16, 244, 104, 292), r=10, fill=theme.PANEL_2, outline=accent, width=2)
    text(60, 268, cur["key"], 24, theme.ACCENT, anchor="mm", bold=True)

    text(116, 250, "%s · %s" % (cur["op"], cur["label"]), theme.F_BODY,
         theme.TEXT, bold=True, max_w=300)
    text(116, 274, "这一按对应 %s 的%s" % (cur["op"], cur["label"]),
         theme.F_TINY, theme.TEXT_MUTED, max_w=300)

    # ---------- 后面依次：改用 chip，避免长文本被截 ----------
    text(16, 316, "后面", theme.F_TINY, theme.TEXT_MUTED, anchor="lm")
    x = 52
    tail = SEQUENCE[INDEX + 1:]
    for j, s in enumerate(tail[:3]):
        label = "%s %s" % (s["op"], s["key"])
        w = fonts.pil_text_width(label, F(theme.F_TINY), False) / k + 18
        shape((x, 304, x + w, 328), r=7, fill=theme.PANEL_2,
              outline=theme.BORDER)
        text(x + w / 2, 316, label, theme.F_TINY, theme.TEXT_DIM, anchor="mm")
        x += w + 6
    if len(tail) > 3:
        w = fonts.pil_text_width("+%d" % (len(tail) - 3), F(theme.F_TINY)) / k + 16
        shape((x, 304, x + w, 328), r=7, fill=theme.PANEL, outline=theme.BORDER)
        text(x + w / 2, 316, "+%d" % (len(tail) - 3), theme.F_TINY,
             theme.TEXT_MUTED, anchor="mm")

    # ---------- 底部 ----------
    ty = 340
    text(16, ty, "透明度", theme.F_TINY, theme.TEXT_MUTED, anchor="lm")
    d.line([S(92), S(ty), S(250), S(ty)], fill=rgb(theme.BORDER) + (255,),
           width=S(4))
    pos = 92 + 158 * 0.93
    d.line([S(92), S(ty), S(pos), S(ty)], fill=rgb(theme.ACCENT) + (255,),
           width=S(4))
    d.ellipse([S(pos - 7), S(ty - 7), S(pos + 7), S(ty + 7)],
              fill=rgb(theme.ACCENT) + (255,))
    text(266, ty, "95%", theme.F_TINY, theme.ACCENT, anchor="lm", bold=True)

    text(16, 376, "进行中", theme.F_SMALL, theme.ACCENT, anchor="lm", bold=True)
    text(480 - 16, 376, "F7 开始  F8 重置  F9 隐藏  F10", theme.F_TINY,
         theme.TEXT_MUTED, anchor="rm", max_w=280)
    return img


def main():
    shots = [(1.15, 1.20, "默认 552×451"),
             (1.00, 1.00, "最小 480×392")]
    imgs = [(render(a, b), t) for a, b, t in shots]

    pad = 24
    top = 48
    total_w = sum(i.size[0] for i, _ in imgs) + pad * (len(imgs) + 1)
    total_h = top + max(i.size[1] for i, _ in imgs) + 40
    canvas = Image.new("RGB", (total_w, total_h), rgb(theme.BG))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 12), "方案 B（横向流水线）排版修订：固定槽宽 + 统一基线 + chip 代替长文本",
           font=fonts.pil_font(14, True), fill=rgb(theme.TEXT) + (255,))

    x = pad
    for im, title in imgs:
        canvas.paste(im, (x, top), im)
        d.text((x, top + im.size[1] + 8), title,
               font=fonts.pil_font(11, True), fill=rgb(theme.ACCENT) + (255,))
        x += im.size[0] + pad

    canvas.save(OUT)
    print("saved", OUT, canvas.size)


if __name__ == "__main__":
    main()
