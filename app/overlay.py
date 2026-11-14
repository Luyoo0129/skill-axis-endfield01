# -*- coding: utf-8 -*-
"""悬浮窗：长条流水线形态。

要点：
    · 图标全部等大，横向一条排队
    · 当前技能用「只包住图标的描边框」标记，不压下面的键位文字
    · 已按过的只变暗，不画对勾
    · 窗口宽度 = 技能数量决定（自适应），高度按等比例
    · 整窗等比缩放：拖边框/四角，保持长宽比

渲染方式：Pillow 合成 RGBA → UpdateLayeredWindow 逐像素贴图，
底色 alpha 跟透明度走，文字/图标恒为不透明。
"""
import ctypes
import time
import tkinter as tk

from PIL import Image, ImageDraw

from . import fonts, layeredwin, theme
from .gamepad import button_name
from .keys import vk_label
from .model import KIND_COMBO, KIND_ULT

# 基准尺寸（scale = 1.0 时）
B_ICON = 44
B_GAP = 6
B_PAD = 14
B_HEADER = 32
B_HEIGHT = 136

MIN_SCALE = 0.6
MAX_SCALE = 2.2
SS = 2                      # 超采样

EDGE = 8                    # 边框拖拽感应宽度
MIN_W = 430                 # 顶栏需要的最小宽度，太窄会挤坏布局


def _rgb(hexcolor):
    hexcolor = hexcolor.lstrip("#")
    return tuple(int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))


def _rgba(hexcolor, alpha):
    r, g, b = _rgb(hexcolor)
    return (r, g, b, max(0, min(255, int(round(alpha)))))


