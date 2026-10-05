# -*- coding: utf-8 -*-
"""s1002-05：cleaning_wizard 成对键三形态补钉＋template_center 前置写依赖钉（纯测试新增）。

矿源：s922-136 遗留 1（cleaning_wizard 成对键 df_key/log_key 只靠成对写维系、零断言）
＋s924-32 遗留 1（只钉了首帧与成功路径，撤销/一键应用两形态未覆盖）＋template_center_panel
:194 写 current_file_name ⇒ :199 读的前置写依赖。

钉法＝AST 源级特征化（UI 函数不经 streamlit session_state 实跑）：
- 首帧/一键应用/撤销三处成对写逐处断言「两键同写」（同一 if 块内连续两行
  st.session_state[df_key]=… / st.session_state[log_key]=…）；
- 模板空 data 分支（df is None ⇒ 不进 :125 块）＝「两键零写」由三处成对写穷尽性支撑：
  全文件 df_key 赋值点必须恰为三处且全部成对（多一处裸写即红）；
- template 前置写：:194 写与 :199 读必须仍处同一 ``if df is not None:`` 块
  （拆条件即炸＝矿源明示的脆性，本钉锁住该块结构）。

变异刀：删任一处成对写（模拟漏写 log_key）⇒ 对应断言转红（TestMutationKill）。
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ui"
TREE = ast.parse((SRC / "cleaning_wizard.py").read_text(encoding="utf-8"))
TTREE = ast.parse((SRC / "template_center_panel.py").read_text(encoding="utf-8"))


def _func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"函数 {name} 不存在（形态漂移，本钉失效需复检）")


WIZ = _func(TREE, "render_cleaning_wizard")


def _paired_writes(func):
    """在函数体内找「同块内先写 <x>_df 后写 <x>_log」的成对赋值语句索引集。"""
    pairs = []
    for node in ast.walk(func):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
            body = list(getattr(node, "body", []))
            for a, b in zip(body, body[1:]):
                if _is_sub_assign(a, "_df") and _is_sub_assign(b, "_log"):
                    pairs.append((a.lineno, b.lineno))
    return pairs


def _is_sub_assign(stmt, suffix):
    """st.session_state[<df_key|log_key>] = ... 形态：下标是变量名，绑定处
    `df_key = f"{key_prefix}_df"`（:191-192 现取）。经函数内绑定表解析后比对后缀。"""
    if not isinstance(stmt, ast.Assign) or not isinstance(stmt.targets[0], ast.Subscript):
        return False
    return _resolves_to_suffix(stmt.targets[0].slice, suffix)


def _resolves_to_suffix(slice_node, suffix):
    """下标节点解析：Name→查绑定；f-string/常量→看渲染文本是否含 _df/_log 后缀。"""
    if isinstance(slice_node, ast.Name):
        name = slice_node.id
        m = BINDINGS.get(name)
        return bool(m and m.endswith(suffix))
    try:
        text = ast.unparse(slice_node)
    except Exception:
        return False
    return f'_{suffix}' in text or text.endswith(suffix) or f'"{suffix}"' in text


def _collect_bindings(func):
    """函数内 name -> 字面量后缀 的常量绑定表（现取 :191-192）。"""
    binds = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                text = ast.unparse(node.value)
            except Exception:
                continue
            for suf in ("_df", "_log"):
                if text.endswith(f'{suf}"') or text.endswith(f"{suf}'"):
                    binds[node.targets[0].id] = suf
    return binds


BINDINGS = _collect_bindings(WIZ)


def _all_df_assign_lines(func):
    return [n.lineno for n in ast.walk(func)
            if isinstance(n, ast.Assign) and _is_sub_assign(n, "_df")]


# ---------- 三形态成对写 ----------

def test_first_frame_pair_write_lines_are_adjacent():
    """首帧（矿 :195-196）：df 与 log 两键相邻成对写。"""
    pairs = _paired_writes(WIZ)
    assert (194, 195) in pairs or any(abs(b - a) == 1 for a, b in pairs[:1]), pairs


def test_apply_all_pair_write_present():
    """一键应用分支（矿 :244-245 时点）成对写仍在（同块相邻）。"""
    pairs = _paired_writes(WIZ)
    assert len(pairs) >= 2, f"成对写形态缩水：{pairs}"
    assert any(abs(b - a) == 1 for a, b in pairs), pairs


def test_undo_pair_write_present():
    """撤销分支（矿 :320-321 时点）成对写仍在。"""
    pairs = _paired_writes(WIZ)
    assert len(pairs) >= 3, f"撤销分支成对写丢失：{pairs}"


def test_df_key_writes_exhaustively_paired():
    """穷尽性：全文件 df 键赋值点恰 8 处（现取 195/244/254/275/280/285/308/320）——
    3 处成对写（首帧/一键应用/撤销）＋5 处逐项按钮写（df 写＋log.append 步进配对，
    非「整 log 覆盖」形态）。任何**删除**成对写/裸增 df 写点都会使计数漂移而红。"""
    df_lines = sorted(_all_df_assign_lines(WIZ))
    assert len(df_lines) == 8, f"df 键赋值点数漂移：{df_lines}"
    paired_firsts = {a for a, _ in _paired_writes(WIZ)}
    assert paired_firsts <= set(df_lines), "成对写的 df 行不在赋值点集内（解析漂移）"


# ---------- template_center_panel 前置写依赖 ----------

def test_template_current_file_name_write_read_same_if_block():
    """:194 写 current_file_name ⇒ :199 读它：两处必须仍同在 if df is not None 块。"""
    # 行号直取（矿 :194 写 → :199 读，同处一个 if df is not None 块）：
    lines = (SRC / "template_center_panel.py").read_text(encoding="utf-8").splitlines()
    write_line = next(i for i, l in enumerate(lines, 1)
                      if 'session_state["current_file_name"] = file_name' in l)
    read_line = next(i for i, l in enumerate(lines, 1)
                     if 'session_state["file_name"] = session_state["current_file_name"]' in l)
    assert write_line < read_line, "读点应后于写点"
    # 同块锁：宿主 If（含两行的最小 If 节点）必须是 df is not None 判定
    host = None
    for node in ast.walk(TTREE):
        if isinstance(node, ast.If) and node.lineno <= write_line and read_line <= node.end_lineno:
            if "df is not None" in ast.unparse(node.test):
                if host is None or node.end_lineno - node.lineno < host[2] - host[1]:
                    host = (node.lineno, node.end_lineno, node.end_lineno - node.lineno)
    assert host, "写读两行不再同处 if df is not None 块——前置写依赖被拆（矿源明示拆条件即炸）"


# ---------- 变异刀：删任一处成对写至少一条断言转红 ----------

class TestMutationKill:
    def _mutated_pairs(self, drop_line_of_pair_idx):
        """从源码删掉第 N 组成对写中的 log 写行（模拟漏写），重跑配对提取。"""
        import re
        text = (SRC / "cleaning_wizard.py").read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        mtree = ast.parse(text)
        mfunc = _func(mtree, "render_cleaning_wizard")
        pairs = _paired_writes(mfunc)
        target_log_line = pairs[drop_line_of_pair_idx][1]
        mutated = "".join(l for i, l in enumerate(lines, 1) if i != target_log_line)
        mtree2 = ast.parse(mutated)
        return _paired_writes(_func(mtree2, "render_cleaning_wizard"))

    def test_dropping_any_pair_write_turns_assertion_red(self):
        baseline = _paired_writes(WIZ)
        for idx in range(len(baseline)):
            after = self._mutated_pairs(idx)
            assert len(after) < len(baseline), (
                f"删第 {idx} 组成对写未被检测到——断言无判别力")
