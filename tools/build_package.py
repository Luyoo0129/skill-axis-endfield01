# -*- coding: utf-8 -*-
"""打包成免安装 exe（onedir + 外置 data/）。

用法：
    python tools/build_package.py
产出：
    dist/大祥老师的终末地助手/    —— 直接压缩发人
"""
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBS = os.path.join(BASE, "_buildtmp", "libs")
DIST = os.path.join(BASE, "dist")
APP_NAME = "大祥老师的终末地助手"
OUT_DIR = os.path.join(DIST, APP_NAME)

sys.path.insert(0, LIBS)


def main():
    if not os.path.isdir(LIBS):
        print("缺少 PyInstaller，请先运行 _fetch_pyinstaller.py")
        return 1

    # 先确认目标目录没被占用：程序正开着时 PyInstaller 会删掉旧目录再失败，
    # 留下一个残缺的 dist（用户下次就启动不了）。
    if os.path.isdir(OUT_DIR):
        probe = os.path.join(OUT_DIR, APP_NAME + ".exe")
        try:
            if os.path.isfile(probe):
                with open(probe, "ab"):
                    pass
        except OSError:
            print("目标 exe 正被占用（程序还开着？）——先退出程序再打包。")
            return 2

    env = dict(os.environ)
    env["PYTHONPATH"] = LIBS + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--windowed",
        "--name", APP_NAME,
        "--icon", os.path.join(BASE, "assets", "app_icon.ico"),
        "--distpath", DIST,
        "--workpath", os.path.join(BASE, "_buildtmp", "work"),
        "--specpath", os.path.join(BASE, "_buildtmp"),
        # Pillow 的 Tk 支持
        "--hidden-import", "PIL._tkinter_finder",
        # 本项目不需要这些，排掉能小一半体积
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "pytest",
        "--exclude-module", "IPython",
        "--exclude-module", "setuptools",
        "--exclude-module", "pip",
        os.path.join(BASE, "main.py"),
    ]
    print("执行:", " ".join(cmd))
    rc = subprocess.call(cmd, env=env, cwd=BASE)
    if rc != 0:
        print("打包失败，返回码", rc)
        return rc

    # onedir 产物在 dist/大祥老师的终末地助手/大祥老师的终末地助手.exe
    exe = os.path.join(OUT_DIR, APP_NAME + ".exe")
    if not os.path.exists(exe):
        # PyInstaller 6 会把内容再套一层
        alt = os.path.join(OUT_DIR, "main.exe")
        if os.path.exists(alt):
            exe = alt
    print("exe:", exe, "exists:", os.path.exists(exe))

    # 把 data/、assets/（软件图标）和说明拷到 exe 旁边
    for name in ("data", "assets"):
        src = os.path.join(BASE, name)
        dst = os.path.join(OUT_DIR, name)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print("拷贝", name)

    for name in ("使用说明.md", "启动说明.txt"):
        src = os.path.join(BASE, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(OUT_DIR, name))
            print("拷贝", name)

    # 清掉打包测试残留
    for junk in ("_selftest_tmp", "_selftest_tmp2", "_selftest_tmp3",
                 "_selftest_tmp4", "_selftest_tmp5", "_selftest_tmp6"):
        p = os.path.join(OUT_DIR, "data", junk)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)

    print("\n完成：", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
