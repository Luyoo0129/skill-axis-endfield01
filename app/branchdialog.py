# -*- coding: utf-8 -*-
"""分支点编辑：可嵌进主界面时间轴下方（不再开弹窗）。

设计要点（用户 2026-11-14 定）：
- 分支点仍是一个菱形节点；**单击就地在时间轴下方展开设置**
- 每条分支一行：触发干员 / 种类 → 路线轴 → 汇合方式，右侧可删
- 路线内容不在面板里编辑，只显示「名字 + 节点数」和「编辑路线」按钮，
  点它就切到那条路线轴继续排（路线轴本身是普通轴，左边栏能编辑）
- 改动即时保存（没有「保存」按钮），收起靠「收起」或点时间轴空白处
"""
import tkinter as tk

from . import theme
from .model import KIND_CN, KINDS, ROLE_ROUTE, ROLE_ROUTE as _ROUTE
from .textdialog import ask_text


class BranchEditor:
    """把分支设置画进 parent 这个 Frame 里。"""

    def __init__(self, parent, app, node, on_change):
        self.parent = parent
        self.app = app
        self.store = app.store
        self.node = node
        self.on_change = on_change
        if not node.options:
            node.options = [self._blank_option()]

    # ---------- 数据 ----------
    def _team(self):
        rot = self.store.active_rotation()
        members = rot.members() if rot else self.store.team.normalized()
        return [m for m in members if m]

    def _route_axes(self):
        return [a for a in self.store.axes if getattr(a, "role", "") == ROLE_ROUTE]

    def _blank_option(self):
        team = self._team()
        axes = self._route_axes()
        return {
            "operator": team[0] if team else "",
            "kind": KINDS[0],
            "axis": axes[0].id if axes else "",
            "merge": True,
        }

    def options(self):
        return self.node.options or []

    # ---------- 界面 ----------
    def build(self):
        for w in self.parent.winfo_children():
            w.destroy()

        head = tk.Frame(self.parent, bg=theme.PANEL)
        head.pack(fill="x")
        tk.Label(head, text="分支点设置", bg=theme.PANEL, fg=theme.ACCENT,
                 font=theme.font(theme.F_SECTION, True)).pack(side="left")
        tk.Label(head, text="按到哪个键 → 走哪条路线", bg=theme.PANEL,
                 fg=theme.TEXT_MUTED, font=theme.font(theme.F_TINY)).pack(
            side="left", padx=(8, 0))
        tk.Button(head, text="＋ 添加分支", command=self._add,
                  bg=theme.PANEL_3, fg=theme.CYAN, relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2",
                  font=theme.font(theme.F_TINY), padx=10, pady=3).pack(side="right",
                                                                     padx=(6, 0))
        tk.Button(head, text="收起", command=self._collapse,
                  bg=theme.PANEL_3, fg=theme.TEXT_DIM, relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2",
                  font=theme.font(theme.F_TINY), padx=10, pady=3).pack(side="right")

        if not self.options():
            tk.Label(self.parent, text="还没有分支，点「＋ 添加分支」",
                     bg=theme.PANEL, fg=theme.TEXT_MUTED,
                     font=theme.font(theme.F_SMALL), anchor="w").pack(
                fill="x", pady=6)
            return

        cols = tk.Frame(self.parent, bg=theme.PANEL)
        cols.pack(fill="x", pady=(6, 2))
        for label, width in (("触发干员", 9), ("种类", 5), ("路线轴", 14),
                             ("走完", 8), ("路线内容", 16)):
            tk.Label(cols, text=label, bg=theme.PANEL, fg=theme.TEXT_MUTED,
                     font=theme.font(theme.F_TINY), width=width,
                     anchor="w").pack(side="left")

        for i, opt in enumerate(self.options()):
            self._row(i, opt)

    def _row(self, i, opt):
        row = tk.Frame(self.parent, bg=theme.PANEL_2)
        row.pack(fill="x", pady=1)

        team = self._team()
        op = opt.get("operator") or (team[0] if team else "")
        opt["operator"] = op
        self._menu(row, op, team or ["（队伍为空）"], 9,
                   lambda v, o=opt: o.update(operator=v))

        kind_cn = KIND_CN.get(opt.get("kind"), "战技")
        self._menu(row, kind_cn, [KIND_CN[k] for k in KINDS], 5,
                   lambda v, o=opt: o.update(kind=self._kind_of(v)))

        axes = self._route_axes()
        names = [a.name for a in axes] or ["（先建路线轴）"]
        cur = opt.get("axis") or ""
        cur_name = next((a.name for a in axes if a.id == cur), names[0])
        self._menu(row, cur_name, names, 14,
                   lambda v, o=opt: o.update(axis=self._axis_id(v)))

        merge_cn = "汇合" if opt.get("merge", True) else "各走各的"
        self._menu(row, merge_cn, ["汇合", "各走各的"], 8,
                   lambda v, o=opt: o.update(merge=(v == "汇合")))

        # 路线内容：名字 + 节点数（只读预览）
        target = self._axis_by_id(opt.get("axis") or "")
        if target is None:
            summary = "未选路线"
        else:
            summary = "%d 个节点" % len(target.nodes)
        tk.Label(row, text=summary, bg=theme.PANEL_2, fg=theme.TEXT_MUTED,
                 font=theme.font(theme.F_TINY), width=12, anchor="w").pack(
            side="left")
        tk.Button(row, text="编辑路线", command=lambda a=target: self._goto(a),
                  bg=theme.PANEL_3, fg=theme.CYAN, relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2",
                  font=theme.font(theme.F_TINY), padx=6, pady=1).pack(
            side="left", padx=(2, 4))
        tk.Button(row, text="×", command=lambda i=i: self._del(i),
                  bg=theme.PANEL_3, fg=theme.BAD, relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2",
                  font=theme.font(theme.F_TINY), padx=6, pady=1).pack(side="left")

    def _menu(self, parent, value, values, width, on_pick):
        var = tk.StringVar(value=value)
        m = tk.OptionMenu(parent, var, *values,
                          command=lambda v: (on_pick(v), self._changed()))
        m.configure(bg=theme.PANEL_2, fg=theme.TEXT, relief="flat", bd=0,
                    highlightthickness=0, anchor="w",
                    font=theme.font(theme.F_TINY), width=width)
        m["menu"].configure(bg=theme.PANEL_2, fg=theme.TEXT,
                            font=theme.font(theme.F_TINY))
        m.pack(side="left", padx=(0, 4))
        return m

    def _kind_of(self, label):
        for k in KINDS:
            if KIND_CN[k] == label:
                return k
        return KINDS[0]

    def _axis_by_id(self, axis_id):
        for a in self._route_axes():
            if a.id == axis_id:
                return a
        return None

    def _axis_id(self, name):
        for a in self._route_axes():
            if a.name == name:
                return a.id
        return ""

    # ---------- 动作 ----------
    def _changed(self):
        try:
            self.on_change()
        except Exception:  # noqa: BLE001
            pass
        self.build()

    def _add(self):
        self.options().append(self._blank_option())
        self._changed()

    def _del(self, i):
        opts = self.options()
        if 0 <= i < len(opts):
            opts.pop(i)
        self._changed()

    def _goto(self, axis):
        if axis is not None:
            self.app.editor.select_axis(axis.id)

    def _collapse(self):
        self.app.editor.close_branch_panel()

    def new_route_axis(self):
        """在面板里直接建一条路线轴，命名走「路线 · N」。"""
        axis = self.store.add_axis(_ROUTE)
        self.app.editor.refresh_order()
        return axis
