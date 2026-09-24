# -*- coding: utf-8 -*-
"""src/ui/questionnaire_import_panel.py 渲染层补面（s923-01）。

对象是两处此前零 AppTest/桩级命中的渲染面（锚点复核于 2026-09-23，行号逐字一致）：
  * `:170 def _render_results(session_state: dict)` —— 消费 `_CLEANED_KEY` 渲染结果的那一半；
  * `:203 def get_cleaning_log_for_deliverable(session_state: dict) -> list[dict]` —— 日志摊平。

来账：`zcode-bridge/done/s922-10-psy-qimport-3more.result.md` 把 `_render_results` 记为
「同族补面缺口，留作下一单」，并指出 `get_cleaning_log_for_deliverable` **只被 dict 层测过**
——现存的 `tests/test_questionnaire_import_panel.py::test_cleaning_log_for_deliverable`
和 `::test_empty_deliverable_log` 确实只断言 dict 长度/首元素，且后者测的是
「session_state 里根本没有 result」这一形态，**「有 result 但 log 为空」从未被覆盖**（本件补上）。

只加测试，**不改生产码**。

口径说明（为什么是「会话桩级」而不是 `streamlit.testing.v1.AppTest`）：
`tests/conftest.py::_APP_TEST_FILES` 是一枚**文件名白名单**——不在名单里的文件享受不到
`isolate_streamlit_app_test_storage` 的存储隔离（PSY_ANALYSIS_HOME / archive / logs 重定向）。
要走真 AppTest 就得把本文件名追加进 conftest，那会违反本单完成标准
「porcelain 相对开工仅新增该一件」。故沿用本仓渲染面板的既有主流桩型
（见 `tests/test_items_upload_airview.py:28 FakeSt` ／ `tests/test_feed_panel_charac.py:146`）：
`monkeypatch.setattr(panel, "st", fake)` ＋ `__getattr__` 对未预期调用直接判红。
**后来人若要把本件升级成真 AppTest，必须同时改 `_APP_TEST_FILES`，否则等于零隔离。**
→ s924-01 已按这句话把本文件名登记进 `tests/conftest.py::_APP_TEST_FILES`，并在下文第六节补真
AppTest 双形态用例；**上面那段「为什么是会话桩」的说明属当时的口径，保留不回改**（一~五节的
桩型用例一条没删，与六节的真运行时面互补：桩型能盯「未预期调用直接判红」，真运行时盯元素顺序）。

追加（s924-02，2026-09-24）：下面第四、五节把 `_render_results` 的 **summary 缺键形态**钉进本件——
来账 `zcode-bridge/done/s923-01.result.md` 自述「`:179-181` 是直接下标而非 `.get`，
缺键会 `KeyError` 冒到 UI 层而不是降级提示，本单只测了正常形态、没测缺键形态」。
那三处直接下标**今天仍在位**（锚点复核见下文注释）。**钉的是现状，不是规范**：
是否改成 `.get` ＋降级文案属生产行为改动，**待主班/人工裁决**，本单零 `src/` 改动。
"""
import os
import pathlib
from dataclasses import replace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import src.ui.questionnaire_import_panel as qip
from src.questionnaire.import_cleaning import (
    CleaningLogEntry,
    CleaningResult,
    ScaleDimension,
    export_cleaning_log,
    run_questionnaire_cleaning,
)

# --------------------------------------------------------------------------- #
# 记录型 st 桩：只放行 _render_results 实际会打的那几个方法，其余一律判红
# --------------------------------------------------------------------------- #


class FakeColumn:
    def __init__(self, host):
        self.host = host

    def metric(self, label, value, **k):
        self.host.metrics.append((label, value))


class FakeSt:
    def __init__(self):
        self.infos: list[str] = []
        self.markdowns: list[str] = []
        self.dataframes: list[object] = []
        self.downloads: list[tuple] = []
        self.metrics: list[tuple] = []
        self.columns_calls: list[int] = []

    def info(self, msg, **k):
        self.infos.append(msg)

    def markdown(self, msg, **k):
        self.markdowns.append(msg)

    def dataframe(self, data, **k):
        self.dataframes.append(data)

    def columns(self, spec, **k):
        self.columns_calls.append(spec)
        n = spec if isinstance(spec, int) else len(spec)
        return tuple(FakeColumn(self) for _ in range(n))

    def download_button(self, *a, **k):
        self.downloads.append(a)

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


