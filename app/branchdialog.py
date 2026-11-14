# -*- coding: utf-8 -*-
"""分支点设置：给每个分支选「触发键 + 走哪条路线轴 + 是否汇合」。

设计上不新画一套编辑界面：路线本身就是普通技能轴（role=route），
在左边栏能像别的轴一样加节点；这里只配「按哪个键走哪条」。
"""
import tkinter as tk

from . import theme
from .model import KIND_CN, KINDS, ROLE_ROUTE
from .widgets import center_window


class BranchDialog:
    def __init__(self, app, node, on_save):
        self.app = app
        self.store = app.store
        self.node = node
        self.on_save = on_save
        # 复制一份，取消就不影响原数据
        self.options = [dict(o) for o in (node.options or [])]
        if not self.options:
            self.options = [self._blank_option()]

        self.win = tk.Toplevel(app.root)
        self.win.title("分支设置")
        self.win.configure(bg=theme.BG)
        self.win.transient(app.root)
        self.win.grab_set()

        self._build()
        center_window(self.win, app.root, 640, 460)

    def _blank_option(self):
        team = self._team()
        axes = self._route_axes()
        return {
            "operator": team[0] if team else "",
            "kind": KINDS[0],
            "axis": axes[0].id if axes else "",
            "merge": True,
        }

    def _team(self):
        rot = self.store.active_rotation()
        members = rot.members() if rot else self.store.team.normalized()
        return [m for m in members if m]

    def _route_axes(self):
        return [a for a in self.store.axes if getattr(a, "role", "") == ROLE_ROUTE]

    # ---------- 界面 ----------
    def _build(self):
        head = tk.Frame(self.win, bg=theme.BG, padx=18, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="分支设置", bg=theme.BG, fg=theme.TEXT,
                 font=theme.font(theme.F_TITLE, True)).pack(side="left")
        tk.Label(head, text="按到哪个键 → 走哪条路线轴", bg=theme.BG,
                 fg=theme.TEXT_MUTED, font=theme.font(theme.F_TINY)).pack(
            side="left", padx=(10, 0))

        body = tk.Frame(self.win, bg=theme.BG, padx=18)
        body.pack(fill="both", expand=True)

        self.rows = tk.Frame(body, bg=theme.PANEL, padx=8, pady=8)
        self.rows.pack(fill="both", expand=True)
        self._render_rows()

        foot = tk.Frame(body, bg=theme.BG)
        foot.pack(fill="x", pady=(8, 0))
        tk.Button(foot, text="＋ 加一条分支", command=self._add_row,
                  bg=theme.PANEL_3, fg=theme.TEXT, relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2",
                  font=theme.font(theme.F_SMALL), padx=12, pady=5).pack(side="left")

        bottom = tk.Frame(self.win, bg=theme.BG, padx=18, pady=14)
        bottom.pack(fill="x", side="bottom")
        tk.Button(bottom, text="保存", command=self.save, bg=theme.ACCENT,
                  fg="#221a06", relief="flat", bd=0, highlightthickness=0,
                  cursor="hand2", font=theme.font(theme.F_BODY, True),
                  padx=20, pady=6).pack(side="right")
        tk.Button(bottom, text="取消", command=self.close, bg=theme.PANEL_3,
                  fg=theme.TEXT, relief="flat", bd=0, highlightthickness=0,
                  cursor="hand2", font=theme.font(theme.F_BODY),
                  padx=16, pady=6).pack(side="right", padx=(0, 8))

        self.win.bind("<Escape>", lambda e: self.close())

    def _render_rows(self):
        for w in self.rows.winfo_children():
            w.destroy()
        self.row_widgets = []
        if not self.options:
            tk.Label(self.rows, text="还没有分支，点下面「＋ 加一条分支」",
                     bg=theme.PANEL, fg=theme.TEXT_MUTED,
                     font=theme.font(theme.F_SMALL)).pack(anchor="w")
            return

        head = tk.Frame(self.rows, bg=theme.PANEL)
        head.pack(fill="x", pady=(0, 4))
        for text, width in (("触发干员", 10), ("种类", 6), ("路线轴", 16),
                            ("走完", 8)):
            tk.Label(head, text=text, bg=theme.PANEL, fg=theme.TEXT_MUTED,
                     font=theme.font(theme.F_TINY), width=width, anchor="w").pack(
                side="left")

        for i, opt in enumerate(self.options):
            row = tk.Frame(self.rows, bg=theme.PANEL)
            row.pack(fill="x", pady=2)

            team = self._team()
            op_var = tk.StringVar(value=opt.get("operator") or (team[0] if team else ""))
            self._menu(row, op_var, team or ["（队伍为空）"], 10,
                       lambda v, o=opt: o.update(operator=v))

            kind_var = tk.StringVar(value=KIND_CN.get(opt.get("kind"), "战技"))
            self._menu(row, kind_var, [KIND_CN[k] for k in KINDS], 6,
                       lambda v, o=opt: o.update(kind=self._kind_of(v)))

            axes = self._route_axes()
            names = [a.name for a in axes] or ["（先建路线轴）"]
            cur = opt.get("axis") or ""
            cur_name = next((a.name for a in axes if a.id == cur), names[0])
            axis_var = tk.StringVar(value=cur_name)
            self._menu(row, axis_var, names, 16,
                       lambda v, o=opt: o.update(axis=self._axis_id(v)))

            merge_var = tk.StringVar(value="汇合" if opt.get("merge", True) else "各走各的")
            self._menu(row, merge_var, ["汇合", "各走各的"], 8,
                       lambda v, o=opt: o.update(merge=(v == "汇合")))

            tk.Button(row, text="删", command=lambda i=i: self._del_row(i),
                      bg=theme.PANEL_3, fg=theme.BAD, relief="flat", bd=0,
                      highlightthickness=0, cursor="hand2",
                      font=theme.font(theme.F_TINY), padx=8).pack(side="left")

    def _menu(self, parent, var, values, width, on_pick):
        m = tk.OptionMenu(parent, var, *values,
                          command=lambda v: (on_pick(v), self._render_rows()))
        m.configure(bg=theme.PANEL_2, fg=theme.TEXT, relief="flat", bd=0,
                    highlightthickness=0, anchor="w",
                    font=theme.font(theme.F_SMALL), width=width)
        m["menu"].configure(bg=theme.PANEL_2, fg=theme.TEXT,
                            font=theme.font(theme.F_SMALL))
        m.pack(side="left", padx=(0, 6))
        return m

    def _kind_of(self, label):
        for k in KINDS:
            if KIND_CN[k] == label:
                return k
        return KINDS[0]

    def _axis_id(self, name):
        for a in self._route_axes():
            if a.name == name:
                return a.id
        return ""

    # ---------- 动作 ----------
    def _add_row(self):
        self.options.append(self._blank_option())
        self._render_rows()

    def _del_row(self, i):
        if 0 <= i < len(self.options):
            self.options.pop(i)
        self._render_rows()

    def save(self):
        clean = []
        for o in self.options:
            op = str(o.get("operator") or "")
            if not op:
                continue
            clean.append({
                "operator": op,
                "kind": o.get("kind") if o.get("kind") in KINDS else KINDS[0],
                "axis": str(o.get("axis") or ""),
                "merge": bool(o.get("merge", True)),
            })
        self.on_save(clean)
        self.close()

    def close(self):
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass
