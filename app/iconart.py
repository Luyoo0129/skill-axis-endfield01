# -*- coding: utf-8 -*-
"""按游戏内样式合成技能图标。

结构（照游戏底图实测复刻，96x96 基准）：
    · 正圆，铺满画布，圆外透明
    · 暗色圆底          #181a20
    · 底部 120° 扇形    ← 底图里是灰色占位 #6e7278，游戏运行时按元素重新着色
    · 白色外环          4px / 96px ≈ 4.2% 直径
    · 白色符号压在最上层，约占直径 66%

终结技：整个圆填元素色（没有扇形分界）。
连携技：与技能完全同款。

实测依据：
    底图 96x96，不透明包围盒铺满；0.6R 处按角度采样，
    120°~240° 为 #6e7278（正好三分之一），其余为 #181a20；
    沿半径 r=44 起是白色环，厚 4px。
"""
import math
import os

from PIL import Image, ImageDraw

# 圆内暗色底（取自游戏底图）
BASE_DARK = (24, 26, 32, 255)      # #181a20
# 白色外环
RING_WHITE = (255, 255, 255, 236)
# 白环厚度占直径的比例（底图 4px / 96px）
RING_RATIO = 4.0 / 96.0

# 扇形角度：0°=正上方、顺时针。120°~240° 正好是底部三分之一。
SECTOR_START = 120
SECTOR_END = 240

# 圆铺满画布，不留白
MARGIN = 0.0
# 白色符号占直径的比例（实测底图成品 67/96 ≈ 70%）
GLYPH_RATIO = 0.70
# 超采样倍数
SUPERSAMPLE = 4

# 元素配色，从用户提供的元素图标吸取
#   物理 #ffffff / 电磁 #ffbf00 / 寒冷 #22c6d1 / 灼热 #ff623c / 自然 #c3e151
# 物理原色是纯白，白符号放白底上会看不见；底图本身给的中性灰正好可用。
ELEMENT_RGB = {
    "Physical": (110, 114, 120),   # #6e7278，与底图占位灰一致
    "Electric": (255, 191, 0),     # #ffbf00
    "Cryo": (34, 198, 209),        # #22c6d1
    "Heat": (255, 98, 60),         # #ff623c
    "Nature": (195, 225, 81),      # #c3e151
}
DEFAULT_RGB = (110, 114, 120)

# 元素中文名，界面和样张都会用到
ELEMENT_CN = {
    "Physical": "物理",
    "Electric": "电磁",
    "Cryo": "寒冷",
    "Heat": "灼热",
    "Nature": "自然",
}

# 扇形/纯色底的压暗系数。1.0 = 直接用元素色。
SECTOR_DIM = 1.0


def element_rgb(element):
    return ELEMENT_RGB.get(element, DEFAULT_RGB)


def sector_rgb(element):
    r, g, b = element_rgb(element)
    if SECTOR_DIM >= 1.0:
        return (r, g, b)
    return (int(round(r * SECTOR_DIM)),
            int(round(g * SECTOR_DIM)),
            int(round(b * SECTOR_DIM)))


