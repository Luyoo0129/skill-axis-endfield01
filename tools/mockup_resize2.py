# -*- coding: utf-8 -*-
"""悬浮窗改版预览（无手柄版）：拖边框/四角缩放。

输出 preview/overlay_resize_clean.png
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PIL import Image, ImageDraw  # noqa: E402

from app import fonts, theme  # noqa: E402
from app.icons import IconStore  # noqa: E402
from app.model import Store  # noqa: E402

OUT = os.path.join(BASE, "preview", "overlay_resize_clean.png")

store = Store(BASE)
icons = IconStore(BASE)
rot = store.active_rotation()
axis = store.axis_by_id(rot.charge_axes[0]) if rot.charge_axes else None
node = axis.nodes[0] if axis and axis.nodes else None
nxt = axis.nodes[1] if axis and len(axis.nodes) > 1 else None


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw(k=1.0, boost=1.0):
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
               anchor={"la": "la", "lm": "lm", "mm": "mm", "rm": "rm",
                       "ra": "ra"}.get(anchor, "la"))

    def paste(icon, cx, cy, size):
        if not icon:
            return
        im = icons.render_pil(icon, S(size))
        if im is not None:
            img.alpha_composite(im, (S(cx) - im.width // 2, S(cy) - im.height // 2))

    shape((1, 1, 480 - 1, 392 - 1), r=14, fill=theme.BG, outline=theme.BORDER,
          width=2)

    d.ellipse([S(444), S(8), S(470), S(34)], fill=rgb(theme.PANEL_2) + (255,),
              outline=rgb(theme.BORDER) + (255,), width=S(1))
    text(457, 21, "✕", theme.F_SMALL, theme.TEXT_DIM, anchor="mm", bold=True)

    text(16, 14, rot.name, theme.F_BODY, theme.TEXT, bold=True, max_w=320)
    text(436, 14, "第 1 轮", theme.F_TINY, theme.TEXT_MUTED, anchor="rm")

    badge = "充能轴 1/2"
    bw = fonts.pil_text_width(badge, F(theme.F_TINY), True) / max(k, 0.01) + 22
    shape((16, 34, 16 + bw, 58), r=6, fill=theme.PANEL_2,
          outline=theme.CHARGE, width=2)
    text(16 + bw / 2, 46, badge, theme.F_TINY, theme.CHARGE, anchor="mm",
         bold=True)
    text(480 - 16, 46, axis.name if axis else "", theme.F_TINY,
         theme.TEXT_MUTED, anchor="rm", max_w=250)
    d.line([S(16), S(66), S(480 - 16), S(66)], fill=rgb(theme.BORDER) + (255,),
           width=S(1))

    shape((12, 76, 480 - 12, 214), r=12, fill=theme.PANEL_2,
          outline=icons.accent_for(cn=node.operator) if node else theme.BORDER,
          width=2)
    if node:
        paste(node.icon, 56, 145, 76)
        text(108, 96, node.operator, theme.F_SMALL, theme.TEXT_DIM)
        text(108, 118, node.label, 20, theme.TEXT, bold=True)
        text(108, 152, "键盘 1 · 手柄 X", theme.F_SMALL, theme.ACCENT, bold=True)
    text(480 - 24, 90, "01 / 02", theme.F_TINY, theme.TEXT_MUTED, anchor="rm")

    text(16, 228, "下一个", theme.F_TINY, theme.TEXT_MUTED, anchor="lm")
    if nxt:
        paste(nxt.icon, 90, 233, 32)
        text(114, 233, "%s · %s" % (nxt.operator, nxt.label), theme.F_SMALL,
             theme.TEXT_DIM, anchor="lm", max_w=320)

    if axis:
        x = 16
        for i, n in enumerate(axis.nodes[:8]):
            paste(n.icon, x + 17, 279, 34)
            if i == 0:
                d.ellipse([S(x - 2), S(262 - 2), S(x + 36), S(262 + 36)],
                          outline=rgb(theme.ACCENT) + (255,), width=S(2))
            x += 41

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
    text(480 - 16, 376, "F7 开始  F8 重置  F9 隐藏  F10 穿透", theme.F_TINY,
         theme.TEXT_MUTED, anchor="rm", max_w=330)
    return img


def zone_diagram(im):
    """在截图边上画一圈可拖拽区域示意（仅是示意图，不是运行时外观）。"""
    w, h = im.size
    out = im.copy()
    d = ImageDraw.Draw(out)
    edge = 7
    col = rgb(theme.ACCENT) + (150,)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, outline=col, width=2)
    # 四边
    d.line([edge, edge, w - edge, edge], fill=col, width=2)
    d.line([edge, h - edge, w - edge, h - edge], fill=col, width=2)
    d.line([edge, edge, edge, h - edge], fill=col, width=2)
    d.line([w - edge, edge, w - edge, h - edge], fill=col, width=2)
    # 箭头
    def arrow(cx, cy, dx, dy):
        L = 12
        d.line([cx - dx * L // 2, cy - dy * L // 2,
                cx + dx * L // 2, cy + dy * L // 2], fill=col, width=3)
        d.polygon([(cx + dx * (L // 2 + 5), cy + dy * (L // 2 + 5)),
                   (cx + dx * L // 2 - dy * 5, cy + dy * L // 2 - dx * 5),
                   (cx + dx * L // 2 + dy * 5, cy + dy * L // 2 + dx * 5)],
                  fill=col)
    arrow(w // 2, edge, 1, 0)
    arrow(w // 2, h - edge, 1, 0)
    arrow(edge, h // 2, 0, 1)
    arrow(w - edge, h // 2, 0, 1)
    return out


def main():
    k, b = 1.15, 1.20
    variants = [
        (1.00, 1.00, "最小 480×392"),
        (k, b, "默认 552×451（推荐）"),
        (1.55, 1.45, "放大 744×607"),
    ]
    imgs = [(draw(a, c), t) for a, c, t in variants]

    pad = 26
    top = 54
    cap_h = 30
    total_w = sum(im.size[0] for im, _ in imgs) + pad * (len(imgs) + 1)
    total_h = top + max(im.size[1] for im, _ in imgs) + cap_h + pad

    canvas = Image.new("RGB", (total_w, total_h), rgb(theme.BG))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 14), "悬浮窗缩放预览 · 不画手柄，拖边框或四角即可缩放",
           font=fonts.pil_font(15, True), fill=rgb(theme.TEXT) + (255,))
    d.text((pad + 480, 18), "（底下那条示意图里的黄线表示可拖拽区域，实际运行时不显示）",
           font=fonts.pil_font(10), fill=rgb(theme.TEXT_MUTED) + (255,))

    x = pad
    for im, title in imgs:
        canvas.paste(im, (x, top), im)
        d.text((x, top + im.size[1] + 6), title,
               font=fonts.pil_font(11, True), fill=rgb(theme.ACCENT) + (255,))
        x += im.size[0] + pad

    # 示意图
    base = draw(k, b)
    diag = zone_diagram(base)
    dy = total_h + 6
    canvas2 = Image.new("RGB", (total_w, dy + diag.size[1] + 40), rgb(theme.BG))
    canvas2.paste(canvas, (0, 0))
    d2 = ImageDraw.Draw(canvas2)
    d2.text((pad, dy), "可拖拽区域示意（仅说明用）：四条边 + 四个角，各 7px 宽",
            font=fonts.pil_font(12, True), fill=rgb(theme.TEXT) + (255,))
    canvas2.paste(diag, (pad, dy + 22), diag)

    canvas2.save(OUT)
    print("saved", OUT, canvas2.size)


if __name__ == "__main__":
    main()
