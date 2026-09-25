# -*- coding: utf-8 -*-
"""s924-59 · LR 漏斗修订 `_lr_pending_rescore` 的 AppTest 端到端（兑现 s922-105 遗留出口）。

来账：`zcode-bridge/done/s922-105-lr-dirty-frozen-pins.result.md` §遗留问题 1（正文 :83）原话
    「③ 的两条用例是『真实语句 exec ＋ AST 结构冻结』，**不是端到端渲染** `render_literature_review`
      …出口：B 案施工时补一条 AppTest 端到端，确认 rerun 会重新调用打分器（永久重试的用户可见后果）」
本件就是那条端到端：真 `streamlit.testing.v1.AppTest` 起 `render_literature_review`，
钉「重调 / 清标志 / 二次 rerun 不再重调」三件事。只加测试，**零生产码改动**。

锚点复核（本班 2026-09-25 现取，`src/ui/literature_review_panel.py`）：
  * `:121` `if st.session_state.get("_lr_pending_rescore"):`     —— 消费侧
  * `:122` `_do_relevance_rescore(upstream, lr_state)`            —— 打分入口
  * `:123` `st.session_state["_lr_pending_rescore"] = False`      —— 清标志侧
  * `:180` `st.session_state["_lr_pending_rescore"] = True`       —— 置位侧（微调案，回到 stage 5）
  * `:189` `st.session_state["_lr_pending_rescore"] = True`       —— 置位侧（重新选题案，回到 stage 1）
    ⚠ 卷宗只点名 `:180` 一枚生产者；磁盘实况是**两枚**（与 s922-105 遗留问题 2 的「生产者在
    `:180`／`:189`」一致）。故本件两条置位侧都钉，见 `test_revide_dialog_sets_pending_rescore`。

沙盒纪律（本仓最危险面：`data/` 整层在 `.gitignore` 里 ⇒ git 无还原点）：
`tests/conftest.py::_APP_TEST_FILES` 的 autouse 夹具只重定向 PSY_ANALYSIS_HOME／archive／logs／
usage_logger，**不含 `LITERATURE_FEED_DATA_ROOT`**。故本件自带 `feed_sandbox` 夹具把文献库根指进
每例独占的 `tmp_path`，并在 `test_feed_guard_is_live` 里正面证它生效（纪律档 §九.2／§廿一）。
打分器（`rescore_existing_items`）由离线桩替代 ⇒ 全程零 LLM、零网络。

⚠ 施工障碍与处置（s924-59 实测，**非本件引入**）：`_render_export_tab`（`:647`）里有**两枚同名
`key="_lr_dl_review"` 的 `st.download_button`**（`:670` 在 `try` 内、`:727` 在 `try` 外），
文献列表非空时后一枚必抛**未被捕获**的 `StreamlitDuplicateElementKey`，把整帧渲染打断。
本件的对象是 `:121→:123` 那条标志消费链，它在 `:147` 之前执行 ⇒ 主用例用 `quiet_export_tab`
夹具把那一枚 tab 换成 no-op，**不会**影响被钉的调用计数（顺序见上）。
缺陷本身由 `test_export_tab_duplicate_key_defect_is_live` 单独钉住现状（不修、不改判据数值、
不给下载口挂白名单——那是导出/下载门禁域，超出执行手授权，见 `test_export_gate_global_scan.py`
与纪律档 §八）。修复后该钉桩应翻红并被复核。
"""
import pathlib
import sys

import pytest
from streamlit.testing.v1 import AppTest

import src.ui.literature_review_panel as panel
from src.literature_feed import paths as feed_paths

_ROOT = pathlib.Path(__file__).resolve().parents[1].as_posix()

_MISSING = object()   # _ss() 的「不给默认值」哨兵（不能用 None，None 可能是合法存量值）

# 最小会话壳：只起 render_literature_review 一枚主入口，不引 app.py（app.py 此刻是他班在册脏件）。
_PANEL_SCRIPT = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
import streamlit as st
from src.ui.literature_review_panel import render_literature_review