class Overlay:
    def __init__(self, app):
        self.app = app
        s = app.store.settings

        self.scale = float(getattr(s, "overlay_scale", 1.0) or 1.0)
        self.scale = max(MIN_SCALE, min(MAX_SCALE, self.scale))
        self.opacity = float(s.opacity) or 0.95
        self._pulse_on = False
        self._hint = ""
        self._hint_until = 0
        self._branch_hint_id = None
        self._drag = None
        self._resize = None
        self._opacity_drag = False
        self._img = None
        self._W = 0
        self._H = 0

        x, y = int(s.overlay_x), int(s.overlay_y)
        sw = app.root.winfo_screenwidth()
        sh = app.root.winfo_screenheight()
        if (x, y) in ((120, 120), (0, 0)):
            x = max(20, (sw - 900) // 2)
            y = max(20, sh - 260)
        self._x, self._y = x, y

        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=theme.BG)
        self.win.geometry("+%d+%d" % (x, y))

        self.win.bind("<Button-1>", self._press)
        self.win.bind("<B1-Motion>", self._motion)
        self.win.bind("<ButtonRelease-1>", self._release)
        self.win.bind("<Motion>", self._hover)
        self.win.bind("<Escape>", lambda e: app.hide_overlay())

        self.redraw()
        self._tick()
        for d in (40, 120, 300):
            try:
                self.win.after(d, self.redraw)
            except tk.TclError:
                pass

    # ---------- 尺寸 ----------
    def _metrics(self):
        ic = max(16, int(round(B_ICON * self.scale)))
        gap = max(2, int(round(B_GAP * self.scale)))
        pad = max(6, int(round(B_PAD * self.scale)))
        head = max(18, int(round(B_HEADER * self.scale)))
        height = max(60, int(round(B_HEIGHT * self.scale)))
        return ic, gap, pad, head, height

    def _nodes(self):
        p = self.app.player
        nodes = p.nodes_of_segment()
        if nodes:
            return nodes
        for seg in p.segments:
            if seg.axis.nodes:
                return list(seg.axis.nodes)
        return []

    def _node_width(self, node, ic, gap):
        """节点占多宽：普通节点一格；分支格按分支数并排（图标大小不变）。"""
        if getattr(node, "kind", "") == "branch":
            n = len(self._branch_trigger_items(node))
            if n <= 0:
                return ic
            n = min(12, n)
            g = max(2, gap // 2)
            return n * ic + (n - 1) * g
        return ic

    def _fit_window(self, widths, idx, ic, gap, pad, max_w):
        """从当前节点往两边扩，尽量多显示，返回 (start, visible)。"""
        n = len(widths)
        if n == 0:
            return 0, 0
        idx = max(0, min(idx, n - 1))
        lo = hi = idx
        width = widths[idx]
        while True:
            grew = False
            if hi + 1 < n and pad * 2 + width + gap + widths[hi + 1] <= max_w:
                hi += 1
                width += gap + widths[hi]
                grew = True
            if lo - 1 >= 0 and pad * 2 + width + gap + widths[lo - 1] <= max_w:
                lo -= 1
                width += gap + widths[lo]
                grew = True
            if not grew:
                break
        return lo, hi - lo + 1

    def _layout(self):
        """算出窗口尺寸、可见区间、每个节点的宽度。"""
        ic, gap, pad, head, height = self._metrics()
        nodes = self._nodes()
        n = max(1, len(nodes))
        widths = [self._node_width(nd, ic, gap) for nd in nodes] or [ic]
        max_w = int(self.win.winfo_screenwidth() * 0.92)
        min_w = max(MIN_W, int(round(MIN_W * self.scale)))

        p = self.app.player
        idx = max(0, min(p.index, len(widths) - 1))
        start, visible = self._fit_window(widths, idx, ic, gap, pad, max_w)
        content_w = pad * 2 + sum(widths[start:start + visible]) + \
            gap * max(0, visible - 1)
        W = max(min_w, min(content_w, max_w))
        return W, height, head, ic, gap, pad, nodes, visible, start, widths

    def _min_width(self):
        return max(MIN_W, int(round(MIN_W * self.scale)))

    # ---------- 透明度 / 显隐 ----------
    def set_opacity(self, value, persist=True):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self.opacity = max(0.25, min(1.0, value))
        if persist:
            s = self.app.store.settings
            s.opacity = self.opacity
            try:
                self.app.persist_settings()
            except Exception:
                pass
        self._safe_redraw()

    def set_scale(self, value, persist=True):
        self.scale = max(MIN_SCALE, min(MAX_SCALE, float(value)))
        if persist:
            s = self.app.store.settings
            s.overlay_scale = self.scale
            try:
                self.app.persist_settings()
            except Exception:
                pass
        self._safe_redraw()

    def _safe_redraw(self):
        try:
            self.redraw()
        except tk.TclError:
            pass

    def show(self):
        try:
            self.win.deiconify()
            self.win.lift()
        except tk.TclError:
            pass
        self.redraw()
        for d in (40, 120):
            try:
                self.win.after(d, self.redraw)
            except tk.TclError:
                pass

    def hide(self):
        try:
            self.win.withdraw()
        except tk.TclError:
            pass

    def visible(self):
        try:
            return bool(self.win.winfo_exists()) and bool(self.win.winfo_viewable())
        except tk.TclError:
            return False

    def exists(self):
        try:
            return bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def set_click_through(self, enabled):
        layeredwin.set_layered(self.win, layered=True, click_through=enabled)

    def show_hint(self, text):
        self._hint = text
        self._hint_until = time.time() + 2.0
        self.redraw()

    def _tick(self):
        self._pulse_on = not self._pulse_on
        try:
            self.win.after(520, self._tick)
        except tk.TclError:
            return
        if self.app.player.state == "running":
            self.redraw()

    # ---------- 数据 ----------
    def team_members(self):
        rot = self.app.player.rotation or self.app.store.active_rotation()
        if rot is not None:
            return rot.members()
        return self.app.store.team.normalized()

    def _maybe_branch_hint(self):
        """走到分支点：顶部闪一行「按 X 走 A / 按 Y 走 B」，同一次停留只提示一次。"""
        try:
            node = self.app.player.current()
        except Exception:  # noqa: BLE001
            return
        is_branch = getattr(node, "kind", "") == "branch"
        if not is_branch:
            self._branch_hint_id = None
            return
        if node.id == self._branch_hint_id:
            return
        text = self._branch_hint_text(node)
        self._branch_hint_id = node.id
        if text:
            self._hint = text
            self._hint_until = time.time() + 2.6

    def _branch_trigger_items(self, node):
        """分支的触发项：[(图标文件, 键位文字, 干员, 种类中文)]，按选项顺序。"""
        from .model import KIND_CN, option_trigger

        out = []
        for opt in (getattr(node, "options", None) or []):
            trig = option_trigger(opt)
            op = str(trig.get("operator") or "")
            kind = trig.get("kind") or "skill"
            if not op:
                continue
            icon = self.app.icons.icon_for(op, kind, trig.get("stage") or 1) or ""
            out.append((icon, self._trigger_key(op, kind),
                        op, KIND_CN.get(kind, "战技"), kind))
        return out

    def _trigger_key(self, operator, kind):
        s = self.app.store.settings
        if self._use_pad():
            if kind == "combo":
                return button_name(s.pad_combo, s.gamepad_scheme)
            try:
                slot = self.team_members().index(operator)
            except ValueError:
                return "?"
            letter = button_name(s.pad_slot_key(slot), s.gamepad_scheme) or "?"
            if kind == "ult":
                if getattr(s, "pad_ult_mode", "hold") == "chord":
                    return "%s+%s" % (button_name(s.pad_combo, s.gamepad_scheme),
                                      letter)
                return "长" + letter
            return letter
        if kind == "combo":
            return vk_label(s.combo_key) if s.combo_key else "E"
        try:
            slot = self.team_members().index(operator)
        except ValueError:
            return "?"
        digit = s.slot_key(slot)
        if digit is None:
            return "?"
        label = vk_label(digit)
        return ("长" + label) if kind == "ult" else label

    def _draw_branch_cell(self, d, node, x, icon_cy, ic, width, cur, past,
                          key_y):
        """分支格：所有触发技能并排（图标大小和普通节点一致），下面各标键位。"""
        items = self._branch_trigger_items(node)[:12]
        if not items:
            k = ic * 0.38
            cx = x + width / 2
            self._shape(d, (cx - k, icon_cy - k, cx + k, icon_cy + k),
                        r=4 * self._sc, fill=theme.PANEL_3,
                        outline=theme.ACCENT, width=2)
            return

        n = len(items)
        g = max(2, int(3 * self._sc))
        col = (theme.ACCENT if cur
               else (theme.TEXT_MUTED if past else theme.TEXT_DIM))
        # 顶部小字「分支」（画在图标上方的一小条里，不压图标）
        self._text(d, x + 1, icon_cy - ic / 2 - 9 * self._sc, "分支",
                   theme.F_TINY, col, anchor="lm", bold=cur)
        for i, item in enumerate(items):
            icon_file = item[0]
            cx = x + ic / 2 + i * (ic + g)
            im = (self.app.icons.render_pil(icon_file, int(ic * SS))
                  if icon_file else None)
            if im is not None and past:
                im = im.copy()
                r, gg, b, a = im.split()
                a = a.point(lambda v: int(v * 0.35))
                im = Image.merge("RGBA", (r, gg, b, a))
            self._paste(im, cx, icon_cy)
            self._text(d, cx, key_y, item[1], theme.F_TINY, col,
                       anchor="mm", bold=cur, max_w=ic + g - 1)
        # 琥珀底栏，标明这是一组「选路」
        self._shape(d, (x, icon_cy + ic / 2 + 3 * self._sc,
                        x + width, icon_cy + ic / 2 + 3 * self._sc +
                        max(1, 2 * self._sc)),
                    r=1 * self._sc, fill=theme.ACCENT if cur else theme.ACCENT_SOFT)

    def _branch_hint_text(self, node):
        """分支成为当前节点时顶部闪的那行提醒。"""
        items = self._branch_trigger_items(node)
        if not items:
            return ""
        parts = []
        for item in items:
            _icon, key, op, kind_cn = item[0], item[1], item[2], item[3]
            kind = item[4] if len(item) > 4 else "skill"
            verb = "长按 %s" % key[-1] if kind == "ult" else "按 %s" % key
            parts.append("%s 走 %s·%s" % (verb, op, kind_cn))
        return "选路：" + " / ".join(parts)

    def _branch_keys(self, node):
        """分支点下面那行：把每条分支的触发键压成「1/E」这种。"""
        s = self.app.store.settings
        out = []
        for opt in (getattr(node, "options", None) or []):
            kind = opt.get("kind")
            if kind == KIND_COMBO:
                out.append(vk_label(s.combo_key) if s.combo_key else "E")
                continue
            try:
                slot = self.team_members().index(str(opt.get("operator") or ""))
            except ValueError:
                continue
            digit = s.slot_key(slot)
            label = vk_label(digit) if digit is not None else "?"
            out.append(("长" + label) if kind == KIND_ULT else label)
        return "/".join(out) if out else "选路"

    def _use_pad(self):
        """现在是否该按手柄显示：启用手柄监听 + 确实连上了。"""
        try:
            return (bool(self.app.store.settings.gamepad_enabled)
                    and bool(self.app.pad_connected))
        except AttributeError:
            return False

    def key_hint(self, node):
        """这颗节点在悬浮窗下面显示的按键：连了手柄显手柄键，否则显键盘键。"""
        s = self.app.store.settings
        if getattr(node, "kind", "") == "branch":
            return "选路"
        if self._use_pad():
            if node.kind == KIND_COMBO:
                return button_name(s.pad_combo, s.gamepad_scheme)
            try:
                slot = self.team_members().index(node.operator)
            except ValueError:
                return "?"
            letter = button_name(s.pad_slot_key(slot), s.gamepad_scheme)
            if not letter:
                return "?"
            if node.kind == KIND_ULT:
                if getattr(s, "pad_ult_mode", "hold") == "chord":
                    return "%s+%s" % (button_name(s.pad_combo, s.gamepad_scheme),
                                      letter)
                return "长" + letter
            return letter
        if node.kind == KIND_COMBO:
            return vk_label(s.combo_key) if s.combo_key else "—"
        try:
            slot = self.team_members().index(node.operator)
        except ValueError:
            return "?"
        digit = s.slot_key(slot)
        if digit is None:
            return "?"
        label = vk_label(digit)
        return ("长按" + label) if node.kind == KIND_ULT else label

    def _status_text(self, nodes):
        """底部状态行：先警告，其次手柄连接状态。"""
        warn = self._warn_text(nodes)
        if warn:
            return warn, theme.WARN
        try:
            s = self.app.store.settings
        except AttributeError:
            return "", theme.TEXT_MUTED
        if s.gamepad_enabled:
            if self.app.pad_connected:
                return "手柄：已连接（按键按手柄显示）", theme.TEXT_MUTED
            return "手柄：未连接（当前按键按键盘显示）", theme.WARN
        return "", theme.TEXT_MUTED

    def notify_pad(self, connected):
        """手柄连上/断开时闪一行提醒。"""
        if connected:
            self.show_hint("手柄已连接，按键已切换为手柄")
        else:
            self.show_hint("手柄已断开，按键切回键盘")
        self._safe_redraw()

    def _warn_text(self, nodes):
        """给出「为什么按了没反应」的可见提示。"""
        p = self.app.player
        if not nodes:
            return "这条技能轴还没有技能"
        if p.state in ("idle",):
            return "按 F7 开始提示（当前未启动）"
        team = self.team_members()
        missing = []
        for n in nodes:
            if n.operator and n.operator not in team and n.operator not in missing:
                missing.append(n.operator)
        if missing:
            return "这些干员不在当前编队里：%s" % "、".join(missing[:3])
        return ""

    # ---------- 命中区 ----------
    def _zone(self, x, y):
        """返回拖拽区：move / n / s / e / w / ne / nw / se / sw。"""
        W, H = self._W, self._H
        if W <= 0 or H <= 0:
            return "move"
        left, right = x <= EDGE, x >= W - EDGE
        top, bottom = y <= EDGE, y >= H - EDGE
        if top and left:
            return "nw"
        if top and right:
            return "ne"
        if bottom and left:
            return "sw"
        if bottom and right:
            return "se"
        if top:
            return "n"
        if bottom:
            return "s"
        if left:
            return "w"
        if right:
            return "e"
        return "move"

    _CURSORS = {"n": "sb_v_double_arrow", "s": "sb_v_double_arrow",
                "e": "sb_h_double_arrow", "w": "sb_h_double_arrow",
                "ne": "size_ne_sw", "sw": "size_ne_sw",
                "nw": "size_nw_se", "se": "size_nw_se",
                "move": "fleur"}

    def _hover(self, e):
        if self.app.store.settings.click_through:
            return
        z = self._zone(e.x, e.y)
        try:
            self.win.configure(cursor=self._CURSORS.get(z, "arrow"))
        except tk.TclError:
            pass

    def _in_close(self, x, y):
        m = max(4, int(round(4 * self.scale)))
        cx, cy = self._W - int(round(22 * self.scale)), int(round(16 * self.scale))
        r = int(round(11 * self.scale)) + m
        return (cx - r) <= x <= (cx + r) and (cy - r) <= y <= (cy + r)

    # ---------- 交互 ----------
    def _slider_rect(self):
        """透明度滑条的命中矩形（与绘制用同一套坐标）。"""
        s = self.scale
        W = self._W
        head = max(18, int(round(B_HEADER * s)))
        ymid = head / 2.0
        cr = 11 * s
        ccx = W - 22 * s
        sl_w = 62 * s
        sl_x2 = ccx - cr - 26 * s
        sl_x1 = sl_x2 - sl_w
        h = max(8, 9 * s)
        return sl_x1 - 2, sl_x2 + 2, ymid - h, ymid + h

    def _in_slider(self, x, y):
        x1, x2, y1, y2 = self._slider_rect()
        return x1 <= x <= x2 and y1 <= y <= y2

    def _apply_slider(self, x):
        x1, x2, _y1, _y2 = self._slider_rect()
        if x2 <= x1:
            return
        ratio = max(0.0, min(1.0, (x - x1) / float(x2 - x1)))
        self.opacity = 0.25 + ratio * 0.75
        self.redraw()

    def _press(self, e):
        if self.app.store.settings.click_through:
            return
        if self._in_close(e.x, e.y):
            self.app.hide_overlay()
            return
        if self._in_slider(e.x, e.y):
            self._opacity_drag = True
            self._apply_slider(e.x)
            return
        z = self._zone(e.x, e.y)
        if z != "move":
            self._resize = {"zone": z, "sx": e.x_root, "sy": e.y_root,
                            "w": self._W, "h": self._H, "scale": self.scale}
            return
        self._drag = (e.x_root - self.win.winfo_x(),
                      e.y_root - self.win.winfo_y())

    def _motion(self, e):
        if self._resize is not None:
            self._do_resize(e)
            return
        if self._opacity_drag:
            self._apply_slider(e.x)
            return
        if not self._drag:
            return
        dx, dy = self._drag
        try:
            self.win.geometry("+%d+%d" % (e.x_root - dx, e.y_root - dy))
        except tk.TclError:
            pass

    def _release(self, e):
        if self._opacity_drag:
            self._opacity_drag = False
            self.set_opacity(self.opacity)
            return
        if self._resize is not None:
            self._resize = None
            self.set_scale(self.scale)
            self.redraw()
            return
        if not self._drag:
            return
        self._drag = None
        s = self.app.store.settings
        s.overlay_x, s.overlay_y = self.win.winfo_x(), self.win.winfo_y()
        self.app.persist_settings()

    def _do_resize(self, e):
        """等比缩放：按拖动主轴换算比例。"""
        r = self._resize
        dx = e.x_root - r["sx"]
        dy = e.y_root - r["sy"]
        zone = r["zone"]

        if zone in ("e", "w"):
            delta, base = dx, r["w"]
        elif zone in ("n", "s"):
            delta, base = dy, r["h"]
        else:
            delta = dx if abs(dx) > abs(dy) else dy
            base = r["w"] if abs(dx) > abs(dy) else r["h"]

        if zone in ("w", "n", "nw", "sw"):
            delta = -delta

        if base <= 0:
            return
        new_scale = r["scale"] * (base + delta) / float(base)
        new_scale = max(MIN_SCALE, min(MAX_SCALE, new_scale))
        if abs(new_scale - self.scale) < 0.005:
            return
        self.scale = new_scale
        self.redraw()

    # ---------- 绘制 ----------
    def redraw(self):
        if not self.exists():
            return
        self._ensure_layered()
        self._maybe_branch_hint()

        W, H, head, ic, gap, pad, nodes, visible, start, widths = self._layout()
        if W != self._W or H != self._H:
            self._W, self._H = W, H
            try:
                self.win.geometry("%dx%d+%d+%d"
                                  % (W, H, self.win.winfo_x(), self.win.winfo_y()))
            except tk.TclError:
                pass

        img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        self._img_cur = img
        d = ImageDraw.Draw(img)
        self._d = d
        self._W, self._H = W, H
        self._a = self.opacity * 255.0
        self._sc = self.scale

        self._frame(d, W, H)
        self._header(d, W, head, nodes)
        self._strip(d, W, H, head, ic, gap, pad, nodes, visible, start, widths)

        # 底部最多两行：上行 = 瞬时提醒（选路/手柄连接），下行 = 状态/警告。
        # 两行间距固定 14px 且都做宽度截断，避免文字互相压住。
        line_gap = max(14, int(14 * self._sc))
        bottom_y = H - max(6, 6 * self._sc)
        warn, warn_color = self._status_text(nodes)
        if warn:
            self._text(d, W / 2, bottom_y, warn, theme.F_TINY, warn_color,
                       anchor="mm", bold=True, max_w=W - 2 * pad)

        if self._hint and time.time() < self._hint_until:
            self._text(d, W / 2, bottom_y - line_gap, self._hint,
                       theme.F_TINY, theme.ACCENT, anchor="mm", bold=True,
                       max_w=W - 2 * pad)
        elif self._hint:
            self._hint = ""

        out = img.resize((W, H), Image.LANCZOS)
        self._img = out
        layeredwin.blit(self.win, out)

    def _ensure_layered(self):
        try:
            hwnd = layeredwin.hwnd_of(self.win)
            if not hwnd:
                return
            style = layeredwin.user32.GetWindowLongW(
                ctypes.c_void_p(hwnd), layeredwin.GWL_EXSTYLE)
            if not (style & layeredwin.WS_EX_LAYERED):
                layeredwin.user32.SetWindowLongW(
                    ctypes.c_void_p(hwnd), layeredwin.GWL_EXSTYLE,
                    style | layeredwin.WS_EX_LAYERED)
        except Exception:
            pass

    # 单位换算
    def _S(self, v):
        return int(round(v * SS))

    def _fs(self, pt):
        return max(7, int(round(pt * self._sc)))

    def _shape(self, d, box, r=8, fill=None, outline=None, width=1):
        d.rounded_rectangle(
            [self._S(box[0]), self._S(box[1]), self._S(box[2]), self._S(box[3])],
            radius=self._S(r),
            fill=_rgba(fill, self._a) if fill else None,
            outline=_rgba(outline, self._a) if outline else None,
            width=max(1, self._S(width)))

    def _text(self, d, x, y, s, pt, color, anchor="la", bold=False,
              max_w=None):
        if not s:
            return
        size = self._fs(pt)
        if max_w is not None:
            s = fonts.pil_fit(s, size * SS, max_w * SS, bold)
            if not s:
                return
        d.text((self._S(x), self._S(y)), s, font=fonts.pil_font(size * SS, bold),
               fill=_rgba(color, 255),
               anchor={"la": "la", "lm": "lm", "mm": "mm", "rm": "rm",
                       "ra": "ra", "ls": "ls"}.get(anchor, "la"))

    def _paste(self, im, cx, cy):
        if im is None:
            return
        self._img_cur.alpha_composite(
            im, (int(self._S(cx) - im.width / 2), int(self._S(cy) - im.height / 2)))

    def _frame(self, d, W, H):
        r = max(6, int(round(10 * self._sc)))
        self._shape(d, (0.5, 0.5, W - 0.5, H - 0.5), r=r, fill=theme.BG,
                    outline=theme.BORDER, width=max(1, self._sc))

    def _header(self, d, W, head, nodes):
        s = self._sc
        p = self.app.player
        rot = p.rotation
        name = rot.name if rot else "未选择编队"
        ymid = head / 2.0

        # 关闭
        cr = 11 * s
        ccx, ccy = W - 22 * s, ymid
        d.ellipse([self._S(ccx - cr), self._S(ccy - cr),
                   self._S(ccx + cr), self._S(ccy + cr)],
                  fill=_rgba(theme.PANEL_2, self._a),
                  outline=_rgba(theme.BORDER, self._a), width=max(1, self._S(1)))
        self._text(d, ccx, ccy, "✕", theme.F_TINY, theme.TEXT_DIM, anchor="mm",
                   bold=True)

        # 右侧：透明度
        sl_w = 62 * s
        sl_x2 = ccx - cr - 26 * s
        sl_x1 = sl_x2 - sl_w
        self._text(d, sl_x1 - 6 * s, ymid, "透明度", theme.F_TINY,
                   theme.TEXT_MUTED, anchor="rm")
        d.line([self._S(sl_x1), self._S(ymid), self._S(sl_x2), self._S(ymid)],
               fill=_rgba(theme.BORDER, self._a), width=max(1, self._S(2)))
        pos = sl_x1 + (sl_x2 - sl_x1) * (
            (self.opacity - 0.25) / 0.75)
        d.line([self._S(sl_x1), self._S(ymid), self._S(pos), self._S(ymid)],
               fill=_rgba(theme.ACCENT, self._a), width=max(1, self._S(2)))
        kr = 4 * s
        d.ellipse([self._S(pos - kr), self._S(ymid - kr),
                   self._S(pos + kr), self._S(ymid + kr)],
                  fill=_rgba(theme.ACCENT, self._a))
        self._text(d, sl_x2 + 5 * s, ymid, "%d%%" % int(round(self.opacity * 100)),
                   theme.F_TINY, theme.ACCENT, anchor="lm", bold=True)

        # 进度（只读，不改播放器状态）
        idx = max(0, min(p.index, max(0, len(nodes) - 1)))
        prog = "%d / %d" % (idx + 1, len(nodes)) if nodes else "0 / 0"
        self._text(d, sl_x1 - 34 * s, ymid, prog, theme.F_TINY,
                   theme.TEXT_MUTED, anchor="rm")

        # 编队名 + 徽章
        name_right = sl_x1 - 44 * s
        nm = fonts.pil_fit(name, self._fs(theme.F_BODY) * SS,
                           max(60, name_right - 14 * s - 90 * s) * SS, True)
        self._text(d, 14 * s, ymid, nm, theme.F_BODY, theme.TEXT, anchor="lm",
                   bold=True)
        name_w = fonts.pil_text_width(nm, self._fs(theme.F_BODY) * SS, True) / SS
        bx = 14 * s + name_w + 10 * s

        seg = p.current_segment()
        if seg is None:
            return
        if seg.role == "burst":
            color, label = theme.BURST, "爆发轴"
        else:
            color = theme.CHARGE
            label = ("充能轴 %d/%d" % (seg.charge_index, seg.charge_total)
                     if seg.charge_total > 1 else "充能轴")
            # 这条轴设了循环：显示「×N」以及现在是第几遍
            try:
                want = int(getattr(seg.axis, "repeat", 1) or 1)
            except (TypeError, ValueError):
                want = 1
            if want > 1:
                label += " · ×%d" % want
        bw = fonts.pil_text_width(label, self._fs(theme.F_TINY) * SS, True) / SS + 16 * s
        if bx + bw <= name_right:
            self._shape(d, (bx, ymid - 9 * s, bx + bw, ymid + 9 * s),
                        r=4 * s, fill=theme.PANEL_2, outline=color, width=1)
            self._text(d, bx + bw / 2, ymid, label, theme.F_TINY, color,
                       anchor="mm", bold=True)

    def _strip(self, d, W, H, head, ic, gap, pad, nodes, visible, start, widths):
        if not nodes:
            self._text(d, W / 2, head + (H - head) / 2, "这条轴还没有技能",
                       theme.F_SMALL, theme.TEXT_MUTED, anchor="mm")
            return

        p = self.app.player
        idx = max(0, min(p.index, len(nodes) - 1))
        shown = nodes[start:start + visible]
        shown_w = widths[start:start + visible]

        top = head + 12 * self._sc
        icon_cy = top + ic / 2
        key_y = icon_cy + ic / 2 + 11 * self._sc

        content_w = pad * 2 + sum(shown_w) + gap * max(0, len(shown_w) - 1)
        x = (W - content_w) / 2.0 + pad
        for i, node in enumerate(shown):
            gi = start + i
            w = shown_w[i]
            cur = gi == idx
            past = gi < idx
            cx = x + w / 2

            if getattr(node, "kind", "") == "branch":
                self._draw_branch_cell(d, node, x, icon_cy, ic, w, cur, past,
                                       key_y)
            else:
                if cur:
                    k = 5 * self._sc
                    self._shape(d, (cx - ic / 2 - k, icon_cy - ic / 2 - k,
                                    cx + ic / 2 + k, icon_cy + ic / 2 + k),
                                r=8 * self._sc, fill=None, outline=theme.ACCENT,
                                width=2)
                im = (self.app.icons.render_pil(node.icon, int(ic * SS))
                      if node.icon else None)
                if im is not None and past:
                    im = im.copy()
                    r, g, b, a = im.split()
                    a = a.point(lambda v: int(v * 0.35))
                    im = Image.merge("RGBA", (r, g, b, a))
                self._paste(im, cx, icon_cy)
                col = (theme.ACCENT if cur
                       else (theme.TEXT_MUTED if past else theme.TEXT_DIM))
                self._text(d, cx, key_y, self.key_hint(node), theme.F_TINY, col,
                           anchor="mm", bold=cur, max_w=w - 2)
            x += w + gap

        if len(nodes) > visible:
            side = "→" if start + visible < len(nodes) else ""
            if side:
                self._text(d, W - pad - 2, icon_cy, side, theme.F_BODY,
                           theme.TEXT_MUTED, anchor="rm")

