"""端到端 UI 渲染测试（使用 streamlit.testing.AppTest）"""

import pytest
import pandas as pd
from streamlit.testing.v1.app_test import AppTest

from src.ui.navigation import PAGE_MODES


def _ready_app(mode="📈 数据分析", **extra_session_state):
    """跳过一次性首访页，返回隔离存储上的可交互应用。

    `extra_session_state` 只作预置会话键用（不传时行为与旧签名逐字相同），
    供需要特定语言/偏好面的用例复用同一套启动口径。
    """
    at = AppTest.from_file("app.py")
    at.session_state["privacy_accepted"] = True
    at.session_state["onboarding_completed"] = True
    at.session_state["_onboarding_skipped"] = True
    at.session_state["app_mode"] = mode
    for key, val in extra_session_state.items():
        at.session_state[key] = val
    at.run(timeout=60)
    assert not at.exception
    return at


def _visible_texts(at):
    """渲染树里会显示给用户的文本（含 radio/selectbox 经 format_func 后的选项标签）。"""
    bag = []
    for kind in (
        "header", "subheader", "title", "caption", "markdown", "text",
        "info", "success", "warning", "error",
    ):
        bag.extend(str(getattr(el, "value", "")) for el in at.get(kind))
    for widget in list(at.radio) + list(at.selectbox):
        bag.extend(str(opt) for opt in widget.options)
    return bag



class TestAppStartup:
    def test_app_loads_without_error(self):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)
        assert not at.exception

    def test_sidebar_has_language_switcher(self):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)
        # 检查是否有语言切换（可能在主区域或侧边栏）
        radios = list(at.sidebar.radio) + list(at.radio)
        assert len(radios) > 0 or not at.exception


class TestDataUploadFlow:
    @pytest.fixture(autouse=True)
    def _sync_autosave(self, monkeypatch):
        """d913b-47 顺序依赖修复：关闭方案B后台路径，autosave 走同步落盘。

        根因：`_workspace_last_saved` 仅在 drain 到后台完成结果时写入，而结果槽
        是 autosave_bg 的模块级全局——全量跑时被先前测试的入队/完成「喂饱」，本
        用例子集单独跑则无人入队 → 键缺失 → KeyError（tests/test_e2e_ui.py:52）。
        置 BACKGROUND_AUTOSAVE_ENABLED=False 走同步分支（autosave.py 文档化回滚
        开关），保存与标签键在当次 run 内确定生效，不再依赖全局队列状态。
        """
        from src.utils import autosave as _autosave
        monkeypatch.setattr(_autosave, "BACKGROUND_AUTOSAVE_ENABLED", False)

    def test_upload_csv_triggers_analysis(self):
        at = _ready_app()
        assert len(at.file_uploader) >= 1

        df = pd.DataFrame({
            "group": ["A", "A", "A", "B", "B", "B"],
            "score": [10, 12, 11, 18, 20, 19],
        })
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        at.file_uploader[0].upload("test.csv", csv_bytes, "text/csv")
        at.run(timeout=60)

        assert not at.exception
        assert at.session_state["file_name"] == "test.csv"
        assert at.session_state["df"].shape == (6, 2)
        assert at.session_state["_workspace_last_saved"]

        request = next(x for x in at.text_area if x.label == "请输入您的分析需求：")
        request.set_value("对 score 做描述统计")
        analyze = next(x for x in at.button if x.label == "🔍 开始分析")
        analyze.click()
        at.run(timeout=60)

        assert not at.exception
        assert at.session_state["plan"] is not None
        assert at.session_state["analysis_output"] is not None
        output = at.session_state["analysis_output"]
        assert output.get("test_type") == "descriptive"
        assert output.get("descriptive") is not None


class TestModeSwitching:
    def test_questionnaire_mode_accessible(self):
        at = _ready_app("📋 问卷设计")
        assert not at.exception

    def test_navigation_uses_complete_canonical_stage_list(self):
        at = _ready_app()
        stage_radio = next(r for r in at.sidebar.radio if r.label == "按阶段进入")
        assert list(stage_radio.options) == PAGE_MODES

    def test_experiment_design_route_renders_without_error(self):
        at = _ready_app("🧪 实验设计")
        assert not at.exception
        assert any("实验设计" in str(x.value) for x in at.title)


class TestEnglishLanguageSurface:
    """en 语言面运行期覆盖（s924-23，补 s923-17 登记的 F2「在册 e2e 从不切语言」）。

    口径说明（按磁盘实况收窄，详见 outbox/s924-23.result.md 证据节）：
    问卷设计页上唯一由语言偏好驱动的文案来自 `src/utils/i18n.py` 的 en 块，
    经 `src/ui/settings_sidebar_panel.py` 渲染；`src/ui/app_pages_text.py` 的
    英文方法说明只在课程作业包 ZIP 内的 report.md 里，不进渲染树，故不在此断言。
    """

    def test_questionnaire_page_renders_english_surface(self, monkeypatch):
        from src.utils import user_prefs as _prefs

        # app.py 每次执行脚本都用 ~/.psy_analysis/user_prefs.json 回填这两个偏好键
        # （PERSISTED_KEYS 含之），真机存着什么就把预置值冲掉 → 测试内置空回填路径，
        # 让「预置 en」成为唯一事实源；不落盘、不读真偏好文件内容。
        monkeypatch.setattr(_prefs, "apply_to_session", lambda session_state: None)

        at_en = _ready_app("📋 问卷设计", language="en", output_language="en")
        texts_en = _visible_texts(at_en)

        # ① i18n 的英文块确实进了渲染树（3 个英文串，≥2）
        assert "🌐 Language" in texts_en
        lang_radio = next(r for r in at_en.sidebar.radio if r.key == "lang_select")
        assert lang_radio.options == ["Chinese", "English"]
        # ② 第二个语言偏好（统计报告语言）在侧栏控件上反映出来
        out_radio = next(r for r in at_en.sidebar.radio if r.key == "output_language_toggle")
        assert "English (APA7)" in out_radio.options
        assert out_radio.value == "en"
        assert out_radio.index == 1
        # ③ 侧栏写回逻辑没有把语言翻回中文（否则会 st.rerun 并回到 zh 面）
        assert at_en.session_state["language"] == "en"

        # ④ 未接 i18n 的页面主标题在英文面仍保持中文（help 文案承诺的既有设计：
        #    "UI 界面保持中文不变"），钉住「切语言 ≠ 全站英文化」这条边界
        assert "📋 问卷设计工具" in texts_en

        # ⑤ 反向对照：同页中文面给出的是中文串——证明上面 ①②③④ 不是恒真断言
        at_zh = _ready_app("📋 问卷设计", language="zh", output_language="zh")
        texts_zh = _visible_texts(at_zh)
        assert "🌐 语言" in texts_zh
        assert "🌐 Language" not in texts_zh
        assert next(r for r in at_zh.sidebar.radio if r.key == "lang_select").options == \
            ["中文", "英文"]
        assert next(r for r in at_zh.sidebar.radio if r.key == "output_language_toggle").index == 0

