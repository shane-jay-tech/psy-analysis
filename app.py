"""心理学研究工具 — 研究全流程辅助、统计分析与交付。"""

import sys
import os
import json
import time
import io
import html
import threading
import zipfile
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict


logger = logging.getLogger(__name__)


class _DummyContext:
    """v3.7: progress 不存在时的 noop context manager（避免 with None 崩）。"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd

from config.settings import TEST_NAMES_ZH, VAR_ROLE_LABELS, get_test_name
from src.data.loader import load_data, validate_data
from src.data.inspector import inspect_dataframe
from src.utils.memory_manager import (
    render_memory_manager_ui, cleanup_literature_cache, get_system_status,
)
from src.utils.pipeline_manager import render_pipeline_ui
from src.utils.i18n import t, DEFAULT_LANG
from src.utils.guardrails import (
    check_sample_size, check_multiple_comparisons,
    check_variable_type_match,
)
from src.utils.archive_manager import (
    archive_analysis, list_archives, list_tags, load_archive,
    get_archive_count,
)
from src.utils.env_check import (
    render_env_health_banner, render_env_status_toasts, run_startup_check,
)
from src.ui.quick_entries import render_quick_entry_homepage, render_quick_entry_detail
from src.ui.navigation import PAGE_MODES
from src.utils.usage_hooks import (
    on_page_visit, on_template_select, on_data_upload, on_method_recommend,
    on_analysis_execute, on_table_generate, on_consistency_check,
    on_privacy_precheck, on_export, on_error_display, on_diagnosis_run,
    on_next_step_show, on_next_step_click, AnalysisTimer,
)

# ============================================================
st.set_page_config(
    page_title="心理学研究工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

from src.ui.accessibility import render_accessibility_support
from src.ui.design_system import render_design_system
render_design_system()
render_accessibility_support()



def _get_onboarding_text(mode: str) -> str:
    """根据当前模式返回对应的入门指导文本"""
    common = (
        '<div class="onboarding-step">'
        '<strong>📂 步骤1:</strong> 上传数据文件（CSV/Excel），或使用内置示例数据。'
        '</div>'
    )

    guides = {
        "📈 数据分析": (
            common +
            '<div class="onboarding-step">'
            '<strong>🔍 步骤2:</strong> 系统自动识别变量类型和角色。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📊 步骤3:</strong> 选择研究问题和分析方法，点击运行。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📋 步骤4:</strong> 查看分析结果表格、效应量、置信区间和解读。'
            '</div>'
        ),
        "📋 问卷设计": (
            '<div class="onboarding-step">'
            '<strong>🎯 步骤1:</strong> 输入您的研究问题或构念名称。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>🧠 步骤2:</strong> 系统从知识库匹配构念或通过LLM分析。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📝 步骤3:</strong> 自动生成题目列表、指导语和计分方式。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>✅ 步骤4:</strong> 使用质量检查、反向题审阅等功能打磨问卷。'
            '</div>'
        ),
        "🧪 实验设计": (
            '<div class="onboarding-step">'
            '<strong>🔬 步骤1:</strong> 选择实验设计类型和范式。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📐 步骤2:</strong> 运行检验力分析确定所需样本量。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>🔄 步骤3:</strong> 生成实验程序、拉丁方平衡、指导语。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📑 步骤4:</strong> 生成预注册文档（AsPredicted格式）。'
            '</div>'
        ),
        "📝 论文写作": (
            '<div class="onboarding-step">'
            '<strong>📖 步骤1:</strong> 选择研究主题和论文框架。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📚 步骤2:</strong> 系统自动检索相关文献并格式化引用。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>✍️ 步骤3:</strong> 逐章节生成论文初稿（支持LLM润色）。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>🔍 步骤4:</strong> 自动检测非常规结果、交叉校验引用。'
            '</div>'
        ),
    }

    guide = guides.get(mode, common)
    return (
        f'<div style="font-size:0.85em; line-height:1.6;">'
        f'{guide}'
        f'<div style="margin-top:6px; color:#888;">'
        f'💡 <em>将鼠标悬停在按钮和输入框上可查看提示信息。</em>'
        f'</div>'
        f'</div>'
    )



def _build_homework_package(output, df, tag=""):
    """生成一键作业包 ZIP：数据 + APA7报告 + 方法说明"""
    plan = st.session_state.get("plan")
    test_type = plan.test_type if plan else output.get("test_type", "")
    test_name = output.get("test_name_zh", test_type)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. 数据文件（脱敏）
        from src.utils.guardrails import redact_dataframe_for_storage
        df_saved, redaction_report = redact_dataframe_for_storage(df)
        zf.writestr("data.csv", df_saved.to_csv(index=False, encoding="utf-8-sig"))

        # 2. APA7 报告
        report = build_apa7_report(output)
        method_desc = _generate_method_description(test_type, test_name, output)
        full_md = (
            f"# {test_name} — 课程作业分析报告\n\n"
            f"生成时间：{now}\n\n"
            f"---\n\n"
            f"## 方法说明\n{method_desc}\n\n"
            f"---\n\n"
            f"{report}"
        )
        zf.writestr("report.md", full_md)

        # 3. 分析参数
        params = {
            "test_type": test_type,
            "test_name": test_name,
            "timestamp": now,
            "privacy_redaction": redaction_report,
        }
        if plan:
            params["dependent_vars"] = plan.dependent_vars if hasattr(plan, "dependent_vars") else []
            params["independent_vars"] = plan.independent_vars if hasattr(plan, "independent_vars") else []
        zf.writestr(
            "params.json",
            json.dumps(params, ensure_ascii=False, indent=2, default=str),
        )

        # 4. README
        readme = (
            "心理学课程作业包\n"
            "==================\n\n"
            f"分析方法：{test_name}\n"
            f"生成时间：{now}\n"
            f"标签/课程：{tag or '未标注'}\n\n"
            "文件说明：\n"
            "- data.csv: 分析数据（高敏感列已移除，身份标识列已哈希）\n"
            "- report.md: APA7 格式分析报告 + 方法说明\n"
            "- params.json: 分析参数记录\n\n"
            "学术诚信提醒：请确保你理解所用方法的原理，在论文中正确表述统计结果。\n"
        )
        zf.writestr("README.txt", readme)

    buf.seek(0)
    safe_name = "".join(c for c in test_name if c.isalnum() or c in "._-（）()")[:20]
    st.download_button(
        f"📥 下载作业包 ({safe_name}.zip)",
        data=buf,
        file_name=f"作业包_{safe_name}_{now}.zip",
        mime="application/zip",
        width="stretch",
    )
    st.success("✅ 作业包已生成！包含数据、APA7报告和方法说明。")


def _generate_method_description(test_type: str, test_name: str, output: Dict) -> str:
    """根据检验方法生成简要方法说明"""
    lang = st.session_state.get("output_language", "zh")
    if lang == "en":
        descriptions = {
            "independent_ttest": "This study used an independent-samples t-test to compare the means of two independent groups. "
                                "Assumptions of normality and homogeneity of variance were checked before analysis. "
                                "Cohen's d was reported as the effect size measure.",
            "paired_ttest": "This study used a paired-samples t-test to compare two related measurements within the same subjects. "
                            "The normality assumption of difference scores was verified.",
            "one_way_anova": "This study used a one-way between-subjects ANOVA to compare means across multiple independent groups. "
                             "Levene's test was used to check homogeneity of variance. Partial η² was reported as effect size. "
                             "Post-hoc comparisons used Tukey HSD correction.",
            "pearson_corr": "This study used Pearson correlation to examine linear relationships between continuous variables. "
                           "Normality was checked via Shapiro-Wilk test; Spearman correlation was used as a non-parametric alternative when necessary.",
            "spearman_corr": "This study used Spearman's rank correlation, a non-parametric method, to examine monotonic relationships.",
            "cronbach_alpha": "Cronbach's α was used to assess the internal consistency reliability of the scale. α ≥ 0.70 was considered acceptable.",
            "chi_square_independence": "A chi-square test of independence examined the association between two categorical variables. "
                                       "Cramér's V was reported as the effect size measure.",
            "mann_whitney": "The Mann-Whitney U test, a non-parametric alternative to the independent t-test, was used due to non-normal data distribution.",
            "kruskal_wallis": "The Kruskal-Wallis H test, a non-parametric alternative to one-way ANOVA, was used. "
                              "Dunn's test with Bonferroni correction was used for post-hoc comparisons.",
            "mediation": "Mediation analysis was conducted using the bootstrap method (5000 resamples). "
                        "The indirect effect (a×b) was considered significant if the 95% CI did not contain zero.",
            "moderation": "Moderation analysis examined whether a third variable moderated the relationship between IV and DV. "
                         "Simple slope analysis was conducted at ±1 SD of the moderator.",
            "efa": "Exploratory Factor Analysis (EFA) was conducted using principal axis factoring with varimax rotation. "
                   "KMO and Bartlett's test confirmed data suitability. Factor retention used Kaiser criterion (eigenvalue > 1).",
        }
        return descriptions.get(test_type, f"This study used {test_name} for statistical analysis. Effect sizes and 95% CIs were reported per APA 7th Edition guidelines.")
    else:
        descriptions = {
            "independent_ttest": "本研究使用独立样本 t 检验比较两组独立样本的均值差异。分析前检验了正态性和方差齐性假设。效应量报告 Cohen's d。",
            "paired_ttest": "本研究使用配对样本 t 检验比较同一组被试在两个条件下的测量差异。分析前检验了差值分的正态性假设。",
            "one_way_anova": "本研究使用单因素被试间方差分析比较多组独立样本的均值差异。使用 Levene 检验检查方差齐性。效应量报告偏 η²。事后比较使用 Tukey HSD 校正。",
            "pearson_corr": "本研究使用 Pearson 相关分析两个连续变量间的线性关系。使用 Shapiro-Wilk 检验检查正态性；不满足时使用 Spearman 相关作为非参数替代。",
            "spearman_corr": "本研究使用 Spearman 秩相关（非参数方法）分析变量间的单调关系。",
            "cronbach_alpha": "使用 Cronbach's α 系数评估量表的内部一致性信度。α ≥ 0.70 为可接受水平。",
            "chi_square_independence": "使用卡方独立性检验分析两个类别变量间的关联。效应量报告 Cramér's V。",
            "mann_whitney": "使用 Mann-Whitney U 检验（独立样本 t 检验的非参数替代）比较两组差异，因数据不满足正态性假设。",
            "kruskal_wallis": "使用 Kruskal-Wallis H 检验（单因素方差分析的非参数替代）比较多组差异。事后比较使用 Dunn 检验 + Bonferroni 校正。",
            "mediation": "使用 Bootstrap 法（5000次重抽样）进行中介效应分析。若间接效应 (a×b) 的 95% CI 不包含 0，则认为中介效应显著。",
            "moderation": "使用调节效应分析检验第三个变量是否调节自变量与因变量间关系的强度或方向。在调节变量 ±1 SD 处进行简单斜率分析。",
            "efa": "使用探索性因素分析（主成分法 + 最大方差旋转）探索潜在因素结构。使用 KMO 和 Bartlett 检验确认数据适合性。因子保留使用 Kaiser 准则（特征值 > 1）。",
        }
        return descriptions.get(test_type, f"本研究使用{test_name}进行统计分析。按 APA 第7版要求报告效应量和95%置信区间。")


# ============================================================
# 会话状态
# ============================================================
_defaults = {
    "df": None, "meta": None, "inspector": None,
    "analysis_output": None, "plan": None, "file_name": None,
    "questionnaire_design": None,
    "paper_engine": None,
    "experiment_engine": None,
    # v4.4: LLM 配置统一走顶部「🤖 AI 模型」selectbox + D:\code\.env.local
    "quick_model_id": "",
    "onboarding_completed": False,
    "privacy_accepted": False,
    "undergrad_mode": False,
    "undergrad_path": None,
    "undergrad_step": 0,
    "undergrad_wizard_data": {},
    "analysis_history": [],
    "_wizard_return": None,
    "workspace_saved": None,
    "language": "zh",
    "output_language": "zh",
    "interactive_charts": False,
    "archive_tag": "",  # 档案标签
    "quick_entry": None,  # 快捷入口
    "show_quick_detail": False,
    "startup_check_done": False,  # 启动检查标记
    "env_status": None,  # 环境检查结果
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# v3.7: 应用持久化的用户偏好（隐私声明/新手指引等关掉浏览器后还记得）
try:
    from src.utils.user_prefs import apply_to_session
    apply_to_session(st.session_state)
except Exception:
    pass

# “开始新研究”发生在控件实例化之后；延迟到下一轮、控件创建前清理上传框。
for _widget_key in st.session_state.pop("_pending_widget_resets", []):
    st.session_state.pop(_widget_key, None)

# ============================================================
# 隐私声明（首次使用时弹出）
# ============================================================
if not st.session_state.privacy_accepted:
    with st.container():
        st.markdown("### 🔒 隐私声明")
        st.markdown("""
        <div class="info-box">
        <p><strong>数据隐私承诺</strong></p>
        <p>本工具的统计处理和项目存储均在您的本地计算机上完成；项目文件不会由本工具开发者收集。</p>
        <ul>
            <li>上传的数据会进入当前会话，并随自动保存写入本机项目目录，方便恢复</li>
            <li>关闭浏览器不会删除本地项目；可在项目管理或缓存清理中主动删除</li>
            <li>使用云端 AI 功能时，你提交的文本会发送给所选服务商；原始数据不会被自动上传，除非功能明确提示</li>
            <li>文献爬取功能仅向公开 API 发送关键词查询，不涉及个人数据</li>
        </ul>
        <p><em>如使用云端 LLM 服务，请遵守相应平台的数据使用协议。</em></p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("✅ 我已阅读并同意", type="primary", width="stretch"):
                st.session_state.privacy_accepted = True
                # v3.7: 持久化，下次启动不再弹
                try:
                    from src.utils.user_prefs import update_pref
                    update_pref("privacy_accepted", True)
                except Exception:
                    pass
                st.rerun()

    st.stop()

# ============================================================
# 启动时自动清理（文献缓存 7 天过期 + cancel_id 清理）
# ============================================================
if "has_auto_cleaned" not in st.session_state:
    st.session_state.has_auto_cleaned = True
    try:
        cache_result = cleanup_literature_cache(older_than_days=7)
        if cache_result["cleaned"] > 0:
            import logging
            logging.info(f"文献缓存自动清理：{cache_result['cleaned']} 个过期文件")
    except Exception:
        pass

# ============================================================
# 启动时一键环境检查（v5.8：毫秒级 find_spec 自检，toast 弹出，不阻塞）
# ============================================================
if not st.session_state.startup_check_done:
    st.session_state.startup_check_done = True
    try:
        env_status = run_startup_check()
        st.session_state.env_status = env_status
        render_env_status_toasts(env_status)
    except Exception:
        # 自检失败绝不能让整个应用白屏（v5.8 鲁棒性修复）
        st.session_state.env_status = None

# v5.8: 后台预热重型统计依赖（daemon 线程，不阻塞渲染）。
# 用户在阅读界面/上传数据的同时，pingouin/statsmodels/semopy 等
# 已在后台导入完成，第一次点「开始分析」不再额外等待 10~30s。
def _preload_heavy_deps() -> None:
    try:
        import scipy.stats  # noqa: F401
        import statsmodels.api  # noqa: F401
        import pingouin  # noqa: F401
        import sklearn.cluster  # noqa: F401
        import factor_analyzer  # noqa: F401
        import openpyxl  # noqa: F401
        import jieba  # noqa: F401
        import semopy  # noqa: F401
        import kaleido  # noqa: F401
    except Exception:
        pass  # 预热失败静默——真正用到时会有明确的懒加载错误提示

