# -*- coding: utf-8 -*-
"""多段技能（同一颗键分几段按）的元数据。

游戏里有干员的技能是「两段」的：按下同一个键先出第一段，再按一次出第二段。
比如「祀 · 战技」是两段，「诀 · 终结」是两段。它们共用同一颗键，
所以轴里要放两个节点（第 1 段、第 2 段），按键判定不变。

段数从 data/forms.json 读；没有登记的干员一律按 1 段处理。
"""
import json
import os

from . import paths

_CACHE = {}


def forms_path():
    return os.path.join(paths.base_dir(), "data", "forms.json")


def _load():
    path = forms_path()
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return {}
    cached = _CACHE.get(path)
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f) or {}
    except (OSError, ValueError):
        data = {}
    table = data.get("stages") or {}
    _CACHE[path] = (stamp, table)
    return table


def stages(cn, kind):
    """这位干员这个技能分几段（1 表示普通单段）。"""
    if not cn:
        return 1
    per = _load().get(cn) or {}
    try:
        n = int(per.get(kind, 1))
    except (TypeError, ValueError):
        return 1
    return max(1, min(9, n))


def stage_counts(cn):
    """{kind: 段数}，只列段数大于 1 的。"""
    out = {}
    for kind in ("skill", "combo", "ult"):
        n = stages(cn, kind)
        if n > 1:
            out[kind] = n
    return out


def has_multi(cn):
    return bool(stage_counts(cn))


def stage_suffix(stage):
    """① ② ③ … 供界面标段号。"""
    marks = "①②③④⑤⑥⑦⑧⑨"
    try:
        i = int(stage) - 1
    except (TypeError, ValueError):
        i = 0
    return marks[i] if 0 <= i < len(marks) else str(stage)
