# -*- coding: utf-8 -*-
"""量化一张参考截图：主色、边框粗细、圆角、图标占比。

用法：
    python tools/measure_ref.py 图.png
    python tools/measure_ref.py 图.png --box 1200,900,1700,1000

看不到图的时候靠它把画面变成数字：
    1) 主色排行（找出边框色 / 底色）
    2) 粗粒度色块图（把画面缩成字符网格，能看出形状）
    3) 扫描线（量边框宽度）
"""
import argparse
import os
import sys
from collections import Counter

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow：python -m pip install pillow")
    raise SystemExit(2)

RAMP = " .:-=+*#%@"


def hexof(c):
    return "#%02x%02x%02x" % c[:3]


def quantize(im, step=16):
    px = im.convert("RGB").load()
    w, h = im.size
    c = Counter()
    for y in range(0, h, max(1, h // 400)):
        for x in range(0, w, max(1, w // 400)):
            r, g, b = px[x, y]
            c[(r // step * step, g // step * step, b // step * step)] += 1
    return c


def dominant(im, top=12):
    c = quantize(im)
    total = sum(c.values())
    print(f"--- 主色排行（{im.size[0]}x{im.size[1]}）---")
    for col, n in c.most_common(top):
        print(f"  {hexof(col)}  {100.0 * n / total:5.1f}%")


def ascii_map(im, cols=56):
    """把画面缩成字符网格：亮的地方是 @，暗的地方是空格。"""
    w, h = im.size
    rows = max(1, int(cols * h / w * 0.5))
    small = im.convert("L").resize((cols, rows))
    px = small.load()
    print(f"--- 色块图 {cols}x{rows} ---")
    for y in range(rows):
        line = "".join(RAMP[min(len(RAMP) - 1, px[x, y] * len(RAMP) // 256)]
                       for x in range(cols))
        print("  |" + line + "|")


def hue_map(im, cols=56):
    """用字母标出颜色倾向：R 红 / O 橙 / Y 黄 / G 绿 / C 青 / B 蓝 / P 紫 / . 灰"""
    w, h = im.size
    rows = max(1, int(cols * h / w * 0.5))
    small = im.convert("RGB").resize((cols, rows))
    px = small.load()
    out = []
    for y in range(rows):
        line = []
        for x in range(cols):
            r, g, b = px[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn < 26:
                line.append("." if mx > 90 else " ")
                continue
            if mx == r:
                line.append("R" if g < 80 else ("O" if g < 150 else "Y"))
            elif mx == g:
                line.append("G" if b < 120 else "C")
            else:
                line.append("B" if r < 100 else "P")
        out.append("".join(line))
    print(f"--- 色相图 {cols}x{rows} ---")
    for line in out:
        print("  |" + line + "|")


def scanline(im, y):
    """沿一条水平线打印颜色变化，用来量边框宽度。"""
    w, _ = im.size
    px = im.convert("RGB").load()
    print(f"--- 第 {y} 行颜色分段 ---")
    prev = None
    run_start = 0
    runs = []
    for x in range(w):
        col = px[x, y]
        key = (col[0] // 8, col[1] // 8, col[2] // 8)
        if key != prev:
            if prev is not None:
                runs.append((run_start, x - 1, x - run_start, last_col))
            prev = key
            run_start = x
            last_col = col
    runs.append((run_start, w - 1, w - run_start, last_col))
    for a, b, n, col in runs:
        if n >= 1:
            print(f"  x {a:4d}-{b:4d}  宽 {n:3d}px  {hexof(col)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--box", help="裁剪区域 x1,y1,x2,y2")
    ap.add_argument("--scan", type=int, help="扫描线 y 坐标")
    ap.add_argument("--cols", type=int, default=56)
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print("找不到文件:", args.image)
        return 2

    im = Image.open(args.image)
    if args.box:
        x1, y1, x2, y2 = (int(v) for v in args.box.split(","))
        im = im.crop((x1, y1, x2, y2))
        print(f"裁剪到 {im.size}")

    dominant(im)
    ascii_map(im, args.cols)
    hue_map(im, args.cols)
    if args.scan is not None:
        scanline(im, min(args.scan, im.size[1] - 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
