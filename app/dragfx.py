# -*- coding: utf-8 -*-
"""拖拽与动画的共用零件。

三条铁律（之前「乱飞」就是违反了第一条）：

1. **一个 canvas 同时只允许一条动画**。以前每次 mousemove 都新起一条
   `after` 循环，旧循环还在按自己的增量推坐标，几条叠加就飞了。
2. 动画按**绝对目标位置**算位移（用 bbox 取当前位置），重复调用不会累积误差。
3. 重建 canvas 内容（refresh_*）之前必须先 `cancel()`，否则旧动画会去搬
   重建出来的同名 tag，看起来就是卡片自己乱跳。

对外：`Animator`（move_to / cancel）、`make_ghost`、`set_ghost_alpha`、`DRAG_THRESHOLD`。
"""
import time
import tkinter as tk

from . import theme

# 拖动阈值：手抖小于这个像素距离算「点了一下」，不算拖
DRAG_THRESHOLD = 5

# 按住多久才算「要拖动」（防误触）：这段时间内先移动超过 CANCEL_DIST 就判为误触
HOLD_MS = 200
CANCEL_DIST = 12

# 让位动画时长（毫秒）与帧间隔
MOVE_MS = 120
FRAME_MS = 16


def ease_out(t):
    """ease-out cubic：起步快、收尾稳。"""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return 1.0 - (1.0 - t) ** 3


class Animator:
    """单个 canvas 的位移动画：同一时间只跑一条，新的会顶掉旧的。"""

    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self._job = None

    # ---------- 控制 ----------
    def cancel(self):
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except (tk.TclError, ValueError):
                pass
            self._job = None

    def busy(self):
        return self._job is not None

    # ---------- 动画 ----------
    def move_to(self, targets, duration=MOVE_MS, done=None):
        """targets: [(tag, x, y)] —— tag 想要到达的左上角坐标（绝对）。

        每次都从「当前实际位置」重新算位移，所以连续调用是收敛的，
        不会像累加增量那样越跑越远。
        """
        self.cancel()
        moves = []
        for tag, x, y in targets:
            try:
                box = self.canvas.bbox(tag)
            except tk.TclError:
                continue
            if not box:
                continue
            dx, dy = x - box[0], y - box[1]
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                continue
            moves.append((tag, dx, dy))

        if not moves:
            if done is not None:
                done()
            return

        start = time.monotonic()
        span = max(1, int(duration)) / 1000.0
        state = {"done": 0.0}

        def step():
            elapsed = time.monotonic() - start
            t = min(1.0, elapsed / span)
            target = ease_out(t)
            delta = target - state["done"]
            state["done"] = target
            for tag, dx, dy in moves:
                try:
                    self.canvas.move(tag, dx * delta, dy * delta)
                except tk.TclError:
                    continue
            if t < 1.0:
                try:
                    self._job = self.root.after(FRAME_MS, step)
                except tk.TclError:
                    self._job = None
            else:
                self._job = None
                if done is not None:
                    done()

        try:
            self._job = self.root.after(FRAME_MS, step)
        except tk.TclError:
            self._job = None
            if done is not None:
                done()


# ---------------- 幽灵 ----------------

def make_ghost(root, label, image=None):
    """跟随鼠标的小幽灵窗口，返回 (toplevel, photo_ref)。"""
    try:
        ghost = tk.Toplevel(root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.configure(bg=theme.ACCENT)
        box = tk.Frame(ghost, bg=theme.PANEL_3)
        box.pack(padx=2, pady=2)
        if image is not None:
            tk.Label(box, image=image, bg=theme.PANEL_3, bd=0).pack(padx=6, pady=6)
            tk.Label(box, text=label, bg=theme.PANEL_3, fg=theme.TEXT,
                     font=theme.font(theme.F_TINY)).pack(pady=(0, 4))
        else:
            tk.Label(box, text=label, bg=theme.PANEL_3, fg=theme.TEXT,
                     font=theme.font(theme.F_SMALL), padx=8, pady=5).pack()
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


def set_ghost_alpha(ghost, alpha=0.86):
    """幽灵半透明，免得把落点完全挡住。"""
    try:
        ghost.attributes("-alpha", alpha)
    except tk.TclError:
        pass


def hide_ghost(ghost):
    if ghost is None:
        return
    try:
        ghost.destroy()
    except tk.TclError:
        pass
