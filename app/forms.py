# -*- coding: utf-8 -*-
"""多段 / 多形态技能的元数据：按「名称」区分。

游戏里有干员的技能分两段（同一颗键按两次），或者有两种形态。
用户要求**用名字区分**，不要 ①/② 序号，所以这里存的是名字：

    "祀": {"skill": ["战技·第一段", "战技·第二段"]}

数组顺序 = 段号（1 起）。按键判定不受影响（仍只看 干员+种类），
名字只用于技能栏/时间轴的显示，让你一眼知道现在排的是哪一段。

数据在 data/forms.json；没登记的干员一律按单段处理。
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
        return {}, {}
    cached = _CACHE.get(path)
    if cached and cached[0] == stamp:
        return cached[1], cached[2]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f) or {}
    except (OSError, ValueError):
        data = {}
    names = data.get("names") or {}
    legacy = data.get("stages") or {}
    _CACHE[path] = (stamp, names, legacy)
    return names, legacy


def names(cn, kind):
    """该技能各段的显示名（顺序即段号）。"""
    if not cn:
        return []
    table, _legacy = _load()
    per = table.get(cn) or {}
    items = per.get(kind) or []
    return [str(x) for x in items if x]


def stages(cn, kind):
    """段数（1 表示单段）。以名字表为准，兼容旧的 stages 计数。"""
    if not cn:
        return 1
    table, legacy = _load()
    named = len(names(cn, kind))
    per = legacy.get(cn) or {}
    try:
        old = int(per.get(kind, 1))
    except (TypeError, ValueError):
        old = 1
    return max(1, min(9, max(named, old)))


def label_for(cn, kind, stage=1, fallback=""):
    """第 stage 段的显示名；没有登记就用 fallback。"""
    items = names(cn, kind)
    if not items:
        return fallback
    try:
        i = int(stage) - 1
    except (TypeError, ValueError):
        i = 0
    if 0 <= i < len(items):
        return items[i]
    return items[0]


def stage_of_name(cn, kind, label):
    """给定时显示名反查段号（找不到返回 1）。"""
    items = names(cn, kind)
    for i, s in enumerate(items, 1):
        if s == label:
            return i
    return 1


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
    """没登记名字时的兜底序号（①②③…）。"""
    marks = "①②③④⑤⑥⑦⑧⑨"
    try:
        i = int(stage) - 1
    except (TypeError, ValueError):
        i = 0
    return marks[i] if 0 <= i < len(marks) else str(stage)
