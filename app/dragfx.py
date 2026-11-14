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
    """单个 canvas 的「跟随目标」动画。

    以前是每次 mousemove 都 cancel 上一条再重启一条 8 帧补间：
    拖动频率高时（60~120Hz）会不停重启，看起来一顿一顿的。
    现在改成**一条常驻循环**：
        move_to() 只更新目标位置，循环按帧把内容往最新目标推，
        全部到位后自动停。
    这样不论鼠标多快，都是同一套平滑跟随。
    """

    # 每帧向目标靠近的比例（越大越快）；按帧时间再折算一次，避免掉帧变慢
    FOLLOW = 0.55
    EPS = 0.6

    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self._job = None
        self._targets = {}

    # ---------- 控制 ----------
    def cancel(self):
        self._targets.clear()
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
        """targets: [(tag, x, y)] —— tag 的目标左上角坐标（绝对）。

        只记录目标，动画循环会把它们平滑推过去；重复调用只更新目标，
        不会重启循环，所以高频拖动也顺。
        """
        for tag, x, y in targets:
            self._targets[tag] = (float(x), float(y))
        if done is not None:
            self._pending_done = done
        if self._job is None and self._targets:
            self._schedule()

    def _schedule(self):
        try:
            self._job = self.root.after(2, self._step)
        except tk.TclError:
            self._job = None
            self._finish()

    def _step(self):
        self._job = None
        remaining = 0
        for tag, (tx, ty) in list(self._targets.items()):
            try:
                box = self.canvas.bbox(tag)
            except tk.TclError:
                box = None
            if not box:
                self._targets.pop(tag, None)
                continue
            dx = tx - box[0]
            dy = ty - box[1]
            if abs(dx) <= self.EPS and abs(dy) <= self.EPS:
                self._targets.pop(tag, None)
                continue
            remaining += 1
            try:
                self.canvas.move(tag, dx * self.FOLLOW, dy * self.FOLLOW)
            except tk.TclError:
                self._targets.pop(tag, None)

        if self._targets and remaining:
            try:
                self._job = self.root.after(FRAME_MS, self._step)
            except tk.TclError:
                self._job = None
        else:
            self._finish()

    def _finish(self):
        self._targets.clear()
        cb = getattr(self, "_pending_done", None)
        self._pending_done = None
        if cb is not None:
            cb()


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
