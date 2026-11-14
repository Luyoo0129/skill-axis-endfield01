# -*- coding: utf-8 -*-
"""生成「手柄按键映射对照图」，供用户对着游戏内设置核对。

读 data/settings.json + data/team.json，输出 preview/pad_map.png。

对照图要回答的问题只有一个：
    LB + X/Y/A/B 这四个面键，到底分别对应队伍第几位？

所以面键圆里直接标出槽位号（白字母 + 琥珀数字），右侧表格给出
「手柄组合 → 等价的键盘键 → 干员 → 短按/长按结果」。
"""
import json
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402

from app import fonts as fontlib  # noqa: E402
from app.iconart import compose_portrait  # noqa: E402
from app.model import (DEFAULT_PAD_COMBO, DEFAULT_PAD_MODIFIER,  # noqa: E402
                       DEFAULT_PAD_SLOTS)

OUT = os.path.join(BASE, "preview", "pad_map.png")
PORTRAIT_DIR = os.path.join(BASE, "data", "portraits")

# 配色取 app/theme.py
BG = (11, 14, 19)
CARD = (18, 22, 29)
CARD_2 = (23, 28, 37)
CARD_3 = (30, 37, 48)
CARD_4 = (37, 45, 58)
LINE = (42, 50, 64)
LINE_2 = (57, 68, 85)
TEXT = (232, 237, 244)
DIM = (154, 165, 180)
MUTED = (107, 118, 134)
ACCENT = (245, 196, 81)
ACCENT_DARK = (74, 58, 20)
CYAN = (87, 200, 216)
CYAN_DARK = (20, 52, 58)

PAD_BITS = {0x1000: "A", 0x2000: "B", 0x4000: "X", 0x8000: "Y"}
BIT_OF = {v: k for k, v in PAD_BITS.items()}
PAD_NAMES = {0x0100: "LB", 0x0200: "RB", 0x1000: "A", 0x2000: "B",
             0x4000: "X", 0x8000: "Y"}

W, H = 1240, 862

# 手柄几何（都写死成常量，避免各处随手算导致贴边）
BODY = (140, 214, 480, 400)
GRIP_L = (126, 322, 250, 496)
GRIP_R = (370, 322, 494, 496)
CLUSTER = (392, 298)      # ABXY 中心
FACE_R = 24
FACE_GAP = 43


def font(size, bold=False):
    return fontlib.pil_font(size, bold)


def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def text(d, xy, s, size, fill, anchor="la", bold=False):
    d.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)


