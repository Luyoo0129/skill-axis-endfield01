# -*- coding: utf-8 -*-
"""手柄组合键判定（纯逻辑：不碰 Tk、不碰 XInput、时间由调用方传入）。

游戏内「终结技」有两种触发风格，玩家在游戏设置里选一种，所以这边必须跟着切：

    hold （默认）  LB + X/Y/A/B，长按 = 终结技，短按 = 战技
    chord         LB + RB + X/Y/A/B = 终结技，不用长按

两种风格唯一的冲突点是 RB：chord 风格里 RB 是终结技组合的一半，
所以「已经按住 LB 时按下的 RB」不能算连携，否则 LB+RB+X 会先推进一个连携节点。
单独按 RB（没按 LB）在两种风格下都还是连携技。

判定结果统一成 ("press", 数字键, 是否长按)，交给 Application 转给播放器，
这样键盘和手柄仍然共用同一套推进逻辑。
"""
from .model import PAD_ULT_CHORD, PAD_ULT_HOLD


class PadRules:
    """把「LB / RB / 面键」的按下松开序列翻译成一次按键意图。"""

    def __init__(self, settings):
        self.settings = settings
        self.held = set()      # 当前按住的手柄键位
        self._arm = {}         # 面键位 -> {start, chord, fired}

    # ---------- 状态 ----------
    def reset(self):
        """丢手柄、切设置时清干净，避免残留按住状态。"""
        self.held.clear()
        self._arm.clear()

    def mode(self):
        m = getattr(self.settings, "pad_ult_mode", PAD_ULT_HOLD)
        return m if m in (PAD_ULT_HOLD, PAD_ULT_CHORD) else PAD_ULT_HOLD

    def _modifier(self):
        try:
            return int(self.settings.pad_modifier or 0)
        except (TypeError, ValueError):
            return 0

    def _combo(self):
        try:
            return int(self.settings.pad_combo or 0)
        except (TypeError, ValueError):
            return 0

    # ---------- 主入口 ----------
    def handle(self, phase, bit, now):
        """喂一个手柄事件，返回 None 或 ("press", vk, hold)。"""
        mod = self._modifier()
        combo = self._combo()
        chord_mode = self.mode() == PAD_ULT_CHORD

        if phase == "down":
            self.held.add(bit)

            # 连携技：RB 单独按才算
            if bit == combo:
                if chord_mode and mod and mod != combo and mod in self.held:
                    return None          # LB+RB 是终结技的前半段
                vk = int(self.settings.combo_key or 0)
                return ("press", vk, False) if vk else None

            slot = self.settings.pad_slot_of(bit)
            if slot is None:
                return None

            if mod and mod not in self.held:
                # 没按住 LB，面键单独按不算施放
                self._arm.pop(bit, None)
                return None

            chord = bool(chord_mode and combo and combo != bit and combo in self.held)
            self._arm[bit] = {"start": now, "chord": chord}
            if chord:
                # 组合风格：按下当场就是终结技，不等松开
                self._arm[bit]["fired"] = True
                return self._digit(slot, True)
            return None

        # ---------- 松开 ----------
        self.held.discard(bit)
        armed = self._arm.pop(bit, None)
        if armed is None:
            return None

        slot = self.settings.pad_slot_of(bit)
        if slot is None:
            return None
        if armed.get("fired"):
            return None                  # 按下时已经算过终结技，别重复触发
        if chord_mode:
            # 组合风格没有长按说法：没凑成 LB+RB 就是战技
            return self._digit(slot, False)

        elapsed = (now - armed["start"]) * 1000.0
        hold = elapsed >= float(self.settings.hold_ms or 280)
        return self._digit(slot, hold)

    # ---------- 小工具 ----------
    def _digit(self, slot, hold):
        vk = self.settings.slot_key(slot)
        return ("press", vk, bool(hold)) if vk else None
