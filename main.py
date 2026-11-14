# -*- coding: utf-8 -*-
"""大祥老师的终末地助手 入口。

用法：
    python main.py              正常启动
    python main.py --selftest   只跑逻辑自测，不开窗口
    python main.py --smoke      构建界面后自动关闭，用于快速验证
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

if getattr(sys, "frozen", False):
    # 打包后：把 exe 所在目录也加进来，方便读取外置 data/
    _exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if _exe_dir not in sys.path:
        sys.path.insert(0, _exe_dir)


def _maybe_elevate():
    """打包运行时，如果不是管理员就尝试提权重启。

    游戏通常以管理员运行，而 Windows 的 UIPI 会挡住低权限进程的键盘钩子，
    表现就是「桌面上能按键，切到游戏就完全没反应」。
    """
    if not getattr(sys, "frozen", False):
        return False
    if "--no-elevate" in sys.argv:
        return False
    try:
        from app import paths
        from app.elevation import is_admin, relaunch_as_admin
        from app.model import Store
        store = Store(paths.base_dir())
        if not getattr(store.settings, "auto_elevate", True):
            return False
        if is_admin():
            return False
        return relaunch_as_admin()
    except Exception:
        return False


def main():
    if "--selftest" in sys.argv:
        from app.selftest import main as selftest_main
        raise SystemExit(selftest_main())

    if "--smoke" in sys.argv:
        from app.application import Application
        app = Application()
        app.root.after(900, app.on_close)
        app.root.mainloop()
        print("SMOKE_OK")
        return

    if _maybe_elevate():
        return          # 已发起提权，当前进程退出

    from app.application import run
    run()


if __name__ == "__main__":
    main()
