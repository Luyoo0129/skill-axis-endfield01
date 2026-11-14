# -*- coding: utf-8 -*-
"""好看一点的弹出菜单：自绘圆角面板 + 淡入淡出，替代 tk.Menu 的方块样式。"""
import time
import tkinter as tk

from . import theme


class NiceMenu:
    """items: [(label, value)] 或 [(label, value, sub)]；选中回调 on_pick(value)。"""

    WIDTH = 240

    def __init__(self, root, items, on_pick, width=None, anchor=None):
        self.root = root
        self.items = list(items)
        self.on_pick = on_pick
        self.width = width or self.WIDTH
        self._alpha = 0.0
        self._closing = False
        self._born = time.monotonic()

        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        win.configure(bg=theme.ACCENT)
        self.win = win

        inner = tk.Frame(win, bg=theme.PANEL_2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.inner = inner

        rows = 0
        for item in self.items:
            label, value = item[0], item[1]
            sub = item[2] if len(item) > 2 else ""
            row = tk.Frame(inner, bg=theme.PANEL_2, cursor="hand2")
            row.pack(fill="x", padx=6, pady=1)
            lab = tk.Label(row, text=label, bg=theme.PANEL_2, fg=theme.TEXT,
                           font=theme.font(theme.F_SMALL), anchor="w")
            lab.pack(fill="x", padx=8, pady=(5 if not sub else 3, 0))
            widgets = [row, lab]
            if sub:
                sl = tk.Label(row, text=sub, bg=theme.PANEL_2,
                              fg=theme.TEXT_MUTED,
                              font=theme.font(theme.F_TINY), anchor="w")
                sl.pack(fill="x", padx=8, pady=(0, 4))
                widgets.append(sl)

            def enter(_e, ws=widgets):
                for w in ws:
                    w.configure(bg=theme.PANEL_3)

            def leave(_e, ws=widgets):
                for w in ws:
                    w.configure(bg=theme.PANEL_2)

            def click(_e, v=value):
                self._choose(v)

            for w in widgets:
                w.bind("<Enter>", enter)
                w.bind("<Leave>", leave)
                w.bind("<Button-1>", click)
            rows += 1

        # 位置：指针处，并夹在屏幕内
        x, y = (anchor if anchor else
                (root.winfo_pointerx(), root.winfo_pointery()))
        win.update_idletasks()
        w = self.width
        h = win.winfo_reqheight()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x = max(8, min(int(x), sw - w - 8))
        y = max(8, min(int(y), sh - h - 8))
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))

        win.bind("<Escape>", lambda e: self.close())
        win.bind("<FocusOut>", lambda e: self._fade_out())
        # 点菜单以外的任何地方都收起（Tk 的 overrideredirect 窗口拿不到焦点时
        # FocusOut 不会触发，所以再挂一层全局点击判断）
        try:
            self._outside_bind = root.bind("<Button-1>", self._on_outside_click,
                                           add="+")
        except tk.TclError:
            self._outside_bind = None
        try:
            win.focus_force()
        except tk.TclError:
            pass
        self._fade_in()

    # ---------- 动画 ----------
    def _set_alpha(self, a):
        try:
            self.win.attributes("-alpha", max(0.0, min(1.0, a)))
        except tk.TclError:
            pass
        self._alpha = a

    def _fade_in(self, step=0.16):
        if self._closing or getattr(self, "_destroyed", False):
            return
        nxt = self._alpha + step
        self._set_alpha(nxt if nxt < 1.0 else 1.0)
        if nxt < 1.0:
            self.win.after(16, lambda: self._fade_in(step))

    def _fade_out(self, step=0.18):
        # 注意：这里不能「已关闭就直接 return」——那会把正在跑的淡出链也掐断，
        # 窗口会卡在半透明、永远不销毁。
        if getattr(self, "_destroyed", False):
            return
        self._closing = True
        nxt = self._alpha - step
        if nxt <= 0.02:
            self._destroy()
            return
        self._set_alpha(nxt)
        self.win.after(16, lambda: self._fade_out(step))

    def _on_outside_click(self, e):
        if self._closing or getattr(self, "_destroyed", False):
            return
        # 刚弹出的这一下点击会冒泡到 root，别把自己立刻关掉
        if time.monotonic() - self._born < 0.15:
            return
        try:
            x, y = self.win.winfo_rootx(), self.win.winfo_rooty()
            w, h = self.win.winfo_width(), self.win.winfo_height()
        except tk.TclError:
            return
        if x <= e.x_root <= x + w and y <= e.y_root <= y + h:
            return
        self.close()

    def _choose(self, value):
        cb = self.on_pick
        self._destroy()
        if cb is not None:
            try:
                cb(value)
            except Exception:  # noqa: BLE001
                pass

    def close(self):
        self._fade_out()

    def _destroy(self):
        self._destroyed = True
        root = self.root
        try:
            if self._outside_bind is not None:
                root.unbind("<Button-1>", self._outside_bind)
                self._outside_bind = None
        except (tk.TclError, TypeError):
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass
