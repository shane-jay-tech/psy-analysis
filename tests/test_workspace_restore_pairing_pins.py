# -*- coding: utf-8 -*-
"""`restore_workspace` 的**成对恢复契约**钉桩（案 a：四键齐备才写 df）。

本档的来历分两代，读改动时请连起来看：
- **s922-108**（09-22，HEAD `9551e1d`）钉的是「**改前基线**」——df 独活、inspector 缺席且不报警，
  并在档头写明「日间若给恢复路径补成对断言（普查档结论 4 建议收口顺序第一步），
  本档用例应主动转红——那是设计内翻正信号，请改断言不要删用例」。
- **s927-28**（本班，HEAD `635680e`）落地案 a，按上述预告**把断言翻正、一条用例没删**，
  并补「缺键恢复被拒／四键齐备成功」的成对断言。翻正点逐条标了 `s927-28 翻正` 便于回查。

施工面：`src/utils/workspace.py` 新增 `DF_PARTNER_KEYS` / `missing_df_partner_keys()`，
`restore_workspace` 的 df 分支改为「四键（meta/inspector/file_name/analysis_history）**齐备且非 None**
才解码写回」，缺键时记一条 `logger.warning` 并整组不写；其余键的恢复条件、返回值口径均未变。

为什么判据是「非 None」而不是「键在不在」：普查档
`docs/insights/psy-session-state-attr-read-census-20260921.md` **结论 4**（:98-101）点名的
是**值语义**风险——app.py 一片读点用 `if st.session_state.df is not None:` 掩护
meta / inspector / file_name / analysis_history 的读取，键存在但为 None 时守卫照样过，
报错发生在离缺键现场很远的下游、形态是 AttributeError/TypeError 而不是缺键。

本班实测的收口范围（**与卷宗锚点数不一致，按磁盘实况收窄**）：他键守卫点位现值 **11** 处
（工作树版与 HEAD 版 app.py 同值；卷宗写 13），其中外层守卫测 `df` 因而被案 a 收口的是 **6** 处，
守卫测 `analysis_output`／`undergrad_mode` 的 5 处**案 a 收不到**。逐点表见
`docs/insights/s927-28-guard13.md`。

锚点复核（HEAD `635680e` 现取）：
- `src/utils/workspace.py:594` `df_b64 = loaded.get("df_b64")` → 现值 `:616`，其上新增案 a 门卫
- `:606-611` 的 `for k in ["meta", "inspector", "file_name", "analysis_history", ...]: if k in loaded`
  → 现值 `:637-642`，逐键条件**未改**（案 a 只收紧 df 一侧）
- 写侧对照 `build_workspace_snapshot:238-241` 四键各 `if v is not None` **未改**（改它＝另一单）

隔离口径：`src/utils/workspace.py` 全模块**零文件 IO**（见 `test_restore_module_has_zero_file_io`），
项目文件由调用方读写 ⇒ 一律用 `tmp_path` 造真 JSON 文件再回读喂进 `restore_workspace`，
不触碰 `~/.psy_analysis`，不写 `data/`。零 sqlite、零网络、零 LLM、零子进程。
"""
from __future__ import annotations

import base64
import io
import json
import logging

import pandas as pd
import pytest
import streamlit as st

from src.data.inspector import inspect_dataframe
from src.utils.workspace import (
    DF_PARTNER_KEYS,
    build_workspace_snapshot,
    missing_df_partner_keys,
    restore_workspace,
)

# 现状常量：df 在恢复侧必须与这四键成对（案 a）
PARTNER_KEYS = ("meta", "inspector", "file_name", "analysis_history")
CURRENT_SCHEMA = "v3.5"  # workspace.py:403，写进 payload 以避开迁移链旁路


