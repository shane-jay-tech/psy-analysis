"""`app.py` 模块级页面分支（mode 路由链）语义锚看守（s924-20，AST 读盘、不执行 app.py）。

## 为什么钉

`zcode-bridge/done/s923-14.result.md` 遗留问题 1 原文：
「页面分支后四个锚点（:2314/:2345/:2353/:2397）与 :1119/:1128 届时需再重取……**没有**给这些锚点
建立可自动校验的看守——若要长期防漂，需要一条单独的测试或脚本（属规划域，未做）」。
（引用的那串行号是**当时的历史锚点**，本件一条都不依赖。）

同族在册件 `tests/test_navigation_pagemodes_snapshot.py` 钉的是**导航事实源** `PAGE_MODES`；
`app.py` 侧的路由链此前只有两条成员级断言（`tests/test_app_routes_v6_panels.py`），
⇒ 删页、改名、换序、或「侧栏加了页而 app.py 忘了接分支」都不翻红。本件补的就是路由链这一侧。

## 口径（绑磁盘 AST 实取，零执行、零行号）

- `_route_chain_from_text()` 解析 `app.py` 模块级以 `mode == "<页名>"` 为条件的 `if`/`elif` 链，返回**有序**页名表；
- 判据三向互证：**集合等 / 有序表等 / 基数等**（三条独立：换序只破有序表，重复页只破基数与去重项）；
- **行号不参与任何断言** ⇒ `app.py` 上方的代码增删（他班在途那种 +12/−40 形态）不会误红，
  `test_guard_is_line_number_agnostic` 用「同一份源码整体下移 137 行再解析」正面坐实；
- **正则 + AST 双轨**（纪律档 §九.3）：`_elif_line_pattern` 逐行数链身，与 AST 提取的 elif 数对到位；
  两条口径差额非零即红，避免只报一个数。正则串刻意写成 `\\s+` 形式，本文件因此**不会**成为
  页面路由口径在 `tests/` 下的额外命中。

## 为什么 `EXPECTED_ELIF_COUNT` 是 6（完成标准②的同款口径）

链首那一支是 `if`，其余 6 支才是 `elif` ⇒ 链**总页数 7**、`elif` **数 6**。
判据点名的实取命令只数 `elif` 那一侧，所以内联值取 6，并与 `_elif_line_pattern` 逐行读数互锁。

## 与导航事实源的交叉锚

`test_chain_covers_page_modes_exactly`：路由链的**页名集合**必须等于 `PAGE_MODES` 集合（现读两侧均 7）。
两表分处 `app.py` 与 `src/ui/navigation.py`，任一侧单独漂移（最常见是加了侧栏项忘了加分支）当场翻红。
⚠ 两侧**书写序不同且各自有意义**（侧栏按研究流程排，路由链按代码搬迁史排，`📈 数据分析` 恒在链首），
故这里只比集合；链序的看守归本件 `_assert_chain_pins`，侧栏序归 `test_navigation_pagemodes_snapshot.py`。

## 反向自证

`test_reverse_self_check_tampering_the_chain_flips_the_guard`：篡改**解析结果**（删页/改名/换序/重复）必红。
`test_reverse_self_check_on_synthetic_source`：篡改**源码文本**再走一遍解析器，同样必红——
这一刀覆盖的是解析器本身，防止「比较器有效但解析器读不到东西」的假绿。
改名那一刀刻意用**逐字前缀加长**（`X` 而非截断）的形态：本件全部是精确等值判定，
若有人把它改成子串判定，前两刀会当场失效并被这条自证读出来（纪律档 §十二.末节）。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from src.ui.navigation import PAGE_MODES

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PY = REPO_ROOT / "app.py"

# ── 语义锚：路由链的有序页名表（链首是 if，其余 6 支是 elif）──
# 现取口径见模块 docstring；改 app.py 页面分支时，按磁盘实况重取并同步本表与文档。
EXPECTED_MODE_CHAIN: list[str] = [
    "\U0001f4c8 数据分析",
    "\U0001f9ea 实验设计",
    "\U0001f4cb 问卷设计",
    "\U0001f4dd 论文写作",
    "\U0001f4da 文献与选题",
    "\U0001f4e6 交付包导出",
    "\U0001f5c2\ufe0f 模板中心",
]
# 链身（除链首）的条数——与「逐行数链身」的正则口径同值，内联而非现算，正是被钉的对象。
EXPECTED_ELIF_COUNT = 6

# 正则轨道：^elif\s+mode\s*==\s*"(.*)":$ （刻意用 \s+，见 docstring「双轨」段）
_ELIF_LINE_RE = re.compile(r'^elif\s+mode\s*==\s*"([^"]*)"\s*:\s*$', re.M)
_IF_LINE_RE = re.compile(r'^if\s+mode\s*==\s*"([^"]*)"\s*:\s*$', re.M)


def _app_text() -> str:
    return APP_PY.read_text(encoding="utf-8")


def _mode_eq_str(test: ast.expr) -> str | None:
    """`mode == "<字符串字面量>"` → 返回该字面量；其它写法（in / != / 变量右值）返回 None。"""
    if (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.left, ast.Name)
        and test.left.id == "mode"
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and isinstance(test.comparators[0].value, str)
    ):
        return test.comparators[0].value
    return None


def _walk_chain(root: ast.If) -> list[tuple[str, bool]]:
    """沿 orelse 展开一条 if/elif 链 → [(页名, 是否为 elif)]；遇到非 mode== 字面量的支即停。"""
    out: list[tuple[str, bool]] = []
    cur: ast.If | None = root
    depth = 0
    while isinstance(cur, ast.If):
        label = _mode_eq_str(cur.test)
        if label is None:
            break
        out.append((label, depth > 0))
        depth += 1
        tail = cur.orelse
        cur = tail[0] if (len(tail) == 1 and isinstance(tail[0], ast.If)) else None
        if depth > 64:  # 防意外的自引用结构把测试挂住
            raise AssertionError("mode 路由链深度超过 64 层，解析器拒绝猜测")
    return out


def _route_chain_from_text(src: str, filename: str = "<memory>") -> list[str]:
    """模块级 mode 路由链的有序页名表（只读源码，不执行）。"""
    tree = ast.parse(src, filename=filename)
    chains = [n for n in tree.body if isinstance(n, ast.If) and _mode_eq_str(n.test) is not None]
    if len(chains) != 1:
        raise AssertionError(
            f"模块级 mode 路由链应恰好 1 条，实读 {len(chains)} 条"
            f"（{filename} 内链首行号 {[c.lineno for c in chains]}）"
            "⇒ 路由被拆成多条链或搬进了函数体，本看守的语义前提已失效，请人工复核后重写锚点"
        )
    branches = _walk_chain(chains[0])
    if not branches:
        raise AssertionError(f"{filename}: 链首存在但没提取到任何页名，解析器与源码形态不符")
    head_labels = [label for label, is_elif in branches if not is_elif]
    assert len(head_labels) == 1, (
        f"{filename}: mode 路由链的链首应恰好 1 支 if，实读 {len(head_labels)} 支——解析器读歪了"
    )
    return [label for label, _ in branches]


def _disk_chain() -> list[str]:
    return _route_chain_from_text(_app_text(), filename=str(APP_PY))


def _assert_chain_pins(chain: list[str], source_note: str = "工作树 app.py") -> None:
    """三向互证 + 去重不变量。四条断言互相独立，任一向破了都红。"""
    missing = sorted(set(EXPECTED_MODE_CHAIN) - set(chain))
    extra = sorted(set(chain) - set(EXPECTED_MODE_CHAIN))
    dup = sorted({p for p in chain if chain.count(p) > 1})
    detail = f"缺页={missing} 多页={extra} 重复={dup}（读自 {source_note}）"

    assert set(chain) == set(EXPECTED_MODE_CHAIN), f"路由链页名集合漂移：{detail}"
    assert chain == EXPECTED_MODE_CHAIN, (
        f"路由链**顺序**漂移（集合相同也会走到这里）：实读 {chain} / 锚点 {EXPECTED_MODE_CHAIN}；{detail}"
    )
    assert len(chain) == len(EXPECTED_MODE_CHAIN), f"路由链基数漂移：{detail}"
    assert not dup, f"路由链含重复页名：{detail}"


# ────────────────────────── 主判据 ──────────────────────────
def test_module_level_mode_chain_is_pinned() -> None:
    """删页 / 改名 / 换序 / 重复页 都必红；行号漂移不红。"""
    _assert_chain_pins(_disk_chain())


def test_elif_count_inline_expectation_is_6() -> None:
    """完成标准②的可执行版：链身（elif）条数与内联值 6 对到位。"""
    tree = ast.parse(_app_text(), filename=str(APP_PY))
    chain_root = next(n for n in tree.body if isinstance(n, ast.If) and _mode_eq_str(n.test) is not None)
    branches = _walk_chain(chain_root)
    elif_count = sum(1 for _, is_elif in branches if is_elif)
    assert elif_count == EXPECTED_ELIF_COUNT, (
        f"AST 读到 {elif_count} 支 elif，内联锚点 {EXPECTED_ELIF_COUNT}"
        "（链总页数应为 7：1 支 if + 6 支 elif）"
    )


def test_regex_and_ast_tracks_agree() -> None:
    """双轨对账（纪律档 §九.3）：逐行正则与 AST 各数一遍，差额必须为 0 并逐条点名。"""
    text = _app_text()
    regex_elif = _ELIF_LINE_RE.findall(text)
    regex_if = _IF_LINE_RE.findall(text)
    tree = ast.parse(text, filename=str(APP_PY))
    chain_root = next(n for n in tree.body if isinstance(n, ast.If) and _mode_eq_str(n.test) is not None)
    ast_chain = [label for label, _ in _walk_chain(chain_root)]

    assert len(regex_if) == 1, f"正则轨道读到链首 {len(regex_if)} 支（应为 1）：{regex_if}"
    assert len(regex_elif) == EXPECTED_ELIF_COUNT, (
        f"正则轨道逐行数到 {len(regex_elif)} 支 elif，锚点 {EXPECTED_ELIF_COUNT}：{regex_elif}"
    )
    both = regex_elif + [regex_if[0]]
    assert sorted(both) == sorted(ast_chain), (
        f"正则轨 vs AST 轨差额非零（缩进/写法差异会在这里现形，别只信一个数）："
        f"正则={both} AST={ast_chain}"
    )


def test_guard_is_line_number_agnostic() -> None:
    """正面坐实「语义锚」：同一份源码整体下移 137 行，链读数逐字不变。"""
    text = _app_text()
    shifted = _route_chain_from_text("\n" * 137 + text, filename="<shifted>")
    assert shifted == _disk_chain(), "加了 137 行空行就改变读数 ⇒ 本件其实依赖了行号，判据写错了"


def test_chain_covers_page_modes_exactly() -> None:
    """交叉锚：app.py 路由链页名集合 == navigation.PAGE_MODES 集合（序不比，见 docstring）。"""
    chain = _disk_chain()
    only_in_chain = sorted(set(chain) - set(PAGE_MODES))
    only_in_nav = sorted(set(PAGE_MODES) - set(chain))
    assert (only_in_chain, only_in_nav) == ([], []), (
        f"app.py 路由链与 PAGE_MODES 不再同集：只在链里={only_in_chain} 只在导航里={only_nav}"
        f"（链 {len(chain)} 页 / 导航 {len(PAGE_MODES)} 页）"
    )
    assert len(chain) == len(PAGE_MODES) == 7, (
        f"两侧基数不再相等：链 {len(chain)} / 导航 {len(PAGE_MODES)}（现读均为 7）"
    )


def test_chain_head_is_data_analysis_and_body_is_elif() -> None:
    """结构锚：链首那支是 `if`（数据分析页恒在链首，全流程模式也会把 mode 设成它）。"""
    tree = ast.parse(_app_text(), filename=str(APP_PY))
    chain_root = next(n for n in tree.body if isinstance(n, ast.If) and _mode_eq_str(n.test) is not None)
    branches = _walk_chain(chain_root)
    assert branches[0][1] is False, "链首第一支必须是 if（写成 elif 就是语法错误，读到这里说明解析器坏了）"
    assert branches[0][0] == "\U0001f4c8 数据分析", f"链首页名漂移：{branches[0][0]!r}"
    assert all(is_elif for _, is_elif in branches[1:]), "除链首外每一支都必须是 elif"


# ────────────────────────── 反向自证 ──────────────────────────
_PAPER = "\U0001f4dd 论文写作"
_EXPERIMENT = "\U0001f9ea 实验设计"

MUTATIONS: dict[str, tuple[str, object]] = {
    "删页（丢一支分支）": ("drop", _PAPER),
    "改名（逐字前缀加长，杀精确等值）": ("rename", _PAPER),
    "换序（相邻两支对调）": ("swap", (_EXPERIMENT, _PAPER)),
    "重复页（同页两支）": ("dup", "\U0001f4e6 交付包导出"),
}


def _mutate(chain: list[str], kind: str, arg: object) -> list[str]:
    out = list(chain)
    if kind == "drop":
        return [p for p in out if p != arg]
    if kind == "rename":
        return [(p + "X" if p == arg else p) for p in out]
    if kind == "swap":
        left, right = arg  # type: ignore[misc]
        i, j = out.index(left), out.index(right)
        out[i], out[j] = out[j], out[i]
        return out
    if kind == "dup":
        out.insert(out.index(arg) + 1, arg)  # type: ignore[arg-type]
        return out
    raise AssertionError(f"未知变异形态 {kind}")


def _synthetic_source(chain: list[str]) -> str:
    lines = ["import streamlit as st", "mode = st.session_state.get('app_mode')", ""]
    for i, page in enumerate(chain):
        lines.append(f"{'if' if i == 0 else 'elif'} mode == \"{page}\":")
        lines.append(f"    st.write({page!r})")
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_reverse_self_check_tampering_the_chain_flips_the_guard(name: str) -> None:
    """完成标准①点名的反向自证：篡改**解析结果**必红（证明主判据不是恒真）。"""
    kind, arg = MUTATIONS[name]
    tampered = _mutate(EXPECTED_MODE_CHAIN, kind, arg)
    assert tampered != EXPECTED_MODE_CHAIN, f"变异 {name} 没产生差异，这一刀是假刀"
    with pytest.raises(AssertionError):
        _assert_chain_pins(tampered, source_note=f"反向自证：{name}")


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_reverse_self_check_on_synthetic_source(name: str) -> None:
    """覆盖解析器本身：把变异做进**源码文本**再重跑「解析 + 判据」，同样必红。"""
    kind, arg = MUTATIONS[name]
    source = _synthetic_source(_mutate(EXPECTED_MODE_CHAIN, kind, arg))
    with pytest.raises(AssertionError):
        _assert_chain_pins(_route_chain_from_text(source, filename=f"<synthetic:{name}>"))


def test_synthetic_source_without_mutation_satisfies_the_guard() -> None:
    """自证的对照位：同一套「解析 + 判据」对未篡改的合成源码必须放行，
    否则上面两条反向自证是「什么都红」的假严格。"""
    _assert_chain_pins(_route_chain_from_text(_synthetic_source(EXPECTED_MODE_CHAIN)), source_note="合成对照")


def test_expected_anchor_list_is_self_consistent() -> None:
    """锚点表自检：7 页、无重复、逐页与 PAGE_MODES 同集，且 `🗂️` 那页保住 U+FE0F 变体选择符。"""
    assert len(EXPECTED_MODE_CHAIN) == 7
    assert len(set(EXPECTED_MODE_CHAIN)) == 7
    assert set(EXPECTED_MODE_CHAIN) == set(PAGE_MODES)
    assert EXPECTED_MODE_CHAIN[-1] == "\U0001f5c2\ufe0f 模板中心" and "\ufe0f" in EXPECTED_MODE_CHAIN[-1]
    assert all(p == p.strip() and p for p in EXPECTED_MODE_CHAIN)


if __name__ == "__main__":  # 允许脱离 pytest 快速自检
    _chain = _disk_chain()
    print(f"链总页数={len(_chain)} elif数={len(_chain) - 1}")
    for _p in _chain:
        print(repr(_p))
    _assert_chain_pins(_chain)
    raise SystemExit(0)
