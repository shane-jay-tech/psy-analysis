"""s923-55：`assumption_router`「N 法」注记 ↔ 实现现值的三向钉桩（含反"自证式快照"守卫）。

钉什么（**不是**把当前计数抄进断言自证）
--------------------------------------
三方在**同一来源**上判等，任何一边单独漂移动都会翻红：

① 实现现值 —— `describe_assumption_routes()` 的键集（= `_METHOD_ASSUMPTIONS` 注册表现值）
② 本文件写死的 id 快照字面量 —— 增删法必须显式改这里，改动留痕
③ `KNOWN_ISSUES.md` 的「…路由已扩至 N 法」注记数字 —— **只扫该文件**，绝不扫本件（防自命中假阳）

外加三条反假绿守卫（都对应在册踩过的坑）：
- 快照必须是**真字面量**：把它改成 `frozenset(describe_assumption_routes())` 的那一刻，
  整个钉桩就退化成"实现 == 实现"的自证，本件会当场翻红。
- 注记必须**恰 1 处**：出现第二份互相矛盾的数字时，"判等"没有对象，先收敛文档。
- 本件不得被整件 skip / xfail 标记：`pytestmark = skip` 的桩是"绿但零覆盖"（9/23 §廿七形态）。
- `_drift_report` 是三向比对的唯一实现，下面用**四刀变异**直接喂它，证明它有牙。

开工前实测（先跑后写死，非推断）
------------------------------
    .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');\\
        from src.analysis.assumption_router import describe_assumption_routes as d;\\
        print(len(d()))"                     -> 15
    git show aee4139:src/analysis/assumption_router.py  →  AST 取 _METHOD_ASSUMPTIONS 键 -> 15
    git show cebcddc --format=%h%s          ->  assumption_router.py 最后一次改动（2026-09-06）

⇒ 在册缺陷归因：`KNOWN_ISSUES.md:144` 的「14 法」**生下来就少 1**，不是后来长出来的——
写下该注的 commit `aee4139`（2026-09-09）当天注册表已是 15 键。
订正方向只能是文档（本次已把 :144 数字订正为实测 15 并注明复测日期与出处），
🔴 **不改 `src/` 去凑注记**，本件也不碰任何统计数值结论。
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

from src.analysis import assumption_router

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
KNOWN_ISSUES_PATH = REPO_ROOT / "KNOWN_ISSUES.md"
SELF_PATH = pathlib.Path(__file__).resolve()

# 注记句锚点：只要「假设检验路由 … N 法」这一语义，不锁 "已扩至" 三字
# （锁死措辞会让下一次改文案白白翻红；且本文件刻意不出现 "已扩至" 串，
#  免得将来有人 repo 级 rg "已扩至" 数注记时把本件当成第二份注记）。
DOC_ROUTE_COUNT_RE = re.compile("假设检验路由[^\\d\\n]{0,10}?(\\d+)\\s*法")
DOC_NOTE_HEAD = "假设检验路由"

# ---- 2026-09-24 实测基线（判据：先跑后写死；命令原文见模块 docstring）----
BASELINE_ROUTE_METHOD_IDS = frozenset(
    [
        "binary_logistic",
        "chi_square_gof",
        "chi_square_independence",
        "hierarchical_regression",
        "hlm",
        "linear_regression",
        "manova",
        "mixed_anova",
        "multinomial_logistic",
        "multiple_regression",
        "ordinal_logistic",
        "partial_corr",
        "point_biserial",
        "sem",
        "two_way_anova",
    ]
)


# --------------------------------------------------------------------------- 取数

def _live_profile() -> dict:
    """实现现值：注册表覆盖画像（唯一来源就是生产函数本身）。"""
    return assumption_router.describe_assumption_routes()


def _doc_route_count_claims(text: str) -> list:
    """扫给定文本，返回 [(行号, 命中文串, 法数)]。纯函数 ⇒ 变异取证不需要写盘。"""
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in DOC_ROUTE_COUNT_RE.finditer(line):
            hits.append((lineno, m.group(0), int(m.group(1))))
    return hits


def _known_issues_text() -> str:
    return KNOWN_ISSUES_PATH.read_text(encoding="utf-8")


def _doc_route_count() -> int:
    """取 `KNOWN_ISSUES.md` 的法数注记；命中数不是恰 1 处时**当场拒判**（不静默取第一个）。"""
    claims = _doc_route_count_claims(_known_issues_text())
    assert len(claims) == 1, (
        "KNOWN_ISSUES.md 的法数注记命中 "
        f"{len(claims)} 处（应恰 1 处）：{claims}\n"
        "⇒ 出现互相矛盾的第二份注记，「三向判等」没有唯一对象，先收敛文档再谈钉桩。"
    )
    return claims[0][2]


# --------------------------------------------------------------------------- 比对

def _drift_report(live_ids, snapshot_ids, doc_number) -> list:
    """三向比对的**唯一**实现，返回漂移说明列表（空 == 三向一致）。

    参数全部外灌 ⇒ 变异取证可直接喂"少一法 / 多一法 / 只改文档数字"三种假现场。
    """
    live = set(live_ids)
    snap = set(snapshot_ids)
    problems = []

    dropped = sorted(snap - live)
    if dropped:
        problems.append(f"注册表已下架但快照仍钉着：{dropped}")
    added = sorted(live - snap)
    if added:
        problems.append(f"注册表新增未登记（增删法必须显式改快照）：{added}")

    if doc_number is None:
        problems.append("文档注记缺失或不唯一，无法与实现判等")
    elif doc_number != len(live):
        problems.append(
            f"文档注记 {doc_number} ≠ 实现现值 {len(live)} 法"
            f"（注记：{KNOWN_ISSUES_PATH.name}）"
        )
    return problems


# --------------------------------------------------------------------------- 钉桩

def test_live_count_value_matches_snapshot_and_doc_note():
    """判据 1：`len(describe_assumption_routes())` 数值双向对齐。"""
    profile = _live_profile()
    assert len(profile) == len(BASELINE_ROUTE_METHOD_IDS), (
        f"实现现值 {len(profile)} 法 ≠ 快照 {len(BASELINE_ROUTE_METHOD_IDS)} 法"
    )
    assert _doc_route_count() == len(profile), (
        f"文档注记 {_doc_route_count()} ≠ 实现现值 {len(profile)}"
    )


def test_method_id_set_matches_snapshot_both_directions():
    """判据 2：方法 id 集合**两向**判等（既不许漏钉也不许多钉）。"""
    live = set(_live_profile())
    assert live - BASELINE_ROUTE_METHOD_IDS == set(), f"实现里有未登记的新法：{sorted(live - BASELINE_ROUTE_METHOD_IDS)}"
    assert BASELINE_ROUTE_METHOD_IDS - live == set(), f"快照里钉着已下架的旧法：{sorted(BASELINE_ROUTE_METHOD_IDS - live)}"


def test_three_way_agreement_is_clean_right_now():
    """判据 3：三向（实现 / 快照 / 注记）当前零漂移。"""
    assert _drift_report(set(_live_profile()), BASELINE_ROUTE_METHOD_IDS, _doc_route_count()) == []


def test_profile_is_the_whole_registry_without_filtering():
    """画像必须是注册表全量：函数若加过滤，注记的"法数"会静默换口径。"""
    profile = _live_profile()
    registry = assumption_router._METHOD_ASSUMPTIONS
    assert set(profile) == set(registry)
    assert len(profile) == len(registry)


def test_pinned_function_is_the_live_src_object():
    """身份护栏：钉的是 src/analysis/assumption_router.py 里那个活对象，不是副本/替身。"""
    mod = sys.modules["src.analysis.assumption_router"]
    assert assumption_router is mod
    fn = assumption_router.describe_assumption_routes
    assert fn is mod.describe_assumption_routes
    assert fn.__code__.co_filename.replace("\\", "/").endswith("src/analysis/assumption_router.py")


# ------------------------------------------------------------------- 变异取证（有牙自证）

def test_mutant_one_method_removed_is_caught():
    live = set(_live_profile()) - {"sem"}
    report = _drift_report(live, BASELINE_ROUTE_METHOD_IDS, len(BASELINE_ROUTE_METHOD_IDS))
    assert any("下架" in p for p in report), f"少一法的变异竟然没被抓：{report}"


def test_mutant_one_method_added_is_caught():
    live = set(_live_profile()) | {"brand_new_route_method"}
    report = _drift_report(live, BASELINE_ROUTE_METHOD_IDS, len(BASELINE_ROUTE_METHOD_IDS))
    assert any("新增" in p for p in report), f"多一法的变异竟然没被抓：{report}"


def test_mutant_doc_number_bumped_only_is_caught():
    """变异：只把文档数字写成"实现现值 +1"（不依赖当前注记取值，免得假变异）。"""
    report = _drift_report(set(_live_profile()), BASELINE_ROUTE_METHOD_IDS, len(_live_profile()) + 1)
    assert len(report) == 1 and "文档注记" in report[0], f"只改文档数字的变异竟然没被抓：{report}"


def test_mutant_snapshot_rewritten_to_live_but_doc_stale_is_caught():
    """专防"改测试凑实现"这一型自证式修法：快照抄实现后 id 两向恒真，
    但只要文档数字仍 ≠ 现值，三向比对必须仍然只剩这一条红。"""
    live = set(_live_profile())
    report = _drift_report(live, frozenset(live), len(live) + 1)
    assert len(report) == 1 and "文档注记" in report[0], f"快照退化为自证时竟未翻红：{report}"


def test_second_contradictory_doc_note_would_be_rejected():
    """注记唯一性是判等前提：合成"第二份注记"（不落盘）必须被数出来。"""
    real = _doc_route_count_claims(_known_issues_text())
    assert len(real) == 1, f"真档注记命中数已非 1：{real}"
    synthetic = _known_issues_text() + f"\n- 另一处也记：{DOC_NOTE_HEAD}共 99 法。\n"
    assert len(_doc_route_count_claims(synthetic)) == 2, "第二份矛盾注记竟然没被数出来"


# ------------------------------------------------------------- 反"静默失明的绿"结构守卫

def test_snapshot_is_a_hard_literal_with_no_duplicate_entry():
    """快照必须是字符串字面量集合，且**不得含重复项**。

    - 若有人改成 `frozenset(describe_assumption_routes())` ⇒ 钉桩退化为自证，本条翻红。
    - 若在续行里重复粘贴同一个 id，frozenset 会静默塌缩成 14 ⇒ 字面量元素数 ≠ 集合长度，本条翻红。
    """
    tree = ast.parse(SELF_PATH.read_text(encoding="utf-8"))
    literal_elems = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        else:
            continue
        if "BASELINE_ROUTE_METHOD_IDS" not in targets:
            continue
        value = node.value
        elems = value
        if isinstance(value, ast.Call):
            assert any(
                isinstance(c, ast.Name) and c.id in {"frozenset", "set", "list", "tuple", "sorted"}
                for c in ast.walk(value.func)
            ), f"快照推导自未知调用：{ast.dump(value)[:200]}"
            assert not any(
                (isinstance(c, ast.Name) and c.id in {"_live_profile", "_live_ids", "_doc_route_count"})
                or (isinstance(c, ast.Attribute) and c.attr == "describe_assumption_routes")
                for c in ast.walk(value)
            ), "快照已改成从实现/文档推导 ⇒ 钉桩变成自证，必须回退成显式字面量"
            assert len(value.args) == 1, "快照构造应只包一层容器"
            elems = value.args[0]
        assert isinstance(elems, (ast.List, ast.Tuple, ast.Set)), (
            f"快照容器不是字面量列表/元组/集合：{type(elems).__name__}"
        )
        literal_elems = elems.elts
        break
    assert literal_elems is not None, "找不到 BASELINE_ROUTE_METHOD_IDS 的模块级赋值 ⇒ 快照被搬走了"
    assert all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in literal_elems), "快照含非字符串元素"
    values = [e.value for e in literal_elems]
    assert len(values) == len(set(values)), f"快照字面量有重复项（集合会静默塌缩）：{sorted(values)}"
    assert len(values) == len(BASELINE_ROUTE_METHOD_IDS)


def test_this_file_is_not_module_or_case_level_skipped():
    """整件 skip 的桩＝绿但零覆盖。本文件既不许有 pytestmark，也不许给用例挂 skip/xfail。"""
    tree = ast.parse(SELF_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            assert "pytestmark" not in names, "本件加了 pytestmark ⇒ 快照可能整件被跳过而报告仍显示绿"
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            for dec in node.decorator_list:
                dump = ast.dump(dec)
                assert "skip" not in dump and "xfail" not in dump, f"{node.name} 被挂了跳过/预期失败标记"
    assert KNOWN_ISSUES_PATH.is_file(), f"注记文件不在位：{KNOWN_ISSUES_PATH}"


def test_known_issues_note_line_still_carries_the_pointer_phrase():
    """注记行按内容定位（不锁行号，行号会被别人的插入推走），并核对活口句仍在。"""
    hits = [
        (i, line)
        for i, line in enumerate(_known_issues_text().splitlines(), start=1)
        if DOC_ROUTE_COUNT_RE.search(line)
    ]
    assert len(hits) == 1, f"法数注记行不唯一：{[i for i, _ in hits]}"
    line = hits[0][1]
    assert "src/analysis" in line, "注记的「精确清单以代码为准」活口句被删 ⇒ 需同步改写本套件说明"
