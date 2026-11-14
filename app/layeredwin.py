# -*- coding: utf-8 -*-
"""把一张 RGBA 图按「逐像素 alpha」贴到窗口上（UpdateLayeredWindow）。

相比 Tk 的 -transparentcolor（整色抠除），逐像素 alpha 的好处：
    文字抗锯齿边缘可以和背后正常混合，不会留下一圈不透明灰边。
"""
import ctypes
import ctypes.wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
DIB_RGB_COLORS = 0


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte),
                ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte),
                ("AlphaFormat", ctypes.c_ubyte)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


user32.GetParent.restype = ctypes.c_void_p
user32.GetParent.argtypes = [ctypes.c_void_p]
user32.GetDC.restype = ctypes.c_void_p
user32.GetDC.argtypes = [ctypes.c_void_p]
user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.RECT)]
user32.UpdateLayeredWindow.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wt.POINT),
    ctypes.POINTER(wt.SIZE), ctypes.c_void_p, ctypes.POINTER(wt.POINT),
    wt.DWORD, ctypes.POINTER(BLENDFUNCTION), wt.DWORD]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.CreateDIBSection.restype = ctypes.c_void_p
gdi32.CreateDIBSection.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wt.UINT,
    ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wt.DWORD]
gdi32.SelectObject.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]


def hwnd_of(widget):
    """Tk 控件 -> 真正的顶层窗口句柄。"""
    try:
        wid = widget.winfo_id()
        parent = user32.GetParent(ctypes.c_void_p(wid))
        return parent or wid
    except Exception:
        return None


def set_layered(widget, layered=True, click_through=False):
    """给窗口加/去 WS_EX_LAYERED 与 WS_EX_TRANSPARENT。"""
    hwnd = hwnd_of(widget)
    if not hwnd:
        return
    try:
        style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
        if layered:
            style |= WS_EX_LAYERED
        if click_through:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, style)
    except Exception:
        pass


def blit(widget, image):
    """把 PIL RGBA 图贴到窗口上（位置保持不变）。"""
    hwnd = hwnd_of(widget)
    if not hwnd:
        return False
    try:
        w, h = image.size
        data = image.tobytes("raw", "BGRA")

        screen_dc = user32.GetDC(None)
        mem_dc = gdi32.CreateCompatibleDC(ctypes.c_void_p(screen_dc))
        if not mem_dc:
            return False

        bi = BITMAPINFO()
        bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.bmiHeader.biWidth = w
        bi.bmiHeader.biHeight = -h          # 负数 = 自上而下
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        bi.bmiHeader.biCompression = 0      # BI_RGB

        ppv = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(
            ctypes.c_void_p(mem_dc), ctypes.byref(bi), DIB_RGB_COLORS,
            ctypes.byref(ppv), None, 0)
        if not hbmp or not ppv:
            gdi32.DeleteDC(ctypes.c_void_p(mem_dc))
            user32.ReleaseDC(None, ctypes.c_void_p(screen_dc))
            return False

        old = gdi32.SelectObject(ctypes.c_void_p(mem_dc), ctypes.c_void_p(hbmp))
        ctypes.memmove(ppv, data, len(data))

        rect = wt.RECT()
        user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
        pt_dst = wt.POINT(rect.left, rect.top)
        size = wt.SIZE(w, h)
        pt_src = wt.POINT(0, 0)
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

        ok = user32.UpdateLayeredWindow(
            ctypes.c_void_p(hwnd), ctypes.c_void_p(screen_dc),
            ctypes.byref(pt_dst), ctypes.byref(size),
            ctypes.c_void_p(mem_dc), ctypes.byref(pt_src),
            0, ctypes.byref(blend), ULW_ALPHA)

        gdi32.SelectObject(ctypes.c_void_p(mem_dc), ctypes.c_void_p(old))
        gdi32.DeleteObject(ctypes.c_void_p(hbmp))
        gdi32.DeleteDC(ctypes.c_void_p(mem_dc))
        user32.ReleaseDC(None, ctypes.c_void_p(screen_dc))
        return bool(ok)
    except Exception:
        return False
