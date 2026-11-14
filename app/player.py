# -*- coding: utf-8 -*-
"""播放逻辑：编队 = 若干充能轴 → 1 个爆发轴，然后整体重复。

状态机对外只暴露：
    state   idle / running / paused / finished
    current()      当前节点
    current_axis() 当前所在技能轴（悬浮窗据此显示「充能轴 / 爆发轴」）
"""

MATCH = "match"
WRONG = "wrong"
IGNORED = "ignored"
FINISHED = "finished"

IDLE = "idle"

from .model import (KIND_BRANCH, KIND_COMBO, KIND_SKILL, KIND_ULT,  # noqa: E402
                    Node)


class Segment:
    """编队里的一段 = 一条技能轴。"""

    def __init__(self, axis, role, charge_index, charge_total):
        self.axis = axis
        self.role = role
        self.charge_index = charge_index      # 第几个充能轴（1 起），爆发轴为 0
        self.charge_total = charge_total


class Player:
    def __init__(self, rotation=None, store=None, settings=None):
        self.store = store
        self.settings = settings
        self.rotation = rotation
        self.state = IDLE
        self.cycle = 0              # 第几轮
        self.segment = 0            # 当前是第几段
        self.index = 0              # 段内第几个节点
        self.done = set()
        self._segments = []
        self.repeat_done = 0        # 当前这一段已经重复走过几遍（充能轴循环用）
        # 分支：走到分支点后选的路线（None 表示在主线）
        #   {"axis": Axis, "nodes": [...], "index": 0, "merge": bool, "name": str}
        self.route = None
        self.rebuild()

    # ---------- 结构 ----------
    def set_rotation(self, rotation):
        self.rotation = rotation
        self.rebuild()
        self.reset()

    def rebuild(self):
        """把编队展开成 [充能轴..., 爆发轴] 的段列表。"""
        self._segments = []
        if not self.rotation or not self.store:
            return
        charges = [self.store.axis_by_id(a) for a in self.rotation.charge_axes]
        charges = [a for a in charges if a is not None]
        total = len(charges)
        for i, axis in enumerate(charges, 1):
            self._segments.append(Segment(axis, "charge", i, total))
        burst = self.store.axis_by_id(self.rotation.burst_axis)
        if burst is not None:
            self._segments.append(Segment(burst, "burst", 0, total))

    @property
    def segments(self):
        return self._segments

    def current_segment(self):
        if 0 <= self.segment < len(self._segments):
            return self._segments[self.segment]
        return None

    def current_axis(self):
        seg = self.current_segment()
        return seg.axis if seg else None

    # ---------- 生命周期 ----------
    def start(self):
        self.reset()
        if self._segments and any(s.axis.nodes for s in self._segments):
            self.state = "running"
        return self.state

    def pause(self):
        if self.state == "running":
            self.state = "paused"

    def resume(self):
        if self.state == "paused":
            self.state = "running"

    def toggle(self):
        if self.state == "running":
            self.pause()
        elif self.state == "paused":
            self.resume()
        else:
            self.start()

    def reset(self):
        self.state = IDLE
        self.cycle = 0
        self.segment = 0
        self.index = 0
        self.done = set()
        self.repeat_done = 0
        self.route = None
        self._skip_empty()

    def _skip_empty(self):
        """跳过没有节点的段，避免卡住。"""
        guard = 0
        while self.segment < len(self._segments) and not self._segments[self.segment].axis.nodes:
            self.segment += 1
            self.index = 0
            guard += 1
            if guard > 64:
                break

    # ---------- 查询 ----------
    @property
    def total(self):
        axis = self.current_axis()
        return len(axis.nodes) if axis else 0

    def current(self):
        if self.route is not None:
            nodes = self.route["nodes"]
            i = self.route["index"]
            return nodes[i] if 0 <= i < len(nodes) else None
        axis = self.current_axis()
        if not axis or self.index >= len(axis.nodes):
            return None
        return axis.nodes[self.index]

    def upcoming(self):
        if self.route is not None:
            nodes = self.route["nodes"]
            i = self.route["index"] + 1
            return nodes[i] if 0 <= i < len(nodes) else None
        axis = self.current_axis()
        if not axis or self.index + 1 >= len(axis.nodes):
            return None
        return axis.nodes[self.index + 1]

    def nodes_of_segment(self):
        if self.route is not None:
            return list(self.route["nodes"])
        axis = self.current_axis()
        return list(axis.nodes) if axis else []

    def current_axis_obj(self):
        """悬浮窗显示用：在路线里就是那条路线轴。"""
        if self.route is not None:
            return self.route.get("axis")
        return self.current_axis()

    @property
    def cycle_repeat(self):
        """永远无限循环。"""
        return 0

    # ---------- 推进 ----------
    def press(self, vk=None, button=None, hold=False):
        """收到一次输入。

        vk     键盘键码
        button 手柄位掩码
        hold   True 表示这是一次长按（用于终结技）
        """
        if self.state != "running":
            return IGNORED, None
        node = self.current()
        if node is None:
            return FINISHED, None

        # 分支点：等一个「预设键」，按到哪条就走哪条
        if node.kind == KIND_BRANCH:
            opt = self._match_branch(node, vk, button, hold)
            if opt is None:
                return IGNORED, None
            self._start_route(node, opt)
            return MATCH, node

        any_key = getattr(self.settings, "mode", "strict") == "any"
        if any_key or self._matches(node, vk, button, hold):
            self.done.add(self.index)
            self._advance()
            return MATCH, node

        # 按到了本段后面节点的键
        axis = self.current_axis()
        for i in range(self.index + 1, len(axis.nodes)):
            n = axis.nodes[i]
            if self._matches(n, vk, button, hold):
                return WRONG, (node, n, i)

        # 也检查后面几段：按到「更后面的轴」的键同样算顺序错
        for seg in self._segments[self.segment + 1:]:
            for i, n in enumerate(seg.axis.nodes):
                if self._matches(n, vk, button, hold):
                    return WRONG, (node, n, i)
        return IGNORED, None

    def _team_members(self):
        """当前编队的队伍；编队没有队伍时退回全局默认。"""
        if self.rotation is not None and self.rotation.team:
            members = self.rotation.team.normalized()
            if any(members):
                return members
        if self.store is not None:
            return self.store.team.normalized()
        return []

    def _slot_of(self, node):
        """节点干员在队伍里的位置（0 起），找不到返回 None。"""
        try:
            return self._team_members().index(node.operator)
        except (ValueError, AttributeError):
            return None

    def _matches(self, node, vk, button, hold=False):
        s = self.settings
        if not s:
            return False

        if node.kind == KIND_COMBO:
            # 连携：所有干员统一一个键，不分长按
            want = s.combo_key
            if vk is not None and want is not None and vk == want:
                return True
            pad = s.pad_for(KIND_COMBO)
            return button is not None and pad is not None and button == pad

        slot = self._slot_of(node)
        digit = s.slot_key(slot)

        if node.kind == KIND_SKILL:
            # 技能：短按该干员的数字键
            if vk is not None and not hold and digit is not None and vk == digit:
                return True
            pad = s.pad_for(KIND_SKILL)
            return button is not None and pad is not None and button == pad

        if node.kind == KIND_ULT:
            # 终结技：长按该干员的数字键
            if vk is not None and hold and digit is not None and vk == digit:
                return True
            pad = s.pad_for(KIND_ULT)
            return button is not None and pad is not None and button == pad

        return False

    def skip(self):
        if self.state != "running" or self.current() is None:
            return False
        node = self.current()
        if node.kind == KIND_BRANCH and node.options:
            # 跳过分支点：默认走第一条
            self._start_route(node, node.options[0])
            return True
        self.done.add(self.index)
        self._advance()
        return True

    # ---------- 分支 ----------
    def _match_branch(self, node, vk, button, hold):
        """返回第一个命中的分支选项。"""
        for opt in node.options or []:
            op = str(opt.get("operator") or "")
            kind = opt.get("kind") or KIND_SKILL
            if not op:
                continue
            probe = Node(operator=op, kind=kind)
            if self._matches(probe, vk, button, hold):
                return opt
        return None

    def _start_route(self, branch_node, opt):
        """按到某个分支选项：切到它的路线轴。"""
        axis = None
        if self.store is not None:
            axis = self.store.axis_by_id(opt.get("axis") or "")
        self.done.add(self.index)
        nodes = list(axis.nodes) if axis is not None else []
        self.route = {
            "axis": axis,
            "nodes": nodes,
            "index": 0,
            "merge": bool(opt.get("merge", True)),
            "name": axis.name if axis is not None else "空路线",
        }
        self._skip_empty_route()

    def _skip_empty_route(self):
        """路线轴可能没配节点：直接当作走完。"""
        route = self.route
        if route is not None and route["index"] >= len(route["nodes"]):
            self._finish_route()

    def _finish_route(self):
        merge = bool(self.route and self.route.get("merge", True))
        self.route = None
        if merge:
            # 回到分支点后面的那个节点
            self.index += 1
            axis = self.current_axis()
            if axis is not None and self.index < len(axis.nodes):
                return
        # 不汇合，或者主线也走完了：按正常推进处理（进下一段 / 下一轮）
        self._advance_segment(after_route=True)

    def _advance(self):
        # 路线里推进：走完再看要不要汇合
        if self.route is not None:
            self.route["index"] += 1
            if self.route["index"] < len(self.route["nodes"]):
                return
            self._finish_route()
            return

        axis = self.current_axis()
        self.index += 1
        if axis and self.index < len(axis.nodes):
            return

        # 本段走完：充能轴如果设了「走 N 遍」，先原地重来，别急着往后
        if axis is not None and self.current_segment() is not None \
                and self.current_segment().role == "charge":
            try:
                want = int(axis.repeat)
            except (TypeError, ValueError):
                want = 1
            if want > 1 and self.repeat_done + 1 < want:
                self.repeat_done += 1
                self.index = 0
                self.done = set()
                return

        self._advance_segment()

    def _advance_segment(self, after_route=False):
        """本段结束：进下一段，或整轮结束回到第一段。"""
        self.segment += 1
        self.index = 0
        self.done = set()
        self.repeat_done = 0
        if self.segment < len(self._segments):
            self._skip_empty()
            if self.segment < len(self._segments):
                return

        # 一轮走完 -> 无限循环，直接回到第一段
        self.cycle += 1
        self.segment = 0
        self.index = 0
        self.done = set()
        self.repeat_done = 0
        self._skip_empty()
        if self.segment >= len(self._segments):
            self.state = "finished"
