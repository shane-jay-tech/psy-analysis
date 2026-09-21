# -*- coding: utf-8 -*-
"""AppTest 实弹：问卷导入面板上传后 `_RAW_DF_KEY` / `_DIMENSIONS_KEY` 是否真落进 session_state。

s921-15（锚点：`done/s920-20-psy-qimport-3keys.result.md` 遗留 1 原文「『上传后 raw df 是否真进了
那个键』仍无人测（要 AppTest 才测得到」。s920-20 那批断言跑在 **dict 层**（测试自己往字典塞键再读回），
本单跑 **真渲染路径**：`st.file_uploader` 投字节 → `_render_upload` 真 `pd.read_csv` → 键真落。
**零生产码改动**。文件名已登记 `tests/conftest.py:_APP_TEST_FILES` ⇒ 运行期 `PSY_ANALYSIS_*`
全指向 tmp_path，不碰用户真实项目/档案/事件日志。

锚点漂移留痕：任务书标题写的是 `questionnaire_panel`，但两键的定义与写入点在
`src/ui/questionnaire_import_panel.py:23-24 / :55 / :128`（`src/ui/questionnaire_panel.py` 是另一个模块，
grep 这两键零命中）⇒ 按磁盘实况测前者。

红线自约：只测「文件字节 → 内存 DataFrame → 键」与「维度表单 → 键」两步。
「执行清洗与计分」按钮（`run_questionnaire_cleaning`，会产出无效样本判定与维度得分）属统计结论域，
s921-15 本单一律不点、不 import、不断言其输出。

s922-10 追加（同文件加例，不改上面那句话的历史口径）：清洗按钮**改为点一次**，但断言面**仍锁在
「键在不在 / 对象类型 / summary 的键集合」三件事上**——`summary` 里任何数值（valid_n、invalid_n、
题项列数、维度数）与维度得分一律不进断言，喂进去的数据是 1..6 的递增斜坡这种一眼假的人造值。
口径出处：`outbox/s921-15-psy-qimport-apptest.result.md` 遗留原文。数值口径归 owner 与统计域。
"""
import pathlib

import pandas as pd
from streamlit.testing.v1 import AppTest

_ROOT = pathlib.Path(__file__).resolve().parents[1].as_posix()

_PANEL_SCRIPT = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
from src.ui.questionnaire_import_panel import render_questionnaire_import_panel

