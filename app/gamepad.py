# -*- coding: utf-8 -*-
"""手柄支持（XInput）+ 按键名称。

手柄按键不是键盘按键，低级键盘钩子抓不到，所以单开一个轮询线程。
轮询只读，不改游戏内存、不注入。
"""
import ctypes
import threading
import time

# XInput 按键位掩码
BUTTONS = {
    0x0001: ("dpad_up", "方向键上", "方向键上"),
    0x0002: ("dpad_down", "方向键下", "方向键下"),
    0x0004: ("dpad_left", "方向键左", "方向键左"),
    0x0008: ("dpad_right", "方向键右", "方向键右"),
    0x0010: ("start", "Start", "Options"),
    0x0020: ("back", "Back", "Share"),
    0x0040: ("ls", "L3", "L3"),
    0x0080: ("rs", "R3", "R3"),
    0x0100: ("lb", "LB", "L1"),
    0x0200: ("rb", "RB", "R1"),
    0x1000: ("a", "A", "×"),
    0x2000: ("b", "B", "○"),
    0x4000: ("x", "X", "□"),
    0x8000: ("y", "Y", "△"),
}

# 扳机键是模拟量，自造两个高位标记
TRIGGER_LT = 0x10000
TRIGGER_RT = 0x20000
TRIGGER_NAMES = {
    TRIGGER_LT: ("lt", "LT", "L2"),
    TRIGGER_RT: ("rt", "RT", "R2"),
}

TRIGGER_THRESHOLD = 110


def button_name(bit, scheme="xbox"):
    """返回手柄按键的显示名。"""
    idx = 2 if scheme == "ps" else 1
    if bit in TRIGGER_NAMES:
        return TRIGGER_NAMES[bit][idx]
    info = BUTTONS.get(bit)
    return info[idx] if info else "手柄键"


def all_buttons(scheme="xbox"):
    """[(bit, 显示名), ...]，给设置界面列出来。"""
    items = [(b, button_name(b, scheme)) for b in BUTTONS]
    items += [(b, button_name(b, scheme)) for b in TRIGGER_NAMES]
    return items


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_ulong),
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [("dwState", _XINPUT_STATE)]


def _load_xinput():
    for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            return ctypes.WinDLL(name)
        except OSError:
            continue
    return None


class GamepadListener:
    """轮询手柄状态，边沿触发放进队列。

    用法与 KeyListener 一致：start() / stop()，事件从 queue 取。
    """

    INTERVAL = 0.016   # 约 60Hz

    def __init__(self, queue, slot=0):
        self.queue = queue
        self.slot = slot
        self.xinput = _load_xinput()
        self.available = self.xinput is not None
        self.connected = False
        self.enabled = True
        self._stop = threading.Event()
        self._thread = None
        self._last = 0
        self.last_error = ""

    # ---------- 查询 ----------
    def _read(self):
        state = _XINPUT_GAMEPAD()
        try:
            rc = self.xinput.XInputGetState(ctypes.c_ulong(self.slot),
                                            ctypes.byref(state))
        except Exception as e:  # pragma: no cover
            self.last_error = str(e)
            return None
        if rc != 0:
            return None
        s = state.dwState
        bits = int(s.wButtons)
        if s.bLeftTrigger > TRIGGER_THRESHOLD:
            bits |= TRIGGER_LT
        if s.bRightTrigger > TRIGGER_THRESHOLD:
            bits |= TRIGGER_RT
        return bits

    def scan(self):
        """返回当前按住的所有按键位（用于设置界面实时显示）。"""
        if not self.xinput:
            return None
        return self._read()

    def connected_now(self):
        return self._read() is not None

    # ---------- 线程 ----------
    def start(self):
        if not self.available or self._thread is not None:
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="gamepad-listener")
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        self._thread = None

    def _run(self):
        while not self._stop.is_set():
            if self.enabled:
                bits = self._read()
                if bits is None:
                    if self.connected:
                        self.connected = False
                        self.queue.put(("gamepad", "disconnected", 0))
                else:
                    if not self.connected:
                        self.connected = True
                        self.queue.put(("gamepad", "connected", self.slot))
                    changed = bits ^ self._last
                    if changed:
                        for bit in BUTTONS:
                            if changed & bit:
                                pressed = bool(bits & bit)
                                self.queue.put(("pad", "down" if pressed else "up", bit))
                        for bit in (TRIGGER_LT, TRIGGER_RT):
                            if changed & bit:
                                pressed = bool(bits & bit)
                                self.queue.put(("pad", "down" if pressed else "up", bit))
                        self._last = bits
                    # 松开全部时清零，避免残留
                    if bits == 0:
                        self._last = 0
            time.sleep(self.INTERVAL)
