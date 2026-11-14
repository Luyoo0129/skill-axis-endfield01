# -*- coding: utf-8 -*-
"""纯逻辑自测，不打开任何窗口。"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.model import (Axis, KIND_COMBO, KIND_SKILL, KIND_ULT,  # noqa: E402
                       Node, ROLE_BURST, ROLE_CHARGE, Rotation, Settings,
                       Store, Team)
from app.player import FINISHED, MATCH, WRONG, Player  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


class FakeStore:
    def __init__(self, axes):
        self.axes = axes
        self.team = Team()

    def axis_by_id(self, axis_id):
        for a in self.axes:
            if a.id == axis_id:
                return a
        return None


def mk_axis(role, name, kinds):
    axis = Axis(name=name, role=role)
    axis.nodes = [Node(operator="干员%d" % i, kind=k) for i, k in enumerate(kinds, 1)]
    return axis


def mk_player(charge_kinds=((KIND_SKILL,), (KIND_COMBO,)),
              burst_kinds=(KIND_ULT,), team=("佩丽卡", "管理员", "陈千语", "余烬")):
    charges = [mk_axis(ROLE_CHARGE, "充能%d" % i, ks)
               for i, ks in enumerate(charge_kinds, 1)]
    burst = mk_axis(ROLE_BURST, "爆发", burst_kinds)
    rot = Rotation(name="测试编队", charge_axes=[c.id for c in charges],
                   burst_axis=burst.id)
    axes = charges + [burst]
    s = Settings()
    store = FakeStore(axes)
    store.team = Team(members=list(team))
    p = Player(rotation=rot, store=store, settings=s)
    # 让每个节点的干员都落在队伍里
    for axis in axes:
        for i, n in enumerate(axis.nodes):
            n.operator = team[i % len(team)]
    return p, rot, axes, s


# ---------- 结构 ----------
def test_segment_order():
    p, rot, axes, _s = mk_player()
    check("编队段数 = 充能2 + 爆发1", len(p.segments) == 3)
    check("段顺序：充能在前、爆发在后",
          [s.role for s in p.segments] == ["charge", "charge", "burst"])
    check("充能轴带序号", p.segments[0].charge_index == 1
          and p.segments[1].charge_index == 2)


def test_play_through():
    p, rot, axes, s = mk_player()
    p.start()
    check("开始时在第 1 个充能轴",
          p.current_segment().role == "charge"
          and p.current_segment().charge_index == 1)
    check("当前节点是技能类", p.current().kind == KIND_SKILL)

    node = p.current()
    slot = p.store.team.normalized().index(node.operator)
    p.press(vk=s.slot_key(slot), hold=False)
    check("充能1 打完进入充能2", p.current_segment().charge_index == 2)

    p.press(vk=s.combo_key)
    check("充能2 打完进入爆发轴", p.current_segment().role == "burst")

    node = p.current()
    slot = p.store.team.normalized().index(node.operator)
    p.press(vk=s.slot_key(slot), hold=True)
    check("一轮打完继续循环（不结束）", p.state == "running")
    check("回到第 1 个充能轴", p.current_segment().charge_index == 1)
    check("轮次 +1", p.cycle == 1)


def test_slot_mapping():
    """数字键按队伍顺序绑定。"""
    p, rot, axes, s = mk_player(charge_kinds=((KIND_SKILL, KIND_SKILL),),
                                team=("佩丽卡", "管理员"))
    p.start()
    n0 = p.current()
    slot0 = p.store.team.normalized().index(n0.operator)
    check("第 1 位对应键 1", s.slot_key(slot0) == 0x31)
    p.press(vk=0x32)          # 按第 2 位的键 -> 顺序错
    check("按错位次的键不推进", p.index == 0)
    p.press(vk=0x31)
    check("按对位次的键推进", p.index == 1)


def test_combo_key():
    """连携统一用 E，和干员无关。"""
    p, rot, axes, s = mk_player(charge_kinds=((KIND_COMBO,),))
    p.start()
    check("连携默认键是 E", s.combo_key == 0x45)
    r, _ = p.press(vk=0x45)
    check("按 E 触发连携", r == MATCH)


def test_ult_requires_hold():
    """终结技必须长按，短按不算。"""
    p, rot, axes, s = mk_player(charge_kinds=((KIND_ULT,),),
                                team=("佩丽卡",))
    p.start()
    slot = p.store.team.normalized().index(p.current().operator)
    digit = s.slot_key(slot)
    r1, _ = p.press(vk=digit, hold=False)
    check("短按不触发终结技", r1 != MATCH)
    r2, _ = p.press(vk=digit, hold=True)
    check("长按触发终结技", r2 == MATCH)


def test_hold_threshold_setting():
    s = Settings()
    check("默认长按阈值 280ms", s.hold_ms == 280)
    s2 = Settings.from_dict({"hold_ms": 500})
    check("阈值可持久化", s2.hold_ms == 500)


def test_hotdata_dirty_flow():
    """保存 / 放弃 的流程。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = os.path.join(base, "data", "_selftest_tmp5")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    store = Store(tmp)
    store.defer_save = True

    axis = store.add_axis(ROLE_CHARGE, "草稿技能轴")
    check("改动后标记为脏", store.dirty is True)

    store2 = Store(tmp)
    check("未保存时磁盘里没有草稿技能轴",
          not any(a.name == "草稿技能轴" for a in store2.axes))

    store.commit()
    store3 = Store(tmp)
    check("保存后磁盘里有草稿技能轴",
          any(a.name == "草稿技能轴" for a in store3.axes))
    check("保存后不再是脏", store.dirty is False)

    store.add_axis(ROLE_CHARGE, "丢弃技能轴")
    store.revert()
    check("放弃后回到磁盘状态",
          not any(a.name == "丢弃技能轴" for a in store.axes))
    check("放弃后不是脏", store.dirty is False)
    shutil.rmtree(tmp, ignore_errors=True)