# --------------------------------------------------------------------------- #
# 夹具：真跑 import_cleaning（纯本地、零网络、零 IO），读数不靠编
# --------------------------------------------------------------------------- #


def _raw_df(n: int = 30) -> pd.DataFrame:
    import numpy as np

    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1, n + 1),
        "gender": np.random.choice(["M", "F"], n),
        "Q1": np.random.randint(1, 6, n),
        "Q2": np.random.randint(1, 6, n),
        "Q3": np.random.randint(1, 6, n),
        "Q4": np.random.randint(1, 6, n),
        "duration": np.random.randint(30, 300, n),
    })


DIMENSIONS = [
    ScaleDimension(name="scale_a", items=["Q1", "Q2"], reverse_items=["Q2"]),
    ScaleDimension(name="scale_b", items=["Q3", "Q4"], reverse_items=[]),
]


@pytest.fixture
def st(monkeypatch):
    fake = FakeSt()
    monkeypatch.setattr(qip, "st", fake)
    return fake


@pytest.fixture
def cleaned_state():
    """带维度＋时长过滤的完整清洗态（实测 log 4 条、df_scored 非空）。"""
    result = run_questionnaire_cleaning(
        _raw_df(), dimensions=DIMENSIONS, duration_column="duration", min_duration_seconds=60,
    )
    return {qip._CLEANED_KEY: result}, result


# --------------------------------------------------------------------------- #
# 一、_render_results 的空态守卫
# --------------------------------------------------------------------------- #


def test_missing_cleaned_result_renders_hint_only(st):
    """没有 _CLEANED_KEY 时只出一条 info 并立即 return，后续渲染一个都不该发生。"""
    qip._render_results({})

    assert st.infos == ["请先执行清洗"]
    assert st.markdowns == []
    assert st.metrics == []
    assert st.dataframes == []
    assert st.downloads == []


def test_present_but_scoreless_state_still_short_circuits(st):
    """守卫读的是 `.get(_CLEANED_KEY)`，因此 None 值与缺键同形——钉住这个等价性。"""
    qip._render_results({qip._CLEANED_KEY: None})
    assert st.infos == ["请先执行清洗"]
    assert st.downloads == []


# --------------------------------------------------------------------------- #
# 二、_render_results 的摘要与日志渲染
# --------------------------------------------------------------------------- #


def test_summary_metrics_render_the_three_sample_counts(st, cleaned_state):
    """三列 metric 的标签与数值直接取自 result.summary（口径逐字对齐 :179-181）。"""
    state, result = cleaned_state
    assert result.summary["original_n"] == 30  # 夹具实测锚，改了夹具就该在这里红
    qip._render_results(state)

    assert st.metrics == [
        ("原始样本", result.summary["original_n"]),
        ("有效样本", result.summary["valid_n"]),
        ("剔除样本", result.summary["invalid_n"]),
    ]
    assert st.columns_calls == [3]


def test_each_log_entry_renders_exactly_one_markdown_line(st, cleaned_state):
    """清洗日志区一条 entry 一行，形如 `- **step**: action`，条数与顺序都不得漂。"""
    state, result = cleaned_state
    assert len(result.log) == 4  # 实测：列分类 / 无效样本检测 / 样本清洗 / 量表计分
    qip._render_results(state)

    body = [m for m in st.markdowns if m.startswith("- **")]
    assert body == [f"- **{e.step}**: {e.action}" for e in result.log]


def test_download_payload_is_same_log_as_rendered_body(st, cleaned_state):
    """端到端钉子：下载件与屏上日志区必须同源，否则会交付一份用户没看过的日志。"""
    state, result = cleaned_state
    qip._render_results(state)

    assert len(st.downloads) == 1
    label, data, file_name, mime = st.downloads[0]
    assert label == "📥 下载清洗日志"
    assert file_name == "cleaning_log.md"
    assert mime == "text/markdown"
    assert data == export_cleaning_log(result.log, format="markdown")
    for e in result.log:
        assert e.step in data and e.action in data