if not st.session_state.get("_heavy_preload_started"):
    st.session_state._heavy_preload_started = True
    try:
        threading.Thread(target=_preload_heavy_deps, daemon=True, name="heavy-preload").start()
    except Exception:
        pass

# v2.9: 顶部环境健康提示条（仅在有问题时显示）
render_env_health_banner()

# v3.1: 项目管理 — 确保有活跃项目（首次访问会迁移 v3.0 autosave 或新建默认项目）
from src.ui.project_panel import ensure_active_project_on_first_visit
ensure_active_project_on_first_visit()

# v3.0: 自动恢复提示（仅在首次访问 + 有 autosave 时）
from src.utils.autosave import render_restore_prompt, trigger_autosave
render_restore_prompt(st)


def _autosave_current_workspace(*, force: bool = False) -> bool:
    """保存当前项目；所有失败由 autosave 状态统一反馈，不阻断主流程。"""
    try:
        from src.utils.workspace import build_workspace_snapshot
        return trigger_autosave(
            st.session_state, build_workspace_snapshot, force=force
        )
    except Exception:
        logger.exception("自动保存入口失败")
        st.session_state["_autosave_last_error"] = "自动保存失败，请手动导出项目快照"
        return False

# v3.0: 5 分钟引导路径（首次访问无任何数据时显示）
from src.ui.onboarding import render_onboarding_card
if render_onboarding_card():
    # 引导卡片显示中，不渲染主界面，避免重复内容
    st.stop()