def test_per_rotation_team():
    """每个编队有自己的队伍。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = os.path.join(base, "data", "_selftest_tmp6")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    store = Store(tmp)
    rot = store.active_rotation()
    rot.team = Team(members=["佩丽卡", "管理员", "陈千语", "余烬"])
    r2 = store.add_rotation("第二个编队")
    check("新建编队继承当前队伍", r2.members() == rot.members())

    r2.team = Team(members=["伊冯", "别礼", "卡缪", "大潘"])
    store.commit()

    store2 = Store(tmp)
    a = store2.rotation_by_id(rot.id)
    b = store2.rotation_by_id(r2.id)
    check("编队队伍各自持久化",
          a.members()[0] == "佩丽卡" and b.members()[0] == "伊冯")

    check("rotation_team 取对应编队的队伍",
          store2.rotation_team(b).normalized()[0] == "伊冯")
    shutil.rmtree(tmp, ignore_errors=True)


def test_rotation_team_affects_keys():
    """不同编队同一干员的位置不同，按键也不同。"""
    p, rot, axes, s = mk_player(charge_kinds=((KIND_SKILL,),),
                                team=("佩丽卡", "管理员"))
    p.start()
    node = p.current()
    check("队伍第 1 位是佩丽卡", node.operator == "佩丽卡")
    check("佩丽卡技能对应键 1", s.slot_key(0) == 0x31)

    # 换一支队伍，佩丽卡排到第 3 位
    rot.team = Team(members=["余烬", "管理员", "佩丽卡", "陈千语"])
    p.rebuild()
    p.start()
    check("换了队伍后仍在技能节点", p.current().kind == KIND_SKILL)
    check("佩丽卡现在对应键 3", s.slot_key(2) == 0x33)
    r, _ = p.press(vk=0x31)
    check("按 1 不再触发（她已不在第1位）", r != MATCH)
    r2, _ = p.press(vk=0x33)
    check("按 3 触发", r2 == MATCH)


def test_rename_rotation():
    store = Store.__new__(Store)
    r = Rotation(name="旧名字")
    r.name = "新名字"
    check("编队可以改名", r.name == "新名字")
    check("改名后持久化字段正确", r.to_dict()["name"] == "新名字")


def test_infinite():
    p, rot, axes, s = mk_player()
    p.start()
    for _ in range(5):
        node = p.current()
        slot = p.store.team.normalized().index(node.operator)
        p.press(vk=s.slot_key(slot))
        p.press(vk=s.combo_key)
        node = p.current()
        slot = p.store.team.normalized().index(node.operator)
        p.press(vk=s.slot_key(slot), hold=True)
    check("永远不结束", p.state == "running")
    check("轮次累计 5", p.cycle == 5)


def test_wrong_key():
    p, rot, axes, s = mk_player()
    p.start()
    n = p.current()
    slot = p.store.team.normalized().index(n.operator)
    digit = s.slot_key(slot)
    r, _ = p.press(vk=digit, hold=True)   # 当前是技能，长按是终结技的写法
    check("技能节点遇到长按不推进", r != MATCH)
    check("不推进时仍在原位", p.index == 0)


def test_key_map():
    p, rot, axes, s = mk_player()
    s.combo_key = 0x51          # 改成 Q
    p.start()
    p.press(vk=0x31)            # 技能推进
    r1, _ = p.press(vk=0x45)    # 旧 E 不再有效
    check("改键后旧连携键无效", r1 != MATCH)
    r2, _ = p.press(vk=0x51)
    check("改键后新连携键有效", r2 == MATCH)


def test_any_mode():
    p, rot, axes, s = mk_player()
    s.mode = "any"
    p.start()
    r, _ = p.press(vk=0x99)
    check("任意键模式推进", r == MATCH and p.current_segment().charge_index == 2)


def test_gamepad():
    p, rot, axes, s = mk_player()
    p.start()
    bit = s.pad_for(KIND_SKILL)
    r, _ = p.press(button=bit)
    check("手柄按键能匹配", r == MATCH)


def test_pad_ult_modes():
    """终结技两种风格：LB+长按面键 / LB+RB+面键。"""
    from app.padrules import PadRules

    def mk(mode):
        s = Settings()
        s.pad_ult_mode = mode
        return s, PadRules(s)

    # ---- 风格一：LB + 长按面键 ----
    s, r = mk("hold")
    LB, RB, X = s.pad_modifier, s.pad_combo, s.pad_slot_key(0)
    check("默认终结技风格是长按", Settings().pad_ult_mode == "hold")
    check("单独按面键不算施放", r.handle("down", X, 0.0) is None)
    check("没按 LB 松开也不触发", r.handle("up", X, 0.05) is None)

    r = PadRules(s)
    r.handle("down", LB, 0.0)
    r.handle("down", X, 0.01)
    a = r.handle("up", X, 0.06)
    check("风格一：LB+短按面键 = 战技", a == ("press", 0x31, False), repr(a))

    r = PadRules(s)
    r.handle("down", LB, 0.0)
    r.handle("down", X, 0.02)
    a = r.handle("up", X, 0.42)
    check("风格一：LB+长按面键 = 终结技", a == ("press", 0x31, True), repr(a))

    r = PadRules(s)
    r.handle("down", LB, 0.0)
    a = r.handle("down", RB, 0.02)
    check("风格一：不按 LB 单按 RB 是连携", a == ("press", 0x45, False), repr(a))

    # ---- 风格二：LB + RB + 面键 ----
    s2, r2 = mk("chord")
    check("终结技风格二可读回", r2.mode() == "chord")
    check("风格二：单独 RB 仍算连携",
          PadRules(s2).handle("down", RB, 0.0) == ("press", 0x45, False))

    r2 = PadRules(s2)
    r2.handle("down", LB, 0.0)
    a = r2.handle("down", RB, 0.02)
    check("风格二：按住 LB 时 RB 不抢连携", a is None, repr(a))
    a = r2.handle("down", X, 0.05)
    check("风格二：LB+RB+面键 = 终结技", a == ("press", 0x31, True), repr(a))
    check("风格二：松开面键不重复触发", r2.handle("up", X, 0.30) is None)
    check("风格二：松开 RB 不误触连携", r2.handle("up", RB, 0.34) is None)

    r3 = PadRules(s2)
    r3.handle("down", LB, 0.0)
    r3.handle("down", X, 0.02)
    a = r3.handle("up", X, 0.60)
    check("风格二：光长按不放只算战技", a == ("press", 0x31, False), repr(a))

    # 切风格后残留的按住状态要清掉
    r4 = PadRules(s2)
    r4.handle("down", LB, 0.0)
    r4.reset()
    check("reset 清掉按住状态", not r4.held and r4.handle("up", X, 0.2) is None)

    # ---- 持久化 ----
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "_selftest_tmp5")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir, exist_ok=True)
    store = Store(tmp_dir)
    store.settings.pad_ult_mode = "chord"
    store.save_settings()
    store2 = Store(tmp_dir)
    check("终结技风格持久化", store2.settings.pad_ult_mode == "chord")
    check("旧设置缺字段时默认长按",
          Settings.from_dict({"hold_ms": 300}).pad_ult_mode == "hold")
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_team_unique():
    """队伍不允许重复：已经在队里的干员再放进来 -> 两个位置互换。"""
    from app.model import Team, assign_member

    base = ["佩丽卡", "管理员", "陈千语", "余烬"]

    moved = assign_member(base, 3, "佩丽卡")
    check("重复加入变成互换", moved == ["余烬", "管理员", "陈千语", "佩丽卡"], repr(moved))
    check("互换后仍然 4 人且不重复",
          len(moved) == 4 and len(set(moved)) == 4)

    replaced = assign_member(base, 1, "新干员")
    check("换成队伍外的人直接替换",
          replaced == ["佩丽卡", "新干员", "陈千语", "余烬"], repr(replaced))

    to_empty = assign_member(["佩丽卡", "", "", ""], 2, "佩丽卡")
    check("拖到空位 = 移动（原位置清空）", to_empty == ["", "", "佩丽卡", ""],
          repr(to_empty))

    cleared = assign_member(base, 2, "")
    check("清空某个位置", cleared == ["佩丽卡", "管理员", "", "余烬"], repr(cleared))

    bad = assign_member(base, 9, "佩丽卡")
    check("越界索引不改动", bad == base, repr(bad))

    # 旧存档里已经重复的：显示时只保留第一次出现，后面清空
    dedup = Team(members=["佩丽卡", "管理员", "佩丽卡", "余烬"]).normalized()
    check("重复存档自动去重", dedup == ["佩丽卡", "管理员", "", "余烬"], repr(dedup))
    check("去重后长度仍是 4", len(dedup) == 4)


def test_move_item():
    """拖拽换序的统一语义：插入式整体挪位（不是两两互换）。"""
    from app.model import move_item

    base = ["A", "B", "C", "D"]
    check("拖到后面：整体前移", move_item(base, 0, 3) == ["B", "C", "A", "D"],
          repr(move_item(base, 0, 3)))
    check("拖到最前：整体后移", move_item(base, 3, 0) == ["D", "A", "B", "C"],
          repr(move_item(base, 3, 0)))
    check("拖到自己原位不变", move_item(base, 1, 1) == base, repr(move_item(base, 1, 1)))
    check("往后挪一格", move_item(base, 1, 3) == ["A", "C", "B", "D"],
          repr(move_item(base, 1, 3)))
    check("挪到末尾之后的缝", move_item(base, 0, 4) == ["B", "C", "D", "A"],
          repr(move_item(base, 0, 4)))
    check("越界索引原样返回", move_item(base, 9, 1) == base)
    check("元素数量不变", len(move_item(base, 2, 0)) == 4)


def test_skip():
    p, rot, axes, s = mk_player(charge_kinds=((KIND_SKILL, KIND_ULT),))
    p.start()
    ok = p.skip()
    check("跳过节点", ok and p.index == 1)


def test_empty_segment_skipped():
    charges = [mk_axis(ROLE_CHARGE, "空充能", ())]
    burst = mk_axis(ROLE_BURST, "爆发", (KIND_SKILL,))
    rot = Rotation(name="t", charge_axes=[charges[0].id], burst_axis=burst.id)
    p = Player(rotation=rot, store=FakeStore(charges + [burst]),
               settings=Settings())
    p.start()
    check("跳过没有节点的段", p.current_segment().role == "burst")


# ---------- 存储 ----------
def test_store_roundtrip():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = os.path.join(base, "data", "_selftest_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    store = Store(tmp)
    check("首次载入生成示例数据",
          len(store.axes) == 3 and len(store.rotations) == 1)

    axis = store.add_axis(ROLE_CHARGE, "我的充能")
    axis.nodes = [Node(operator="佩丽卡", kind=KIND_ULT, icon="佩丽卡_终结.png")]
    store.save_axes()

    store2 = Store(tmp)
    found = [a for a in store2.axes if a.name == "我的充能"]
    check("技能轴持久化", len(found) == 1)
    if found:
        check("节点 kind 持久化", found[0].nodes[0].kind == KIND_ULT)
        check("技能轴类型持久化", found[0].role == ROLE_CHARGE)

    rot = store2.active_rotation()
    check("编队持久化", rot is not None and len(rot.charge_axes) == 2)

    store2.team = Team(members=["A", "B", "C", "D"])
    store2.save_team()
    store3 = Store(tmp)
    check("队伍持久化", store3.team.normalized() == ["A", "B", "C", "D"])


def test_settings_keys():
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "_selftest_tmp4")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir, exist_ok=True)
    store = Store(tmp_dir)
    s = store.settings
    check("默认连携键是 E", s.combo_key == 0x45)
    check("默认长按阈值 280", s.hold_ms == 280)
    s.combo_key = 0x51
    s.hold_ms = 400
    s.pad[KIND_ULT] = 0x1000
    store.save_settings()
    store2 = Store(tmp_dir)
    check("连携键持久化", store2.settings.combo_key == 0x51)
    check("长按阈值持久化", store2.settings.hold_ms == 400)
    check("手柄映射持久化", store2.settings.pad_for(KIND_ULT) == 0x1000)
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_export_import():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = os.path.join(base, "data", "_selftest_tmp2")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    store = Store(tmp)
    data = store.export_dict()
    check("导出包含 axes/rotations/team/settings",
          all(k in data for k in ("axes", "rotations", "team", "settings")))

    tmp2 = os.path.join(base, "data", "_selftest_tmp3")
    shutil.rmtree(tmp2, ignore_errors=True)
    os.makedirs(tmp2, exist_ok=True)
    store2 = Store(tmp2)
    before = len(store2.axes)
    ok, msg = store2.import_dict(data, merge=True)
    check("导入成功", ok, msg)
    check("追加模式技能轴数增加", len(store2.axes) > before)
    ok_bad, _ = store2.import_dict({"foo": 1})
    check("非法文件被拒绝", not ok_bad)
    shutil.rmtree(tmp2, ignore_errors=True)


def test_legacy_migration():
    axis = Axis.from_dict({
        "id": "old1", "name": "旧技能轴", "kind": "loop",
        "nodes": [{"operator": "佩丽卡", "icon": "佩丽卡_连携.png",
                   "vk": 0x31, "note": "旧备注"}],
    })
    check("旧数据可解析", axis.nodes[0].operator == "佩丽卡")
    check("旧图标推断出连携类型", axis.nodes[0].kind == KIND_COMBO)
    check("旧技能轴默认按爆发处理", axis.role == ROLE_BURST)


# ---------- 资源 ----------
def test_assets():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons = os.path.join(base, "data", "icons")
    portraits = os.path.join(base, "data", "portraits")
    n_icons = len([f for f in os.listdir(icons) if f.endswith(".png")]) \
        if os.path.isdir(icons) else 0
    n_portraits = len([f for f in os.listdir(portraits) if f.endswith(".png")]) \
        if os.path.isdir(portraits) else 0
    check("技能图标库存在", n_icons >= 100, "共 %d 张" % n_icons)
    check("干员立绘存在", n_portraits >= 30, "共 %d 张" % n_portraits)


def test_render():
    try:
        from app.iconart import compose, compose_combo, compose_portrait
    except Exception as exc:  # noqa: BLE001
        check("图标合成模块可导入", False, repr(exc))
        return
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    glyph = os.path.join(base, "data", "icons", "佩丽卡_技能.png")
    portrait = os.path.join(base, "data", "portraits", "佩丽卡.png")
    if not os.path.isfile(glyph):
        check("图标合成：素材存在", False)
        return
    for kind in ("skill", "ult"):
        im = compose(glyph, 96, "Electric", kind)
        check("合成 %s 正常" % kind, im.size == (96, 96) and im.mode == "RGBA")
    if os.path.isfile(portrait):
        im = compose_combo(portrait, glyph, 96, "Electric")
        check("合成连携图标正常", im.size == (96, 96) and im.mode == "RGBA")
        im2 = compose_portrait(portrait, 96, "Electric")
        check("合成纯头像正常", im2.size == (96, 96) and im2.mode == "RGBA")


def test_fonts():
    try:
        from app import fonts
    except Exception as exc:  # noqa: BLE001
        check("字体模块可导入", False, repr(exc))
        return
    check("字体模块有 fit 截断函数", callable(getattr(fonts, "fit", None)))
    check("字体模块有 wrap 折行函数", callable(getattr(fonts, "wrap", None)))


def main():
    for fn in (test_segment_order, test_play_through, test_slot_mapping,
               test_combo_key, test_ult_requires_hold, test_hold_threshold_setting,
               test_infinite, test_wrong_key, test_key_map, test_any_mode,
               test_gamepad, test_pad_ult_modes, test_team_unique, test_move_item, test_skip, test_empty_segment_skipped,
               test_hotdata_dirty_flow, test_per_rotation_team,
               test_rotation_team_affects_keys, test_rename_rotation,
               test_store_roundtrip, test_settings_keys, test_export_import,
               test_legacy_migration, test_assets, test_render, test_fonts):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__ + " 未抛异常", False, repr(exc))

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for d in ("_selftest_tmp", "_selftest_tmp2", "_selftest_tmp3",
              "_selftest_tmp4", "_selftest_tmp5", "_selftest_tmp6"):
        shutil.rmtree(os.path.join(base, "data", d), ignore_errors=True)

    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + name + ("   %s" % detail if detail else ""))
    print("-" * 60)
    print("共 %d 项，失败 %d 项" % (len(results), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