def test_scored_preview_section_absent_when_df_scored_is_none(st):
    """不传 dimensions 的分支：df_scored 为 None ⇒ 不出预览区、不调 dataframe，但摘要照出。"""
    result = run_questionnaire_cleaning(_raw_df())
    assert result.df_scored is None  # 实测读数
    qip._render_results({qip._CLEANED_KEY: result})

    assert st.dataframes == []
    assert not any("维度得分预览" in m for m in st.markdowns)
    assert [lab for lab, _ in st.metrics] == ["原始样本", "有效样本", "剔除样本"]
    assert len(st.downloads) == 1


def test_scored_preview_present_with_dimensions_and_caps_at_ten_rows(st, cleaned_state):
    """对照分支：df_scored 非空时出预览，且送进 dataframe 的是 head(10) 而非全表。"""
    state, result = cleaned_state
    qip._render_results(state)

    assert any("维度得分预览" in m for m in st.markdowns)
    assert len(st.dataframes) == 1
    shown = st.dataframes[0]
    assert isinstance(shown, pd.DataFrame)
    assert len(shown) == min(10, len(result.df_scored))
    assert list(shown.columns) == list(result.df_scored.head(10).columns)


# --------------------------------------------------------------------------- #
# 三、get_cleaning_log_for_deliverable 的摊平（空 log／多条 log 两形态）
# --------------------------------------------------------------------------- #

FLATTEN_KEYS = {"step", "action", "affected_rows", "affected_cols", "detail"}


def test_deliverable_flattens_every_entry_in_order(cleaned_state):
    """多条 log：逐条摊平成 dict，键集恰为 5 个，值与 entry 属性一一对应，顺序不变。"""
    state, result = cleaned_state
    out = qip.get_cleaning_log_for_deliverable(state)

    assert len(out) == len(result.log) == 4
    assert all(set(d) == FLATTEN_KEYS for d in out)
    assert out == [
        {"step": e.step, "action": e.action, "affected_rows": e.affected_rows,
         "affected_cols": e.affected_cols, "detail": e.detail}
        for e in result.log
    ]
    # 逐字锚一条真实读数，防止上面那个「与源对账」式断言两边一起漂
    assert out[1] == {"step": "无效样本检测", "action": "标记 1 个无效样本",
                      "affected_rows": 1, "affected_cols": 0,
                      "detail": "作答时长过短或同质作答比例过高"}


def test_deliverable_defaults_materialize_for_bare_entry():
    """dataclass 默认值（affected_rows=0 / detail=''）在摊平后必须**显式存在**，不能缺键。"""
    entry = CleaningLogEntry(step="列分类", action="识别 4 题项列")
    assert entry.affected_rows == 0 and entry.detail == ""  # 默认值实测
    out = qip.get_cleaning_log_for_deliverable(
        {qip._CLEANED_KEY: CleaningResult(df_cleaned=pd.DataFrame(), log=[entry])}
    )
    assert out == [{"step": "列分类", "action": "识别 4 题项列",
                    "affected_rows": 0, "affected_cols": 0, "detail": ""}]
    assert set(out[0]) == FLATTEN_KEYS


def test_deliverable_empty_list_when_result_present_but_log_empty():
    """**本单补的真缺口**：有 result 但 log 为空 ⇒ []，与「没有 result」同值但不同路径。

    现存 `test_empty_deliverable_log` 测的是 session_state 里根本没挂 result，
    这条挂上的是一个 log=[] 的 CleaningResult——两条分支必须各自成立。
    """
    state = {qip._CLEANED_KEY: CleaningResult(df_cleaned=pd.DataFrame(), log=[])}
    assert qip.get_cleaned_result(state) is not None  # 前置：确实进了非空守卫
    assert qip.get_cleaning_log_for_deliverable(state) == []


