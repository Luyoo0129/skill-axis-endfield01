# -*- coding: utf-8 -*-
"""权限检测：判断本程序是否以管理员运行。

为什么重要：
    游戏（尤其带反作弊的）通常以管理员权限启动。
    Windows 的 UIPI 会挡住低权限进程的键盘钩子 ——
    于是「桌面上能听到按键，切到游戏就完全收不到」。
"""
import ctypes
import ctypes.wintypes as wt

shell32 = ctypes.WinDLL("shell32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

TOKEN_QUERY = 0x0008
TokenElevation = 20


def is_admin():
    """True = 当前进程已提权。"""
    try:
        # 简单可靠的判定
        return bool(shell32.IsUserAnAdmin())
    except Exception:
        pass
    try:
        token = wt.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                         TOKEN_QUERY, ctypes.byref(token)):
            return False
        try:
            elevation = wt.DWORD()
            size = wt.DWORD()
            if advapi32.GetTokenInformation(token, TokenElevation,
                                            ctypes.byref(elevation),
                                            ctypes.sizeof(elevation),
                                            ctypes.byref(size)):
                return bool(elevation.value)
        finally:
            kernel32.CloseHandle(token)
    except Exception:
        pass
    return False


def relaunch_as_admin():
    """以管理员身份重新启动自己（会弹 UAC）。返回是否成功发起。"""
    import os
    import subprocess
    import sys

    try:
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = " ".join(sys.argv[1:])
        else:
            exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            params = '"%s" %s' % (script, " ".join(sys.argv[1:]))
        # ShellExecuteW 的 runas 动词最稳，不依赖 PowerShell
        ret = shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return int(ret) > 32
    except Exception:
        return False