def _csv_b64(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")


def _sample_df(n=3) -> pd.DataFrame:
    return pd.DataFrame({"score": list(range(n)), "group": [f"g{i}" for i in range(n)]})


def _complete_payload(df: pd.DataFrame | None = None, **overrides) -> dict:
    """四键齐备的项目文件负载（案 a 之后 df 能被恢复的**唯一**形态）。"""
    df = _sample_df(3) if df is None else df
    payload = {
        "_schema": CURRENT_SCHEMA,
        "df_b64": _csv_b64(df),
        "meta": {"rows": len(df)},
        "inspector": inspect_dataframe(df),
        "file_name": "survey.csv",
        "analysis_history": [],
    }
    payload.update(overrides)
    return payload


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


# ─────────────── 成对契约判据（s922-108 的现状判据按预告翻正） ───────────────
def _df_should_restore(payload: dict) -> bool:
    """案 a 语义（s927-28 翻正）：`df_b64` 非空 **且四键齐备非 None** 才会写 `session_state.df`。

    改前的判据只看「有 df_b64 且能解码」，那正是 `:594-611` 零耦合的写法。
    解码失败仍算「不该恢复」——案 a 的门卫在解码**之前**，所以脏 b64 与缺键两种形态
    在 session_state 上依然同形（这条没被本单改坏，见 `test_dirty_df_b64_*`）。
    """
    raw = payload.get("df_b64")
    if not raw:
        return False
    if missing_df_partner_keys(payload):
        return False
    try:
        pd.read_csv(io.BytesIO(base64.b64decode(raw)))
    except Exception:
        return False
    return True


def _pinned_pairing_facts(payload: dict, present: set, restored: int) -> list[str]:
    """返回「偏离案 a 成对契约」的原因列表；契约成立时应为空（s927-28 由现状判据翻正而来）。

    四条判据都从 payload 出发反推应有形态，不看实现——若有人把门卫改回「df 独写」
    或改成「连兄弟键一起不写」，本函数立刻报红。
    """
    fails: list[str] = []
    expect_df = _df_should_restore(payload)

    if expect_df and "df" not in present:
        fails.append("四键齐备且可解码却没恢复 df：案 a 的门卫写过头了（或解码分支被改坏）")
    if not expect_df and "df" in present:
        fails.append("缺兄弟键或不可解码却凭空写了 df：案 a 的成对前提失效（回退成 df 独活）")
    if expect_df:
        missing_now = [k for k in PARTNER_KEYS if k not in present]
        if missing_now:
            fails.append(f"df 已恢复但兄弟键缺席 {missing_now}：成对不变式破了")
        if restored < 1:
            fails.append(f"df 已恢复却返回 {restored}：计数口径从「成功项数」变了")
    return fails


@pytest.fixture(autouse=True)
def clean_session_state():
    """逐个用例前后清空 session_state，防本班读漏别班留下的 df/inspector。"""
    st.session_state.clear()
    yield
    st.session_state.clear()


# ─────────────────────────────── 契约用例 ───────────────────────────────
def test_df_only_project_file_is_refused_and_leaves_no_df(tmp_path):
    """s927-28 翻正（原 `test_df_only_project_file_restores_df_and_leaves_inspector_absent`）：
    只带 df_b64 的项目文件在案 a 下**整组不写**——改前它是 df 恢复、inspector 键根本不存在，
    正是普查结论 4 的现场；现在 df 也不写，且 `restored == 0`、不抛。
    """
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(_sample_df())}
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored == 0
    assert "df" not in _keys_present()
    for k in PARTNER_KEYS:
        assert k not in _keys_present(), f"恢复层不该凭空补 {k}"
    assert st.session_state.get("df") is None
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_df_restore_is_refused_when_any_one_partner_key_is_missing(tmp_path):
    """成对断言·被拒半边（逐键四格）：四键少任一个 ⇒ df 不写，**其余键照写**。

    「照写」是案 a 的边界：本单只收紧 df 一侧，没有把恢复改成全有或全无。
    """
    for missing in PARTNER_KEYS:
        st.session_state.clear()
        payload = _complete_payload()
        del payload[missing]
        _path, loaded = _project_file(tmp_path, payload, name=f"no_{missing}.json")

        restored = restore_workspace(loaded)

        assert "df" not in _keys_present(), f"缺 {missing} 却恢复了 df"
        assert restored == len(PARTNER_KEYS) - 1, f"缺 {missing} 时其余键应照恢复"
        for k in PARTNER_KEYS:
            if k != missing:
                assert k in _keys_present()
        assert missing not in _keys_present()
        assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_partner_key_present_but_null_also_refuses_df(tmp_path):
    """成对断言·被拒半边（None 变体）：键在但值为 null 也算缺——这才是结论 4 的**值语义**风险。

    判据若写成 `k in loaded`，这份文件就会放行 df，下游 `inspector` 读到 None 照样炸；
    本条与上一条合起来把「键在」与「值有用」分开钉住。
    """
    payload = _complete_payload(inspector=None)
    _path, loaded = _project_file(tmp_path, payload, name="null_inspector.json")

    restored = restore_workspace(loaded)

    assert missing_df_partner_keys(loaded) == ("inspector",)
    assert "df" not in _keys_present()
    # inspector 这一格被 `if k in loaded` 照原样写成 None（本单没改这条循环）
    assert st.session_state.get("inspector") is None and "inspector" in _keys_present()
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_all_four_partner_keys_present_restores_df_and_partners(tmp_path):
    """成对断言·成功半边（s922-108 的对照组，案 a 落地后**必须仍绿**）：四键齐备 ⇒ df 照恢复。

    齐备路径是用户日常形态，本条证明门卫没把好的文件一起拦掉：
    `restored == 1(df) + 4 == 5`、四键全部非 None、df 内容逐格相等。
    """
    df = _sample_df(3)
    payload = _complete_payload(df)
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored == 5
    assert _keys_present() >= {"df"} | set(PARTNER_KEYS)
    assert st.session_state.inspector is not None
    assert st.session_state.file_name == "survey.csv"
    assert st.session_state.analysis_history == []
    pd.testing.assert_frame_equal(st.session_state.df, df)
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_missing_partner_key_warning_is_emitted_and_mentions_the_gap(caplog, tmp_path):
    """被拒不许静默：案 a 拦下 df 时记一条 warning 并点名缺哪几键。

    改前的形态是「恢复层零留痕」（s922-108 现状钉 ①），调用方 `project_panel.py:62/:83/:97`
    又不消费返回值 ⇒ 用户与排障者都看不出 df 没回来。本班把留痕补在恢复层，
    没动返回值口径，也没往 session_state 塞新键（普查结论 3：非 _defaults 的键属性读会整页红）。
    """
    payload = _complete_payload()
    del payload["inspector"]
    _path, loaded = _project_file(tmp_path, payload, name="no_inspector.json")

    with caplog.at_level(logging.WARNING, logger="src.utils.workspace"):
        restore_workspace(loaded)

    msgs = [r.getMessage() for r in caplog.records
            if r.name == "src.utils.workspace" and r.levelno >= logging.WARNING]
    assert any("跳过 df" in m and "inspector" in m for m in msgs), msgs