def test_render_and_deliverable_agree_on_entry_count(st, cleaned_state):
    """两个出口对同一份 log 的读数必须相等：屏上几行，交付包里就几条。"""
    state, result = cleaned_state
    qip._render_results(state)
    rendered = [m for m in st.markdowns if m.startswith("- **")]
    assert len(rendered) == len(qip.get_cleaning_log_for_deliverable(state)) == len(result.log)


# --------------------------------------------------------------------------- #
# 四、summary 缺键形态（s924-02 特征化：钉的是现状，非规范）
# --------------------------------------------------------------------------- #
#
# 被测面（复核于 2026-09-24，与 `src/ui/questionnaire_import_panel.py:179-181` 逐字一致）：
#     col1.metric("原始样本", result.summary["original_n"])
#     col2.metric("有效样本", result.summary["valid_n"])
#     col3.metric("剔除样本", result.summary["invalid_n"])
# 三处都是**直接下标**，故缺键时 KeyError 直接冒到 UI 层（没有 try、没有降级文案）。
# 下面几例把这个行为钉成现状：**若将来改判为 `.get` ＋降级提示，这些用例会翻红，
# 那是预期信号**——翻红时要连同「本段注释」一起改写，别只摘掉红的那几条。
SUMMARY_METRIC_ORDER = (
    ("原始样本", "original_n"),
    ("有效样本", "valid_n"),
    ("剔除样本", "invalid_n"),
)
SUMMARY_KEYS = tuple(k for _, k in SUMMARY_METRIC_ORDER)


def _summary_without(result, *keys):
    """在**真清洗产物**上摘掉指定 summary 键（其余字段一字不动）。"""
    patched = {k: v for k, v in result.summary.items() if k not in keys}
    assert patched != result.summary, f"夹具里没有 {keys} 可摘，变异没发生"
    return replace(result, summary=patched)


def test_control_full_summary_renders_all_three_metrics(st, cleaned_state):
    """控制组：三键齐全时一条都不炸、三列 metric 全落地。

    没有这一条，下面的 `pytest.raises(KeyError)` 就可能只是"夹具本来就不全"的假绿。
    """
    state, result = cleaned_state
    assert set(SUMMARY_KEYS) <= set(result.summary)  # 真跑 import_cleaning 的读数
    qip._render_results(state)
    assert [label for label, _ in st.metrics] == [label for label, _ in SUMMARY_METRIC_ORDER]
    assert len(st.downloads) == 1


@pytest.mark.parametrize("missing", SUMMARY_KEYS)
def test_single_missing_summary_key_raises_keyerror_mid_render(st, cleaned_state, missing):
    """缺任一个 summary 键 ⇒ `_render_results` 抛 KeyError，且 `str(exc)` 里就是那个键名。

    顺带钉下**半渲染态**的爆炸半径：抛点之前的 metric 已经落到屏上（用户看到半截数字），
    之后的维度预览与下载口一条都不会出现。
    """
    _, result = cleaned_state
    cut = _summary_without(result, missing)
    idx = SUMMARY_KEYS.index(missing)

    with pytest.raises(KeyError) as exc:
        qip._render_results({qip._CLEANED_KEY: cut})

    assert missing in str(exc.value), "判据 ①：异常消息里必须含被缺的键名"
    # 消息**恰等于**那一个键名。⚠ 不要写成"其它键名不得出现在消息里"：
    # `invalid_n` 字面上就含着 `valid_n`，那种断言会在 missing='invalid_n' 臂上假红。
    assert str(exc.value) == repr(missing), f"KeyError 消息形态漂了：{str(exc.value)!r}"
    # 抛点之前已经渲染出去的部分（逐字取自 :179-181 的顺序）
    assert st.metrics == [
        (label, result.summary[key]) for label, key in SUMMARY_METRIC_ORDER[:idx]
    ]
    assert st.markdowns == ["### 清洗摘要"]      # 只到小标题，一条降级提示都没有
    assert st.columns_calls == [3]
    assert st.dataframes == []                    # df_scored 明明非空，却再也渲染不到
    assert st.downloads == []                     # 清洗日志下载口随渲染一起消失


