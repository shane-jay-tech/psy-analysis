# -*- coding: utf-8 -*-
"""s922-108：`restore_workspace` 的**非成对恢复现状**钉桩（df 独活 / inspector 缺席且不报警）。

⚠️ 本档钉的是「改前基线」，不是「应有形态」。普查档
`docs/insights/psy-session-state-attr-read-census-20260921.md` **结论 4**（:98-101 行）点名的
值语义风险正是这条路径；日间若给恢复路径补成对断言（结论 4 的建议收口顺序第一步），
本档用例应主动转红 —— 那是设计内翻正信号，请改断言不要删用例。

锚点复核（2026-09-22 本班按磁盘实况，HEAD `9551e1d`，**任务书三处锚点零漂移**）：
- `src/utils/workspace.py:594` `df_b64 = loaded.get("df_b64")`
- `:598` `st.session_state.df = pd.read_csv(io.BytesIO(csv_bytes))`（包在 `:596-601` 的 try 里，
  `except Exception: pass` —— 解码失败**静默吞**）
- `:606-611` `for k in ["meta", "inspector", "file_name", "analysis_history", ...]: if k in loaded`
  逐键独立条件恢复，与 df 分支**零耦合**
- 写侧对照 `:238-241` `build_workspace_snapshot`：四键各自 `if v is not None` 才落盘 ⇒ 快照本身也不成对

普查档的两处 app.py 行号**已漂**（本班实测留痕，不影响结论本身）：
结论 4 记的「显式合取只有 1 处 `app.py:1173`」现在落在 **`app.py:990`**；
`if st.session_state.df is not None:` 属性式读取实测 4 处（`:767 / :877 / :990 / :1050`），
合取式仍**只有 1 处**（`:990`）—— 结论 4 的实质判断成立，只是行号要跟。

隔离口径：`src/utils/workspace.py` 全模块 **零文件 IO**（`open(` / `Path(` / `.home(` / `json.load` /
`write_text` / `mkdir` 六个串实测零命中，见 `test_restore_module_has_zero_file_io`），
项目文件由调用方读写 ⇒ 本班一律用 `tmp_path` 造真 JSON 文件再回读喂进 `restore_workspace`，
不触碰 `~/.psy_analysis`。零 sqlite、零网络、零 LLM、零子进程。
"""
from __future__ import annotations

import base64
import io
import json

import pandas as pd
import pytest
import streamlit as st

from src.data.inspector import inspect_dataframe
from src.utils.workspace import build_workspace_snapshot, restore_workspace

# 现状常量：恢复分支里 df 与这三键**不配对**（结论 4 的核心事实）
PARTNER_KEYS = ("meta", "inspector", "file_name", "analysis_history")
CURRENT_SCHEMA = "v3.5"  # workspace.py:403，写进 payload 以避开迁移链旁路


