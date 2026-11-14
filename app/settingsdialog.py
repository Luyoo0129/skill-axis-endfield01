# -*- coding: utf-8 -*-
"""设置对话框：运行设置 + 键位映射。"""
import tkinter as tk

from . import theme
from .gamepad import button_name
from .model import KIND_CN, KINDS, PAD_ULT_CHORD, PAD_ULT_MODES
from .widgets import center_window


class SettingsDialog:
    def __init__(self, app):
        self.app = app
        self.store = app.store
        self.s = self.store.settings

        self.win = tk.Toplevel(app.root)
        self.win.title("设置")
        self.win.configure(bg=theme.BG)
        self.win.transient(app.root)
        self.win.grab_set()

        self._build()
        # 高度跟着内容走：字体/DPI 不同的机器上也不会把底部「完成」按钮截掉
        try:
            self.win.update_idletasks()
            need = self.win.winfo_reqheight()
        except tk.TclError:
            need = 780
        center_window(self.win, app.root, 520, max(660, min(940, need + 10)))

    # ---------- 界面 ----------
    def _build(self):
        self._subs = {}
        head = tk.Frame(self.win, bg=theme.BG, padx=20, pady=16)
        head.pack(fill="x")
        tk.Label(head, text="设置", bg=theme.BG, fg=theme.TEXT,
                 font=theme.font(theme.F_TITLE, True)).pack(side="left")

        body = tk.Frame(self.win, bg=theme.BG, padx=20)
        body.pack(fill="both", expand=True)

        # ---- 运行设置 ----
        box1 = self._card(body, "运行设置")
        self.mode_var = tk.StringVar(value=self.s.mode)
        for val, label in (("strict", "必须按对键才推进"), ("any", "任意键推进")):
            tk.Radiobutton(
                box1, text=label, value=val, variable=self.mode_var,
                command=self._on_mode, bg=theme.PANEL, fg=theme.TEXT_DIM,
                selectcolor=theme.PANEL_2, activebackground=theme.PANEL,
                activeforeground=theme.TEXT, relief="flat", bd=0,
                highlightthickness=0, anchor="w",
                font=theme.font(theme.F_BODY)).pack(fill="x", padx=8)

        self.focus_var = tk.BooleanVar(value=bool(self.s.only_game_focus))
        tk.Checkbutton(
            box1, text="仅当游戏窗口在前台时响应", variable=self.focus_var,
            command=self._on_focus, bg=theme.PANEL, fg=theme.TEXT_DIM,
            selectcolor=theme.PANEL_2, activebackground=theme.PANEL,
            activeforeground=theme.TEXT, relief="flat", bd=0,
            highlightthickness=0, anchor="w",
            font=theme.font(theme.F_BODY)).pack(fill="x", padx=8)

        self.pad_var = tk.BooleanVar(value=bool(self.s.gamepad_enabled))
        tk.Checkbutton(
            box1, text="启用手柄监听", variable=self.pad_var,
            command=self._on_pad, bg=theme.PANEL, fg=theme.TEXT_DIM,
            selectcolor=theme.PANEL_2, activebackground=theme.PANEL,
            activeforeground=theme.TEXT, relief="flat", bd=0,
            highlightthickness=0, anchor="w",
            font=theme.font(theme.F_BODY)).pack(fill="x", padx=8)

        # ---- 键位规则（只保留长按判定）----
        box2 = self._card(body, "键位规则")

        row2 = tk.Frame(box2, bg=theme.PANEL)
        row2.pack(fill="x", padx=8, pady=3)
        tk.Label(row2, text="长按判定", bg=theme.PANEL, fg=theme.TEXT_DIM, width=8,
                 anchor="w", font=theme.font(theme.F_SMALL)).pack(side="left")
        self.hold_var = tk.StringVar(value=str(self.s.hold_ms))
        sp = tk.Spinbox(row2, from_=80, to=1200, increment=20, width=7,
                        textvariable=self.hold_var, command=self._on_hold,
                        bg=theme.PANEL_2, fg=theme.TEXT,
                        buttonbackground=theme.PANEL_3, relief="flat", bd=0,
                        highlightthickness=1, highlightbackground=theme.BORDER,
                        font=theme.font(theme.F_SMALL))
        sp.pack(side="left", ipady=2)
        sp.bind("<KeyRelease>", lambda e: self._on_hold())
        tk.Label(row2, text="毫秒（默认 280）", bg=theme.PANEL, fg=theme.TEXT_MUTED,
                 font=theme.font(theme.F_TINY)).pack(side="left", padx=(8, 0))

        # ---- 手柄（照游戏内规则）----
        box3 = self._card(body, "手柄", self._pad_rule_text())

        self.pad_btns = {}

        def add_row(key, label, value):
            r = tk.Frame(box3, bg=theme.PANEL)
            r.pack(fill="x", padx=8, pady=3)
            tk.Label(r, text=label, bg=theme.PANEL, fg=theme.TEXT_DIM,
                     width=8, anchor="w",
                     font=theme.font(theme.F_SMALL)).pack(side="left")
            pb = tk.Button(r, text=value, bg=theme.PANEL_2, fg=theme.TEXT,
                           activebackground=theme.PANEL_3,
                           activeforeground=theme.TEXT, relief="flat", bd=0,
                           highlightthickness=1, highlightbackground=theme.BORDER,
                           cursor="hand2", font=theme.font(theme.F_SMALL),
                           command=lambda k=key: self._bind_pad_key(k))
            pb.pack(side="left", padx=(6, 0), ipady=2, expand=True, fill="x")
            self.pad_btns[key] = pb

        add_row("modifier", "修饰键", self._pad_name(self.s.pad_modifier))
        add_row("combo", "连携技", self._pad_name(self.s.pad_combo))
        for _i in range(4):
            add_row("slot%d" % _i, "槽位 %d" % (_i + 1),
                    self._pad_name(self.s.pad_slot_key(_i)))

        # ---- 终结技触发风格（要跟游戏内设置选的那一种对齐）----
        tk.Frame(box3, bg=theme.BORDER, height=1).pack(fill="x", padx=8, pady=(8, 4))
        row_ult = tk.Frame(box3, bg=theme.PANEL)
        row_ult.pack(fill="x", padx=8)
        tk.Label(row_ult, text="终结技方式", bg=theme.PANEL, fg=theme.TEXT_DIM,
                 width=8, anchor="w",
                 font=theme.font(theme.F_SMALL)).pack(side="left")

        self.ult_var = tk.StringVar(value=self.s.pad_ult_mode)
        for val, label in PAD_ULT_MODES:
            tk.Radiobutton(
                row_ult, text=label, value=val, variable=self.ult_var,
                command=self._on_ult_mode, bg=theme.PANEL, fg=theme.TEXT_DIM,
                selectcolor=theme.PANEL_2, activebackground=theme.PANEL,
                activeforeground=theme.TEXT, relief="flat", bd=0,
                highlightthickness=0, anchor="w",
                font=theme.font(theme.F_SMALL)).pack(side="left", padx=(6, 0))

        self.ult_note = tk.Label(
            box3, text=self._ult_note_text(), bg=theme.PANEL, fg=theme.TEXT_MUTED,
            font=theme.font(theme.F_TINY), anchor="w", justify="left")
        self.ult_note.pack(fill="x", padx=16, pady=(2, 2))

        self.hint = tk.Label(body, text="点按钮后按下对应的键即可重新绑定",
                             bg=theme.BG, fg=theme.TEXT_MUTED,
                             font=theme.font(theme.F_TINY), anchor="w")
        self.hint.pack(fill="x", pady=(6, 0))

        # ---- 底部 ----
        foot = tk.Frame(self.win, bg=theme.BG, padx=20, pady=14)
        foot.pack(fill="x", side="bottom")
        tk.Button(foot, text="完成", command=self.close, bg=theme.ACCENT,
                  fg="#221a06", activebackground=theme.ACCENT_SOFT,
                  activeforeground="#221a06", relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2",
                  font=theme.font(theme.F_BODY, True),
                  padx=20, pady=6).pack(side="right")

        self.win.bind("<Escape>", lambda e: self.close())

    def _card(self, parent, title, sub=None):
        f = tk.Frame(parent, bg=theme.BG)
        f.pack(fill="x", pady=(12, 6))
        tk.Label(f, text=title, bg=theme.BG, fg=theme.TEXT,
                 font=theme.font(theme.F_SECTION, True)).pack(side="left")
        lbl = None
        if sub:
            lbl = tk.Label(f, text=sub, bg=theme.BG, fg=theme.TEXT_MUTED,
                           font=theme.font(theme.F_TINY), justify="left")
            lbl.pack(side="left", padx=(8, 0))
            self._subs[title] = lbl
        box = tk.Frame(parent, bg=theme.PANEL, padx=4, pady=6)
        box.pack(fill="x")
        return box

    # ---------- 文案 ----------
    def _pad_name(self, bit):
        return button_name(bit, self.s.gamepad_scheme) if bit else "未设置"

    def _pad_rule_text(self):
        """手柄卡片的副标题：跟着终结技风格变，别让人对着旧文案配键。"""
        mod = self._pad_name(self.s.pad_modifier)
        combo = self._pad_name(self.s.pad_combo)
        if self.s.pad_ult_mode == PAD_ULT_CHORD:
            return "连携 = %s（单独按）　战技 = %s + 面键　终结 = %s + %s + 面键" % (
                combo, mod, mod, combo)
        return "连携 = %s　战技 = %s + 短按面键　终结 = %s + 长按面键" % (
            combo, mod, mod)

    def _ult_note_text(self):
        if self.s.pad_ult_mode == PAD_ULT_CHORD:
            return ("游戏里若把终结技设成「组合键」，就选这一项。\n"
                    "注意：按住 %s 时按下的 %s 属于终结技组合，不会推进连携。"
                    % (self._pad_name(self.s.pad_modifier),
                       self._pad_name(self.s.pad_combo)))
        return ("游戏里若把终结技设成「长按」，就选这一项。\n"
                "按住 %s 后面键按不满 %dms 算战技，超过算终结技。"
                % (self._pad_name(self.s.pad_modifier), int(self.s.hold_ms)))

    def _refresh_buttons(self):
        for key, pb in self.pad_btns.items():
            if key == "modifier":
                pb.configure(text=self._pad_name(self.s.pad_modifier))
            elif key == "combo":
                pb.configure(text=self._pad_name(self.s.pad_combo))
            elif key.startswith("slot"):
                idx = int(key[4:])
                pb.configure(text=self._pad_name(self.s.pad_slot_key(idx)))

    # ---------- 动作 ----------
    def _on_hold(self):
        try:
            val = int(self.hold_var.get())
        except ValueError:
            return
        self.s.hold_ms = max(80, min(1200, val))
        self.store.save_settings()

    def _bind_pad_key(self, key):
        pb = self.pad_btns.get(key)
        if pb is None:
            return
        pb.configure(text="按下手柄键…", fg=theme.ACCENT)

        def on_pad(bit):
            if key == "modifier":
                self.s.pad_modifier = bit
            elif key == "combo":
                self.s.pad_combo = bit
            elif key.startswith("slot"):
                idx = int(key[4:])
                self.s.pad_slots[idx] = bit
            self.store.save_settings()
            pb.configure(fg=theme.TEXT)
            self._refresh_buttons()

        self.app.begin_pad_bind(on_pad)

    def _on_ult_mode(self):
        self.s.pad_ult_mode = self.ult_var.get()
        self.store.save_settings()
        # 切风格时清掉手柄按住状态，避免新旧规则混用
        rules = getattr(self.app, "pad_rules", None)
        if rules is not None:
            try:
                rules.reset()
            except AttributeError:
                pass
        sub = self._subs.get("手柄")
        if sub is not None:
            sub.configure(text=self._pad_rule_text())
        self.ult_note.configure(text=self._ult_note_text())

    def _on_mode(self):
        self.s.mode = self.mode_var.get()
        self.store.save_settings()

    def _on_focus(self):
        self.s.only_game_focus = bool(self.focus_var.get())
        self.store.save_settings()

    def _on_pad(self):
        self.s.gamepad_enabled = bool(self.pad_var.get())
        self.store.save_settings()
        self.app.set_gamepad_enabled(self.pad_var.get())

    def close(self):
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass
