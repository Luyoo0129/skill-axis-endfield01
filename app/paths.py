# -*- coding: utf-8 -*-
"""路径工具：打包成 exe 后仍能找到程序目录。

开发时：项目根目录
打包后：exe 所在目录（data/ 就放在 exe 旁边，用户可以直接看到和备份）
"""
import os
import sys


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def base_dir():
    """程序根目录（data/、使用说明.md 等所在处）。"""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_dir():
    """只读资源目录（PyInstaller 解包目录），没有则退回 base_dir。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and os.path.isdir(meipass):
        return meipass
    return base_dir()