def _csv_b64(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")


def _sample_df(n=3) -> pd.DataFrame:
    return pd.DataFrame({"score": list(range(n)), "group": [f"g{i}" for i in range(n)]})


def _project_file(tmp_path, payload: dict, name: str = "proj_001.json"):
    """把 payload 落成 tmp_path 下的真项目文件再回读，返回 (路径, 回读后的 dict)。

    走真文件往返是因为结论 4 的风险载体是「项目文件缺字段」，不是内存字典缺键——
    少这一跳就会把 JSON 层（键丢失/None 变体）的形态漏掉。
    """
    path = tmp_path / "projects" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _keys_present() -> set:
    return {k for k in st.session_state.keys()}


# ─────────────────── 现状形态判据（与 s922-104 的 _pinned_paths 同构） ───────────────────
def _df_should_restore(payload: dict) -> bool:
    """现状语义：`df_b64` 非空 **且能解码成 CSV** 才会写 `session_state.df`。

    判据必须先算这个，否则会把「脏 base64 被 except 吞掉」误判成「加了成对前提」——
    那两种形态在 session_state 上的留痕**本来就完全相同**（这正是本档要钉的风险）。
    """
    raw = payload.get("df_b64")
    if not raw:
        return False
    try:
        pd.read_csv(io.BytesIO(base64.b64decode(raw)))
    except Exception:
        return False
    return True


def _pinned_pairing_facts(payload: dict, present: set, restored: int) -> list[str]:
    """返回「偏离非成对现状」的原因列表；现状下应为空。

    三条判据都只认 payload 里**有没有**那个键、df 能不能解码，不认邻居键 ——
    这正是 `:594-611` 的写法。若施工方改成「四键齐备才写 df」或「缺 inspector 就补种/报警」，
    本函数就会报红。
    """
    fails: list[str] = []
    expect_df = _df_should_restore(payload)

    if expect_df and "df" not in present:
        fails.append("df_b64 可解码却没恢复：df 分支不再无条件单写（可能加了成对前提）")
    if not expect_df and "df" in present:
        fails.append("文件里没有可解码的 df_b64 却凭空冒出 df：补了默认种或从邻居键推导")
    if expect_df and not payload.get("inspector") and "inspector" in present:
        fails.append("缺 inspector 字段却被补种：恢复路径开始成对了")
    if expect_df and "df" in present and restored < 1:
        fails.append(f"df 已恢复却返回 {restored}：计数口径从「成功项数」变了")
    return fails


@pytest.fixture(autouse=True)
def clean_session_state():
    """逐个用例前后清空 session_state，防本班读漏别班留下的 df/inspector。"""
    st.session_state.clear()
    yield
    st.session_state.clear()


# ─────────────────────────────── 钉桩用例 ───────────────────────────────
def test_df_only_project_file_restores_df_and_leaves_inspector_absent(tmp_path):
    """普查档结论 4 主现场：只带 df_b64 的项目文件恢复后 df 非空、inspector **键根本不存在**。

    现状钉桩。`restored` 返回 1、不抛、不 warn —— 缺键这件事在恢复层零留痕，
    这正是结论 4 说的「值语义风险」而非「不存在风险」。
    """
    _path, loaded = _project_file(tmp_path, {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(_sample_df())})

    restored = restore_workspace(loaded)

    assert restored == 1
    assert st.session_state.df is not None and len(st.session_state.df) == 3
    assert "df" in _keys_present()
    for k in PARTNER_KEYS:
        assert k not in _keys_present(), f"恢复层不该凭空补 {k}"
    assert st.session_state.get("inspector") is None
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_downstream_df_guard_passes_while_conjunction_guard_fails(tmp_path):
    """结论 4 的爆点形态：df 单条件守卫过、合取守卫不过，且属性式读 inspector 当场 AttributeError。

    现状钉桩（**报错发生在离缺键现场很远的下游**，形态是 AttributeError 而不是缺键）。
    两种守卫形状照 `app.py:767/:877/:1050`（单条件）与 `app.py:990`（唯一一处合取）各复刻一行，
    不 import app.py —— app.py 是他班 12/40 在途件，本班不碰。
    """
    _path, loaded = _project_file(tmp_path, {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(_sample_df(2))})
    restore_workspace(loaded)

    single_cond = st.session_state.df is not None          # app.py:767 形状
    conjunction = (st.session_state.df is not None
                   and st.session_state.get("inspector") is not None)  # app.py:990 形状
    assert single_cond is True and conjunction is False
    with pytest.raises(AttributeError):
        _ = st.session_state.inspector  # 属性式读取在此刻是整页红，不是 None


def test_dirty_df_b64_is_swallowed_without_raise_or_partial_state(tmp_path):
    """结论 4 点名的 `except Exception: pass`：脏 df_b64 静默吞，恢复计数不涨、df 键不出现。

    现状钉桩。这里喂非法 base64（`b64decode` 抛 binascii.Error）。
    要钉的点是「用户看不出任何异常」——现场既无 log 也无 session 标记，
    恢复后与「文件本来就没 df」两种状态**在 session_state 里不可区分**。
    """
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": "!!!not-base64!!!"}
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)  # 不许抛

    assert restored == 0
    assert _keys_present() == set()  # 连一个键都没写 ⇒ 与「文件本来没 df」逐字节同形
    assert "df" not in _keys_present()
    assert st.session_state.get("df") is None
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []
    assert _df_should_restore(loaded) is False  # 前提自证：这份 b64 确实不可解码


