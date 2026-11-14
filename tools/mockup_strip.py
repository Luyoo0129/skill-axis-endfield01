# -*- coding: utf-8 -*-
"""长条型悬浮窗（流水线）预览：多槽位、图标等大、高亮不压字。

输出 preview/overlay_strip_options.png
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

OUT = os.path.join(BASE, "preview", "overlay_strip_options.png")
icons = IconStore(BASE)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(c1, c2, t):
    a, b = rgb(c1), rgb(c2)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


with open(os.path.join(BASE, "data", "icons", "index.json"), encoding="utf-8") as f:
    manifest = json.load(f)
by_op = {}
for e in manifest:
    by_op.setdefault(e["cn"], {})[e["kind"]] = e

# 造一条 20 个技能的序列
plan = [("佩丽卡", "skill"), ("管理员", "combo"), ("陈千语", "skill"),
        ("余烬", "ult"), ("佩丽卡", "ult"), ("管理员", "skill"),
        ("伊冯", "skill"), ("陈千语", "combo"), ("余烬", "skill"),
        ("佩丽卡", "skill"), ("伊冯", "combo"), ("管理员", "ult"),
        ("陈千语", "ult"), ("佩丽卡", "skill"), ("余烬", "combo"),
        ("伊冯", "ult"), ("管理员", "combo"), ("陈千语", "skill"),
        ("佩丽卡", "ult"), ("余烬", "skill")]
KIND_CN = {"skill": "技能", "combo": "连携", "ult": "终结"}
KIND_KEY = {"skill": None, "combo": "E", "ult": None}   # 数字按队伍位算

TEAM = ["佩丽卡", "管理员", "陈千语", "余烬"]

SEQUENCE = []
for op, kind in plan:
    e = by_op.get(op, {}).get(kind)
    if not e:
        continue
    if kind == "combo":
        key = "E"
    else:
        slot = TEAM.index(op) + 1 if op in TEAM else 0
        key = ("长按%d" % slot) if kind == "ult" else str(slot)
    SEQUENCE.append({"op": op, "icon": e["file"], "key": key,
                     "element": e.get("element", ""), "label": KIND_CN[kind]})
INDEX = 4


def render(W, H, icon_size, gap, slots, boost=1.0, index=INDEX):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = 1.0

    def S(v):
        return int(round(v))

    def F(size):
        return max(8, int(round(size * boost)))

    def shape(box, r=10, fill=None, outline=None, width=1):
        d.rounded_rectangle([S(box[0]), S(box[1]), S(box[2]), S(box[3])],
                            radius=S(r),
                            fill=rgb(fill) + (255,) if fill else None,
                            outline=rgb(outline) + (255,) if outline else None,
                            width=max(1, S(width)))

    def text(x, y, s, size, color, anchor="la", bold=False, max_w=None):
        if not s:
            return
        if max_w is not None:
            s = fonts.pil_fit(s, F(size), S(max_w), bold)
            if not s:
                return
        d.text((S(x), S(y)), s, font=fonts.pil_font(F(size), bold),
               fill=rgb(color) + (255,),
               anchor={"la": "la", "lm": "lm", "mm": "mm", "rm": "rm",
                       "ra": "ra"}.get(anchor, "la"))

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

    # 外框
    shape((1, 1, W - 1, H - 1), r=12, fill=theme.BG, outline=theme.BORDER,
          width=2)

    # 顶栏
    text(14, 15, "示例编队", theme.F_BODY, theme.TEXT, anchor="lm", bold=True,
         max_w=170)
    badge = "充能轴 1/2"
    bw = fonts.pil_text_width(badge, F(theme.F_TINY), True) + 18
    bx = 14 + fonts.pil_text_width("示例编队", F(theme.F_BODY), True) + 14
    shape((bx, 6, bx + bw, 26), r=5, fill=theme.PANEL_2, outline=theme.CHARGE,
          width=1)
    text(bx + bw / 2, 16, badge, theme.F_TINY, theme.CHARGE, anchor="mm",
         bold=True)

    # 右侧：进度 + 透明度 + 关闭
    close_cx = W - 22
    d.ellipse([S(close_cx - 11), S(5), S(close_cx + 11), S(27)],
              fill=rgb(theme.PANEL_2) + (255,),
              outline=rgb(theme.BORDER) + (255,), width=S(1))
    text(close_cx, 16, "✕", theme.F_TINY, theme.TEXT_DIM, anchor="mm", bold=True)

    pct_x2 = close_cx - 44
    pct_x1 = pct_x2 - 66
    text(pct_x1 - 40, 16, "透明度", theme.F_TINY, theme.TEXT_MUTED, anchor="rm")
    d.line([S(pct_x1), S(16), S(pct_x2), S(16)], fill=rgb(theme.BORDER) + (255,),
           width=S(3))
    pos = pct_x1 + (pct_x2 - pct_x1) * 0.93
    d.line([S(pct_x1), S(16), S(pos), S(16)], fill=rgb(theme.ACCENT) + (255,),
           width=S(3))
    d.ellipse([S(pos - 5), S(11), S(pos + 5), S(21)],
              fill=rgb(theme.ACCENT) + (255,))
    text(pct_x2 + 6, 16, "93%", theme.F_TINY, theme.ACCENT, anchor="lm",
         bold=True)

    text(pct_x1 - 96, 16, "%d / %d" % (index + 1, len(SEQUENCE)),
         theme.F_TINY, theme.TEXT_MUTED, anchor="rm")

    # 分隔线
    d.line([S(12), S(32), S(W - 12), S(32)], fill=rgb(theme.BORDER) + (255,),
           width=S(1))

    # 流水线：所有图标同样大小
    start = max(0, min(index - slots // 2, len(SEQUENCE) - slots))
    shown = SEQUENCE[start:start + slots]
    icon_cy = 34 + icon_size / 2 + 6
    key_y = icon_cy + icon_size / 2 + 14
    x = 14
    for i, s in enumerate(shown):
        idx = start + i
        cur = idx == index
        past = idx < index
        cx = x + icon_size / 2

        if cur:
            # 高亮框只包住图标，不压下面的键位文字
            shape((cx - icon_size / 2 - 5, icon_cy - icon_size / 2 - 5,
                   cx + icon_size / 2 + 5, icon_cy + icon_size / 2 + 5),
                  r=9, fill=None, outline=theme.ACCENT, width=2)

        icon(s["icon"], cx, icon_cy, icon_size, alpha=255 if not past else 90)

        if past:
            bx2, by2 = cx + icon_size / 2 - 3, icon_cy - icon_size / 2 - 1
            d.ellipse([S(bx2 - 8), S(by2 - 8), S(bx2 + 8), S(by2 + 8)],
                      fill=rgb(theme.BG) + (255,),
                      outline=rgb(theme.GREEN) + (255,), width=S(1))
            text(bx2, by2, "✓", theme.F_TINY, theme.GREEN, anchor="mm", bold=True)

        col = theme.ACCENT if cur else (theme.TEXT_MUTED if past else theme.TEXT_DIM)
        text(cx, key_y, s["key"], theme.F_TINY, col, anchor="mm", bold=cur)

        x += icon_size + gap

    # 若还有更多，右端提示
    rest = len(SEQUENCE) - (start + slots)
    if rest > 0 and x < W - 30:
        text(W - 16, icon_cy, "→", theme.F_BODY, theme.TEXT_MUTED, anchor="rm")

    return img


def main():
    variants = [
        (1120, 136, 44, 6, 20, 1.0, "A 长条 1120×136（20 个同屏）"),
        (1280, 152, 54, 6, 21, 1.15, "B 稍大 1280×152（21 个同屏）"),
    ]
    imgs = [(render(*v[:6]), v[6]) for v in variants]

    pad = 24
    top = 46
    zoom_h = 190
    total_w = max(i.size[0] for i, _ in imgs) + pad * 2
    total_h = top + sum(i.size[1] for i, _ in imgs) + pad * len(imgs) + 30 + zoom_h
    canvas = Image.new("RGB", (total_w, total_h), rgb(theme.BG))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 12), "长条型悬浮窗：图标统一大小 · 当前用描边框标识 · 不压文字",
           font=fonts.pil_font(14, True), fill=rgb(theme.TEXT) + (255,))

    y = top
    for im, title in imgs:
        canvas.paste(im, (pad, y), im)
        d.text((pad, y + im.size[1] + 6), title,
               font=fonts.pil_font(11, True), fill=rgb(theme.ACCENT) + (255,))
        y += im.size[1] + 26

    # 当前槽特写（3×）
    big = render(1120, 132, 48, 6, 17, 1.0)
    crop = big.crop((14 + 3 * 54 - 16, 24, 14 + 6 * 54 + 20, 132))
    crop = crop.resize((crop.size[0] * 3, crop.size[1] * 3), Image.LANCZOS)
    d.text((pad, y), "当前槽特写 3×：描边框只包图标，键位文字在框外",
           font=fonts.pil_font(12, True), fill=rgb(theme.TEXT) + (255,))
    canvas.paste(crop, (pad, y + 22), crop)

    canvas.save(OUT)
    print("saved", OUT, canvas.size)


if __name__ == "__main__":
    main()
