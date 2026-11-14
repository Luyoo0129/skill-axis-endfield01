# -*- coding: utf-8 -*-
"""悬浮窗方案对比图：三档字号/尺寸。

输出 preview/overlay_scale_options.png
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PIL import Image, ImageDraw  # noqa: E402

from app import fonts, theme  # noqa: E402
from app.icons import IconStore  # noqa: E402
from app.model import KIND_COMBO, KIND_SKILL, KIND_ULT, Store  # noqa: E402

OUT = os.path.join(BASE, "preview", "overlay_scale_options.png")

store = Store(BASE)
icons = IconStore(BASE)
rot = store.active_rotation()
team = rot.members()
axis = store.axis_by_id(rot.charge_axes[0]) if rot.charge_axes else None
node = axis.nodes[0] if axis and axis.nodes else None
nxt = axis.nodes[1] if axis and len(axis.nodes) > 1 else None


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw_variant(k=1.0, boost=1.0, label=""):
    """k = 整体缩放；boost = 文字额外放大系数。"""
    W = int(480 * k)
    H = int(392 * k)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def S(v):
        return int(round(v * k))

    def F(size):
        return max(8, int(round(size * k * boost)))

    def shape(box, r=12, fill=None, outline=None, width=1):
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
               anchor={"la": "la", "lm": "lm", "mm": "mm",
                       "rm": "rm", "ra": "ra", "ls": "ls"}.get(anchor, "la"))

    def paste(icon, cx, cy, size):
        if not icon:
            return
        im = icons.render_pil(icon, S(size))
        if im is not None:
            img.alpha_composite(im, (S(cx) - im.width // 2, S(cy) - im.height // 2))

    shape((1, 1, 480 - 1, 392 - 1), r=14, fill=theme.BG, outline=theme.BORDER,
          width=2)

    # 关闭
    d.ellipse([S(444), S(8), S(470), S(34)], fill=rgb(theme.PANEL_2) + (255,),
              outline=rgb(theme.BORDER) + (255,), width=S(1))
    text(457, 21, "✕", theme.F_SMALL, theme.TEXT_DIM, anchor="mm", bold=True)

    text(16, 14, rot.name, theme.F_BODY, theme.TEXT, bold=True, max_w=330)
    text(436, 14, "第 1 轮", theme.F_TINY, theme.TEXT_MUTED, anchor="rm")

    # 徽章
    badge = "充能轴 1/2"
    bw = fonts.pil_text_width(badge, F(theme.F_TINY), True) / max(k, 0.01) + 22
    shape((16, 34, 16 + bw, 58), r=6, fill=theme.PANEL_2, outline=theme.CHARGE,
          width=2)
    text(16 + bw / 2, 46, badge, theme.F_TINY, theme.CHARGE, anchor="mm", bold=True)
    text(480 - 16, 46, axis.name if axis else "", theme.F_TINY, theme.TEXT_MUTED,
         anchor="rm", max_w=250)
    d.line([S(16), S(66), S(480 - 16), S(66)], fill=rgb(theme.BORDER) + (255,),
           width=S(1))

    # 卡片
    shape((12, 76, 480 - 12, 214), r=12, fill=theme.PANEL_2,
          outline=icons.accent_for(cn=node.operator) if node else theme.BORDER,
          width=2)
    if node:
        paste(node.icon, 56, 145, 76)
        text(108, 96, node.operator, theme.F_SMALL, theme.TEXT_DIM)
        text(108, 118, node.label, 20, theme.TEXT, bold=True)
        text(108, 152, "键盘 1 · 手柄 X", theme.F_SMALL, theme.ACCENT, bold=True)
    text(480 - 24, 90, "01 / 02", theme.F_TINY, theme.TEXT_MUTED, anchor="rm")

    # 下一个
    text(16, 228, "下一个", theme.F_TINY, theme.TEXT_MUTED, anchor="lm")
    if nxt:
        paste(nxt.icon, 90, 233, 32)
        text(114, 233, "%s · %s" % (nxt.operator, nxt.label), theme.F_SMALL,
             theme.TEXT_DIM, anchor="lm", max_w=330)

    # 队列
    if axis:
        x = 16
        for i, n in enumerate(axis.nodes[:8]):
            paste(n.icon, x + 17, 279, 34)
            if i == 0:
                d.ellipse([S(x - 2), S(262 - 2), S(x + 36), S(262 + 36)],
                          outline=rgb(theme.ACCENT) + (255,), width=S(2))
            x += 41

    # 透明度行
    ty = 340
    text(16, ty, "透明度", theme.F_TINY, theme.TEXT_MUTED, anchor="lm")
    d.line([S(92), S(ty), S(250), S(ty)], fill=rgb(theme.BORDER) + (255,),
           width=S(4))
    pos = 92 + 158 * (0.95 - 0.25) / 0.75
    d.line([S(92), S(ty), S(pos), S(ty)], fill=rgb(theme.ACCENT) + (255,),
           width=S(4))
    d.ellipse([S(pos - 7), S(ty - 7), S(pos + 7), S(ty + 7)],
              fill=rgb(theme.ACCENT) + (255,))
    text(266, ty, "95%", theme.F_TINY, theme.ACCENT, anchor="lm", bold=True)

    text(16, 376, "进行中", theme.F_SMALL, theme.ACCENT, anchor="lm", bold=True)
    text(464, 376, "F7 开始  F8 重置  F9 隐藏  F10 穿透", theme.F_TINY,
         theme.TEXT_MUTED, anchor="rm")

    # 右下角缩放手柄
    for i in range(3):
        d.line([S(468 - i * 6), S(384), S(468), S(384 - i * 6)],
               fill=rgb(theme.TEXT_MUTED) + (190,), width=S(1))
    return img, (W, H)


def main():
    variants = [
        (1.00, 1.00, "A 现在（480×392）"),
        (1.15, 1.20, "B 放大一档（552×451，字更大）"),
        (1.30, 1.45, "C 放大两档（624×510，字最大）"),
    ]
    imgs = [(draw_variant(k, b)[0], title) for k, b, title in variants]

    pad = 26
    cap_h = 46
    total_w = sum(im.size[0] for im, _ in imgs) + pad * (len(imgs) + 1)
    total_h = max(im.size[1] for im, _ in imgs) + cap_h + pad * 2

    canvas = Image.new("RGB", (total_w, total_h), rgb(theme.BG))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 14), "悬浮窗尺寸/字号 方案对比（拖动右下角手柄可自由缩放）",
           font=fonts.pil_font(15, True), fill=rgb(theme.TEXT) + (255,))

    x = pad
    for im, title in imgs:
        canvas.paste(im, (x, 54), im)
        d.text((x, 54 + im.size[1] + 10), title,
               font=fonts.pil_font(11, True), fill=rgb(theme.ACCENT) + (255,))
        x += im.size[0] + pad

    canvas.save(OUT)
    print("saved", OUT, canvas.size)


if __name__ == "__main__":
    main()
