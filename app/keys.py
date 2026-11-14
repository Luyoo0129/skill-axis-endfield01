# -*- coding: utf-8 -*-
"""虚拟键码 -> 显示名称的映射。"""

MOUSE_BASE = 0x1000

VK_NAMES = {
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x13: "Pause",
    0x14: "CapsLock", 0x1B: "Esc", 0x20: "Space", 0x21: "PgUp", 0x22: "PgDn",
    0x23: "End", 0x24: "Home", 0x25: "←", 0x26: "↑", 0x27: "→", 0x28: "↓",
    0x2C: "PrintScreen", 0x2D: "Insert", 0x2E: "Delete",
    0x5B: "Win", 0x5C: "Win", 0x5D: "Menu",
    0x90: "NumLock", 0x91: "ScrollLock",
    0x6A: "Num*", 0x6B: "Num+", 0x6D: "Num-", 0x6E: "Num.", 0x6F: "Num/",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/",
    0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}

for _d in range(10):
    VK_NAMES[0x30 + _d] = str(_d)
    VK_NAMES[0x60 + _d] = f"Num{_d}"

for _c in range(26):
    VK_NAMES[0x41 + _c] = chr(0x41 + _c)

for _f in range(24):
    VK_NAMES[0x70 + _f] = f"F{_f + 1}"

MOUSE_NAMES = {1: "鼠标左键", 2: "鼠标右键", 3: "鼠标中键", 4: "侧键1", 5: "侧键2"}

# 绑定时按住这些键不算（避免把 Ctrl/Shift 单独绑上）
MODIFIER_VKS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C}


def vk_label(vk):
    """返回按键的可读名称。"""
    if vk is None:
        return "未绑定"
    if vk >= MOUSE_BASE:
        return MOUSE_NAMES.get(vk - MOUSE_BASE, f"鼠标{vk - MOUSE_BASE}")
    return VK_NAMES.get(vk, f"VK{vk:02X}")


def is_mouse(vk):
    return vk is not None and vk >= MOUSE_BASE