def test_all_three_summary_keys_missing_dies_on_the_first_one_only(st, cleaned_state):
    """缺多键（三枚计数键一起摘）：KeyError 只报**第一个**被碰的键，
    错误消息根本不告诉维护者还缺几个。

    ⚠ 实测：`run_questionnaire_cleaning` 产出的 summary 除三枚计数键外还有
    `item_columns` / `dimensions_scored` 两键（2026-09-24 读数），故"摘掉三枚计数键"
    ≠ "整张 summary 为空"——别把这条误读成 default_factory 形态。
    """
    _, result = cleaned_state
    assert set(SUMMARY_KEYS) <= set(result.summary)
    cut = _summary_without(result, *SUMMARY_KEYS)
    assert set(SUMMARY_KEYS).isdisjoint(cut.summary)      # 三枚计数键确实全缺

    with pytest.raises(KeyError) as exc:
        qip._render_results({qip._CLEANED_KEY: cut})

    assert "original_n" in str(exc.value)
    assert "valid_n" not in str(exc.value) and "invalid_n" not in str(exc.value)
    assert st.metrics == []                       # 一个数字都没落地
    assert st.markdowns == ["### 清洗摘要"]
    assert st.downloads == []


def test_missing_summary_keys_do_not_reach_the_deliverable_path(cleaned_state):
    """钉影响面边界：同一份缺键 result 喂另一个出口（交付包摊平）**不炸**，
    因为它不读 summary。⇒ 这条 KeyError 是**渲染摘要面**的局部缺陷，别升级成全链路面报告。"""
    _, result = cleaned_state
    cut = _summary_without(result, *SUMMARY_KEYS)
    state = {qip._CLEANED_KEY: cut}

    assert set(SUMMARY_KEYS).isdisjoint(cut.summary)
    assert qip.get_cleaned_result(state) is cut
    out = qip.get_cleaning_log_for_deliverable(state)
    assert len(out) == len(result.log) == 4
    assert all(set(d) == FLATTEN_KEYS for d in out)


# --------------------------------------------------------------------------- #
# 六、真 AppTest 双形态（s924-01：本文件名同时登记进 conftest._APP_TEST_FILES）
# --------------------------------------------------------------------------- #
#
# 一~五节跑的是 monkeypatch 掉的 `st` 桩；本节换成 streamlit 真运行时：`AppTest.from_string`
# 起整枚 `render_questionnaire_import_panel`，`_render_results` 落在第 4 个 tab「结果与导出」里。
# 桩型测不到的三件事由本节盯住：
#   ① 真 `session_state` 里那份 CleaningResult 渲染出的元素**标签与顺序**；
#   ② 「未清洗 → 已清洗」同一会话内提示语消失、摘要面出现的**形态切换**；
#   ③ `df_scored is not None` 守卫在真 dataframe 元素计数上的读数。
# 口径继承 `tests/test_e2e_qimport_upload.py` 顶部 s921-15／s922-10 两段的自约：清洗按钮点一次，
# 断言面锁在「元素在不在／标签与顺序／与会话对象同源等式」三件事上，**不钉任何统计数值**
# （valid_n、invalid_n、维度得分属统计结论红线域）。喂进去的是 1..6 递增斜坡这种一眼假的人造值。
# 文献库守卫：`feed_sandbox` 夹具把 `LITERATURE_FEED_DATA_ROOT` 指进本用例独占沙盒（纪律档 §廿一／§九）。

_ROOT = pathlib.Path(__file__).resolve().parents[1].as_posix()

_PANEL_SCRIPT = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
from src.ui.questionnaire_import_panel import render_questionnaire_import_panel