def test_quiet_when_partners_are_complete(caplog, tmp_path):
    """反证配平：四键齐备时**不该**有本模块的 warning（否则上一条 warn 断言就是恒真的假绿）。

    只筛 `src.utils.workspace` 这一个 logger——裸模式跑 streamlit 会自己刷
    「missing ScriptRunContext」的 WARNING，跟案 a 无关，混进来会让本条永远红。
    """
    _path, loaded = _project_file(tmp_path, _complete_payload(), name="ok.json")

    with caplog.at_level(logging.WARNING, logger="src.utils.workspace"):
        restore_workspace(loaded)

    own = [r.getMessage() for r in caplog.records
           if r.name == "src.utils.workspace" and r.levelno >= logging.WARNING]
    assert own == []
    # 配平原判据的另一种写法：既没跳过 df，df 也确实回来了
    assert st.session_state.df is not None


def test_downstream_df_guard_cannot_be_fooled_by_a_df_only_file(tmp_path):
    """s927-28 翻正（原 `test_downstream_df_guard_passes_while_conjunction_guard_fails`）：
    结论 4 的爆点形态「单条件守卫过、合取守卫不过」由 df-only 文件驱动，案 a 之后**驱动不起来**。

    两种守卫形状照 `app.py:879/:887`（单条件）与 `app.py:990`（唯一一处合取）各复刻一行，
    不 import app.py——app.py 是他班 12/40 在途件，本班不碰。
    改前这里 `single_cond is True and conjunction is False`＋属性读当场 AttributeError；
    现在 df 压根没回来，单条件守卫与合取守卫同判 False，属性式读 inspector 仍是缺键红
    （键没被凭空补种），但**读点根本走不到**（它被同一个 df 守卫挡在外面）。
    """
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(_sample_df(2))}
    _path, loaded = _project_file(tmp_path, payload)
    restore_workspace(loaded)

    single_cond = st.session_state.get("df") is not None      # app.py:879 形状的判据
    conjunction = (st.session_state.get("df") is not None
                   and st.session_state.get("inspector") is not None)  # app.py:990 形状
    assert single_cond is False and conjunction is False      # 两判据同值＝不再分裂
    assert "df" not in _keys_present() and "inspector" not in _keys_present()
    with pytest.raises(AttributeError):
        _ = st.session_state.inspector  # 键仍不存在；但读点在 app.py 里被 df 守卫挡在前面