def pill(d, x, y, s, size, bg, fg, padx=11, h=None, outline=None, bold=True):
    """画一个胶囊形按键标签，返回右边界 x。"""
    h = h or size + 13
    w = int(fontlib.pil_text_width(s, size, bold)) + padx * 2
    rrect(d, [x, y, x + w, y + h], h // 2, fill=bg, outline=outline)
    text(d, (x + w // 2, y + h // 2 + 1), s, size, fg, anchor="mm", bold=bold)
    return x + w


def load_json(name, default):
    path = os.path.join(BASE, "data", name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def element_of(cn, entries):
    for e in entries:
        if e.get("cn") == cn:
            return e.get("element", "Physical")
    return "Physical"


# ---------------- 手柄线稿 ----------------

def draw_controller(img, d):
    """画一台手柄；面键圆里是「字母 + 槽位号」。"""
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle(BODY, radius=66, fill=255)
    md.ellipse(GRIP_L, fill=255)
    md.ellipse(GRIP_R, fill=255)

    body = Image.new("RGBA", (W, H), CARD_2 + (255,))
    img.paste(body, (0, 0), mask)

    # 外描边：mask 膨胀一圈减去自身
    ring = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(7)), mask)
    img.paste(Image.new("RGBA", (W, H), LINE_2 + (255,)), (0, 0), ring)

    # 肩键：落在机身上沿，不悬空
    pill(d, 176, 186, "LB", 14, ACCENT, ACCENT_DARK, padx=15, h=28)
    pill(d, 396, 186, "RB", 14, CYAN, (8, 38, 44), padx=15, h=28)

    # 摇杆（弱化，只交代形体）
    for sx, sy in ((206, 292), (300, 348)):
        d.ellipse([sx - 26, sy - 26, sx + 26, sy + 26], fill=CARD_3,
                  outline=LINE_2, width=2)
        d.ellipse([sx - 14, sy - 14, sx + 14, sy + 14], fill=CARD_4,
                  outline=LINE, width=2)

    # 方向键
    dxx, dyy = 206, 368
    rrect(d, [dxx - 9, dyy - 25, dxx + 9, dyy + 25], 4, fill=CARD_3,
          outline=LINE, width=2)
    rrect(d, [dxx - 25, dyy - 9, dxx + 25, dyy + 9], 4, fill=CARD_3,
          outline=LINE, width=2)

    cx, cy = CLUSTER
    slots = {DEFAULT_PAD_SLOTS[i]: i for i in range(4)}
    faces = {
        "Y": (cx, cy - FACE_GAP),
        "X": (cx - FACE_GAP, cy),
        "B": (cx + FACE_GAP, cy),
        "A": (cx, cy + FACE_GAP),
    }
    for letter, (bx, by) in faces.items():
        d.ellipse([bx - FACE_R, by - FACE_R, bx + FACE_R, by + FACE_R],
                  fill=CARD_4, outline=ACCENT, width=2)
        text(d, (bx, by - 5), letter, 15, TEXT, anchor="mm", bold=True)
        slot = slots.get(BIT_OF[letter])
        if slot is not None:
            text(d, (bx, by + 12), str(slot + 1), 10, ACCENT, anchor="mm",
                 bold=True)


# ---------------- 右侧表格 ----------------

# 列坐标（卡片 620..1200，内边距 24）
C_SLOT = 644
C_PAD = 702
C_KEY = 858
C_OP = 934
C_TAP = 1058
C_HOLD = 1128


def draw_table(img, d, entries, team, settings):
    rrect(d, [620, 120, 1200, 640], 14, fill=CARD, outline=LINE, width=1)
    text(d, (644, 140), "技能键位换算", 17, TEXT, bold=True)
    text(d, (644, 166), "手柄动作先换算成等价的数字键，再交给播放器", 12, MUTED)

    hy = 198
    for cx, label in ((C_SLOT, "队伍位"), (C_PAD, "手柄组合"), (C_KEY, "等价键盘键"),
                      (C_OP, "干员"), (C_TAP, "短按"), (C_HOLD, "长按")):
        text(d, (cx, hy), label, 11, MUTED, bold=True)
    d.line([644, hy + 17, 1176, hy + 17], fill=LINE, width=1)

    slots = settings.get("pad_slots") or {str(k): v for k, v in DEFAULT_PAD_SLOTS.items()}
    mod_bit = int(settings.get("pad_modifier") or DEFAULT_PAD_MODIFIER)
    mod_name = PAD_NAMES.get(mod_bit, "LB")
    members = (team or {}).get("members") or []

    y = hy + 30
    row_h = 62
    for slot in range(4):
        bit = int(slots.get(str(slot), DEFAULT_PAD_SLOTS[slot]))
        letter = PAD_BITS.get(bit, "?")
        member = members[slot] if slot < len(members) else ""

        d.line([644, y + row_h - 8, 1176, y + row_h - 8], fill=LINE, width=1)

        bc = (C_SLOT + 13, y + 20)
        d.ellipse([bc[0] - 13, bc[1] - 13, bc[0] + 13, bc[1] + 13], fill=ACCENT)
        text(d, (bc[0], bc[1] + 1), str(slot + 1), 13, ACCENT_DARK,
             anchor="mm", bold=True)

        px = pill(d, C_PAD, y + 7, mod_name, 12, CARD_3, DIM, padx=9, h=26,
                  outline=LINE_2)
        text(d, (px + 10, y + 20), "+", 12, MUTED, anchor="mm")
        pill(d, px + 21, y + 7, letter, 13, CARD_4, ACCENT, padx=12, h=26,
             outline=ACCENT)

        pill(d, C_KEY, y + 7, str(slot + 1), 12, CARD_3, DIM, padx=11, h=26,
             outline=LINE_2)

        if member and os.path.isfile(os.path.join(PORTRAIT_DIR, member + ".png")):
            avatar = compose_portrait(os.path.join(PORTRAIT_DIR, member + ".png"),
                                      34, element_of(member, entries))
            img.paste(avatar, (C_OP, y + 4), avatar)
        text(d, (C_OP + 42, y + 21), member or "—", 13, TEXT, bold=True)

        text(d, (C_TAP, y + 21), "战技", 12, DIM)
        text(d, (C_HOLD, y + 21), "终结技", 12, ACCENT)
        y += row_h

    # 连携技：整行单独高亮
    cb = y + 4
    rrect(d, [634, cb, 1186, cb + 62], 10, fill=CYAN_DARK)
    d.rectangle([634, cb, 638, cb + 62], fill=CYAN)
    text(d, (654, cb + 12), "连携技", 12, CYAN, bold=True)
    text(d, (654, cb + 32), "全队共用", 10, (120, 180, 190))

    combo_bit = int(settings.get("pad_combo") or DEFAULT_PAD_COMBO)
    combo_name = PAD_NAMES.get(combo_bit, "RB")
    px = pill(d, C_PAD, cb + 16, combo_name, 13, CYAN, (8, 38, 44), padx=12, h=28)
    text(d, (px + 11, cb + 30), "→", 12, CYAN, anchor="mm")
    vk = int(settings.get("combo_key") or 0x45)
    key_label = chr(vk) if 0x41 <= vk <= 0x5A else str(vk)
    pill(d, C_KEY, cb + 16, key_label, 13, CYAN_DARK, CYAN, padx=13, h=28,
         outline=CYAN)

    text(d, (C_OP, cb + 22), "全部干员", 12, (200, 235, 240))
    text(d, (C_OP, cb + 40), "单键，不用组合", 10, (110, 170, 180))
    text(d, (C_TAP, cb + 30), "连携技", 12, CYAN, bold=True)


# ---------------- 底部核对清单 ----------------

def draw_checklist(d, hold_ms):
    rrect(d, [40, 660, 1200, 806], 14, fill=CARD, outline=LINE, width=1)
    text(d, (64, 676), "对着游戏「设置 → 手柄」核对这三条", 15, TEXT, bold=True)
    text(d, (64, 700), "只要有一条对不上，说明默认键位要改；把实际顺序告诉我即可，不用你自己改代码",
         11, MUTED)

    items = (
        ("连携技", "是不是 RB（右肩键）单独触发？"),
        ("战技 / 终结技", "是不是 按住 LB 再按面键？"),
        ("长按判定", "按住不放 ≥ %dms 算终结技，短于则算战技" % hold_ms),
    )
    for i, (head, body) in enumerate(items):
        bx = 64 + i * 372
        rrect(d, [bx, 726, bx + 348, 790], 10, fill=CARD_2, outline=LINE, width=1)
        d.ellipse([bx + 14, 742, bx + 38, 766], fill=ACCENT)
        text(d, (bx + 26, 755), str(i + 1), 13, ACCENT_DARK, anchor="mm", bold=True)
        text(d, (bx + 50, 738), head, 12, ACCENT, bold=True)
        text(d, (bx + 50, 760), body, 11, DIM)


def draw_legend(d):
    """左卡片下沿：把「数字代表什么」和操作前置条件说清楚。"""
    text(d, (310, 528), "面键圆里的小数字 = 队伍第几位", 12, DIM, anchor="ma")
    text(d, (310, 550), "必须先按住 LB，单独按面键不算施放", 12, MUTED, anchor="ma")
    text(d, (310, 584), "默认键位照游戏内设置复刻 · 可在「设置 → 手柄」逐项重绑",
         10, MUTED, anchor="ma")


def main():
    settings = load_json("settings.json", {})
    team = load_json("team.json", {"members": []})
    entries = load_json(os.path.join("icons", "index.json"), [])

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    text(d, (40, 32), "手柄按键映射对照", 28, TEXT, bold=True)
    text(d, (40, 72), "照游戏内手柄设置复刻 · 读自 data/settings.json 当前生效配置",
         13, MUTED)

    rrect(d, [40, 120, 600, 640], 14, fill=CARD, outline=LINE, width=1)
    text(d, (64, 140), "面键 → 队伍位", 17, TEXT, bold=True)
    text(d, (64, 166), "X / Y / A / B 依次对应队伍第 1~4 位", 12, MUTED)

    draw_controller(img, d)
    draw_legend(d)

    draw_table(img, d, entries, team, settings)
    draw_checklist(d, int(settings.get("hold_ms") or 280))

    text(d, (40, 826),
         "生成时间 %s　·　数据源 data/settings.json + data/team.json"
         % datetime.now().strftime("%Y-%m-%d %H:%M"), 11, MUTED)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("saved", OUT, img.size)

    slots = settings.get("pad_slots") or {}
    for slot in range(4):
        bit = int(slots.get(str(slot), DEFAULT_PAD_SLOTS[slot]))
        member = (team.get("members") or [""] * 4)[slot]
        print("  队伍位 %d ← %s ← %s" % (slot + 1, PAD_BITS.get(bit, "?"), member))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