def _circle_mask_im(im, ss=4):
    """把方图裁成圆形（带抗锯齿 alpha）。"""
    w, h = im.size
    d = min(w, h)
    im = im.crop(((w - d) // 2, (h - d) // 2, (w - d) // 2 + d, (h - d) // 2 + d))
    mask = Image.new("L", (d * ss, d * ss), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * ss - 1, d * ss - 1), fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def _load_glyph(path):
    """读白色符号并按不透明包围盒收紧。"""
    im = Image.open(path).convert("RGBA")
    bbox = im.split()[3].getbbox()
    return im.crop(bbox) if bbox else im


# 连携技：以干员立绘为主体的圆盘
COMBO_BADGE_RATIO = 0.36      # 右下角小图标直径占大盘的比例
COMBO_BADGE_POS = 0.70        # 小图标圆心离大盘圆心的距离（相对半径）
COMBO_BADGE_ANGLE = 45.0      # 方向：右下 45°


def _backdrop_rgb(element):
    """立绘圆盘的底色：暗底里掺一点元素色。"""
    r, g, b = element_rgb(element)
    return (int(round(24 + r * 0.16)),
            int(round(26 + g * 0.16)),
            int(round(32 + b * 0.16)))


def _portrait_disc(portrait_path, S, element, canvas=None):
    """画一个纯立绘圆盘：底色 + 立绘 + 白色外环，不带任何角标。"""
    if canvas is None:
        canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    box = [0, 0, S - 1, S - 1]

    # 1) 底色圆盘
    draw.ellipse(box, fill=_backdrop_rgb(element) + (255,))

    # 2) 立绘：居中裁方 -> 铺满圆 -> 裁成圆形
    if portrait_path and os.path.isfile(portrait_path):
        portrait = Image.open(portrait_path).convert("RGBA")
        w, h = portrait.size
        d = min(w, h)
        portrait = portrait.crop(((w - d) // 2, (h - d) // 2,
                                  (w - d) // 2 + d, (h - d) // 2 + d))
        portrait = portrait.resize((S, S), Image.LANCZOS)
        portrait = _circle_mask_im(portrait, ss=2)
        canvas.alpha_composite(portrait, (0, 0))

    # 3) 白色外环
    ring_w = max(1, int(round(S * RING_RATIO)))
    draw.ellipse(box, outline=RING_WHITE, width=ring_w)
    return canvas


def compose_portrait(portrait_path, size, element="Physical"):
    """纯干员头像：立绘圆盘，没有右下角技能图标。队伍栏用这个。"""
    size = max(8, int(size))
    S = size * SUPERSAMPLE
    canvas = _portrait_disc(portrait_path, S, element)
    return canvas.resize((size, size), Image.LANCZOS)


def compose_combo(portrait_path, glyph_path, size, element="Physical"):
    """连携技图标：立绘为主体，右下角叠一个小号的连携技能图标。

    portrait_path: 干员头像（透明或带底的方形胸像）
    glyph_path:    连携技能的白色符号
    """
    size = max(16, int(size))
    S = size * SUPERSAMPLE
    canvas = _portrait_disc(portrait_path, S, element)
    draw = ImageDraw.Draw(canvas)

    # 右下角的小号连携图标
    badge = int(round(S * COMBO_BADGE_RATIO))
    small = compose(glyph_path, max(8, badge // SUPERSAMPLE), element, "combo")
    small = small.resize((badge, badge), Image.LANCZOS)

    R = S / 2.0
    ang = math.radians(COMBO_BADGE_ANGLE)
    bx = int(round(R + math.sin(ang) * R * COMBO_BADGE_POS - badge / 2.0))
    by = int(round(R + math.cos(ang) * R * COMBO_BADGE_POS - badge / 2.0))
    # 一圈暗色描边，把小图标和立绘分开
    pad = max(1, int(round(S * 0.012)))
    shadow = Image.new("RGBA", (badge + pad * 2, badge + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [0, 0, badge + pad * 2 - 1, badge + pad * 2 - 1], fill=(10, 12, 16, 225))
    canvas.alpha_composite(shadow, (bx - pad, by - pad))
    canvas.alpha_composite(small, (bx, by))

    return canvas.resize((size, size), Image.LANCZOS)


def compose(glyph_path, size, element="Physical", kind="skill"):
    """合成一张技能图标，返回 RGBA 的 PIL Image。

    kind: skill（技能）/ combo（连携）/ ult（终结技）
    """
    size = max(8, int(size))
    S = size * SUPERSAMPLE
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    pad = S * MARGIN
    box = [pad, pad, S - pad - 1, S - pad - 1]
    fill = sector_rgb(element) + (255,)

    if kind == "ult":
        # 终结技：整个圆是纯元素色
        draw.ellipse(box, fill=fill)
    else:
        # 技能 / 连携：暗底 + 底部扇形
        draw.ellipse(box, fill=BASE_DARK)
        # PIL 角度：0° 在 3 点钟方向、顺时针。换算后 30°~150° = 底部三分之一
        draw.pieslice(box, start=SECTOR_START - 90, end=SECTOR_END - 90, fill=fill)

    # 白色外环
    ring_w = max(1, int(round(S * RING_RATIO)))
    draw.ellipse(box, outline=RING_WHITE, width=ring_w)

    if glyph_path and os.path.isfile(glyph_path):
        glyph = _load_glyph(glyph_path)
        target = S * GLYPH_RATIO
        gw, gh = glyph.size
        scale = target / float(max(gw, gh))
        new = (max(1, int(round(gw * scale))), max(1, int(round(gh * scale))))
        glyph = glyph.resize(new, Image.LANCZOS)
        canvas.alpha_composite(glyph, (int(round((S - new[0]) / 2.0)),
                                       int(round((S - new[1]) / 2.0))))

    return canvas.resize((size, size), Image.LANCZOS)