def test_dirty_df_b64_is_swallowed_without_raise_or_partial_state(tmp_path):
    """结论 4 点名的 `except Exception: pass`：脏 df_b64 静默吞，df 键不出现。

    s927-28 翻正：载荷补成**四键齐备**——改前它只有 df_b64，案 a 的门卫在解码之前就拦下，
    那条 try 分支根本没被走到，本例就会钉不到自己声称的东西。补键后「脏 b64 被 except 吞」
    这一面仍然可达，判据照旧：不抛、df 键不出现；四个兄弟键按各自条件恢复（restored==4）。
    """
    payload = _complete_payload(df=None)
    payload["df_b64"] = "!!!not-base64!!!"
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)  # 不许抛

    assert "df" not in _keys_present()
    assert st.session_state.get("df") is None
    assert restored == 4  # 四个兄弟键照恢复
    assert _df_should_restore(loaded) is False  # 前提自证：这份 b64 确实不可解码
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_empty_string_df_b64_is_skipped_before_the_try_block(tmp_path):
    """结论 4 相邻面：`if df_b64:` 短路在 try **之前**（案 a 的门卫也在 try 内，不改这条）。

    现状照旧：空串连解码都不进，与「文件本来没 df」在 session_state 上同形。
    """
    payload = _complete_payload()
    payload["df_b64"] = ""
    _path, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored == 4 and "df" not in _keys_present()
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_snapshot_roundtrip_through_real_project_file_still_drops_none_partners(tmp_path):
    """写侧→文件→读侧全链路：df 有值而 inspector 为 None 时的快照与恢复形态。

    s927-28 翻正：改后 `restored == 1`（只有 meta）、df **不**回来（案 a 整组拦截）。
    ⚠ s922-108 已证明「df 独活」不是畸形文件，而是**上传后尚未跑 inspect 的正常中间态**。

    **s930-01 翻面（q927-28 遗留·写侧补法①落地）**：写侧快照现在**成对补跑**
    inspect_dataframe 并回填 session——df-only 快照不再产生（繁殖链切断）。
    本钉由「钉修复前形态（快照不带 inspector）」翻为「钉成对后形态」：
    快照带 inspector（新），file_name/analysis_history 仍 None 不落盘（不变）；
    恢复侧案 a 语义不变——四键（meta/inspector/file_name/analysis_history）仍缺三，
    `restored == 1`、df 与 inspector **都不**回来（拦截保护未被写侧补丁削弱）。
    """
    df = _sample_df(4)
    st.session_state.df = df
    st.session_state.meta = {"n": 4}
    st.session_state.inspector = None       # inspect 还没跑
    st.session_state.file_name = None
    st.session_state.analysis_history = None
    snap = build_workspace_snapshot()
    assert "df_b64" in snap and "meta" in snap
    assert "inspector" in snap              # s930-01 成对：df-only 快照不再产生
    assert "file_name" not in snap and "analysis_history" not in snap  # None 键仍不落盘

    path, loaded = _project_file(tmp_path, snap)
    st.session_state.clear()
    restored = restore_workspace(loaded)

    assert restored == 2  # meta＋inspector（成对后 inspector 键在场＝合法回流）；df 仍被案 a 四键闸拦
    assert "df" not in _keys_present()
    assert "inspector" in _keys_present()  # s930-01：inspector 不再随 df-only 快照湮灭
    assert path.exists() and path.parent.is_relative_to(tmp_path)
    assert _pinned_pairing_facts(loaded, _keys_present(), restored) == []