# ============================================================
# 侧边栏 — 模式选择
# ============================================================
with st.sidebar:
    st.title("📊 心理学研究工具")

    # ── v4.3 快捷模型选择器（一键切换 4 个预设模型）──
    try:
        from src.llm_gateway.quick_models import list_available_quick_models
        _quick_models = list_available_quick_models()
        _qm_options = [("", "📌 默认（手动设置）")] + [
            (q["id"], q["label"] if q["available"] else f"{q['label']} ⚠️未配置")
            for q in _quick_models
        ]
        _qm_ids = [o[0] for o in _qm_options]
        _qm_labels = [o[1] for o in _qm_options]
        _qm_current = st.session_state.get("quick_model_id", "")
        try:
            _qm_idx = _qm_ids.index(_qm_current)
        except ValueError:
            _qm_idx = 0
        _qm_picked_label = st.selectbox(
            "🤖 AI 模型",
            _qm_labels,
            index=_qm_idx,
            key="_quick_model_picker",
            help="选了之后所有 AI 调用都走这个模型；选「默认」则按下方「LLM 设置」里手填的走。",
        )
        _qm_picked_id = _qm_ids[_qm_labels.index(_qm_picked_label)]
        if _qm_picked_id != _qm_current:
            # v4.6: 切换模型前取消 in-flight LLM 任务，避免旧模型响应回到新模型上下文
            for _pkey in ("_q_design_pending", "_exp_design_pending"):
                _pending = st.session_state.get(_pkey)
                if not _pending:
                    continue
                _cid = _pending.get("cancel_id")
                if _cid is not None:
                    try:
                        if _pkey == "_q_design_pending":
                            from src.questionnaire.llm_engine import (
                                cancel_design_request as _cancel_pending_design,
                            )
                        else:
                            from src.experiment_design import (
                                cancel_design_request as _cancel_pending_design,
                            )
                        _cancel_pending_design(_cid)
                    except Exception:
                        pass
                _fut = _pending.get("future")
                if _fut is not None:
                    try:
                        _fut.cancel()
                    except Exception:
                        pass
                st.session_state.pop(_pkey, None)
            st.session_state.quick_model_id = _qm_picked_id
            st.rerun()
        if _qm_current:
            _qm_meta = next((q for q in _quick_models if q["id"] == _qm_current), None)
            if _qm_meta:
                if _qm_meta["available"]:
                    st.caption(f"✅ `{_qm_meta['model']}` · {_qm_meta['description']}")
                else:
                    st.warning("⚠️ 该模型在 `D:\\code\\.env.local` 中未配置完整 BASE_URL/API_KEY/MODEL")
    except Exception as _qm_exc:
        st.caption(f"⚠️ 快捷模型加载失败：{_qm_exc}")

    st.divider()

    # ── 一键全流程开关（v3.7 改名：原「📚 本科论文模式」）──
    _pending_undergrad_mode = st.session_state.pop("_pending_undergrad_mode", None)
    if isinstance(_pending_undergrad_mode, bool):
        st.session_state.undergrad_mode = _pending_undergrad_mode
        st.session_state["undergrad_mode_toggle"] = _pending_undergrad_mode
    if "undergrad_mode_toggle" not in st.session_state:
        st.session_state["undergrad_mode_toggle"] = bool(st.session_state.undergrad_mode)
    undergrad_mode = st.toggle(
        "🎯 一键全流程引导",
        key="undergrad_mode_toggle",
        help="开启后从选题→文献→设计→分析→写作→答辩按真实科研顺序引导（共 13+ 步）。"
              "关闭后可单独进入任一阶段。建议第一次使用时开启。",
    )
    if undergrad_mode != st.session_state.undergrad_mode:
        st.session_state.undergrad_mode = undergrad_mode
        if undergrad_mode:
            st.session_state.undergrad_path = None
            st.session_state.undergrad_step = 0
            st.session_state.undergrad_wizard_data = {}
        st.rerun()

    if not st.session_state.undergrad_mode:
        _pending_mode = st.session_state.pop("_pending_app_mode", None)
        if _pending_mode in PAGE_MODES:
            st.session_state.app_mode = _pending_mode
        if st.session_state.get("app_mode") not in PAGE_MODES:
            st.session_state.app_mode = "📈 数据分析"
        mode = st.radio(
            "按阶段进入",
            PAGE_MODES,
            key="app_mode",
            help="每个阶段可独立使用；阶段间数据自动共享。",
        )
        try:
            from src.ui.next_step_panel import render_next_step_panel
            render_next_step_panel(mode)
        except Exception:
            pass
    else:
        mode = "📈 数据分析"  # 全流程模式下隐藏，但保持变量存在

    # v5.4: 页面访问事件日志
    _prev_mode = st.session_state.get("_last_logged_mode")
    if mode != _prev_mode:
        on_page_visit(mode)
        st.session_state["_last_logged_mode"] = mode

    st.divider()

    # ── 📁 项目 · 工作区（导出/导入/研究档案/清除会话）──
    with st.expander("📁 项目 · 工作区", expanded=False):
        from src.utils.workspace import build_workspace_snapshot, restore_workspace, FutureSchemaError
        from datetime import datetime

        st.markdown(
            '<p style="font-size:0.8em; color:#888;">日常使用无需手动保存，autosave 会自动保留当前项目。'
            '此处用于导出快照供备份或迁移。</p>',
            unsafe_allow_html=True,
        )
        _autosave_error = st.session_state.get("_autosave_last_error")
        _autosave_saved = st.session_state.get("_workspace_last_saved")
        if _autosave_error:
            st.warning(f"⚠️ {_autosave_error}")
        elif _autosave_saved:
            st.caption(f"✅ 当前项目已自动保存：{_autosave_saved}")
        st.markdown(
            '<p style="font-size:0.75em; color:#c0392b;">⚠️ 工作区文件含原始数据，妥善保管勿分享。</p>',
            unsafe_allow_html=True,
        )

        # v5.8 性能修复：快照（含全量 df.to_csv + base64）此前在每次 rerun
        # 都被重算——大文件下每次点击交互都要等 1~3s。改为「点击后才生成」，
        # 生成结果暂存 session_state，点「下载」取走。
        if st.button("📥 导出项目快照", width="stretch",
                     help="生成当前数据 + 分析结果 + 向导状态的备份文件（大文件需要几秒）"):
            with st.spinner("正在打包工作区快照..."):
                try:
                    workspace = build_workspace_snapshot()
                    ws_json = json.dumps(workspace, ensure_ascii=False, default=str, indent=2)
                    st.session_state["_ws_export_json"] = ws_json
                    st.session_state["_ws_export_ts"] = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.session_state["_workspace_last_saved"] = workspace.get(
                        "_saved_at", datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                except Exception as _ws_err:
                    st.error(f"❌ 快照生成失败：{_ws_err}")

        _ws_json = st.session_state.get("_ws_export_json")
        if _ws_json:
            st.download_button(
                "💾 下载快照文件",
                data=_ws_json,
                file_name=f"psy_workspace_{st.session_state.get('_ws_export_ts', datetime.now().strftime('%Y%m%d_%H%M%S'))}.json",
                mime="application/json",
                width="stretch",
                help="快照已生成，点击下载。",
            )
            if st.button("🗑 丢弃快照（释放内存）", key="_ws_export_discard"):
                st.session_state.pop("_ws_export_json", None)
                st.session_state.pop("_ws_export_ts", None)
                st.rerun()

        st.markdown(
            '<p style="font-size:0.85em; font-weight:600; margin-top:8px;">📤 导入项目快照</p>',
            unsafe_allow_html=True,
        )
        workspace_file = st.file_uploader(
            "选择工作区文件",
            type=["json"],
            key="workspace_loader",
            label_visibility="collapsed",
        )
        if workspace_file is not None:
            import hashlib as _hashlib
            _workspace_cheap_identity = (
                workspace_file.name,
                int(getattr(workspace_file, "size", 0)),
                str(getattr(workspace_file, "file_id", "")),
            )
            _workspace_handled = st.session_state.get("_workspace_import_handled")
            if not (
                isinstance(_workspace_handled, tuple)
                and _workspace_handled[:3] == _workspace_cheap_identity
            ):
                _workspace_bytes = workspace_file.getvalue()
                _workspace_identity = _workspace_cheap_identity + (
                    _hashlib.sha256(_workspace_bytes).hexdigest(),
                )
                try:
                    loaded = json.loads(_workspace_bytes.decode("utf-8"))
                    restored_count = restore_workspace(loaded)
                    st.session_state["_workspace_import_handled"] = _workspace_identity
                    st.success(
                        f"✅ 已恢复 {restored_count} 个数据项"
                        f" (保存时间: {loaded.get('_saved_at', '未知')})"
                    )
                    mig_info = st.session_state.get("_workspace_migration_info")
                    if mig_info:
                        st.info(
                            f"🔄 已自动升级旧版工作区：{mig_info['from_version']} → {mig_info['to_version']}"
                        )
                        st.session_state.pop("_workspace_migration_info", None)
                    if st.session_state.get("undergrad_mode"):
                        step = st.session_state.get("undergrad_step", 0)
                        st.info(f"📚 已恢复本科向导模式，当前第 {step} 步。")
                    st.rerun()
                except FutureSchemaError as e:
                    st.error(f"❌ {str(e)}")
                except Exception as e:
                    st.error(f"❌ 恢复失败: {str(e)}")

        st.divider()
        st.markdown(
            '<p style="font-size:0.85em; font-weight:600;">🗂 我的研究档案</p>',
            unsafe_allow_html=True,
        )
        archive_count = get_archive_count()
        if archive_count == 0:
            st.caption("暂无存档。完成分析后会自动保存。")
        else:
            st.caption(f"📦 共 {archive_count} 条存档记录")
            tags = list_tags()
            if tags:
                filter_tag = st.selectbox(
                    "按标签筛选",
                    ["全部"] + tags,
                    key="archive_filter_tag",
                )
            else:
                filter_tag = "全部"
            entries = list_archives(tag="" if filter_tag == "全部" else filter_tag)
            for i, entry in enumerate(entries[:20]):
                ts = entry.get("timestamp", "")[:16].replace("T", " ")
                tag_badge = f" [{entry.get('tag', '')}]" if entry.get("tag") else ""
                test_name = entry.get("test_name_zh", entry.get("test_type", ""))
                label = f"{ts} — {test_name}{tag_badge}"
                if st.button(label, key=f"archive_{i}_{entry['archive_id'][:8]}",
                            width="stretch"):
                    loaded = load_archive(entry["archive_id"])
                    if loaded and "df" in loaded:
                        st.session_state.df = loaded["df"]
                        st.session_state.inspector = inspect_dataframe(loaded["df"])
                        st.session_state.file_name = entry.get("file_name", "存档数据")
                        st.session_state.archive_tag = entry.get("tag", "")
                        if "params" in loaded:
                            st.session_state._loaded_params = loaded["params"]
                        st.success(f"✅ 已加载存档：{test_name}")
                        st.rerun()

        st.divider()
        # 清空前先保存当前项目，再切换到新的空白项目，避免研究资产交叉污染。
        if st.session_state.get("_clear_session_confirm"):
            st.warning("⚠️ 将保存当前项目并创建一个新的空白项目；当前研究不会被删除。")
            _cc1, _cc2 = st.columns(2)
            if _cc1.button("✅ 保存并开始新研究", type="primary", width="stretch", key="_clear_session_yes"):
                import gc
                try:
                    from src.ui.session_reset import clear_research_session
                    from src.utils import project_manager as _pm
                    from src.utils.workspace import build_workspace_snapshot

                    _active_id = _pm.get_active_project_id(st.session_state)
                    if _active_id is not None:
                        _current_snapshot = build_workspace_snapshot()
                        if not _pm.save_workspace(_active_id, _current_snapshot):
                            raise OSError("当前项目保存失败，请先导出项目快照")
                    _new_project = _pm.create_project(
                        f"新研究 {datetime.now().strftime('%Y-%m-%d %H%M')}"
                    )
                    _pm.set_active_project(st.session_state, _new_project.id)
                    clear_research_session(st.session_state)
                    st.session_state["_clear_session_confirm"] = False
                    st.session_state["_session_reset_notice"] = "已保存原项目，并进入新的空白研究。"
                    gc.collect()
                    st.rerun()
                except Exception as _reset_err:
                    st.error(f"无法开始新研究：{_reset_err}")
            if _cc2.button("取消", width="stretch", key="_clear_session_no"):
                st.session_state["_clear_session_confirm"] = False
                st.rerun()
        elif st.button("➕ 开始新研究", type="secondary", width="stretch",
                       help="保存当前项目后创建空白项目，避免不同研究的数据混用"):
            st.session_state["_clear_session_confirm"] = True
            st.rerun()

    # ── 💡 帮助 · 入门（向导 + 术语速查）──
    with st.expander("💡 帮助 · 入门", expanded=not st.session_state.onboarding_completed):
        st.markdown(_get_onboarding_text(mode))
        if st.button("🎯 重新打开 5 分钟新手引导", key="restart_onboarding"):
            from src.ui.onboarding import restart_onboarding
            restart_onboarding()
            st.rerun()
        if st.button("✓ 知道了", key="dismiss_onboarding"):
            st.session_state.onboarding_completed = True
            try:
                from src.utils.user_prefs import update_pref
                update_pref("onboarding_completed", True)
            except Exception:
                pass
            st.rerun()

        st.divider()
        st.markdown(
            '<p style="font-size:0.85em; font-weight:600;">📖 统计术语速查</p>',
            unsafe_allow_html=True,
        )
        st.markdown("""
        <div style="font-size:0.75em; line-height:1.6;">
        <p><strong>p 值</strong> — 零假设为真时观察到当前或更极端结果的概率，p &lt; .05 通常视为"显著"。</p>
        <p><strong>效应量</strong> — 衡量效应大小，不受样本量影响，比 p 值更反映实际意义。</p>
        <p><strong>Cohen's d</strong> — 两组均值差异的效应量。0.2=小, 0.5=中, 0.8=大。</p>
        <p><strong>η²</strong> — 方差分析效应量，自变量解释因变量方差的比例。</p>
        <p><strong>r</strong> — 皮尔逊相关。.1=弱, .3=中, .5=强。</p>
        <p><strong>95% CI</strong> — 95% 置信区间，真实效应量有 95% 概率落在该范围。</p>
        <p><strong>α</strong> — 显著性水平/一类错误率，通常 .05。</p>
        <p><strong>检验力 (1-β)</strong> — 正确拒绝错误零假设的概率，通常要 &gt; .80。</p>
        <p><strong>正态性</strong> — 是否符合正态分布，常用 Shapiro-Wilk / K-S 检验。</p>
        <p><strong>方差齐性</strong> — 各组方差是否相等，常用 Levene 检验。</p>
        <p><strong>I²</strong> — 元分析异质性指标，由真实差异（非抽样误差）引起的变异比例。</p>
        </div>
        """, unsafe_allow_html=True)

    # ── 向导返回检测（从问卷/实验模块返回）──
    if st.session_state.get("_wizard_return") is not None:
        st.divider()
        ret = st.session_state._wizard_return
        st.success("✅ 模块操作已完成！")
        if st.button("🔙 返回向导继续", type="primary", width="stretch",
                     key="sidebar_return_wizard"):
            wiz_data = ret["data"]
            design = st.session_state.get("questionnaire_design")
            if design is not None and isinstance(design, dict) and design.get("items"):
                items = design.get("items", [])
                rev_count = sum(1 for it in items if it.get("reverse"))
                wiz_data["module_context"] = {
                    "module": "questionnaire",
                    "construct_name": design.get("construct_name", ""),
                    "dimensions": design.get("dimensions_used", []),
                    "item_count": len(items),
                    "reverse_count": rev_count,
                    "reverse_ratio": round(rev_count / len(items), 2) if items else 0,
                }
            st.session_state["_pending_undergrad_mode"] = True
            st.session_state.undergrad_path = ret["path"]
            st.session_state.undergrad_step = 2
            st.session_state.undergrad_wizard_data = wiz_data
            st.session_state._wizard_return = None
            st.rerun()

    # ── ⚙️ 设置 · 状态（语言 / 系统状态 / LLM 调用 / 环境）──
    with st.expander("⚙️ 设置 · 状态", expanded=False):
        output_lang = st.radio(
            "📝 统计报告语言",
            ["zh", "en"],
            format_func=lambda x: "中文 (APA7)" if x == "zh" else "English (APA7)",
            index=0 if st.session_state.get("output_language", "zh") == "zh" else 1,
            key="output_language_toggle",
            horizontal=True,
            help="切换统计报告和论文生成的语言（APA7 格式）。UI 界面保持中文不变。",
        )
        if output_lang != st.session_state.get("output_language"):
            st.session_state.output_language = output_lang
            st.rerun()

        st.divider()
        st.markdown(
            '<p style="font-size:0.85em; font-weight:600;">📊 系统状态</p>',
            unsafe_allow_html=True,
        )
        st.markdown(f"```\n{get_system_status()}\n```")

        st.divider()
        st.markdown(
            '<p style="font-size:0.85em; font-weight:600;">🔍 LLM 调用统计（本会话）</p>',
            unsafe_allow_html=True,
        )
        try:
            from src.llm_gateway import clear_traces, get_trace_summary
            summary = get_trace_summary()
            if summary["total_calls"] == 0:
                st.caption("尚无 LLM 调用")
            else:
                cost = summary.get("total_cost_cny", 0.0)
                cost_str = f"¥{cost:.4f}" if cost > 0 else "¥0（本地/缓存）"
                st.markdown(
                    f"**总调用**：{summary['total_calls']} 次　"
                    f"**总 token**：~{summary['total_tokens']}　"
                    f"**估算成本**：{cost_str}　"
                    f"**平均耗时**：{summary['avg_elapsed_ms']:.0f}ms"
                )
                st.caption(f"按模块：{summary.get('by_module', {})}")
                st.caption(f"按状态：{summary.get('by_status', {})}")
                by_model_cost = summary.get("by_model_cost", {})
                if by_model_cost:
                    cost_lines = "　".join(
                        f"{m}: ¥{c:.4f}" for m, c in by_model_cost.items() if c > 0
                    )
                    if cost_lines:
                        st.caption(f"按模型：{cost_lines}")
                st.caption("ℹ️ 成本=估算 token×公开价格表，仅供参考；本地 ollama 计 0")
                if st.button("🗑 清空统计", key="_clear_llm_traces"):
                    clear_traces()
                    st.rerun()
        except Exception:
            st.caption("（统计模块异常）")

        if st.session_state.env_status:
            es = st.session_state.env_status
            st.divider()
            st.markdown(
                '<p style="font-size:0.85em; font-weight:600;">🩺 环境状态</p>',
                unsafe_allow_html=True,
            )
            semopy_icon = "✅" if es["semopy_ok"] else "⚠️"
            fa_icon = "✅" if es["factor_analyzer_ok"] else "⚠️"
            llm_icon = "✅" if es["llm_ok"] else "💡"
            st.caption(f"{semopy_icon} CFA/SEM  |  {fa_icon} EFA  |  {llm_icon} LLM")

        st.divider()
        if st.button("🔧 运行系统诊断", key="_sidebar_diag", width="stretch"):
            from src.utils.environment_diagnosis import run_full_diagnosis, format_diagnosis_for_streamlit
            _diag = run_full_diagnosis(project_root=Path("."))
            _diag_results = format_diagnosis_for_streamlit(_diag)
            _s = _diag.summary
            on_diagnosis_run(_s["ok"], _s["warning"], _s["missing"] + _s["error"])
            for _r in _diag_results:
                st.write(f"{_r['icon']} {_r['name']}: {_r['detail']}")
            if _diag.all_ok:
                st.success("✅ 系统正常")
            else:
                st.error("部分组件异常，见上方详情")

    # ── 🧹 缓存清理（隐私伦理模块）──
    with st.expander("🧹 缓存清理", expanded=False):
        from src.utils.privacy_ethics import get_cache_dirs, clear_cache
        _cache_dirs = get_cache_dirs()
        if _cache_dirs:
            for _cd in _cache_dirs:
                st.caption(f"• {_cd['label']}：{_cd['size_mb']} MB")
            if st.button("🗑️ 一键清理所有缓存", key="_privacy_clear_cache", width="stretch"):
                _clear_result = clear_cache()
                if _clear_result["cleared"]:
                    st.success(f"✅ 已清理：{', '.join(_clear_result['cleared'])}")
                if _clear_result["errors"]:
                    st.error(f"部分失败：{'; '.join(_clear_result['errors'])}")
        else:
            st.caption("当前无可清理的缓存目录。")

    from src.version import APP_VERSION_LABEL
    st.caption(f"{APP_VERSION_LABEL} · 单轨 LLM · 本地项目存储 · 云端 AI 按需调用")

# ============================================================
# 本科论文向导模式覆盖（v3.3：路由配置表查表分发）
# ============================================================
if st.session_state.undergrad_mode:
    from src.utils.workspace import get_upstream_state as _get_upstream
    from src.upstream.routing import (
        RouteNotFoundError as _RouteNotFoundError,
        resolve_route as _resolve_route,
    )
    _upstream = _get_upstream(st.session_state)
    _phase = _upstream.get("phase", "funnel")
    _tier = _upstream.get("tier", "beginner")

    # v3.7 N6: 断点续读 banner — 仅在当前位置 ≠ 上次位置时显示
    try:
        from src.utils.workspace import (
            get_last_position as _get_last_pos,
            humanize_elapsed as _humanize,
            is_at_last_position as _is_at_last,
        )
        if not _is_at_last(st.session_state):
            _last = _get_last_pos(st.session_state)
            if _last and _last.get("phase"):
                _elapsed = _humanize(_last.get("timestamp", ""))
                _label = _last.get("label", "")
                _bcols = st.columns([5, 1, 1])
                with _bcols[0]:
                    st.info(f"⏯ **上次到这里：{_label}**" + (f" · {_elapsed}" if _elapsed else ""))
                if _bcols[1].button("跳转", key="_resume_jump", type="primary"):
                    _upstream["phase"] = _last["phase"]
                    if _last.get("step"):
                        _upstream["current_stage"] = int(_last["step"])
                    if _last["phase"] == "wizard" and _last.get("step"):
                        st.session_state["undergrad_step"] = int(_last["step"])
                    st.rerun()
                if _bcols[2].button("忽略", key="_resume_dismiss"):
                    # 把当前位置写成新 bookmark，下次就对齐了
                    from src.utils.workspace import update_last_position as _ulp
                    _cur_step = int(_upstream.get("current_stage", 1)) if _phase == "funnel" else int(st.session_state.get("undergrad_step", 1) or 1)
                    _ulp(_phase, step=_cur_step, session_state=st.session_state)
                    st.rerun()
    except Exception:
        pass

    try:
        _handler_id = _resolve_route(True, _phase, _tier)
    except _RouteNotFoundError as exc:
        st.error(f"❌ 不支持的路由组合：{exc}")
        st.info("请重置项目或在侧边栏切换设置。")
        st.stop()

    if _handler_id == "funnel_beginner":
        from src.ui.upstream_panel import render_funnel
        render_funnel()
        st.stop()
    elif _handler_id == "funnel_advanced":
        from src.ui.upstream_panel import render_advanced_skip_form
        render_advanced_skip_form()
        st.stop()
    elif _handler_id in ("literature_review_beginner", "literature_review_advanced"):
        from src.ui.literature_review_panel import render_literature_review
        render_literature_review(tier=_tier)
        st.stop()
    elif _handler_id == "wizard":
        from src.ui.undergrad_wizard import render_undergrad_wizard
        render_undergrad_wizard()
        st.stop()
    else:
        st.error(f"❌ 未知 handler_id：{_handler_id}")
        st.stop()

# ============================================================
# 模式1: 数据分析
# ============================================================
if mode == "📈 数据分析":
    # Lazy imports — these modules are heavy (~4s total: scipy, jieba, statsmodels)
    from src.parser.intent_resolver import resolve as resolve_intent
    from src.analysis.runner import run_analysis
    from src.output.formatter import format_result_summary, build_apa7_report, check_effect_size_required
    from src.output.interpretation import generate_interpretation
    from src.ui.renderers import (
        render_assumption, render_result_table, render_charts,
        export_html, export_csv,
    )
    from src.data.demo_datasets import (
        generate_demo_questionnaire_data,
        generate_demo_experiment_data,
        generate_demo_repeated_measures_data,
        generate_demo_multi_group_data,
        generate_demo_mediation_data,
    )
    from src.ui.undergrad_wizard import (
        render_undergrad_wizard,
        render_common_mistake_warnings,
        render_assumption_failure_guidance,
        render_pii_warning,
    )
    st.title("📈 数据分析")
    st.caption("上传研究数据，选择分析任务，并获得可核查的统计结果与 APA7 输出。")

    # ── 数据上传与状态信息（页面顶部，路由 stop() 前必须先渲染） ──
    # 之前在 sidebar；v3.7.x 移到主区，因为只有数据分析页才需要上传，
    # 也腾出 sidebar 空间留给工作区/语言/全局设置。
    _has_df = st.session_state.df is not None
    if _has_df:
        st.markdown("##### 📁 数据上传 / 替换")
    else:
        st.markdown("### 📁 数据上传")
    uploaded_file = st.file_uploader(
        "拖拽文件到此处或点击上传",
        type=["csv", "xlsx", "xls", "sav", "json", "jsonl", "docx", "md", "markdown"],
        help="支持 CSV、Excel (.xlsx/.xls)、SPSS (.sav)、jsPsych (.json/.jsonl)、Word 表格 (.docx)、Markdown 表格 (.md) 格式",
        key="file_uploader",
        label_visibility="collapsed" if _has_df else "visible",
    )

    if uploaded_file is not None:
        from src.ui.upload_state import commit_loaded_dataset, uploaded_file_identity
        current_name = uploaded_file.name
        _upload_identity = uploaded_file_identity(uploaded_file)
        if _upload_identity != st.session_state.get("_uploaded_file_identity"):
            # 大文件列选择提示
            _upload_size = getattr(uploaded_file, "size", None)
            if _upload_size is None:
                _upload_size = len(uploaded_file.getbuffer())
            size_mb = _upload_size / (1024 * 1024)
            usecols = None
            _ready_to_load = True
            if size_mb > 20:
                st.warning(f"⚠️ 文件较大（{size_mb:.1f} MB），建议只加载分析所需的列以节省内存。")
                try:
                    uploaded_file.seek(0)
                    if current_name.lower().endswith(".csv"):
                        preview_cols = pd.read_csv(uploaded_file, nrows=0).columns.tolist()
                    elif current_name.lower().endswith((".xlsx", ".xls")):
                        preview_cols = pd.read_excel(uploaded_file, nrows=0).columns.tolist()
                    else:
                        preview_cols = []
                    uploaded_file.seek(0)
                    if preview_cols:
                        selected_cols = st.multiselect(
                            "选择需要加载的列（留空则加载全部）：",
                            options=preview_cols,
                            default=[],
                            key="large_file_cols",
                        )
                        if selected_cols:
                            usecols = selected_cols
                        _ready_to_load = st.button(
                            "加载所选列" if selected_cols else "加载全部列",
                            key="load_large_file",
                            type="primary",
                        )
                except Exception:
                    uploaded_file.seek(0)
            if _ready_to_load:
                try:
                    uploaded_file.seek(0)
                    with st.spinner("正在加载数据..."):
                        new_df, new_meta = load_data(uploaded_file, usecols=usecols)
                        new_inspector = inspect_dataframe(new_df)
                    # 全部成功后再替换，坏文件不会清掉当前有效数据。
                    commit_loaded_dataset(
                        st.session_state,
                        dataframe=new_df,
                        meta=new_meta,
                        inspector=new_inspector,
                        file_name=current_name,
                        identity=_upload_identity,
                    )
                    on_data_upload(len(new_df), len(new_df.columns), current_name.rsplit(".", 1)[-1])
                    _autosave_current_workspace(force=True)
                except Exception as e:
                    st.session_state["_upload_error"] = str(e)
                    st.error(f"❌ 数据加载失败：{e}。已保留当前数据。")
                    on_error_display("data_load_failed", "error")

    if not _has_df and st.session_state.df is None:
        st.info("👆 请上传数据文件以开始分析")
        st.caption("或者试试示例数据：")
        demo_col1, demo_col2, demo_col3, _ = st.columns([1, 1, 1, 3])
        _demo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures")
        with demo_col1:
            if st.button("📋 问卷数据", width="stretch", help="7维度心理量表 (N=50)"):
                _p = os.path.join(_demo_dir, "sample_survey.csv")
                if os.path.exists(_p):
                    _demo_df, _demo_meta = load_data(_p)
                    st.session_state.df = _demo_df
                    st.session_state.meta = _demo_meta
                    st.session_state.inspector = inspect_dataframe(_demo_df)
                    st.session_state.file_name = "sample_survey.csv"
                    st.rerun()
        with demo_col2:
            if st.button("📊 t 检验数据", width="stretch", help="两组对比数据"):
                _p = os.path.join(_demo_dir, "sample_ttest.csv")
                if os.path.exists(_p):
                    _demo_df, _demo_meta = load_data(_p)
                    st.session_state.df = _demo_df
                    st.session_state.meta = _demo_meta
                    st.session_state.inspector = inspect_dataframe(_demo_df)
                    st.session_state.file_name = "sample_ttest.csv"
                    st.rerun()
        with demo_col3:
            if st.button("🔬 方差分析数据", width="stretch", help="多组对比数据"):
                _p = os.path.join(_demo_dir, "sample_anova.csv")
                if os.path.exists(_p):
                    _demo_df, _demo_meta = load_data(_p)
                    st.session_state.df = _demo_df
                    st.session_state.meta = _demo_meta
                    st.session_state.inspector = inspect_dataframe(_demo_df)
                    st.session_state.file_name = "sample_anova.csv"
                    st.rerun()

    if st.session_state.df is not None:
        df = st.session_state.df
        meta = st.session_state.meta
        inspector = st.session_state.inspector

        # ── 数据状态条 ──
        n_rows = df.shape[0] if hasattr(df, "shape") else len(df)
        n_cols = meta.get('col_count', df.shape[1])
        status_cols = st.columns([4, 2, 1])
        with status_cols[0]:
            st.success(f"✅ 已加载：{st.session_state.file_name}")
        with status_cols[1]:
            st.caption(
                f"格式：{meta.get('source_type', '?').upper()} | "
                f"N={n_rows} | 列数：{n_cols}"
            )
        with status_cols[2]:
            if n_rows < 30:
                st.markdown(
                    '<span style="color:#f39c12; font-size:0.85em;">⚠️ 小样本 (N&lt;30)</span>',
                    unsafe_allow_html=True,
                )
            elif n_rows < 50:
                st.markdown(
                    '<span style="color:#3498db; font-size:0.85em;">ℹ️ 中等样本 (N&lt;50)</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span style="color:#27ae60; font-size:0.85em;">✅ 大样本 (N≥50)</span>',
                    unsafe_allow_html=True,
                )

        # ── 数据细节（折叠） ──
        info_cols = st.columns(2)
        with info_cols[0]:
            with st.expander("📋 数据预览（前10行）"):
                st.dataframe(df.head(10), width="stretch")
        with info_cols[1]:
            with st.expander("🔤 变量列表"):
                for col, info in inspector.items():
                    type_label = VAR_ROLE_LABELS.get(info["type"], info["type"])
                    missing_info = f" | 缺失: {info['n_missing']}" if info["n_missing"] > 0 else ""
                    st.text(f"[{type_label}] {col} (唯一值: {info.get('n_unique', '?')}{missing_info})")

        issues = validate_data(df)
        for issue in issues:
            st.warning(issue)

        render_pii_warning(df)

        # ── 交互式图表开关 ──
        has_plotly = True
        try:
            import plotly
        except Exception:
            has_plotly = False
        interactive = st.toggle(
            "✨ 交互式图表",
            value=st.session_state.interactive_charts,
            key="interactive_charts_toggle",
            disabled=not has_plotly,
            help="开启后图表支持缩放、悬停提示和数据筛选。关闭后渲染为静态图，加载更快。",
        )
        if interactive != st.session_state.interactive_charts:
            st.session_state.interactive_charts = interactive
            st.rerun()
        if not has_plotly:
            st.caption("⚠️ 未检测到 Plotly，交互式图表已禁用。")

    st.divider()

    # ── 快捷入口路由（上传组件已渲染，此时 stop 不会切断上传入口）──
    quick_entry = st.session_state.get("quick_entry")
    # 路径 B/C：用户进了 quick_entry detail，无论有没有数据都展示 detail
    # （detail 内部会按 df 是否存在切换"参数预填 vs 提示先上传"）
    if quick_entry:
        render_quick_entry_detail()
        st.stop()

    # ── 智能首页：无数据时显示三大快捷入口 ──
    if st.session_state.df is None:
        render_quick_entry_homepage()
        st.stop()

    # ── 方法选择助手 ──
    with st.expander("🎯 不知道用什么方法？点击这里", expanded=False):
        st.markdown("#### 根据你的研究目的选择")
        helper_q1 = st.selectbox(
            "你的研究目的是什么？",
            ["", "比较两组均值差异", "比较多组均值差异", "分析两个变量的关系",
             "控制第三变量后的相关", "检验前后变化", "检验分布差异（非正态数据）",
             "检验中介/间接效应", "检验调节效应", "探索潜在维度（因素分析）",
             "检验量表信度", "检验类别变量关联"],
            key="helper_goal",
        )
        if helper_q1:
            recommendations = {
                "比较两组均值差异": ("independent_ttest", "独立样本 t 检验"),
                "比较多组均值差异": ("one_way_anova", "单因素方差分析 (One-Way ANOVA)"),
                "分析两个变量的关系": ("pearson_corr", "Pearson 相关分析"),
                "控制第三变量后的相关": ("partial_corr", "偏相关分析"),
                "检验前后变化": ("paired_ttest", "配对样本 t 检验"),
                "检验分布差异（非正态数据）": ("mann_whitney", "Mann-Whitney U 检验"),
                "检验中介/间接效应": ("mediation", "中介效应分析"),
                "检验调节效应": ("moderation", "调节效应分析"),
                "探索潜在维度（因素分析）": ("efa", "探索性因素分析 (EFA)"),
                "检验量表信度": ("cronbach_alpha", "Cronbach's α 信度分析"),
                "检验类别变量关联": ("chi_square", "卡方检验 (χ²)"),
            }
            if helper_q1 in recommendations:
                method_key, method_name = recommendations[helper_q1]
                st.success(f"🎯 推荐：**{method_name}**")
                if st.session_state.df is not None and st.session_state.inspector is not None:
                    inspector = st.session_state.inspector
                    numeric_cols = [c for c, info in inspector.items()
                                   if info.get("type") in ("continuous", "numeric", "float", "int")]
                    cat_cols = [c for c, info in inspector.items()
                                if info.get("type") in ("categorical", "object", "string", "str")]
                    st.caption(f"📊 可用的数值变量：{', '.join(numeric_cols) if numeric_cols else '未检测到'}")
                    st.caption(f"📁 可用的分类变量：{', '.join(cat_cols) if cat_cols else '未检测到'}")

    # ── 推荐方案预填 ──
    from src.ui.state_keys import ANALYSIS_RECIPE_KEY, RECIPE_EXECUTED_KEY
    _recipe = st.session_state.get(ANALYSIS_RECIPE_KEY)
    _recipe_used = False
    if _recipe and not st.session_state.get(RECIPE_EXECUTED_KEY):
        st.info(
            f"🚀 **来自方法推荐的分析方案**: {_recipe.method_zh}\n\n"
            f"变量角色: {', '.join(f'{k}={v}' for k, v in _recipe.variable_roles.items())}\n\n"
            f"置信度: {_recipe.confidence} | 前提检查: {', '.join(_recipe.assumption_checks[:3]) or '无'}"
        )
        _rcol1, _rcol2, _rcol3 = st.columns([2, 2, 2])
        with _rcol1:
            _recipe_used = st.button("✅ 填入推荐方案", type="primary", key="use_recipe_prefill")
        with _rcol2:
            if st.button("✏️ 修改后使用", key="modify_recipe"):
                st.session_state["_recipe_prefill_text"] = f"使用{_recipe.method_zh}分析"
        with _rcol3:
            if st.button("❌ 忽略推荐", key="dismiss_recipe"):
                st.session_state[RECIPE_EXECUTED_KEY] = "dismissed"
                st.rerun()

    if _recipe_used and _recipe:
        # recipe 中的 variable_roles 是角色说明，不是用户数据的真实列名。
        # 只预填方法，让用户明确变量后再走统一的解析与防呆检查。
        st.session_state["_recipe_prefill_text"] = (
            f"使用{_recipe.method_zh}分析；请在这里补充因变量、自变量或分组变量的列名"
        )
    _prefill_text = st.session_state.pop("_recipe_prefill_text", "")

    col1, col2 = st.columns([3, 1])
    with col1:
        request = st.text_area(
            "请输入您的分析需求：",
            value=_prefill_text,
            placeholder='例如："比较男女生在焦虑量表得分上的差异"\n'
                        '"分析焦虑得分与抑郁得分的相关性"\n'
                        '"比较三个年级在学业成绩上是否存在差异"',
            height=100,
            key="request_input",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🔍 开始分析", type="primary", width="stretch")
        clear_btn = st.button("🗑 清空分析结果", width="stretch")

    if clear_btn:
        st.session_state.analysis_output = None
        st.session_state.plan = None
        st.rerun()

    # 分析执行（含防呆检查）
    if analyze_btn and st.session_state.df is not None and request.strip():
        with st.spinner("正在解析分析需求..."):
            plan = resolve_intent(st.session_state.df, request, col_info=st.session_state.inspector)
            st.session_state.plan = plan

        if plan.ambiguity_score > 0.5 and plan.suggested_followups:
            st.warning("⚠ 分析需求不够明确，请确认以下解析结果：")

        # ── 防呆检查1: 变量类型匹配 ──
        if st.session_state.inspector:
            dv_types = []
            for dv in (plan.dependent_vars or []):
                info = st.session_state.inspector.get(dv, {})
                dv_types.append(info.get("type", "unknown"))
            iv_types = []
            for iv in (plan.independent_vars or []):
                info = st.session_state.inspector.get(iv, {})
                iv_types.append(info.get("type", "unknown"))

            type_check = check_variable_type_match(plan.test_type, dv_types, iv_types)
            if not type_check.passed:
                st.error(f"{type_check.title}\n\n{type_check.message}")
                if type_check.suggested_test_type:
                    st.info(
                        f"💡 建议改用：**{type_check.suggested_test_name}** — "
                        f"在分析需求框中输入相关描述即可自动切换。"
                    )
                st.stop()

        # ── 防呆检查2: 样本量警告 ──
        n_rows = st.session_state.df.shape[0]
        sample_check = check_sample_size(n_rows, plan.test_type)
        if sample_check.severity == "warn":
            st.warning(f"{sample_check.title}\n\n{sample_check.message}")

        # ── 防呆检查3: 多重比较拦截 ──
        multi_check = check_multiple_comparisons(
            st.session_state.analysis_history,
            plan.test_type,
            list(plan.dependent_vars) if hasattr(plan, "dependent_vars") else [],
        )
        if not multi_check.passed:
            st.error(f"{multi_check.title}\n\n{multi_check.message}")
            col_switch, col_ignore = st.columns(2)
            with col_switch:
                if st.button(f"🔄 切换为 {multi_check.suggested_test_name}", type="primary"):
                    new_request = f"使用{multi_check.suggested_test_name}"
                    if hasattr(plan, "dependent_vars") and plan.dependent_vars:
                        new_request += f"分析{'、'.join(plan.dependent_vars)}"
                    st.info(f"请在分析需求框中输入：**{new_request}**")
                    st.stop()
            with col_ignore:
                if st.button("▶️ 仍然运行（我了解风险）"):
                    st.warning("已忽略多重比较警告，继续运行。请务必在论文中报告 Bonferroni 校正结果。")
                    # 继续执行（跳出 if 块，继续下方代码）
                    pass
                else:
                    st.stop()

        # Cache key: data content hash + plan repr。每次真正点击分析时重算内容哈希；
        # 不能用对象 id 代替内容版本，因为清洗器可能原地修改 DataFrame。
        import hashlib
        _df_obj = st.session_state.df
        _df_content_hash = hashlib.md5(
            pd.util.hash_pandas_object(_df_obj).values.tobytes()
        ).hexdigest()
        _cache_key = hashlib.md5(
            f"{_df_content_hash}|{plan}".encode()
        ).hexdigest()
        _prev_cache = st.session_state.get("_analysis_cache_key")
        if _prev_cache == _cache_key and st.session_state.get("analysis_output") is not None:
            output = st.session_state.analysis_output
            st.toast("命中缓存，跳过重复计算", icon="⚡")
        else:
            with st.spinner("正在执行统计分析..."):
                with AnalysisTimer(plan.test_type):
                    output = run_analysis(st.session_state.df, plan)
                st.session_state.analysis_output = output
                st.session_state["_analysis_cache_key"] = _cache_key

            # ── 行为感知：记录分析历史（非向导模式） ──
            if not st.session_state.undergrad_mode:
                history_entry = {
                    "test_type": plan.test_type,
                    "dv": list(plan.dependent_vars) if hasattr(plan, "dependent_vars") else [],
                    "iv": list(plan.independent_vars) if hasattr(plan, "independent_vars") else [],
                }
                st.session_state.analysis_history.append(history_entry)

            _autosave_current_workspace(force=True)

            # ── 自动归档 ──
            try:
                tag = st.session_state.get("archive_tag", "")
                report_md = build_apa7_report(output)
                params = {
                    "test_type": plan.test_type,
                    "test_name_zh": output.get("test_name_zh", ""),
                    "dependent_vars": plan.dependent_vars if hasattr(plan, "dependent_vars") else [],
                    "independent_vars": plan.independent_vars if hasattr(plan, "independent_vars") else [],
                    "confidence_level": plan.confidence_level if hasattr(plan, "confidence_level") else 0.95,
                }
                arch_result = archive_analysis(
                    st.session_state.df, output, report_md, params,
                    tag=tag, file_name=st.session_state.get("file_name", ""),
                )
                st.toast(f"📁 已自动存档: {arch_result['archive_id'][:8]}...", icon="📁")
            except Exception:
                pass  # 存档失败不阻断分析
    elif analyze_btn and st.session_state.df is None:
        st.error("请先上传数据文件！")
    elif analyze_btn and not request.strip():
        st.error("请输入分析需求！")

    # 分析计划。恢复旧工作区时可能只有结果而缺少计划，保持 plan 明确定义。
    plan = st.session_state.get("plan")
    if plan is not None:
        test_name = get_test_name(plan.test_type)
        with st.expander(f"📋 分析计划：{test_name}", expanded=True):
            cols = st.columns(4)
            cols[0].metric("检验方法", test_name)
            cols[1].metric("因变量", ", ".join(plan.dependent_vars) if plan.dependent_vars else "自动选择")
            cols[2].metric("自变量/分组", ", ".join(plan.independent_vars) if plan.independent_vars else "自动选择")
            cols[3].metric("置信度", f"{plan.confidence_level:.0%}")
            if plan.parsed_keywords:
                st.caption(f"识别关键词：{'、'.join(plan.parsed_keywords)}")
            if plan.ambiguity_score > 0.4:
                st.warning(f"解析置信度较低（{1-plan.ambiguity_score:.0%}），请检查分析计划是否正确。")

    # Pipeline 管理
    with st.expander("📊 分析 Pipeline（保存/复跑）", expanded=False):
        render_pipeline_ui()

    # 分析结果
    if st.session_state.analysis_output is not None:
        output = st.session_state.analysis_output
        df = st.session_state.df

        st.divider()

        for err in output.get("errors", []):
            if err["severity"] == "error":
                st.error(f"❌ {err['message']}")
            else:
                st.warning(f"⚠ {err['message']}")

        # ── 行为感知：多次t检验检测（非向导模式） ──
        if not st.session_state.undergrad_mode:
            history = st.session_state.analysis_history
            recent_ttests = [
                h for h in history[-6:]
                if h["test_type"] in ("independent_ttest", "mann_whitney")
            ]
            if len(recent_ttests) >= 3:
                all_dvs = [tuple(h["dv"]) for h in recent_ttests]
                if len(set(all_dvs)) <= 2:
                    st.markdown("""
                    <div class="error-box">
                    <strong>⚠️ 检测到多次两两t检验！</strong><br>
                    你在短时间内进行了 {} 次独立样本t检验，且使用的因变量高度重叠。<br>
                    多次两两比较会<strong>累积一类错误概率</strong>（每次检验5%的错误风险）。<br>
                    <strong>建议：</strong>如果你的分组有3组或以上，请改用<strong>单因素ANOVA + 事后检验</strong>
                    （Tukey HSD 或 Bonferroni 校正）。<br>
                    <em>输入"单因素方差分析"即可切换分析方法。</em>
                    </div>
                    """.format(len(recent_ttests)), unsafe_allow_html=True)

        # ── 本科常见错误预防提示 ──
        render_common_mistake_warnings(output, df, plan)

        # ── 假设失败替代方法引导 ──
        render_assumption_failure_guidance(output, plan, df)

        # ── 相关分析后续建议 ──
        if plan is not None and plan.test_type in ("pearson_corr", "spearman_corr", "partial_corr"):
            result = output.get("result")
            if result is not None and hasattr(result, "corr_matrix") and result.corr_matrix is not None:
                cm = result.corr_matrix
                if hasattr(cm, "values"):
                    vals = cm.values
                else:
                    vals = cm
                high_corr = (abs(vals) > 0.5).sum() > 1
                n_vars = cm.shape[0] if hasattr(cm, "shape") else len(vals)
                if high_corr and n_vars >= 3:
                    st.markdown("""
                    <div class="info-box">
                    <strong>💡 发现了较强的相关关系！</strong><br>
                    你的变量间存在 |r| > 0.5 的相关。如果你想进一步探究：<br>
                    🔗 <strong>中介分析</strong>：一个变量是否通过另一个变量影响第三个变量？<br>
                    🔗 <strong>调节分析</strong>：某个变量是否会加强/减弱另两个变量间的关系？<br>
                    在分析需求框中输入"中介效应"或"调节效应"即可尝试。
                    </div>
                    """, unsafe_allow_html=True)

        # ── 动态术语展示 ──
        if plan is not None:
            term_map = {
                "independent_ttest": ["p值", "Cohen's d", "95% CI", "效应量", "正态性"],
                "paired_ttest": ["p值", "Cohen's d", "95% CI", "效应量", "配对设计"],
                "one_way_anova": ["η²", "事后检验", "主效应", "F检验", "方差齐性"],
                "pearson_corr": ["r", "p值", "95% CI", "效应量", "散点图"],
                "partial_corr": ["r", "p值", "偏相关", "控制变量", "净相关"],
                "mann_whitney": ["p值", "r (效应量)", "中位数", "非参数检验", "秩次"],
                "kruskal_wallis": ["p值", "η²", "中位数", "非参数检验", "Dunn检验"],
                "mediation": ["间接效应", "Bootstrap", "a×b", "总效应", "直接效应"],
                "moderation": ["交互效应", "简单斜率", "调节变量", "主效应", "Johnson-Neyman"],
                "cronbach_alpha": ["α系数", "内部一致性", "题总相关", "删除后α", "信度"],
                "efa": ["KMO", "Bartlett检验", "因子载荷", "特征值", "方差解释率"],
                "chi_square": ["χ²", "Cramér's V", "列联表", "期望频数", "独立性检验"],
            }
            related = term_map.get(plan.test_type, ["p值", "效应量", "95% CI", "检验力", "显著性"])
            # 提取实际变量名用于术语示例
            dv_name = plan.dependent_vars[0] if hasattr(plan, "dependent_vars") and plan.dependent_vars else "因变量"
            iv_name = plan.independent_vars[0] if hasattr(plan, "independent_vars") and plan.independent_vars else "自变量"
            dv_label = dv_name if dv_name and dv_name != "因变量" else "因变量"
            iv_label = iv_name if iv_name and iv_name != "自变量" else "自变量"

            term_descriptions_enhanced = {
                "p值": {
                    "定义": "在零假设为真时，观察到当前或更极端结果的概率。",
                    "通俗理解": "判断结果是否「巧合」的指标。p<.05 意味着如果零假设成立，出现这种结果的可能性不到5%，所以倾向于认为差异是真实的。",
                    "本例应用": f"如果 {dv_label} 分析的 p < .05，可以认为差异具有统计显著性；但p值不能说明效应大小。",
                },
                "Cohen's d": {
                    "定义": "两组均值差异的标准化效应量指标。",
                    "通俗理解": "用来衡量两组之间差异有多大。0.2=小差异（肉眼难辨），0.5=中等差异（可以察觉），0.8=大差异（非常明显）。",
                    "本例应用": f"如果 {iv_label} 两组间 {dv_label} 的 Cohen's d = 0.6，说明组间差异为中等偏大。建议在论文中报告 Cohen's d 并附置信区间。",
                },
                "95% CI": {
                    "定义": "95%置信区间，表示在重复抽样下，真实参数值有95%的概率落在此区间内。",
                    "通俗理解": "真实效应可能在这个范围之内。区间越窄，估计越精确；如果区间包含0，说明效应可能不存在。",
                    "本例应用": f"对于 {dv_label} 的组间差异，如果95% CI为 [2.1, 8.5]，说明真实差异大概率在2.1到8.5之间。",
                },
                "效应量": {
                    "定义": "衡量效应大小的标准化指标，不受样本量影响。",
                    "通俗理解": "p值只告诉你'有没有差异'，效应量告诉你'差异有多大'。大样本下微小差异也会显著，所以效应量比p值更重要。",
                    "本例应用": f"论文中除报告p值外，必须报告 {dv_label} 分析的效应量（Cohen's d / η² / r），这是APA7格式的要求。",
                },
                "η²": {
                    "定义": "方差分析效应量，表示自变量可以解释因变量总变异的比例。",
                    "通俗理解": "这个指标告诉你，你的分组变量能解释结果差异的百分之多少。0.01=解释1%（小），0.06=解释6%（中），0.14=解释14%（大）。",
                    "本例应用": f"如果 {iv_label} 对 {dv_label} 的 η² = 0.10，说明 {iv_label} 可以解释 {dv_label} 10% 的变异，属于中等偏大效应。",
                },
                "r": {
                    "定义": "皮尔逊积差相关系数，衡量两个连续变量之间线性关系的强度和方向。",
                    "通俗理解": "数值在-1到+1之间。正数=一个变量大另一个也大，负数=一个变量大另一个就小。绝对值越接近1关系越强。",
                    "本例应用": f"如果 {dv_label} 与另一个变量的 r = 0.45，说明二者存在中等强度的正相关。注意：相关不代表因果！",
                },
                "正态性": {
                    "定义": "数据分布是否符合正态（钟形）曲线。常用 Shapiro-Wilk 检验或 Q-Q 图判断。",
                    "通俗理解": "很多统计方法（t检验、ANOVA、Pearson相关）假设数据近似正态。不满足时需要用非参数替代方法。",
                    "本例应用": f"对 {dv_label} 进行 Shapiro-Wilk 检验，如果 p > .05 则满足正态性假设；若 p < .05 则需考虑非参数检验。",
                },
                "方差齐性": {
                    "定义": "各组内因变量的方差是否相等。常用 Levene 检验判断。",
                    "通俗理解": "假如实验组和控制组的结果波动程度差别很大，就不满足方差齐性。这时需要调整自由度（Welch校正）或用非参数方法。",
                    "本例应用": f"对 {iv_label} 各组的 {dv_label} 进行 Levene 检验，p > .05 表示方差齐性成立。",
                },
                "事后检验": {
                    "定义": "ANOVA显著后，进行的两两比较检验，确定具体哪些组之间存在差异。",
                    "通俗理解": "ANOVA只会告诉你'有差异'，不会告诉你'谁和谁有差异'。事后检验就像是在各组之间一一比较。",
                    "本例应用": f"若 {iv_label} 的ANOVA显著，使用Tukey HSD（方差齐性时）或Games-Howell（方差不齐时）进行各组 {dv_label} 的两两比较。",
                },
                "F检验": {
                    "定义": "方差分析中的检验统计量，F = 组间变异 / 组内变异。",
                    "通俗理解": "F值越大，说明组间差异相对于组内随机波动越大，越可能显著。",
                    "本例应用": f"单因素方差分析中，F值反映了 {iv_label} 各组间 {dv_label} 差异相对于组内个体差异的倍数。",
                },
                "非参数检验": {
                    "定义": "不依赖数据分布假设（如正态性）的统计检验方法。",
                    "通俗理解": "当数据不符合正态分布时使用的'Plan B'。基于数据的排序（秩次）而非原始数值，更稳健但检验力稍低。",
                    "本例应用": f"若 {dv_label} 不满足正态性，可选用 Mann-Whitney U 检验（两组）或 Kruskal-Wallis 检验（多组）作为替代。",
                },
                "内部一致性": {
                    "定义": "量表或测验中，各题目测量同一潜在构念的程度。",
                    "通俗理解": "衡量你的问卷题目是否'一条心'。如果题目真的在测同一个东西，答题结果应该高度一致。",
                    "本例应用": f"对 {dv_label} 量表进行信度分析，计算 Cronbach's α，若 α > .80 则内部一致性良好，可在论文中报告。",
                },
                "KMO": {
                    "定义": "Kaiser-Meyer-Olkin 取样适切性量数，衡量变量间偏相关大小，判断数据是否适合因素分析。",
                    "通俗理解": "判断你的数据是否适合做因素分析的指标。值越接近1越好，>0.8为良好，<0.5则不适合。",
                    "本例应用": f"对 {dv_label} 相关题项计算 KMO 值，若 KMO > 0.7 则适合进行探索性因素分析。",
                },
                "间接效应": {
                    "定义": "中介分析中，自变量X通过中介变量M对因变量Y产生的影响（a×b路径）。",
                    "通俗理解": "X不是直接导致Y，而是通过一个中间变量M间接影响Y。比如'压力→失眠→成绩下降'，失眠就是中介变量。",
                    "本例应用": f"使用 Bootstrap 法（5000次）估计 {iv_label} 通过中介变量对 {dv_label} 的间接效应，若95% CI不包含0则中介效应显著。",
                },
                "Bootstrap": {
                    "定义": "从原始样本中有放回地重复抽样以估计统计量抽样分布的方法。",
                    "通俗理解": "因为只有一份数据，无法知道统计量的真实分布。Bootstrap就是'把这份数据反复洗牌重抽'来模拟可能的变化范围。",
                    "本例应用": f"中介效应分析中，用Bootstrap（通常5000次）生成间接效应的95%置信区间，比传统Sobel检验更稳健。",
                },
                "交互效应": {
                    "定义": "调节分析中，两个自变量对因变量的联合效应不等于各自主效应之和的部分。",
                    "通俗理解": "交互效应就是'1+1≠2'的情况。例如：压力对成绩的影响，在高社会支持组和低社会支持组可能不同，这就是交互。",
                    "本例应用": f"检验 {iv_label} 与调节变量的交互项对 {dv_label} 是否显著，若显著则存在调节效应，需进一步做简单斜率分析。",
                },
                "χ²": {
                    "定义": "卡方统计量，用于检验观察频数与期望频数之间的差异。",
                    "通俗理解": "用来判断两个类别变量是否有关联。值越大，说明实际分布与'没有关联'的预期差距越大。",
                    "本例应用": f"对 {iv_label} 和 {dv_label} 的列联表进行卡方独立性检验，同时报告 Cramér's V 作为效应量。",
                },
                "α系数": {
                    "定义": "Cronbach's α，衡量量表内部一致性的最常用指标。",
                    "通俗理解": "0.7是底线，0.8是良好，0.9是优秀。太低说明题目各测各的，需要删除或修改部分题目。",
                    "本例应用": f"对 {dv_label} 量表计算 Cronbach's α，报告时需同时给出删除各题后的α值，以评估每题的贡献。",
                },
                "配对设计": {
                    "定义": "同一组被试在不同条件或时间点的测量，控制了个体差异。",
                    "通俗理解": "每个人和自己比（前后对比），而非和别人比。配对设计比独立组设计检验力更高，因为排除了个体差异的干扰。",
                    "本例应用": f"本分析采用配对设计，比较同一被试在 {dv_label} 上的前后变化，使用配对t检验或Wilcoxon检验。",
                },
                "偏相关": {
                    "定义": "在控制一个或多个变量的影响后，两个变量之间的净相关。",
                    "通俗理解": "剥离掉混淆变量的影响后，看X和Y还有没有关系。比如控制'年龄'后看'锻炼'和'健康'的关系。",
                    "本例应用": f"在控制混淆变量后，检验 {dv_label} 与其他变量的净相关，偏相关系数排除了第三变量的影响。",
                },
                "因子载荷": {
                    "定义": "因素分析中，观测变量与潜在因子之间的相关系数，表示变量在因子上的权重。",
                    "通俗理解": "衡量每道题目'属于'哪个因素的程度。载荷越高（通常>0.4），题目越能代表该因素。",
                    "本例应用": f"旋转后各题在 {dv_label} 相关因子上的载荷，>0.4为可接受，>0.6为良好，用于判断因子归属。",
                },
                "Cramér's V": {
                    "定义": "卡方检验的效应量指标，衡量两个类别变量之间的关联强度。",
                    "通俗理解": "类似相关系数，但专门用于类别变量。0.1=弱关联，0.3=中等关联，0.5=强关联。",
                    "本例应用": f"除了报告 χ² 和p值外，还需报告 {iv_label} 与 {dv_label} 的 Cramér's V 作为效应量。",
                },
                "r (效应量)": {
                    "定义": "非参数检验中基于Z值的效应量指标，r = Z/√N。",
                    "通俗理解": "非参数检验中报告p值不够，还需要r来表示效应大小。0.1=小, 0.3=中, 0.5=大。",
                    "本例应用": f"Mann-Whitney U 检验后计算 r 效应量，r > 0.3 表示 {iv_label} 组间 {dv_label} 差异具有中等以上实际意义。",
                },
                "Dunn检验": {
                    "定义": "Kruskal-Wallis检验显著后的非参数事后两两比较方法。",
                    "通俗理解": "非参数版的事后检验，使用Bonferroni校正控制整体一类错误率。",
                    "本例应用": f"Kruskal-Wallis检验显著后，用 Dunn 检验进行 {iv_label} 各组 {dv_label} 的两两比较。",
                },
                "特征值": {
                    "定义": "因素分析中衡量每个因子解释方差量的指标，特征值>1的因子通常保留。",
                    "通俗理解": "可以理解为每个因素的'重要性得分'。特征值>1意味着该因素解释的信息量比一个原始变量还多。",
                    "本例应用": f"根据 Kaiser 准则（特征值>1）和碎石图拐点，确定 {dv_label} 相关题项的因子数量。",
                },
            }
            with st.expander("📖 本次分析相关术语（点击展开）"):
                for term in related:
                    info = term_descriptions_enhanced.get(term)
                    if info:
                        with st.expander(f"**{term}** — {info['通俗理解'][:40]}..."):
                            st.markdown(f"**📖 定义：** {info['定义']}")
                            st.markdown(f"**💡 通俗理解：** {info['通俗理解']}")
                            st.markdown(f"**🔬 本例应用：** {info['本例应用']}")
                    else:
                        st.markdown(f"**{term}**")

        desc = output.get("descriptive")
        if desc is not None and not desc.empty:
            with st.expander("📊 描述性统计", expanded=True):
                st.dataframe(desc, width="stretch")

        assumptions = output.get("assumptions", {})
        if assumptions:
            with st.expander("🔬 假设检验"):
                for category, results in assumptions.items():
                    if isinstance(results, dict):
                        for name, r in results.items():
                            render_assumption(r, f"{category}: {name}")
                    else:
                        render_assumption(results, category)

        reasoning = output.get("reasoning")
        if reasoning is not None:
            with st.expander("💭 分析思路", expanded=False):
                st.markdown(f"### 为什么选择{reasoning.test_name_zh}？")
                st.markdown(reasoning.why_this_test)
                if reasoning.data_requirements:
                    st.markdown("### 数据前提条件")
                    for req in reasoning.data_requirements:
                        icon = "✅" if req.passed else "⚠"
                        detail = f" — {req.detail}" if req.detail else ""
                        st.markdown(f"{icon} **{req.name}**: {req.result}{detail}")
                if reasoning.assumption_checks:
                    st.markdown("### 假设检验结果")
                    for check in reasoning.assumption_checks:
                        icon = "✅" if check.passed else "⚠"
                        detail = f" ({check.detail})" if check.detail else ""
                        st.markdown(f"{icon} **{check.name}**: {check.result}{detail}")
                if reasoning.analysis_steps:
                    st.markdown("### 分析步骤")
                    for step in reasoning.analysis_steps:
                        st.markdown(f"- {step}")
                if reasoning.interpretation_guide:
                    st.markdown("### 结果解读指南")
                    st.info(reasoning.interpretation_guide)
                if reasoning.alternatives:
                    st.markdown("### ⚠ 替代方案")
                    for alt in reasoning.alternatives:
                        st.markdown(f"- {alt}")

        result = output.get("result")
        if result is not None:
            st.subheader(f"📈 {output.get('test_name_zh', '分析结果')}")
            summary = format_result_summary(output)
            if summary:
                st.info(summary)
            render_result_table(result)

        charts_data = output.get("charts_data", {})
        if charts_data:
            st.subheader("📉 可视化图表")
            render_charts(charts_data, df)

        # v4.8.1: 统计结果卡（APA 文本 + 效应量 + 通俗解释）
        try:
            from src.ui.result_card_panel import render_result_card
            render_result_card(output)
        except Exception:
            pass

        st.subheader("💡 结果解读")
        interpretation = generate_interpretation(output)
        st.markdown(interpretation)

        # ── 档案标签输入 ──
        st.divider()
        st.subheader("📁 研究归档")
        col_tag1, col_tag2 = st.columns([3, 1])
        with col_tag1:
            tag_input = st.text_input(
                "标签/课程名（如：社会心理学作业）",
                value=st.session_state.get("archive_tag", ""),
                key="archive_tag_input",
                placeholder="为该分析标注课程名或项目名",
            )
            st.session_state.archive_tag = tag_input

        st.divider()
        col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
        with col_exp1:
            if st.button("📥 导出报告 (HTML)", width="stretch"):
                # 效应量检查
                es_ok, es_msg = check_effect_size_required(output)
                if not es_ok:
                    st.error(es_msg)
                else:
                    export_html(output, df)
        with col_exp2:
            if st.button("📄 导出数据 (CSV)", width="stretch"):
                export_csv(output)
        with col_exp3:
            if st.button("💾 保存快照", width="stretch"):
                try:
                    from src.analysis.runner import export_snapshot
                    snap_path = export_snapshot(output)
                    snap_id = output.get("snapshot_id", "unknown")
                    st.success(f"✅ 分析快照已保存\n`{snap_id}`")
                    st.caption(f"路径：{snap_path}")
                except Exception as e:
                    st.error(f"快照保存失败：{e}")
        with col_exp4:
            if st.button("📦 导出作业包", type="primary", width="stretch"):
                # 效应量检查
                es_ok, es_msg = check_effect_size_required(output)
                if not es_ok:
                    st.error(es_msg)
                else:
                    _build_homework_package(output, df, st.session_state.get("archive_tag", ""))

        # ── 学术诚信声明（分析结果底部） ──
        with st.expander("⚠️ 学术诚信与辅助工具声明"):
            from src.version import APP_VERSION_LABEL
            st.markdown(f"""
            <div style="font-size:0.9em;">
            <h4>📝 研究诚信提醒</h4>
            <ol>
                <li><strong>理解分析，合理使用</strong>：确保你理解所用统计方法的基本原理。如有疑问，请查阅教材或咨询导师。</li>
                <li><strong>完整报告结果</strong>：APA 第7版要求报告确切的 p 值（非仅 p < .05）、效应量及其 95% 置信区间。</li>
                <li><strong>避免 p-hacking</strong>：不要在数据查看后选择性地调整假设或分析策略。</li>
                <li><strong>区分探索性与验证性分析</strong>：预先注册的研究假设应优先报告，探索性分析应明确标注。</li>
            </ol>
            <h4>📄 辅助工具声明模板</h4>
            <p>如你的论文使用了本工具辅助分析，建议在方法部分添加以下声明：</p>
            <pre style="background:#f0f0f0; padding:8px; border-radius:4px; font-size:0.85em;">
本研究使用心理学研究工具 {APP_VERSION_LABEL} 进行数据整理和描述性统计分析。
所有推断统计分析使用 [软件名称与版本] 完成，显著性水平设定为 α = .05（双侧）。
            </pre>
            <p><em>注：请在 [软件名称与版本] 中填写你实际使用的统计软件
            （如 SPSS 26.0、JASP 0.18、jamovi 2.5 或 R 4.3 等）。</em></p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.caption("💡 提示：如果分析结果与预期不符，请尝试调整需求描述的措辞，使其更加具体明确。")


# ============================================================
# 实验设计
# ============================================================
elif mode == "🧪 实验设计":
    from src.ui.experiment_design_ui import render_experiment_design_ui
    render_experiment_design_ui()

# ============================================================
# 模式2: 问卷设计
# ============================================================
elif mode == "📋 问卷设计":
    from src.questionnaire.design_engine import design_questionnaire
    from src.questionnaire.llm_engine import (
        design_questionnaire_llm_async,
        cancel_design_request,
        CancelledLLMError,
    )
    from src.questionnaire.report_generator import (
        generate_design_report, generate_design_summary,
    )
    st.title("📋 问卷设计工具")
    st.caption("输入研究问题 → 智能识别构念 → 生成信效度优秀的问卷 → 完整设计报告")

    # v4.1: 子工作流——AI 反向生成 vs 上传现有题目 vs 导入清洗
    _q_sub_mode = st.radio(
        "选择工作流",
        ["🆕 AI 设计新问卷", "📤 上传现有题目（预审 + 排版导出）", "📊 问卷数据导入与清洗"],
        horizontal=True,
        key="_q_sub_mode_radio",
    )
    if _q_sub_mode.startswith("📤"):
        from src.ui.items_upload_panel import render_items_upload_panel
        render_items_upload_panel()
        st.stop()
    elif _q_sub_mode.startswith("📊"):
        from src.ui.questionnaire_import_panel import render_questionnaire_import_panel
        render_questionnaire_import_panel(st.session_state)
        st.stop()

    # 侧边栏：LLM状态 + 快速指南
    with st.sidebar:
        st.divider()
        st.header("🌐 " + t("language"))
        lang = st.radio(
            "",
            ["zh", "en"],
            format_func=lambda x: t("chinese") if x == "zh" else t("english"),
            index=0 if st.session_state.language == "zh" else 1,
            key="lang_select",
            horizontal=True,
        )
        if lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()

        st.divider()
        st.header("🤖 LLM 状态")
        from src.llm_gateway.active_config import get_active_llm_config as _get_llm
        _active_cfg = _get_llm()
        if _active_cfg:
            st.success(f"✅ `{_active_cfg.get('model', '?')}` 已激活（来自顶部「🤖 AI 模型」）")
        else:
            st.info(
                "📴 未激活 LLM — 将走关键词匹配引擎。\n"
                "如需 LLM：在侧栏顶部「🤖 AI 模型」选一个预设；"
                r"密钥配在 `D:\code\.env.local`（模板见 `.env.local.example`）。"
            )

        # Memory manager
        render_memory_manager_ui()

        st.divider()
        st.header("💡 使用指南")
        st.markdown("""
        **如何使用：**
        1. 在输入框中描述您想测量的心理学构念
        2. （可选）配置 LLM 以获得更智能的设计
        3. 系统自动分析并生成维度框架和题目
        4. 查看完整设计报告（含参考文献）

        **支持领域：**
        - 临床与健康心理
        - 人格心理学
        - 社会心理学
        - 教育心理学
        - 认知心理学
        - 组织行为学

        **示例输入：**
        - "调查大学生的社交焦虑水平"
        - "测量员工的工作满意度"
        - "编制一个大学生自尊量表"
        - "我想研究青少年的学习动机"
        """)

    # 快速模板
    st.markdown("**快速模板** — 一键填入常用问卷类型：")
    _tpl_cols = st.columns(4)
    _templates = {
        "📏 Likert-5 满意度": "设计一份员工工作满意度问卷，使用5点Likert量表（非常不同意~非常同意），包含工作内容、薪酬福利、发展机会、人际关系4个维度",
        "📐 Likert-7 心理资本": "设计一份心理资本问卷，使用7点Likert量表，包含自我效能感、希望、韧性、乐观4个维度，每维度4-5题",
        "👤 人口学变量": "设计人口学信息收集部分：性别、年龄、学历、工作年限、职位层级、所在行业、月收入区间，每题给出合理选项",
        "💼 组织承诺": "设计一份组织承诺量表，包含情感承诺、持续承诺、规范承诺3个维度，使用5点Likert量表，参考Allen和Meyer经典框架",
    }
    for i, (label, prompt) in enumerate(_templates.items()):
        with _tpl_cols[i]:
            if st.button(label, key=f"_qtpl_{i}", width="stretch"):
                st.session_state["q_request_input"] = prompt
                st.rerun()

    # 主区域
    col_q1, col_q2 = st.columns([3, 1])
    with col_q1:
        q_request = st.text_area(
            "请输入您想测量的心理学构念或研究问题：",
            placeholder='例如：\n'
                        '"调查大学生的社交焦虑水平及其影响因素"\n'
                        '"测量企业员工的工作满意度"\n'
                        '"设计一份中学生自尊量表"\n'
                        '"我想研究青少年抑郁症状"',
            height=100,
            key="q_request_input",
        )
    with col_q2:
        st.markdown("<br>", unsafe_allow_html=True)
        # v3.7: ⭐ 高质量模式开关
        premium_mode = st.toggle(
            "⭐ 高质量模式",
            value=st.session_state.get("_q_premium_mode", False),
            key="_q_premium_mode",
            help=(
                "开启后走多步并行生成 + 质检自动重写：\n"
                "• 速度：~30-40 秒（vs 普通 30-90 秒）\n"
                "• 成本：~6-10 次 LLM 调用（vs 普通 1 次）\n"
                "• 质量：明显提升（行为锚定+真反向题+质检循环）\n"
                "• 推荐用 deepseek-chat / gpt-4o / claude-sonnet 等强模型"
            ),
        )
        design_btn = st.button(
            "🔍 开始设计" if not premium_mode else "⭐ 开始高质量设计",
            type="primary", width="stretch",
        )
        q_clear_btn = st.button("🗑 清空", width="stretch")

    if q_clear_btn:
        st.session_state.questionnaire_design = None
        st.rerun()

    # ── 取消进行中设计（v3.7 加进度反馈） ──
    pending = st.session_state.get("_q_design_pending")
    if pending is not None:
        # v3.7 计算已等待时间
        import time as _t
        started_at = pending.get("started_at") or _t.time()
        elapsed = int(_t.time() - started_at)
        from_cache = pending.get("from_cache", False)
        is_premium = pending.get("premium", False)

        if from_cache:
            st.success("⚡ 命中缓存，正在加载...")
        elif is_premium:
            # ⭐ Premium 模式：显示分步进度
            progress = pending.get("progress") or {}
            with progress.get("lock", threading.Lock()) if progress else _DummyContext():
                p_msg = progress.get("msg", "排队中...") if progress else "..."
                p_pct = float(progress.get("pct", 0.0)) if progress else 0.0
            st.markdown(f"### ⭐ 高质量模式生成中（已 {elapsed}s）")
            st.progress(min(1.0, p_pct), text=p_msg)
            st.caption("流程：①骨架 → ②并行生成各维度题目 → ③元数据 → ④质检 → ⑤弱题重写")
            if elapsed > 90:
                st.warning(f"⏳ 已超过 {elapsed}s。Premium 模式正常 30-40s，超 90s 可能模型偏慢，建议取消换更快模型。")
        elif elapsed < 30:
            st.info(f"⏳ LLM 正在生成问卷（已 {elapsed}s，通常 30-90s 完成）...")
        elif elapsed < 90:
            st.info(f"⏳ 仍在生成中（已 {elapsed}s）。结构化问卷生成 60-120s 内属正常。")
        elif elapsed < 120:
            st.warning(
                f"⏳ 已超过 {elapsed}s 仍未完成。如继续无响应，建议点「取消」并切换更快的模型。"
            )
        else:
            st.error(
                f"❌ 已等待 {elapsed}s 超过预设超时（120s）。LLM 可能已卡死或失败，"
                "请点「取消」后切换模型重试。"
            )

        col_cancel, _ = st.columns([1, 3])
        with col_cancel:
            if st.button("❌ 取消生成", width="stretch", key="cancel_q_design"):
                cancel_design_request(pending["cancel_id"])
                try:
                    pending["future"].cancel()
                except Exception:
                    pass
                st.session_state.pop("_q_design_pending", None)
                st.warning("已取消问卷生成。")
                st.rerun()

        # 检查是否完成
        future = pending["future"]
        if future.done():
            st.session_state.pop("_q_design_pending", None)
            try:
                design = future.result()
                design["llm_used"] = True
                st.session_state.questionnaire_design = design
                cache_label = "（命中缓存）" if from_cache else f"（耗时 {elapsed}s）"
                st.success(f"问卷设计完成！{cache_label}")
            except CancelledLLMError:
                st.warning("问卷生成已被取消。")
            except Exception as e:
                err_msg = str(e)
                err_type = type(e).__name__
                is_premium_failed = pending.get("premium", False)
                # v3.7 错误分类（并显示完整异常信息）
                if "400" in err_msg or "Bad Request" in err_msg:
                    from src.llm_gateway.active_config import get_active_llm_config as _gac
                    _ac = _gac() or {}
                    st.error(
                        f"❌ LLM 返回 400 错误：{e}\n\n"
                        f"**最可能的原因**：当前模型 `{_ac.get('model', '?')}` "
                        f"被你设置的 `BASE_URL` API 拒绝（模型 ID 不对 / 渠道不支持）。\n\n"
                        f"**修复步骤**：\n"
                        r"1. 打开 `D:\code\.env.local`（模板见 `D:\code\.env.local.example`）"
                        f"\n"
                        f"2. 检查对应预设的 `*_MODEL` 写法（要和你的中转站文档一致）\n"
                        f"3. 重启 app 后重新点「开始设计」\n\n"
                        f"已自动回退到关键词匹配引擎。"
                    )
                elif "JSON 解析失败" in err_msg or "JSONDecodeError" in err_msg or "Expecting" in err_msg:
                    st.error(
                        f"❌ LLM 输出 JSON 解析失败：{e}\n\n"
                        f"**最可能的原因**：LLM 输出在中途被截断（max_tokens 不够）"
                        f"或返回了非 JSON 格式（如带说明文字）。\n\n"
                        f"**修复步骤**：\n"
                        f"1. **直接重试**——LLM 输出不稳定，重试一次大概率能成功\n"
                        f"2. 如果仍失败，**改短你的研究问题**（输入越短，LLM 输出 JSON 越紧凑）\n"
                        f"3. 或切换更稳的模型（如 `deepseek-chat` / `gpt-4o`）\n\n"
                        f"已自动回退到关键词匹配引擎。"
                    )
                elif "Timeout" in err_msg or "timeout" in err_msg or "超时" in err_msg:
                    st.error(
                        f"❌ LLM 请求超时：{e}\n\n"
                        f"**修复步骤**：\n"
                        f"1. 检查网络（VPN 是否稳定）\n"
                        f"2. 换更快的模型（如 `gpt-4o-mini` / `glm-4-flash`）\n"
                        f"3. 重试一次\n\n"
                        f"已自动回退到关键词匹配引擎。"
                    )
                elif is_premium_failed:
                    # v3.7: ⭐ premium 模式失败 — 三级降级：premium → legacy LLM → 关键词
                    import traceback
                    tb_short = traceback.format_exc()
                    st.warning(
                        f"⚠️ 高质量模式失败（{err_type}）：{e}\n\n"
                        f"**正在尝试普通 LLM 模式作为降级**（不是直接跳关键词路径）..."
                    )
                    with st.expander("🔧 高质量模式失败的完整 traceback", expanded=False):
                        st.code(tb_short, language="text")

                    # 尝试 legacy LLM 路径（同步调用）
                    legacy_design = None
                    try:
                        from src.llm_gateway.active_config import get_active_llm_config as _gac
                        _legacy_cfg = _gac()
                        if not _legacy_cfg:
                            raise RuntimeError("未激活快速模型，无法降级到 legacy LLM")
                        legacy_design = design_questionnaire(
                            q_request.strip(),
                            llm_config={
                                "api_key": _legacy_cfg["api_key"],
                                "base_url": _legacy_cfg["base_url"],
                                "model": _legacy_cfg["model"],
                                "temperature": _legacy_cfg["temperature"],
                            },
                        )
                        if legacy_design and legacy_design.get("llm_used"):
                            st.success("✅ 已通过普通 LLM 模式生成（高质量模式不可用，降级使用）")
                            st.session_state.questionnaire_design = legacy_design
                            design = legacy_design
                        else:
                            raise RuntimeError("legacy LLM 也未成功")
                    except Exception as legacy_e:
                        st.error(
                            f"❌ 普通 LLM 模式也失败（{type(legacy_e).__name__}）：{legacy_e}\n\n"
                            f"**自查**：\n"
                            f"1. 侧栏「⚙️ 设置 · 状态 → LLM 调用统计」看哪步失败\n"
                            r"2. 检查 `D:\code\.env.local` 三件套是否完整 / Key 是否过期"
                            f"\n"
                            f"3. JSON 不稳 → 换更通顺的模型预设（侧栏顶部「🤖 AI 模型」）\n\n"
                            f"最终回退到关键词匹配（题目质量大幅下降）。"
                        )
                        design = design_questionnaire(q_request.strip(), llm_config=None)
                        st.session_state.questionnaire_design = design
                else:
                    st.error(
                        f"❌ LLM 生成失败（{err_type}）：{e}\n\n已自动回退到关键词匹配引擎。"
                    )
                    design = design_questionnaire(q_request.strip(), llm_config=None)
                    st.session_state.questionnaire_design = design
            st.rerun()
        else:
            # v3.7: 未完成时自动 rerun 让进度文字实时更新（每 2 秒）
            import time as _t_sleep
            _t_sleep.sleep(2)
            st.rerun()

    # 问卷设计执行
    if design_btn and q_request.strip():
        # v4.6: 单轨化 — 从 active_config 读
        from src.llm_gateway.active_config import get_active_llm_config as _gac_main
        _active = _gac_main()
        llm_cfg = None
        if _active:
            base_url = _active["base_url"]
            model = _active["model"]
            llm_cfg = {
                "api_key": _active["api_key"],
                "base_url": base_url,
                "model": model,
                "temperature": _active["temperature"],
                "max_tokens": 4096,
                "timeout": 180,
            }
            # 模型不适配警告：reasoner 类模型不适合长结构化生成
            if "reasoner" in (model or "").lower() or "r1" in (model or "").lower():
                st.warning(
                    f"⚠️ 你当前选的是「{model}」（推理模型）。"
                    "推理模型生成 2000+ token 的结构化问卷会非常慢（5-10 分钟），且容易超时。"
                    "**建议切换到 chat 类模型（如 deepseek-chat / gpt-4o-mini / glm-4-flash）后再试**。"
                )

        if llm_cfg:
            import time as _t
            # v3.7: ⭐ premium 模式分支
            if st.session_state.get("_q_premium_mode", False):
                from src.questionnaire.llm_engine_premium import (
                    design_questionnaire_premium_async,
                )
                async_result = design_questionnaire_premium_async(
                    q_request.strip(),
                    api_key=llm_cfg["api_key"],
                    base_url=llm_cfg["base_url"],
                    model=llm_cfg["model"],
                    temperature=llm_cfg["temperature"],
                    max_tokens=llm_cfg["max_tokens"],
                    timeout=llm_cfg["timeout"],
                )
                st.session_state._q_design_pending = {
                    "future": async_result["future"],
                    "cancel_id": async_result["cancel_id"],
                    "progress": async_result.get("progress"),    # 实时进度
                    "started_at": _t.time(),
                    "from_cache": False,
                    "premium": True,
                }
            else:
                # 普通快速模式（v3.4 路径）
                async_result = design_questionnaire_llm_async(
                    q_request.strip(),
                    api_key=llm_cfg["api_key"],
                    base_url=llm_cfg["base_url"],
                    model=llm_cfg["model"],
                    temperature=llm_cfg["temperature"],
                    max_tokens=llm_cfg["max_tokens"],
                    timeout=llm_cfg["timeout"],
                )
                st.session_state._q_design_pending = {
                    "future": async_result["future"],
                    "cancel_id": async_result["cancel_id"],
                    "started_at": _t.time(),
                    "from_cache": async_result.get("from_cache", False),
                    "premium": False,
                }
            st.rerun()
        else:
            # 关键词匹配路径：同步执行（很快，不需要异步）
            with st.spinner("正在分析研究问题，匹配构念知识库..."):
                design = design_questionnaire(q_request.strip(), llm_config=None)
                st.session_state.questionnaire_design = design
    elif design_btn and not q_request.strip():
        st.error("请输入研究问题！")

    # 设计结果展示
    if st.session_state.questionnaire_design is not None:
        design = st.session_state.questionnaire_design

        st.divider()

        # v3.7.5: 显著展示研究理解（让用户看到系统怎么解析的，第一时间发现误解）
        rp = design.get("research_parse")
        if rp:
            with st.container():
                rt = rp.get("research_type", "construct_measurement")
                rt_label = {
                    "construct_measurement": "🧠 构念测量型（测被试个人状态/特质）",
                    "instrument_evaluation": "🛠 工具/标准评估型（评估某工具的合理性/有效性）",
                    "process_diagnostic": "🔍 流程诊断型（诊断流程薄弱环节）",
                    "multi_perspective_audit": "👥 多视角对照型",
                }.get(rt, rt)
                _safe_rt_label = html.escape(str(rt_label))
                _safe_object = html.escape(str(rp.get("research_object", "?")))
                _safe_population = html.escape(str(rp.get("population", "?")))
                _safe_role = html.escape(str(rp.get("respondent_role", "?")))
                _safe_subject = html.escape(str(rp.get("item_subject_template", "?")))
                _safe_summary = html.escape(str(rp.get("summary", "")))
                _framework = rp.get("theoretical_framework")
                _safe_framework_line = (
                    f"理论框架：<b>{html.escape(str(_framework))}</b><br>"
                    if _framework else ""
                )
                st.markdown(
                    f"""<div style="background:#f0f7ff;border-left:4px solid #2e86de;
                    padding:12px 16px;border-radius:6px;margin:8px 0;">
                    <strong>📋 系统对你研究问题的理解</strong><br>
                    <span style="font-size:0.9em;">
                    研究层次：<b>{_safe_rt_label}</b><br>
                    评估对象：<b>{_safe_object}</b><br>
                    答题人群：<b>{_safe_population}</b>（角色：{_safe_role}）<br>
                    题目主语：<b>{_safe_subject}</b><br>
                    {_safe_framework_line}
                    研究意图：{_safe_summary}
                    </span></div>""",
                    unsafe_allow_html=True,
                )
                # v3.7.6: 手动校正表单
                with st.expander("✏️ 系统理解错了？手动校正后重新生成", expanded=False):
                    st.caption(
                        "如果系统对研究层次/答题人群/题目主语等判断错了，"
                        "在此调整后点「用此理解重新生成」即可，**不重新解析**直接走后续步骤。"
                    )
                    rt_options = [
                        ("construct_measurement", "🧠 构念测量型（让答题者自评心理状态/行为）"),
                        ("instrument_evaluation", "🛠 工具/标准评估型（让答题者评估某工具/政策）"),
                        ("process_diagnostic", "🔍 流程诊断型（让答题者评估流程薄弱环节）"),
                        ("multi_perspective_audit", "👥 多视角对照型"),
                    ]
                    rt_keys = [k for k, _ in rt_options]
                    cur_rt = rp.get("research_type", "construct_measurement")
                    new_rt = st.selectbox(
                        "研究层次",
                        rt_keys,
                        format_func=lambda k: dict(rt_options)[k],
                        index=rt_keys.index(cur_rt) if cur_rt in rt_keys else 0,
                        key="_rp_override_rt",
                    )
                    new_population = st.text_input(
                        "答题人群（具体一点）",
                        value=rp.get("population", ""),
                        key="_rp_override_pop",
                        help="例：「点点互动公司全体员工」「初入职场 3 个月内的新员工」",
                    )
                    new_object = st.text_input(
                        "本问卷主测对象/构念",
                        value=rp.get("research_object") or rp.get("primary_construct", ""),
                        key="_rp_override_obj",
                        help="员工自评匹配感→「员工人岗匹配水平」；评估招聘标准→「公司用人标准」",
                    )
                    new_subject = st.text_input(
                        "题目主语模板",
                        value=rp.get("item_subject_template", "我..."),
                        key="_rp_override_subj",
                        help="自评心理状态→「我...」；评估工具→「我们公司的 X...」",
                    )
                    new_role_options = [
                        ("self", "self（自评）"),
                        ("supervisor", "supervisor（上级评下属）"),
                        ("hr_practitioner", "hr_practitioner（HR 评流程/标准）"),
                        ("recruiter", "recruiter（招聘官）"),
                        ("mixed", "mixed（多角色）"),
                    ]
                    role_keys = [k for k, _ in new_role_options]
                    cur_role = rp.get("respondent_role", "self")
                    new_role = st.selectbox(
                        "答题人角色",
                        role_keys,
                        format_func=lambda k: dict(new_role_options)[k],
                        index=role_keys.index(cur_role) if cur_role in role_keys else 0,
                        key="_rp_override_role",
                    )
                    new_framework = st.text_input(
                        "理论框架（可选，用作维度组织）",
                        value=rp.get("theoretical_framework", ""),
                        key="_rp_override_fw",
                        help="例：「人岗匹配 D-A&N-S 模型」「Maslach 倦怠三因素」",
                    )
                    new_summary = st.text_area(
                        "研究意图（一两句话）",
                        value=rp.get("summary", ""),
                        height=68,
                        key="_rp_override_sum",
                    )

                    if st.button("🔄 用此理解重新生成问卷", type="primary",
                                 key="_btn_regen_with_override"):
                        # 构造 override 字典
                        override = dict(rp)
                        override.update({
                            "research_type": new_rt,
                            "population": new_population.strip(),
                            "research_object": new_object.strip(),
                            "primary_construct": new_object.strip(),
                            "item_subject_template": new_subject.strip(),
                            "respondent_role": new_role,
                            "theoretical_framework": new_framework.strip(),
                            "summary": new_summary.strip(),
                        })
                        # 触发新的 premium 异步任务
                        from src.questionnaire.llm_engine_premium import (
                            design_questionnaire_premium_async,
                        )
                        # v4.6: 重建 LLM cfg — 从顶部「🤖 AI 模型」激活的预设读
                        from src.llm_gateway.active_config import get_active_llm_config as _gac_regen
                        _regen_cfg = _gac_regen()
                        if not _regen_cfg:
                            st.error(
                                "❌ 当前没有激活的 AI 模型；请先在侧栏顶部「🤖 AI 模型」选一个预设，"
                                r"或检查 `D:\code\.env.local` 是否配好了对应模型的三件套。"
                            )
                            st.stop()
                        _async = design_questionnaire_premium_async(
                            design.get("research_question", ""),
                            api_key=_regen_cfg["api_key"],
                            base_url=_regen_cfg["base_url"],
                            model=_regen_cfg["model"],
                            temperature=_regen_cfg["temperature"],
                            max_tokens=4096,
                            timeout=180,
                            parsed_research_override=override,
                        )
                        import time as _t_now
                        st.session_state._q_design_pending = {
                            "future": _async["future"],
                            "cancel_id": _async["cancel_id"],
                            "progress": _async.get("progress"),
                            "started_at": _t_now.time(),
                            "from_cache": False,
                            "premium": True,
                        }
                        st.session_state.questionnaire_design = None
                        st.rerun()

        # Engine badge
        if design.get("llm_used"):
            st.caption("🤖 由大语言模型生成 | 请审阅并调整")
        else:
            acad = design.get("academic_enrichment") or {}
            n_acad = acad.get("academic_source_count", 0)
            if n_acad > 0:
                st.caption(f"📚 基于内置知识库 + **{n_acad}** 个真实学术量表来源 | 学术文献增强已启用")
            else:
                st.caption("📚 基于内置知识库生成")

        # 构念识别
        st.subheader("🔍 构念识别")
        if design.get("llm_used"):
            st.success(f"LLM 识别构念：**{design['construct_name']}**")
        elif design["is_exact_match"]:
            st.success(f"精确匹配到构念：**{design['construct_name']}**")
        else:
            st.info(f"未精确匹配，基于关键词推断：**{design['construct_name']}**")

        st.markdown(design["match_reason"])

        # 构念定义 (keyword engine)
        construct = design.get("matched_construct") or {}
        if construct.get("definition"):
            with st.expander("📖 构念定义与理论背景"):
                st.markdown(construct["definition"])
                if construct.get("established_scales"):
                    st.markdown("**已有成熟量表：**")
                    for s in construct["established_scales"]:
                        st.markdown(f"- {s}")

        # 构念定义 (LLM engine)
        if design.get("llm_definition"):
            with st.expander("📖 构念定义与理论背景"):
                st.markdown(design["llm_definition"])

        # 设计思路
        with st.expander("💭 设计思路", expanded=True):
            sc = design["scale_config"]
            dims = design["dimensions_used"]

            st.markdown(f"### 维度框架")
            st.markdown(f"本问卷将 **{design['construct_name']}** 分解为 **{len(dims)}** 个维度：")
            for i, dim in enumerate(dims):
                st.markdown(f"**{i+1}. {dim['name']}** — {dim['desc']} （{dim.get('item_count', '?')}题）")

            # v3.7.9: 用 markdown 渲染替代 st.metric——避免 Streamlit 动态 import Metric.js 失败
            st.markdown(f"### 技术参数")
            tech_cols = st.columns(5)
            _tech_cells = [
                ("题型", design["template_used"]["name"]),
                ("量表点数", f"{sc['points']}点"),
                ("总题量", f"{sc['n_items']}题"),
                ("维度数", str(sc["n_dimensions"])),
                ("反向题", f"{sc['n_reverse']}题 ({sc['reverse_ratio']})"),
            ]
            for col, (label, value) in zip(tech_cols, _tech_cells):
                _safe_label = html.escape(str(label))
                _safe_value = html.escape(str(value))
                col.markdown(
                    f"<div style='padding:8px 4px;'>"
                    f"<div style='font-size:0.85em;color:#666;'>{_safe_label}</div>"
                    f"<div style='font-size:1.5em;font-weight:600;'>{_safe_value}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("### 设计依据")
            st.markdown(f"""
            1. **构念理论**：基于{design['construct_name']}的学术定义和维度理论框架
            2. **题型选择**：{design['template_used']['name']}适合测量此类心理构念
            3. **题量确定**：每维度{min(d.get('item_count', 5) for d in dims)}-{max(d.get('item_count', 5) for d in dims)}题，确保信度同时避免被试疲劳
            4. **反向题策略**：{sc['reverse_ratio']}的题目为反向题，用于控制默认反应偏差
            5. **评分标定**：{sc['points']}点 Likert 量表，各锚点有明确的语言标签
            """)

        # 完整问卷
        with st.expander("📝 完整问卷（含指导语和计分）", expanded=False):
            st.markdown(f"```\n{design['instructions']}\n```")

            current_dim = None
            for item in design["items"]:
                if item["dimension"] != current_dim:
                    current_dim = item["dimension"]
                    st.markdown(f"**▎ {current_dim}**")
                rev_mark = " 🔄" if item["reverse"] else ""
                st.markdown(f"**Q{item['index']}.** {item['text']}{rev_mark}")
                st.caption(f"   [1] [2] [3] [4] [5]  {'（反向计分）' if item['reverse'] else ''}")

        # 计分方式
        with st.expander("🔢 计分方式"):
            st.markdown(design["scoring"])
            rev_items = [it for it in design["items"] if it["reverse"]]
            if rev_items:
                st.markdown("**需反向计分的题目**：" + ", ".join("Q" + str(it["index"]) for it in rev_items))

        # 信效度保障
        with st.expander("✅ 信效度保障策略"):
            psych = design.get("psychometrics") or {}
            if psych:
                tabs = st.tabs(list(psych.keys()))
                for tab, (section, content) in zip(tabs, psych.items()):
                    with tab:
                        st.markdown(content)
            else:
                st.info(
                    "ℹ️ 本次未生成信效度策略（LLM 元数据生成步骤可能未返回，或被截断）。"
                    "建议参考通用方案：内容效度（专家评定 I-CVI ≥ 0.78）、"
                    "结构效度（EFA + CFA）、内部一致性（Cronbach α ≥ 0.70）、"
                    "重测信度（间隔 2-4 周 ICC ≥ 0.70）。"
                )

        # 学术文献增强报告
        acad_enrich = design.get("academic_enrichment")
        if acad_enrich and acad_enrich.get("established_scales"):
            with st.expander("🔬 真实学术文献来源（学术数据库检索）"):
                scales_list = acad_enrich["established_scales"]
                norms = acad_enrich.get("scale_reliability_norms", {})

                st.markdown(f"#### 检索到 **{len(scales_list)}** 个已发表的成熟量表：\n")
                for i, s in enumerate(scales_list, 1):
                    authors = ", ".join(s.get("authors", [])[:2])
                    year = s.get("year", "")
                    name = s.get("name", "未知名量表")
                    doi = s.get("doi", "")
                    n_items = s.get("n_items", 0)
                    alpha = s.get("alpha")
                    cred = s.get("credibility", 0.5)
                    cred_label = "高可信度" if cred >= 0.9 else ("中等可信度" if cred >= 0.6 else "低可信度")

                    st.markdown(f"**{i}. {name}**")
                    st.caption(f"   {authors} ({year}) | {n_items}题 | 可信度：{cred_label}")
                    if alpha:
                        st.caption(f"   Cronbach's α = {alpha}")
                    if doi:
                        st.caption(f"   DOI: [{doi}](https://doi.org/{doi})")

                if norms.get("mean_alpha"):
                    st.markdown("#### 信度常模")
                    nc1, nc2 = st.columns(2)
                    nc1.metric("平均 α", norms["mean_alpha"])
                    nc2.metric("α 范围", norms["alpha_range"])
                    if norms.get("total_sample"):
                        st.caption(f"汇总样本量：{norms['total_sample']}")

                st.markdown("#### 基于学术文献的建议")
                st.markdown(f"- 推荐题目数：**{acad_enrich.get('recommended_item_count', 15)}** 题")
                st.markdown(f"- 预期 Cronbach's α ≥ 0.70")

                refs = acad_enrich.get("academic_references_apa7", [])
                if refs:
                    with st.expander("📖 APA7 参考文献（学术数据库来源）"):
                        for i, ref in enumerate(refs, 1):
                            st.markdown(f"{i}. {ref}")

        # 已有量表参考 (keyword engine)
        if construct.get("established_scales"):
            with st.expander("📚 已有成熟量表（参考）"):
                for scale in construct["established_scales"]:
                    st.markdown(f"- {scale}")

        # 已有量表参考 (LLM engine)
        if design.get("llm_established_scales"):
            with st.expander("📚 已有成熟量表（参考）"):
                st.caption("以下为 LLM 生成，请核实。")
                for scale in design["llm_established_scales"]:
                    st.markdown(f"- {scale}")

        # 参考文献
        with st.expander("📖 参考文献"):
            if construct.get("references"):
                st.markdown("**构念相关文献：**")
                for i, ref in enumerate(construct["references"]):
                    st.markdown(f"{i+1}. {ref}")
            if design.get("llm_references"):
                st.markdown("**LLM 生成的参考文献（请务必核实后再引用）：**")
                for i, ref in enumerate(design["llm_references"]):
                    st.markdown(f"{i+1}. {ref}")
            st.markdown("**测量学通用参考：**")
            general = [
                "DeVellis, R. F., & Thorpe, C. T. (2021). Scale Development: Theory and Applications (5th ed.). SAGE.",
                "Nunnally, J. C., & Bernstein, I. H. (1994). Psychometric Theory (3rd ed.). McGraw-Hill.",
                "Hinkin, T. R. (1998). A brief tutorial on the development of measures for use in survey questionnaires. Organizational Research Methods, 1(1), 104-121.",
                "Haynes, S. N., Richard, D. C. S., & Kubany, E. S. (1995). Content validity in psychological assessment. Psychological Assessment, 7(3), 238-247.",
                "Hu, L., & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance structure analysis. Structural Equation Modeling, 6(1), 1-55.",
            ]
            for i, ref in enumerate(general):
                st.markdown(f"{i+1}. {ref}")

        # 导出
        st.divider()
        st.subheader("📥 导出完整设计报告")

        export_format = st.radio(
            "选择导出格式",
            ["📄 Word (.docx) — 可编辑", "📕 PDF (.pdf)", "🌐 HTML (.html)"],
            horizontal=True,
            key="export_format",
        )

        col_exp_q1, _ = st.columns(2)
        with col_exp_q1:
            export_clicked = st.button(
                "📥 下载报告",
                type="primary",
                width="stretch",
                key="export_btn",
            )

        if export_clicked:
            try:
                _construct_name = str(design.get("construct_name") or "问卷")
                _safe_stem = "".join(
                    ch for ch in _construct_name
                    if ch.isalnum() or ch in "._-（）()"
                )[:60] or "问卷"
                if export_format.startswith("📄 Word"):
                    from src.questionnaire.exporters import export_to_docx
                    docx_bytes = export_to_docx(design)
                    st.download_button(
                        "下载 Word 报告 (.docx)",
                        data=docx_bytes,
                        file_name=f"{_safe_stem}问卷设计报告.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        on_click="ignore",
                    )
                    st.success("✅ Word 报告已生成，可用 Microsoft Word 或 WPS 打开编辑。")

                elif export_format.startswith("📕 PDF"):
                    from src.questionnaire.exporters import export_to_pdf
                    pdf_bytes = export_to_pdf(design)
                    st.download_button(
                        "下载 PDF 报告 (.pdf)",
                        data=pdf_bytes,
                        file_name=f"{_safe_stem}问卷设计报告.pdf",
                        mime="application/pdf",
                        on_click="ignore",
                    )
                    st.success("✅ PDF 报告已生成。")

                else:
                    full_report = generate_design_report(design)
                    # 下载的 HTML 可能在浏览器本地打开；先转义全部用户/LLM 文本，
                    # 再只把受控的 Markdown 标题标记转换成固定标签。
                    from src.ui.html_safety import questionnaire_report_to_html_fragment
                    _safe_report = questionnaire_report_to_html_fragment(full_report)
                    html_report = f"""<html><head><meta charset='utf-8'>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.8; }}
h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
h2 {{ color: #2980b9; margin-top: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; }}
th {{ background-color: #f2f2f2; }}
pre {{ background: #f8f8f8; padding: 1rem; border-radius: 4px; white-space: pre-wrap; }}
</style></head><body>
{_safe_report}
</body></html>"""
                    st.download_button(
                        "下载 HTML 报告 (.html)",
                        data=html_report,
                        file_name=f"{_safe_stem}问卷设计报告.html",
                        mime="text/html",
                        on_click="ignore",
                    )
                    st.success("✅ HTML 报告已生成。")

            except Exception as e:
                st.error(f"❌ 导出失败：{e}")

    st.divider()
    st.caption("💡 提示：生成的问卷为初稿，建议在此基础上根据具体研究目标和被试群体进行调整，并通过预测试检验题目质量。")

# ============================================================

# ============================================================
# 模式4: 论文写作
# ============================================================
elif mode == "📝 论文写作":
    from src.paper_writer import PaperEngine
    from src.ui.paper_writing_ui import render_paper_writing_ui
    _paper_tab_write, _paper_tab_preview, _paper_tab_evidence = st.tabs(["✍️ 写作", "📄 预览与导出", "📚 证据表"])
    with _paper_tab_write:
        render_paper_writing_ui()
    with _paper_tab_preview:
        try:
            from src.ui.paper_preview_panel import render_paper_preview, render_export_panel
            from src.ui.export_gate import render_export_gate
            from src.ui.state_keys import PAPER_BUNDLE_KEY
            _bundle = st.session_state.get(PAPER_BUNDLE_KEY)
            if _bundle is not None:
                render_paper_preview(_bundle)
                st.divider()
                if render_export_gate(st.session_state):
                    render_export_panel(_bundle)
            else:
                st.info("暂无论文草稿。请先在「写作」标签页中生成论文内容。")
        except Exception as _paper_prev_err:
            st.error(f"预览面板加载失败：{_paper_prev_err}")
    with _paper_tab_evidence:
        try:
            from src.ui.evidence_table_panel import render_evidence_table_panel
            render_evidence_table_panel(st.session_state)
        except Exception as _evi_err:
            st.error(f"证据表加载失败：{_evi_err}")

# ============================================================
# 📚 文献与选题（合并：选题漏斗 + 文献雷达 + 文献审核）
# ============================================================
elif mode == "📚 文献与选题":
    st.title("📚 文献与选题")
    _tab_funnel, _tab_feed, _tab_review = st.tabs(["选题与综述", "文献雷达", "文献审核"])
    with _tab_funnel:
        from src.utils.workspace import get_upstream_state as _get_upstream_v37
        _upstream_v37 = _get_upstream_v37(st.session_state)
        _tier_v37 = _upstream_v37.get("tier", "beginner")
        _sub_tab_f, _sub_tab_l = st.tabs(["选题漏斗", "文献综述工作台"])
        with _sub_tab_f:
            from src.ui.upstream_panel import render_advanced_skip_form, render_funnel
            if _tier_v37 == "advanced":
                render_advanced_skip_form()
            else:
                render_funnel()
        with _sub_tab_l:
            from src.ui.literature_review_panel import render_literature_review
            render_literature_review(tier=_tier_v37)
    with _tab_feed:
        try:
            from src.literature_feed.ui import render_literature_feed
            render_literature_feed()
        except Exception as _feed_err:
            st.error(f"文献雷达加载失败：{_feed_err}")
    with _tab_review:
        try:
            from src.literature_feed.storage.feed_store import FeedStore as _ReviewFS
            from src.ui.literature_review_queue_panel import render_review_queue
            _review_store = _ReviewFS()
            render_review_queue(_review_store)
        except Exception as _review_err:
            st.error(f"文献审核加载失败：{_review_err}")


# ============================================================
# v4.9: 📦 交付包导出
# ============================================================
elif mode == "📦 交付包导出":
    st.title("📦 研究交付包导出中心")
    st.caption("查看交付内容清单、导出前检查、选择导出模式（简版/标准版/完整版）。")

    # --- 导出前隐私预检 ---
    from src.utils.privacy_ethics import export_pre_check, DATA_GOVERNANCE_NOTICE
    with st.expander("📋 数据治理声明", expanded=False):
        st.info(DATA_GOVERNANCE_NOTICE)

    # 对 session 中已有分析结果做敏感信息扫描
    _export_text_parts = []
    if st.session_state.get("analysis_output"):
        _export_text_parts.append(str(st.session_state["analysis_output"]))
    _paper_bundle = st.session_state.get("paper_bundle")
    if _paper_bundle is not None:
        _export_text_parts.append(str(_paper_bundle))
    if _export_text_parts:
        _pre_check_result = export_pre_check("\n".join(_export_text_parts), source="交付包")
        on_privacy_precheck(
            _pre_check_result.get("high_count", 0),
            _pre_check_result.get("medium_count", 0),
            _pre_check_result["safe"],
        )
        if not _pre_check_result["safe"]:
            st.error(
                f"⚠️ 隐私预检发现 {_pre_check_result['high_count']} 项高风险敏感信息"
                f"（共 {_pre_check_result['total_count']} 项）。正式交付已阻止，请先检查并脱敏。"
            )
            with st.expander("查看详情"):
                for _f in _pre_check_result["findings"]:
                    _sev_icon = "🔴" if _f.severity == "high" else "🟡"
                    st.markdown(f"{_sev_icon} **{_f.pattern_type}** — 位置: {_f.location} — 样本: `{_f.masked_sample}`")
        else:
            st.success("✅ 隐私预检通过，未发现高风险敏感信息。")

    try:
        from src.ui.deliverable_center_panel import render_deliverable_center_panel
        render_deliverable_center_panel(st.session_state)
    except Exception as _del_err:
        st.error(f"交付包导出面板加载失败：{_del_err}")

# ============================================================
# v5.1: 🗂️ 模板中心
# ============================================================
elif mode == "🗂️ 模板中心":
    st.title("🗂️ 研究模板中心")
    st.caption("从研究模板快速开始新项目——选择模板、预览数据、一键创建。")
    try:
        from src.ui.template_center_panel import render_template_center_panel
        render_template_center_panel()
    except Exception as _tpl_err:
        st.error(f"模板中心加载失败：{_tpl_err}")
        on_error_display("template_center_load_failed", "error")


