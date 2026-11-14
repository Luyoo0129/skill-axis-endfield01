# -*- coding: utf-8 -*-
"""排版自检：表格/标题里每一段文字是否超过它所在列的可容纳宽度。

跑法：python tools/check_pad_map_layout.py
"""
import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from app import fonts as f  # noqa: E402

# (文字, 字号, 是否粗体, 起始 x, 该列右边界)
ITEMS = [
    ("队伍位", 11, True, 644, 702),
    ("手柄组合", 11, True, 702, 858),
    ("等价键盘键", 11, True, 858, 934),
    ("干员", 11, True, 934, 1058),
    ("短按", 11, True, 1058, 1128),
    ("长按", 11, True, 1128, 1176),
    ("战技", 12, False, 1058, 1128),
    ("终结技", 12, False, 1128, 1176),
    ("连携技", 12, True, 1058, 1176),
    ("终结技", 12, False, 1058, 1128),
    ("单键，不用组合", 10, False, 934, 1058),
    ("全部干员", 12, False, 934, 1058),
    ("管理员", 13, True, 976, 1058),
    ("陈千语", 13, True, 976, 1058),
    ("面键圆里的小数字 = 队伍第几位", 12, False, 60, 560),
    ("必须先按住 LB，单独按面键不算施放", 12, False, 60, 560),
    ("默认键位照游戏内设置复刻 · 可在「设置 → 手柄」逐项重绑", 10, False, 60, 560),
    ("照游戏内手柄设置复刻 · 读自 data/settings.json 当前生效配置", 13, False, 40, 620),
    ("只要有一条对不上，说明默认键位要改；把实际顺序告诉我即可，不用你自己改代码",
     11, False, 64, 1176),
    ("按住不放 ≥ 280ms 算终结技，短于则算战技", 11, False, 414, 762),
    # 终结技第二种风格（LB + RB + 面键）下的文案
    ("LB + 面键", 11, False, 1058, 1128),
    ("LB + RB", 11, False, 1128, 1176),
    ("终结技：LB + RB + 面键", 11, True, 862, 1176),
    ("终结技：LB + 长按面键", 11, True, 862, 1176),
    ("游戏里选了「LB + RB + 面键」吗？这边也要选同一项", 11, False, 114, 412),
    ("战技 = LB + 面键　·　终结技 = LB + RB + 面键", 12, False, 60, 560),
]


def main():
    bad = 0
    for s, sz, bold, x, right in ITEMS:
        w = f.pil_text_width(s, sz, bold)
        room = right - x
        ok = w <= room
        if not ok:
            bad += 1
        print("%-6s w=%6.1f  room=%4d  x=%4d  %s" % (
            "OK" if ok else "OVER", w, room, x, s))
    print("-\n%d 项检查，%d 项超宽" % (len(ITEMS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