def test_empty_string_df_b64_is_skipped_before_the_try_block(tmp_path):
    """结论 4 相邻面：`if df_b64:` 短路在 try **之前**（`:595`），空串连解码都不进。

    现状钉桩。与上一条同为「零红」，但走的是 falsy 分支而不是 except 分支 ——
    两分支在 session_state 上留痕完全相同，因此下游更分不出「没数据」与「数据坏了」。
    """
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": ""}
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored == 0 and "df" not in _keys_present()
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_all_four_partner_keys_present_restore_every_key_independently(tmp_path):
    """四键齐备时逐键恢复：`restored` == 1(df) + 4 = 5，inspector 非 None。

    现状钉桩（施工后的对照组：这条在成对断言落地后仍应绿，用来证明改动没把齐备路径改坏）。
    `:606-608` 的循环还带 undergrad_*/app_mode/quick_model_id 五个键，本班只钉普查结论 4 点名的四键。
    """
    df = _sample_df(3)
    payload = {
        "_schema": CURRENT_SCHEMA,
        "df_b64": _csv_b64(df),
        "meta": {"rows": 3},
        "inspector": inspect_dataframe(df),
        "file_name": "survey.csv",
        "analysis_history": [{"test": "ttest"}],
    }
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored == 5
    assert _keys_present() >= {"df"} | set(PARTNER_KEYS)
    assert st.session_state.inspector is not None
    assert st.session_state.file_name == "survey.csv"
    pd.testing.assert_frame_equal(st.session_state.df, df)
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_snapshot_roundtrip_through_real_project_file_drops_none_partners(tmp_path):
    """写侧→文件→读侧全链路：df 有值而 inspector 为 None 时，快照**只带 df_b64**，恢复后必然单活。

    现状钉桩。`build_workspace_snapshot:238-241` 对四键各用 `if v is not None`，
    所以「df 独活」不是构造出来的畸形文件，而是上传后尚未跑 inspect 的**正常中间态**会产出的形态——
    这条把结论 4 的风险从「假设有人手改了项目文件」升级为「常规链路可自然产生」。
    """
    df = _sample_df(4)
    st.session_state.df = df
    st.session_state.meta = {"n": 4}
    st.session_state.inspector = None       # inspect 还没跑
    st.session_state.file_name = None
    st.session_state.analysis_history = None
    snap = build_workspace_snapshot()
    assert "df_b64" in snap and "meta" in snap
    assert "inspector" not in snap and "file_name" not in snap  # None 键根本不落盘

    path, loaded = _project_file(tmp_path, snap)
    st.session_state.clear()
    restored = restore_workspace(loaded)

    assert restored == 2  # df + meta
    assert "inspector" not in _keys_present()
    assert path.exists() and path.parent.is_relative_to(tmp_path)
    pd.testing.assert_frame_equal(st.session_state.df, df)


def test_restore_module_has_zero_file_io():
    """结构性自证：`workspace.py` 全模块零文件 IO ⇒ 本班不可能碰 `~/.psy_analysis`。

    现状钉桩（也是完成标准 3 的证法）：项目文件的读写在调用方
    （`src/ui/project_panel.py:62/:83/:97` 是 `restore_workspace` 的三个调用点），
    恢复函数只吃已加载的 dict。判据取 `inspect.getsource` 的原文子串扫描，不靠 git status
    （`data/` 与本仓 `~/.psy_analysis` 都在 git 视野外，git status 恒空＝零证明力）。
    """
    import inspect

    import src.utils.workspace as ws_mod

    src = inspect.getsource(ws_mod)
    for needle in ("open(", "Path(", ".home(", "json.load", "write_text", "mkdir"):
        assert needle not in src, f"workspace 模块出现文件 IO 痕迹 {needle!r}，tmp_path 隔离前提失效"


def test_pairing_predicate_is_discriminating_against_a_paired_form(tmp_path):
    """反向用例：判据必须能区分「非成对现状」与「已改成成对」——否则本档全是假绿。

    与 s922-104 的两条 monkeypatch 反向用例同一套路，但这里喂的是**两份真项目文件**：
    ① 「缺 inspector 的真风险文件」在现状判据下不报红（判据不误伤）；
    ② 人为造出一份「成对断言已实施后」的读数（df 被拦下不写、inspector 被补种、计数归 0），
       判据必须**同时**报出两条原因。哪天有人把判据改成恒真，这一条会先炸。
    """
    df_ok = _sample_df(2)
    complete = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(df_ok), "inspector": inspect_dataframe(df_ok)}
    risky = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(df_ok)}

    _p1, loaded_full = _project_file(tmp_path, complete, name="complete.json")
    restore_workspace(loaded_full)
    assert _pinned_pairing_facts(loaded_full, _keys_present(), 2) == []  # ① 齐备文件不误伤

    st.session_state.clear()
    _p2, loaded = _project_file(tmp_path, risky, name="risky.json")
    restored = restore_workspace(loaded)
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []  # ① 风险文件也不误伤

    paired_form = (_keys_present() - {"df"}) | {"inspector"}  # ② 施工后的形态
    assert "df" not in paired_form and "inspector" in paired_form
    failures = _pinned_pairing_facts(loaded, paired_form, 0)
    assert len(failures) == 2, f"判据应同时报出两条偏离，实测 {failures}"
    assert any("没恢复" in r for r in failures), failures
    assert any("成对" in r for r in failures), failures


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
