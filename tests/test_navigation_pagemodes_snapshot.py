"""`src/ui/navigation.py::PAGE_MODES` 顺序快照钉桩（s922-141）。

## 为什么钉

`PAGE_MODES` 是主导航的**单一事实源**（`app.py:53/295` 拿它当 `st.radio` 的 options、
`src/ui/next_step_panel.py:18` 拿它做 `page_target` 白名单、`tests/test_e2e_ui.py:89` 断言
`list(stage_radio.options) == PAGE_MODES`）。但在此之前，关于它内容的在册断言只有两条**成员级**的：

- `tests/test_app_routes_v6_panels.py:29` `assert "🧪 实验设计" in PAGE_MODES`
- `tests/test_app_routes_v6_panels.py:40` `assert PAGE_MODES[get_mode_index("不存在")] == "📈 数据分析"`

⇒ **插一页、删一页、换顺序在当时都不会翻红**。而顺序本身就是 UI 契约（侧栏从上到下、
`get_mode_index` 的 index 语义、`MODE_DESCRIPTIONS` 的书写序）。本件把它钉成**全量精确列表比对**。

## 改动了 PAGE_MODES 之后要回写哪些地方（失败信息里会重复这条）

1. `tests/test_app_routes_v6_panels.py`（路由集成测试，与本件同族）
2. 路由文档：`docs/architecture/app-split-blueprint.md`（现读唯一**逐项列全 7 页**的文档）；
   另 6 份文档只提到部分页面名（`docs/USER_QUICKSTART.md`、`docs/history/UPGRADE_REPORT_V5.10.md`、
   `docs/decisions/2026-08-24-impl-system-optimization-v510.md`、三份 `docs/insights/psy-*.md`），
   新增/删除页面时按各自覆盖面复核。
3. 同文件的 `MODE_DESCRIPTIONS`（现读与 `PAGE_MODES` **同序同集**，本件第 6 用例钉住）——
   漏了它，侧栏 `format_func` 会拿到缺键。

## 快照取法（先命令后数字，任务书点名口径）

```
D:\\code\\psy-analysis\\.venv\\Scripts\\python.exe -c "import sys; sys.path.insert(0,'.'); \\
from src.ui.navigation import PAGE_MODES; print(len(PAGE_MODES)); [print(repr(m)) for m in PAGE_MODES]"
→ 7
```

⚠️ 快照里的 `'🗂️ 模板中心'` 含 **U+FE0F 变体选择符**（码位 `1f5c2 fe0f 20 …`），手抄极易丢；
`test_snapshot_entry_0_keeps_its_variation_selector` 专门为这一格设防。
"""
from __future__ import annotations

import pathlib

import pytest

from src.ui.navigation import MODE_DESCRIPTIONS, PAGE_MODES, get_mode_index

# ── 快照值（2026-09-23T01:35 现取，psy HEAD bcb21f4，工作树 src/ui/navigation.py:6-14）──
SNAPSHOT_PAGE_MODES = [
    "🗂️ 模板中心",
    "📚 文献与选题",
    "📋 问卷设计",
    "🧪 实验设计",
    "📈 数据分析",
    "📝 论文写作",
    "📦 交付包导出",
]

SYNC_HINT = (
    "PAGE_MODES 是主导航单一事实源：改它必须同步回写 "
    "tests/test_app_routes_v6_panels.py 与路由文档 docs/architecture/app-split-blueprint.md"
    "（并检查 src/ui/navigation.py::MODE_DESCRIPTIONS 是否同序）"
)


# ────────────────────────── 1. 全量顺序快照 ──────────────────────────
def test_page_modes_exact_list_snapshot():
    """**列表精确比对**（含顺序）。插页/删页/换序都在此翻红。"""
    assert PAGE_MODES == SNAPSHOT_PAGE_MODES, SYNC_HINT


def test_page_modes_count_snapshot():
    """计数快照单列一条：插页时先在这里给出「7 → 8」的清晰读数，而不是只看到长列表 diff。"""
    assert len(PAGE_MODES) == 7, SYNC_HINT