render_questionnaire_import_panel()
""".replace("__ROOT__", _ROOT)

# 合成问卷：3 题项 + 1 人口学 + 1 时长列，数值全是个位数（不构成任何真实被试数据）
_CSV_OK = b"Q1,Q2,Q3,gender,duration_sec\n1,2,3,a,120\n4,5,1,b,300\n2,3,4,c,45\n"
_RAW = "questionnaire_raw_df"
_DIMS = "questionnaire_dimensions"


def _panel() -> AppTest:
    at = AppTest.from_string(_PANEL_SCRIPT, default_timeout=60)
    at.run()
    return at


def _upload(at: AppTest, name: str, payload: bytes) -> AppTest:
    at.file_uploader[0].set_value((name, payload, "text/csv")).run()
    return at


# ───────────────────────────── 最小冒烟 ─────────────────────────────
def test_import_panel_smoke_renders_and_holds_no_keys_yet():
    """主干渲染不炸 + 四步向导的引导态正确（未上传时三处提示、两键都不存在）。"""
    at = _panel()

    assert not at.exception
    assert at.subheader[0].value == "📋 问卷导入与清洗"
    assert [t.label for t in at.tabs] == ["上传数据", "列识别与维度", "清洗与计分", "结果与导出"]
    infos = [i.value for i in at.info]
    assert "请先在上传数据中加载文件" in infos and "请先上传数据" in infos and "请先执行清洗" in infos
    assert _RAW not in at.session_state and _DIMS not in at.session_state   # 键没被预热出来


# ─────────────────────── _RAW_DF_KEY：上传即落键 ───────────────────────
def test_upload_csv_writes_the_real_dataframe_into_raw_df_key():
    """任务的正题：上传后 `session_state["questionnaire_raw_df"]` 里是**真读出来的** DataFrame。

    dict 层测不到这件事——键名对不上、写到别处、读 CSV 抛异常被 except 吞掉，
    在 s920-20 那批断言里全绿；这里用形状 + 列名 + 单元格值三面夹。
    """
    at = _upload(_panel(), "survey.csv", _CSV_OK)

    assert not at.exception
    df = at.session_state[_RAW]                                # ① 键真在
    assert isinstance(df, pd.DataFrame)                        # ② 类型：不是路径、不是 bytes
    assert df.shape == (3, 5)                                  # ③ 形状：3 行 5 列（含表头不吃行）
    assert list(df.columns) == ["Q1", "Q2", "Q3", "gender", "duration_sec"]
    assert df["Q1"].tolist() == [1, 4, 2]                      # ④ 逐格内容，排除"键对了值空了"
    assert len(at.success) == 1 and at.success[0].value == "已加载 3 行 x 5 列"
    assert any(t.startswith("当前数据: 3 行, 5 列") for t in [c.value for c in at.caption])


def test_corrupt_upload_shows_error_and_does_not_write_raw_df_key():
    """except 分支同样走真路径：读不动的字节 ⇒ st.error，且**不**留半截 DataFrame 在键里。"""
    at = _upload(_panel(), "broken.csv", b"not,valid,csv\n\x00\x01\xff\n\xff\xff\xff,too,few\n")

    assert not at.exception                                    # 异常被面板接住，不冒到会话外
    assert len(at.error) == 1 and at.error[0].value.startswith("读取失败")
    assert _RAW not in at.session_state                        # 失败不写键（旧值也不会被覆盖成 None）


# ─────────────────────── _DIMENSIONS_KEY：保存才落键 ───────────────────────
def test_dimensions_key_absent_before_save_and_widget_defaults_after_upload():
    """维度键的写入点只有一个（`:128` 按钮分支）：光上传+改表单不构成写入。"""
    at = _upload(_panel(), "survey.csv", _CSV_OK)
    at.text_input(key="dim_name_0").set_value("负性情绪").run()
    at.text_input(key="dim_items_0").set_value("Q1,Q2").run()

    assert not at.exception
    assert _DIMS not in at.session_state                       # 没点保存 ⇒ 没写
    assert at.session_state["dim_name_0"] == "负性情绪"          # 表单值在 widget 键上，不在结果键上


def test_save_dimensions_button_writes_scale_dimension_objects():
    """点「保存维度配置」⇒ `_DIMENSIONS_KEY` 收到 `ScaleDimension` 实例，字段取自表单。

    这条是 s920-20「写了能在」的另一半：它钉的是**写入点真的接在按钮分支上**，
    以及表单串拆分（逗号分隔 → list）与 int 化（最高/最低分）在真 widget 类型下成立。
    """
    at = _upload(_panel(), "survey.csv", _CSV_OK)
    at.text_input(key="dim_name_0").set_value("负性情绪").run()
    at.text_input(key="dim_items_0").set_value("Q1, Q2 ,Q1").run()   # 含空格与重复项
    at.text_input(key="dim_reverse_0").set_value("Q2").run()

    save = [b for b in at.button if b.label == "保存维度配置"]
    assert len(save) == 1
    save[0].click().run()

    assert not at.exception
    dims = at.session_state[_DIMS]                             # ① 键真在
    from src.questionnaire.import_cleaning import ScaleDimension
    assert isinstance(dims, list) and len(dims) == 1
    assert isinstance(dims[0], ScaleDimension)                 # ② 是模型对象，不是 dict/str
    d = dims[0]
    assert d.name == "负性情绪"
    assert d.items == ["Q1", "Q2", "Q1"]                       # ③ 去空格、按字面保留（不擅自去重）
    assert d.reverse_items == ["Q2"]
    assert (d.max_score, d.min_score) == (5, 1)                # ④ 缺省分值被 int 化
    assert any("已保存 1 个维度" in s.value for s in at.success)


def test_saved_dimensions_read_back_into_widgets_on_next_render():
    """回读路径 `:86/:92-107`：存档后重跑一帧，表单显示的是存进去的值（键→UI 闭合）。"""
    at = _upload(_panel(), "survey.csv", _CSV_OK)
    at.text_input(key="dim_name_0").set_value("外显攻击").run()
    at.text_input(key="dim_items_0").set_value("Q3").run()
    [b for b in at.button if b.label == "保存维度配置"][0].click().run()

    at.run()                                                   # 再来一帧（同会话，session_state 存活）

    assert not at.exception
    assert at.session_state[_DIMS][0].name == "外显攻击"
    name_widget = at.text_input(key="dim_name_0")
    assert name_widget.value == "外显攻击"
    assert at.text_input(key="dim_items_0").value == "Q3"


# ─────────────── _CLEANED_KEY：点「执行清洗与计分」才落键（s922-10） ───────────────
# 写入点只有一个：`src/ui/questionnaire_import_panel.py:163`（`if st.button("执行清洗与计分")` 分支内）。
# 断言面锁死在**键 / 类型 / summary 键集合**，不碰任何统计数值（见文件顶 s922-10 追加说明）。
_CLEANED = "questionnaire_cleaned_result"

# 纯人造问卷：题项是 1..6 的递增斜坡（不含任何真实被试反应形态），时长全部 > 60s
_CSV_SYNTH = b"Q1,Q2,Q3,Q4,gender,duration_sec\n1,2,3,4,a,300\n2,3,4,5,b,400\n3,4,5,6,c,500\n"
_SUMMARY_KEYS = {"original_n", "valid_n", "invalid_n", "item_columns", "dimensions_scored"}


def _uploaded_with_one_dimension() -> AppTest:
    """停在「维度已存、清洗还没点」那一帧——清洗键的写入点只在该帧之后才可达。"""
    at = _upload(_panel(), "synth.csv", _CSV_SYNTH)
    at.text_input(key="dim_name_0").set_value("维度A").run()
    at.text_input(key="dim_items_0").set_value("Q1,Q2,Q3,Q4").run()
    [b for b in at.button if b.label == "保存维度配置"][0].click().run()
    return at


def test_cleaned_result_key_absent_until_the_cleaning_button_is_clicked():
    """上传 + 存维度都不构成写入：`_CLEANED_KEY` 只接在那个按钮分支上。"""
    at = _uploaded_with_one_dimension()

    assert not at.exception
    assert _DIMS in at.session_state                           # 前置条件真成立，不是空跑
    assert _CLEANED not in at.session_state                    # 没点清洗 ⇒ 没写


def test_clicking_cleaning_writes_a_cleaningresult_object_shape_only_claims():
    """点「执行清洗与计分」⇒ `_CLEANED_KEY` 收到 `CleaningResult` 实例，且 summary 键集合是契约面。

    这里刻意**不**断 valid_n / invalid_n / 维度得分任何一个数：那些是统计结论，属红线域。
    键名写错、写成了 dict、summary 少了一族键、日志条目类型漂移——这四种破法本例都会红。
    """
    from src.questionnaire.import_cleaning import CleaningLogEntry, CleaningResult

    at = _uploaded_with_one_dimension()
    clean = [b for b in at.button if b.label == "执行清洗与计分"]
    assert len(clean) == 1
    clean[0].click().run()

    assert not at.exception
    result = at.session_state[_CLEANED]                        # ① 键真在
    assert isinstance(result, CleaningResult)                  # ② 是 dataclass 实例，不是 dict
    assert set(result.summary) == _SUMMARY_KEYS                # ③ summary 键集合（契约面，非数值）
    assert all(isinstance(v, int) for v in result.summary.values())      # 值的**类型**，仍不碰值
    assert isinstance(result.df_cleaned, pd.DataFrame)
    assert isinstance(result.invalid_mask, pd.Series)
    assert isinstance(result.log, list) and result.log
    assert all(isinstance(e, CleaningLogEntry) for e in result.log)
    assert any(s.value.startswith("清洗完成: ") for s in at.success)      # 只断前缀，不比对回显里的数


# ─────────────── .xlsx 分支（s922-10） ───────────────
_XLSX_HEADER = ["Q1", "Q2", "Q3", "gender", "duration_sec"]
_XLSX_ROWS = [[1, 2, 3, "a", 120], [4, 5, 1, "b", 300], [2, 3, 4, "c", 45]]


def _xlsx_bytes(header: list[str], rows: list[list]) -> bytes:
    """内存里造真 xlsx 字节（openpyxl 已在环境内），不落任何临时文件、不读仓内样例。"""
    import io

    from openpyxl import Workbook

    wb = Workbook()
    wb.active.append(header)
    for r in rows:
        wb.active.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_upload_xlsx_goes_through_read_excel_and_lands_the_same_raw_df_key():
    """`:51-54` 的分支判据是文件名后缀：`.csv` → `read_csv`，其余（xlsx/xls）→ `read_excel`。

    投的是真 xlsx 字节 ⇒ 若 `else` 分支被改回 `read_csv`，CSV 解析器读不动 zip 容器，
    面板会落进 `except` 出 st.error，本例当场红（判别力实测见 result）。
    """
    at = _panel()
    at.file_uploader[0].set_value(
        (
            "synth.xlsx",
            _xlsx_bytes(_XLSX_HEADER, _XLSX_ROWS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    ).run()

    assert not at.exception
    assert not at.error, f"read_excel 分支没跑通：{[e.value for e in at.error]}"
    df = at.session_state[_RAW]                                # ① 与 CSV 同一把键
    assert isinstance(df, pd.DataFrame)                        # ② 类型一致
    assert df.shape == (3, 5)
    assert list(df.columns) == _XLSX_HEADER
    assert df["Q1"].tolist() == [1, 4, 2]                       # ④ 逐格，排除「读到了壳、值是空的」
    assert len(at.success) == 1 and at.success[0].value == "已加载 3 行 x 5 列"