def test_restore_module_has_zero_file_io():
    """结构性自证：`workspace.py` 全模块零文件 IO ⇒ 本班不可能碰 `~/.psy_analysis`。

    现状钉桩（也是完成标准的证法）：项目文件的读写在调用方
    （`src/ui/project_panel.py:62/:83/:97` 是 `restore_workspace` 的三个调用点），
    恢复函数只吃已加载的 dict。判据取 `inspect.getsource` 的原文子串扫描，不靠 git status
    （`data/` 与本仓 `~/.psy_analysis` 都在 git 视野外，git status 恒空＝零证明力）。
    案 a 新增的只有 `logging`（不落盘），六个串实测仍零命中。
    """
    import inspect

    import src.utils.workspace as ws_mod

    src = inspect.getsource(ws_mod)
    for needle in ("open(", "Path(", ".home(", "json.load", "write_text", "mkdir"):
        assert needle not in src, f"workspace 模块出现文件 IO 痕迹 {needle!r}，tmp_path 隔离前提失效"


def test_missing_partner_key_predicate_is_discriminating():
    """反向用例（s922-108 的 `test_pairing_predicate_...` 按案 a 翻正）：
    判据必须能区分「齐备」「缺任一键」「键在但为 None」三态，且对四键逐键有鉴别力。

    这是判据自身的防假绿：若 `missing_df_partner_keys` 被写成恒空或恒全缺，
    参数化那两条会先炸。顺序也钉（返回按 DF_PARTNER_KEYS 序），因为 warning 文案直接拼这个序。
    """
    ok = _complete_payload()
    assert DF_PARTNER_KEYS == PARTNER_KEYS  # 模块常量与本档表逐字同（写侧四键表）
    assert missing_df_partner_keys(ok) == ()
    assert missing_df_partner_keys({"_schema": CURRENT_SCHEMA}) == PARTNER_KEYS  # 全缺
    for missing in PARTNER_KEYS:
        assert missing_df_partner_keys(_complete_payload(**{missing: None})) == (missing,)
    assert missing_df_partner_keys(
        _complete_payload(meta=None, file_name=None)) == ("meta", "file_name")
    # 键在但值为 None ⇒ 算缺（值语义），键在且值为假性空容器 ⇒ 不算缺
    assert missing_df_partner_keys(_complete_payload(analysis_history=[])) == ()


def test_paired_contract_is_discriminating_against_the_old_df_only_form(tmp_path):
    """反向用例（承 s922-108 的同名防假绿面）：把**改前形态**的读数喂进现在的判据必须报红。

    ①齐备文件不误伤；②缺键文件在案 a 下不报红（拒绝对）；
    ③人为造一份「df 独活」的读数（改前真实现场）⇒ 判据必须报出「凭空写了 df」。
    哪天有人把判据改成恒真，这一条会先炸。
    """
    _p1, loaded_ok = _project_file(tmp_path, _complete_payload(), name="complete.json")
    restore_workspace(loaded_ok)
    assert _pinned_pairing_facts(loaded_ok, _keys_present(), 5) == []          # ①

    st.session_state.clear()
    risky_payload = _complete_payload()
    del risky_payload["inspector"]
    _p2, loaded_risky = _project_file(tmp_path, risky_payload, name="risky.json")
    restored = restore_workspace(loaded_risky)
    assert _pinned_pairing_facts(loaded_risky, _keys_present(), restored) == []  # ②

    old_form_present = _keys_present() | {"df", "inspector"}                     # ③ 改前形态
    failures = _pinned_pairing_facts(loaded_risky, old_form_present, restored + 1)
    assert any("凭空写了 df" in f for f in failures), failures


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