def test_page_modes_membership_is_closed_both_ways():
    """集合双向比对：把「多了哪页」和「少了哪页」分开报，避免只看 diff 猜方向。"""
    extra = [m for m in PAGE_MODES if m not in SNAPSHOT_PAGE_MODES]
    missing = [m for m in SNAPSHOT_PAGE_MODES if m not in PAGE_MODES]
    assert (extra, missing) == ([], []), SYNC_HINT


# ────────────────────────── 2. 快照本身的可信度 ──────────────────────────
def test_snapshot_values_actually_appear_in_navigation_source():
    """自证「快照值 == 事实源文本」——任务书要求的 rg 一致性核对的**可执行版**。

    本机无 ripgrep（纪律档 §七/§十已记为全工作区事实），故用 python 逐串核对
    `src/ui/navigation.py` 原文；改完事实源而忘了改快照，本用例先红。
    """
    nav_text = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "ui" / "navigation.py"
    ).read_text(encoding="utf-8")
    not_found = [m for m in SNAPSHOT_PAGE_MODES if m not in nav_text]
    assert not_found == [], f"快照里有 {len(not_found)} 项在 src/ui/navigation.py 原文中找不到：{not_found}"


def test_snapshot_entry_0_keeps_its_variation_selector():
    """`'🗂️ 模板中心'` = `U+1F5C2 U+FE0F SP ...`；**手抄快照最常丢 U+FE0F**。

    丢了会变成长列表 diff 里几乎看不出来的「相等却不等」，所以单钉码位。
    """
    assert SNAPSHOT_PAGE_MODES[0] == "\U0001f5c2\ufe0f 模板中心"
    assert PAGE_MODES[0] == "\U0001f5c2\ufe0f 模板中心"
    assert "\ufe0f" in PAGE_MODES[0]


@pytest.mark.parametrize("mode", SNAPSHOT_PAGE_MODES)
def test_every_mode_is_unique_trimmed_and_emoji_prefixed(mode):
    """格式约束：无重复、无首尾空白、非空、以非 ASCII（emoji）开头。

    重复项会让 `PAGE_MODES.index()` 静默取第一个；带尾空格会让 `st.radio` 的
    `index=` 计算与 `get_mode_index` 不一致。两条都是「换了个写法就悄悄坏」。
    """
    assert PAGE_MODES.count(mode) == 1, f"{mode!r} 在 PAGE_MODES 里出现多次：{SYNC_HINT}"
    assert mode in SNAPSHOT_PAGE_MODES
    assert mode == mode.strip() and mode
    assert ord(mode[0]) > 127, f"{mode!r} 不再以 emoji 开头，侧栏视觉序与文档需同步"


# ────────────────────────── 3. 与同文件契约的耦合 ──────────────────────────
def test_mode_descriptions_are_same_order_and_same_set():
    """`MODE_DESCRIPTIONS` 与 `PAGE_MODES` **同序同集**（现读成立，钉住防漂移）。

    插页而漏写说明，侧栏 `format_func` 会 KeyError / 缺描述——这比顺序变化更常发生。
    """
    assert list(MODE_DESCRIPTIONS) == PAGE_MODES, (
        f"MODE_DESCRIPTIONS 与 PAGE_MODES 不再同序同集；{SYNC_HINT}"
    )


def test_get_mode_index_agrees_with_snapshot_position_for_every_mode():
    """index 语义：`get_mode_index(m)` 必须等于 m 在快照里的位置（逐页）。"""
    for expected, mode in enumerate(SNAPSHOT_PAGE_MODES):
        assert get_mode_index(mode) == expected, f"{mode!r} 的位置从 {expected} 变了；{SYNC_HINT}"


def test_unknown_mode_still_falls_back_to_data_analysis_slot():
    """未知页回退到「📈 数据分析」——回退目标本身也是顺序的一部分（index 4）。"""
    assert get_mode_index("不存在的页面") == SNAPSHOT_PAGE_MODES.index("📈 数据分析") == 4
    assert PAGE_MODES[get_mode_index("不存在的页面")] == "📈 数据分析"