render_literature_review(tier="beginner")
""".replace("__ROOT__", _ROOT)

_UPSTREAM_KEY = "upstream_state"
_LR_KEY = "literature_review_state"

# 人造文献：一眼假的合成标题，不含任何真实研究结论；relevance 只用来观察写回。
_ITEMS = [
    {
        "key": "k1",
        "title": "Alpha Widget Study",
        "authors": ["Doe"],
        "year": 2024,
        "journal": "Journal of Synthetic Samples",
        "doi": "10.0000/syn.1",
        "abstract": "synthetic placeholder abstract about widgets",
        "source": "manual",
        "reading_status": "unread",
        "relevance_score": 0.10,
        "tags": [],
    },
    {
        "key": "k2",
        "title": "Beta Gadget Review",
        "authors": ["Roe"],
        "year": 2025,
        "journal": "Journal of Synthetic Samples",
        "doi": "10.0000/syn.2",
        "abstract": "synthetic placeholder abstract about gadgets",
        "source": "manual",
        "reading_status": "unread",
        "relevance_score": 0.20,
        "tags": [],
    },
]


@pytest.fixture
def feed_sandbox(monkeypatch, tmp_path):
    """把文献库根指进本例独占的空沙盒，并**硬检**没有任何在进程模块仍指向生产库根。

    ⚠ 关键实测：`LITERATURE_FEED_DATA_ROOT` 只在 **import 期**被读一次
    （`src/literature_feed/paths.py:16-25` 是模块期常量），且全仓有 8 个模块
    **按值**再绑一次（`from ..paths import DB_PATH` 等：`__init__.py:10`、
    `storage/feed_store.py:29`、`storage/budget_tracker.py:22`、`storage/jsonl_archive.py:22`、
    `scheduler/lock_manager.py:23`、`scheduler/daily_runner.py:67`、`trend/__init__.py:18`、
    `ui/feed_panel.py:24`）⇒ **单靠 monkeypatch `paths.DB_PATH` 保护不到那些已绑定的副本。**
    真正生效的守卫是「pytest 进程启动前就设好环境变量」。本夹具因此做两件事：
      ① 重指 `paths` 上的三个常量（覆盖走 `paths.X` 的点）；
      ② 扫 `sys.modules`，任一模块的 `DB_PATH` 仍等于生产 `data/literature_feed/feed.sqlite`
         就**当场判红**——宁可测试失败，也不拿生产库当沙盒（`data/` 整层 gitignored ⇒ 无还原点）。
    """
    root = tmp_path / "feed_root"
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(root))
    monkeypatch.setattr(feed_paths, "DATA_ROOT", root)
    monkeypatch.setattr(feed_paths, "DB_PATH", root / "feed.sqlite")
    monkeypatch.setattr(
        feed_paths, "TRENDING_WEIGHTS_PATH", root / "trending_weights.yaml")

    prod_db = (
        pathlib.Path(_ROOT) / "data" / "literature_feed" / "feed.sqlite"
    ).resolve()
    leaked = []
    for name, mod in list(sys.modules.items()):
        if mod is None or not name.startswith("src."):
            continue
        candidate = getattr(mod, "DB_PATH", None)
        if candidate is not None and pathlib.Path(str(candidate)).resolve() == prod_db:
            leaked.append(f"{name}.DB_PATH -> {candidate}")
    assert not leaked, (
        "文献库守卫未生效：以下模块仍指向生产库根，拒跑（请用 "
        "LITERATURE_FEED_DATA_ROOT=<沙盒> 包住 pytest 命令）：\n  " + "\n  ".join(leaked)
    )
    return root


@pytest.fixture
def offline_scorer(monkeypatch):
    """离线打分桩：只按标题里是否含给定关键词抬分，零 LLM、零网络。

    返回 (stub, calls) —— calls 记录每次打分的 (items_len, research_q)，
    用来否证「永久重试」（重试会留下第二次记录）。
    """
    calls: list = []

    def _stub(items_dict, research_q, candidate_vars=None):
        calls.append({"n_items": len(items_dict or []), "rq": research_q})
        out = []
        for d in (items_dict or []):
            e = dict(d)
            e["relevance_score"] = 0.9 if "widget" in str(e.get("title", "")).lower() else 0.3
            out.append(e)
        return out

    monkeypatch.setattr(panel, "rescore_existing_items", _stub)
    return _stub, calls


@pytest.fixture
def rescore_spy(monkeypatch):
    """包裹真 `_do_relevance_rescore`：计数后放行原实现（不是替换，故写回/提示面照样跑）。"""
    seen: list = []
    original = panel._do_relevance_rescore

    def _spy(upstream, lr_state):
        seen.append(True)
        return original(upstream, lr_state)

    monkeypatch.setattr(panel, "_do_relevance_rescore", _spy)
    return seen


@pytest.fixture
def quiet_export_tab(monkeypatch):
    """把 `_render_export_tab` 换成 no-op，绕开 HEAD 上那对同名 download key（见文件头）。

    被钉的标志消费链在 `render_literature_review` 的 `:121-123`，早于 tab 区的 `:147`
    ⇒ 本桩只屏蔽「渲染打断」，不屏蔽「打分器有没有被调」。
    """
    monkeypatch.setattr(panel, "_render_export_tab", lambda items, lr_state: None)


def _launch(feed_sandbox, seed_pending: bool, strict: bool = True) -> AppTest:
    """起一次真 AppTest 会话，会话里预置 upstream＋文献状态（可选预置 pending 标志）。"""
    at = AppTest.from_string(_PANEL_SCRIPT, default_timeout=90)
    at.session_state[_UPSTREAM_KEY] = {
        "phase": "literature_review",
        "current_stage": 6,
        "research_question": "widget adoption",
        "candidate_vars": {"dependent_vars": ["adoption"], "independent_vars": ["widget"]},
    }
    at.session_state[_LR_KEY] = {
        "literature_items": [dict(d) for d in _ITEMS],
        "notes": [],
        "matrix": {
            "dimensions": ["样本量", "研究设计", "主要发现", "效应量", "局限"],
            "cells": {},
            "highlighted_keys": [],
        },
        "themes": [],
        "gaps": [],
        "last_search_query": "",
        "last_search_at": "",
    }
    if seed_pending:
        at.session_state["_lr_pending_rescore"] = True
    at.run()
    if strict:
        assert not at.exception, f"主入口渲染抛异常：{[e.value for e in at.exception]}"
    return at


def _click(at: AppTest, label: str) -> AppTest:
    hits = [b for b in at.button if b.label == label]
    assert len(hits) == 1, f"按钮「{label}」命中 {len(hits)} 枚 ⇒ 判据失去唯一锚点"
    hits[0].click().run()
    assert not at.exception, f"点「{label}」后抛异常：{[e.value for e in at.exception]}"
    return at


def _ss(at: AppTest, key: str, default=_MISSING):
    """读 AppTest 会话状态。

    ⚠ AppTest 的 `session_state` 代理**没有 `.get()`**（实测 `AttributeError: get not found
    in session_state`，走的是 `__getattr__`→KeyError 分支），只支持下标与 `in`。
    """
    try:
        return at.session_state[key]
    except KeyError:
        if default is _MISSING:
            raise
        return default


# ---------------------------------------------------------------------------
# 1. 卷宗三条断言：重调 / 清标志 / 不永久重试（最小会话壳＋直接置标志）
# ---------------------------------------------------------------------------


def test_pending_flag_makes_rerun_call_rescore_once_and_clear_it(
    feed_sandbox, quiet_export_tab, offline_scorer, rescore_spy
):
    """置 `_lr_pending_rescore=True` → 首次渲染即调 `_do_relevance_rescore` 恰好 1 次，且标志被清为 False。

    钉的是 `:121→:122→:123` 这条消费链。若 `:123` 的清标志被删，本例第二条断言当场红；
    若 `:122` 的调用被摘，第一条断言红（计数 0）。
    """
    _stub, score_calls = offline_scorer

    at = _launch(feed_sandbox, seed_pending=True)

    assert len(rescore_spy) == 1, (
        f"rerun 后 `_do_relevance_rescore` 应被调 1 次，实调 {len(rescore_spy)} 次"
    )
    assert at.session_state["_lr_pending_rescore"] is False, (
        f"标志应被清为 False，实为 {at.session_state['_lr_pending_rescore']!r}"
    )
    # 打分器真被走到（不是只清了标志就完事）
    assert len(score_calls) == 1
    assert score_calls[0]["n_items"] == len(_ITEMS)


def test_second_rerun_does_not_rescore_again_no_permanent_retry(
    feed_sandbox, offline_scorer, rescore_spy, quiet_export_tab
):
    """二次 rerun 不再重调＝无永久重试（s922-105 出口点名的「用户可见后果」那一面）。

    标志已在首轮清为 False ⇒ 第二轮 `:121` 守卫为假。若实现退化成「每帧都重打分」
    （永久重试），这里计数会变成 2，当场红。
    """
    at = _launch(feed_sandbox, seed_pending=True)
    assert len(rescore_spy) == 1

    at.run()
    assert not at.exception, f"二次 rerun 抛异常：{[e.value for e in at.exception]}"

    assert len(rescore_spy) == 1, (
        f"二次 rerun 不该再调打分器（永久重试），实调 {len(rescore_spy)} 次"
    )
    assert at.session_state["_lr_pending_rescore"] is False


def test_no_pending_flag_means_zero_rescore_calls(
    feed_sandbox, quiet_export_tab, offline_scorer, rescore_spy
):
    """对照刀（否证面）：不置标志时 `_do_relevance_rescore` 一次都不该被调。

    没有这条，前两条的「计数==1」可能只是「无条件每次都调」的假绿。
    """
    _launch(feed_sandbox, seed_pending=False)

    assert rescore_spy == [], f"未置标志却调了 {len(rescore_spy)} 次 ⇒ 守卫失效"


# ---------------------------------------------------------------------------
# 2. 置位侧端到端：真按钮点击链（:180 微调案 / :189 重新选题案）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label, expect_stage",
    [
        ("✅ 微调现有研究问题（回到 stage 5）", 5),
        ("🌱 重新选题（回到 stage 1）", 1),
    ],
    ids=["finetune_stage5", "restart_stage1"],
)
def test_revise_dialog_sets_pending_rescore(
    feed_sandbox, quiet_export_tab, offline_scorer, rescore_spy, label, expect_stage
):
    """从文献综述页点「修订研究问题」→ 选案，标志被置起且下一帧重打分恰好一次。

    卷宗只点名 `:180` 一枚生产者；`:189`（重新选题）是同型第二枚（s922-105 遗留问题 2），
    本例用 parametrize 两案都钉，缺一案即漏面。
    """
    at = _launch(feed_sandbox, seed_pending=False)
    assert rescore_spy == [], "起手未置标志，不该有打分调用"

    at = _click(at, "🔄 修订研究问题")            # 开对话框（置 _lr_revise_dialog）
    assert at.session_state["_lr_revise_dialog"] is True

    at = _click(at, label)                        # 置 `_lr_pending_rescore=True` + st.rerun()

    # 该按钮点完即 st.rerun() ⇒ 同一帧内标志先 True、随后被消费链清 False。
    # 可观察到的用户可见后果就是「打分器被重调了一次」＋标志回到 False。
    assert len(rescore_spy) == 1, (
        f"点「{label}」后应重打分 1 次，实调 {len(rescore_spy)} 次"
    )
    assert at.session_state["_lr_pending_rescore"] is False
    assert at.session_state[_UPSTREAM_KEY]["current_stage"] == expect_stage
    assert at.session_state[_UPSTREAM_KEY]["phase"] == "funnel"

    # 无永久重试：再跑一帧不该又调
    at.run()
    assert len(rescore_spy) == 1


def test_cancel_leaves_no_pending_flag_and_no_rescore(
    feed_sandbox, quiet_export_tab, offline_scorer, rescore_spy
):
    """「取消」案：对话框关掉但不置标志 ⇒ 零重打分（置位侧的否证对照）。"""
    at = _launch(feed_sandbox, seed_pending=False)
    at = _click(at, "🔄 修订研究问题")
    at = _click(at, "取消")

    assert not _ss(at, "_lr_pending_rescore", False), (
        f"取消案不该置起 pending 标志，实为 {_ss(at, '_lr_pending_rescore', '<absent>')!r}"
    )
    assert rescore_spy == [], f"取消案却重打分了 {len(rescore_spy)} 次"


# ---------------------------------------------------------------------------
# 3. 沙盒守卫生效自证（本仓 data/ 无 git 还原点 ⇒ 必须正面证）
# ---------------------------------------------------------------------------


def test_feed_guard_is_live(feed_sandbox, quiet_export_tab, offline_scorer, rescore_spy):
    """证 `LITERATURE_FEED_DATA_ROOT` 在本例会话里真生效：库根＝沙盒、生产根未被指。

    两条正面读数：① `paths.DATA_ROOT`/`DB_PATH` 落在本例 `tmp_path`；
    ② 跑完一帧渲染后沙盒目录仍然没有 `feed.sqlite`（本件不碰文献库，属否证性自证）。
    """
    assert pathlib.Path(feed_paths.DB_PATH).parent == feed_sandbox
    assert str(feed_sandbox) in str(feed_paths.DATA_ROOT)

    _launch(feed_sandbox, seed_pending=True)

    assert not (feed_sandbox / "feed.sqlite").exists(), (
        "本件不应创建文献库文件；若出现说明渲染链里有人开始写文献库，须复核守卫面"
    )


# ---------------------------------------------------------------------------
# 4. 钉住 HEAD 既有缺陷（现状钉桩，不是规范背书）
# ---------------------------------------------------------------------------


def test_export_tab_duplicate_key_defect_is_live(feed_sandbox, offline_scorer, rescore_spy):
    """**钉现状**：不 stub 导出 tab 时，文献列表非空会因同名 key 打断整帧渲染。

    两枚 `key="_lr_dl_review"`（`:670` 在 `try` 内、`:727` 在 `try` 外）⇒ 后一枚抛出的
    `StreamlitDuplicateElementKey` 不在 `try` 保护范围内，直接向上传播。
    本例同时确认「即便整帧被打断，`:121-123` 的标志消费仍然先跑完了」——
    这正是 `quiet_export_tab` 那批用例的合法性来源（桩没挡在被钉的链路上）。

    🔴 修复该缺陷（给两枚 key 改名）后**本例应翻红**，届时请连同
    `quiet_export_tab` 一起撤掉，并把 strict 恢复为默认。
    本班不改生产码、不给下载口挂白名单（导出/下载门禁域超出执行手授权）。
    """
    at = _launch(feed_sandbox, seed_pending=True, strict=False)

    # ⚠ 实测 `at.exception[i].value` 是**消息字符串**而非异常对象（`type(...).__name__` 读出 'str'）
    #    ⇒ 判别只能按消息文本匹配。
    msgs = " | ".join(str(e.value) for e in at.exception)
    assert at.exception, "未复现同名 key 打断：HEAD 缺陷可能已被修，请撤掉本钉桩与 quiet_export_tab"
    assert "multiple elements with the same `key='_lr_dl_review'`" in msgs, (
        f"消息里没找到同名 key 打断，实得：{msgs}"
    )
    # 标志消费链在 tab 之前，故虽整帧被打断，打分器仍已被调 1 次
    assert len(rescore_spy) == 1
