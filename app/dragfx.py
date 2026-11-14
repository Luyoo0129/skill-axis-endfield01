# -*- coding: utf-8 -*-
"""拖拽与动画的共用零件。

编辑器里有三处拖拽（编队行、技能轴节点、队伍卡片），
以前各自的幽灵、阈值、指示线长得不一样，这里统一成一套：

    make_ghost()     —— 跟着鼠标的「幽灵」（文字或头像）
    insert_line()    —— 松手会插到哪的琥珀色竖线/横线
    slide()          —— 松手后让卡片/节点滑到新位置的动画

动画都用 root.after 驱动 ease-out，不阻塞主线程；窗口关掉时抛 TclError 就直接放弃。
"""
import time
import tkinter as tk

from . import theme

# 拖动阈值：手抖小于这个距离算「点了一下」，不算拖
DRAG_THRESHOLD = 5

# 一次滑动的时长（毫秒）
SLIDE_MS = 170
FRAME_MS = 16


def ease_out(t):
    """ease-out cubic：起步快、收尾稳，看起来像有惯性。"""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return 1.0 - (1.0 - t) ** 3


def make_ghost(root, label, image=None):
    """生成一个跟随鼠标的小幽灵窗口，返回 (toplevel, photo_ref)。"""
    try:
        ghost = tk.Toplevel(root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.configure(bg=theme.ACCENT)
        if image is not None:
            box = tk.Frame(ghost, bg=theme.PANEL_3)
            box.pack(padx=2, pady=2)
            tk.Label(box, image=image, bg=theme.PANEL_3, bd=0).pack(padx=6, pady=6)
            tk.Label(box, text=label, bg=theme.PANEL_3, fg=theme.TEXT,
                     font=theme.font(theme.F_TINY)).pack(pady=(0, 4))
        else:
            tk.Label(ghost, text=label, bg=theme.PANEL_3, fg=theme.TEXT,
                     font=theme.font(theme.F_SMALL), padx=10, pady=6).pack(padx=2,
                                                                         pady=2)
        ghost.geometry("+%d+%d" % (root.winfo_pointerx() + 12,
                                   root.winfo_pointery() + 8))
        return ghost, image
    except tk.TclError:
        return None, None


def move_ghost(ghost, x_root, y_root):
    if ghost is None:
        return False
    try:
        ghost.geometry("+%d+%d" % (int(x_root) + 12, int(y_root) + 8))
        return True
    except tk.TclError:
        return False


def insert_line(cv, x1, y1, x2, y2, tag="drop_ind"):
    """插入位置指示线：外圈暗琥珀 + 内芯亮琥珀，比单线更醒目。"""
    try:
        cv.create_line(x1, y1, x2, y2, fill=theme.ACCENT_SOFT, width=6,
                       capstyle="round", tags=(tag,))
        cv.create_line(x1, y1, x2, y2, fill=theme.ACCENT, width=2,
                       capstyle="round", tags=(tag,))
        # 两端小圆点，看起来像「插槽」
        r = 3
        for px, py in ((x1, y1), (x2, y2)):
            cv.create_oval(px - r, py - r, px + r, py + r, fill=theme.ACCENT,
                           outline="", tags=(tag,))
    except tk.TclError:
        pass


def set_ghost_alpha(ghost, alpha=0.86):
    """幽灵半透明，免得它把小一号的插入线整条盖住。"""
    try:
        ghost.attributes("-alpha", alpha)
    except tk.TclError:
        pass


def glide(root, canvas, groups, duration=110, done=None):
    """从当前位置平滑挪到「当前位置 + (dx, dy)」。

    跟 slide() 的区别：slide 假定画面已在新位置、先把内容挪回去再补回来；
    glide 直接按增量移动，适合拖动过程中的实时让位。
    """
    groups = [g for g in (groups or []) if abs(g[1]) > 0.5 or abs(g[2]) > 0.5]
    if not groups:
        if done is not None:
            done()
        return

    start = time.monotonic()
    span = max(1, int(duration)) / 1000.0
    state = {"done": 0.0}

    def step():
        el = time.monotonic() - start
        t = min(1.0, el / span)
        target = ease_out(t)
        delta = target - state["done"]
        state["done"] = target
        for tag, dx, dy in groups:
            try:
                canvas.move(tag, dx * delta, dy * delta)
            except tk.TclError:
                pass
        if t < 1.0:
            try:
                root.after(FRAME_MS, step)
            except tk.TclError:
                pass
        elif done is not None:
            done()

    try:
        root.after(FRAME_MS, step)
    except tk.TclError:
        if done is not None:
            done()


def slide(root, canvas, groups, duration=SLIDE_MS, done=None):
    """让 canvas 上的内容从旧位置滑到当前位置。

    groups: [(tag, dx, dy)]，dx/dy = 旧位置 - 新位置。
    调用前 canvas 里应该已经按新位置画好了；本函数先把它们挪回旧位置，
    再缓动补回来，看起来就是「滑过去」。
    """
    groups = [g for g in (groups or []) if g[1] or g[2]]
    if not groups:
        if done is not None:
            done()
        return

    for tag, dx, dy in groups:
        try:
            canvas.move(tag, -dx, -dy)
        except tk.TclError:
            pass

    start = time.monotonic()
    span = max(1, int(duration)) / 1000.0
    state = {"done": 0.0}

    def step():
        el = time.monotonic() - start
        t = min(1.0, el / span)
        target = ease_out(t)
        delta = target - state["done"]
        state["done"] = target
        for tag, dx, dy in groups:
            try:
                canvas.move(tag, dx * delta, dy * delta)
            except tk.TclError:
                pass
        if t < 1.0:
            try:
                root.after(FRAME_MS, step)
            except tk.TclError:
                pass
        elif done is not None:
            done()

    try:
        root.after(FRAME_MS, step)
    except tk.TclError:
        if done is not None:
            done()