render_questionnaire_import_panel()
""".replace("__ROOT__", _ROOT)

# 人造问卷：题项逐行不同（不触发同质作答），时长一律 > 60s（不触发时长过滤）
_APPT_CSV = b"Q1,Q2,Q3,Q4,gender,duration_sec\n1,2,3,4,a,300\n2,3,4,5,b,400\n3,4,5,6,c,500\n"
_KEY_RAW = "questionnaire_raw_df"
_KEY_DIMS = "questionnaire_dimensions"
_KEY_CLEANED = "questionnaire_cleaned_result"
_HINT_EMPTY = "请先执行清洗"
_HEAD_SUMMARY = "### 清洗摘要"
_HEAD_PREVIEW = "### 维度得分预览"
_HEAD_LOG = "### 清洗日志"
_HEAD_NEXT = "### 下一步"
_INFO_NEXT_STEP = "清洗完成后可进入: 信度分析 / 描述统计 / 方法推荐向导"
_DL_LABEL = "📥 下载清洗日志"


@pytest.fixture
def feed_sandbox(monkeypatch, tmp_path):
    """把文献库根指进本用例独占的空沙盒（`tmp_path/feed_root`）。

    实测本件的导入链（`src.ui.questionnaire_import_panel` → `src.questionnaire.import_cleaning`）
    不含任何 `src.literature_feed*` 模块，故**不需要** `copytree` 真副本；这道 setenv 是防
    「将来有人把文献面板接进同一条渲染链」时拿 `data/literature_feed/` 当沙盒（那目录 git 无还原点）。
    """
    root = tmp_path / "feed_root"
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(root))
    return root


def _aptest(feed_sandbox) -> AppTest:
    """起一次真 AppTest 会话：未上传、未清洗＝`_render_results` 的空态。"""
    at = AppTest.from_string(_PANEL_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, f"主干渲染就抛异常：{[e.value for e in at.exception]}"
    return at


def _upload(at: AppTest) -> AppTest:
    at.file_uploader[0].set_value(("synth.csv", _APPT_CSV, "text/csv")).run()
    assert not at.exception, f"上传帧抛异常：{[e.value for e in at.exception]}"
    return at


def _click(at: AppTest, label: str) -> AppTest:
    hits = [b for b in at.button if b.label == label]
    assert len(hits) == 1, f"按钮「{label}」命中 {len(hits)} 枚 ⇒ 判据失去唯一锚点"
    hits[0].click().run()
    assert not at.exception, f"点「{label}」后抛异常：{[e.value for e in at.exception]}"
    return at


def _markdown(at: AppTest) -> list[str]:
    return [m.value for m in at.markdown]


def test_apptest_empty_state_renders_only_the_guard_hint(feed_sandbox):
    """空态（真运行时）：只有那一枚守卫提示，摘要/预览/日志/下载四面一条都不出。

    与同族 `test_e2e_qimport_upload.py::test_import_panel_smoke_...` 的分工：那条只断「提示在不在」，
    本例钉的是**否证面**——空态下若摘要或下载口漏出来（守卫被摘、提前 return 被删）当场红。
    """
    at = _aptest(feed_sandbox)

    infos = [i.value for i in at.info]
    assert infos.count(_HINT_EMPTY) == 1, f"空态提示不是恰一枚：{infos}"
    assert [m.label for m in at.metric] == []
    assert len(at.dataframe) == 0
    assert len(at.download_button) == 0
    md = _markdown(at)
    for head in (_HEAD_SUMMARY, _HEAD_PREVIEW, _HEAD_LOG, _HEAD_NEXT):
        assert head not in md, f"空态下不该渲染出 {head}"
    assert not any(v.startswith("- **") for v in md), "空态漏出了清洗日志行"
    assert _KEY_CLEANED not in at.session_state       # 前置：空态确实「没有 result」，不是渲染没跑


def test_apptest_success_state_renders_summary_log_and_download(feed_sandbox):
    """成功态（真运行时）：三枚 metric 标签顺序、日志行、下载口全部与会话对象同源。

    数值一律走 `str(result.summary[key])` 的**同源等式**而非字面量 ⇒ 本例不产出任何统计结论，
    但「标签接错列」「顺序漂」「日志与屏面不同源」三种破法都会红。
    """
    at = _upload(_aptest(feed_sandbox))
    at.text_input(key="dim_name_0").set_value("维度A").run()
    at.text_input(key="dim_items_0").set_value("Q1,Q2,Q3,Q4").run()
    at = _click(at, "保存维度配置")
    assert _KEY_CLEANED not in at.session_state, "点「保存维度配置」就写清洗键＝越界"

    at = _click(at, "执行清洗与计分")
    result = at.session_state[_KEY_CLEANED]
    assert set(SUMMARY_KEYS) <= set(result.summary)   # 缺键面由第四节钉，这里只作前置

    assert [(m.label, m.value) for m in at.metric] == [
        (label, str(result.summary[key])) for label, key in SUMMARY_METRIC_ORDER
    ]
    md = _markdown(at)
    assert _HINT_EMPTY not in [i.value for i in at.info], "清洗完成后空态提示还赖在屏上"
    for head in (_HEAD_SUMMARY, _HEAD_LOG, _HEAD_NEXT):
        assert head in md, f"成功态漏了小标题 {head}"
    assert _INFO_NEXT_STEP in [i.value for i in at.info]
    assert [v for v in md if v.startswith("- **")] == [
        f"- **{e.step}**: {e.action}" for e in result.log
    ], "屏上日志区与 result.log 不同源（条数／顺序／文本任一漂）"
    assert len(at.download_button) == 1
    assert at.download_button[0].label == _DL_LABEL
    # 存过维度 ⇒ df_scored 非空 ⇒ 预览区出，dataframe 恰两枚（上传预览 + 得分预览）
    assert _HEAD_PREVIEW in md
    assert len(at.dataframe) == 2


def test_apptest_scoreless_branch_keeps_summary_but_drops_preview(feed_sandbox):
    """第二条成功态分支：不存维度直接点清洗 ⇒ `df_scored is None` ⇒ 预览区一条都不出。

    与上一条只差「存没存维度」这一步，其余断言同向 ⇒ `:183` 那枚守卫在真运行时上确实起作用。
    """
    at = _upload(_aptest(feed_sandbox))
    assert _KEY_DIMS not in at.session_state, "前置：维度键压根没写，才有 dimensions=None 这条分支"

    at = _click(at, "执行清洗与计分")
    result = at.session_state[_KEY_CLEANED]
    assert result.df_scored is None                    # 2026-09-24 实测读数，不是假设

    md = _markdown(at)
    assert _HEAD_PREVIEW not in md
    assert len(at.dataframe) == 1                      # 只剩上传区那一枚
    assert [m.label for m in at.metric] == [label for label, _ in SUMMARY_METRIC_ORDER]
    assert _HEAD_SUMMARY in md and _HEAD_LOG in md
    assert len(at.download_button) == 1 and at.download_button[0].label == _DL_LABEL


def test_apptest_whitelist_row_is_live(feed_sandbox, tmp_path):
    """钉 conftest 那一行**活着**：白名单的门是文件名，登记没生效（typo／漏登记）本例即红。

    读数全取自 conftest 的 autouse 夹具真正写过的 env 与模块属性，测试自己一个字都没塞。
    """
    _aptest(feed_sandbox)                              # 先走一次夹具，确保 fixture 已命中本件

    app_home = tmp_path / ".psy_analysis"
    assert pathlib.Path(os.environ["PSY_ANALYSIS_HOME"]) == app_home
    assert pathlib.Path(os.environ["PSY_ANALYSIS_LOG_DIR"]) == tmp_path / "logs"
    assert pathlib.Path(os.environ["PSY_ANALYSIS_ARCHIVE_DIR"]) == tmp_path / "archive"

    from src.utils import project_manager, usage_logger

    assert project_manager.PROJECTS_DIR == app_home / "projects"
    assert project_manager.INDEX_FILE == app_home / "projects" / "index.json"
    assert pathlib.Path(str(usage_logger._LOG_DIR)) == tmp_path / "logs"

    # 文献库守卫同样在位，且本件的沙盒根一个字节都没被写过（真库零触碰的反证面）
    assert pathlib.Path(os.environ["LITERATURE_FEED_DATA_ROOT"]) == feed_sandbox
    assert not feed_sandbox.exists() or list(feed_sandbox.iterdir()) == []

