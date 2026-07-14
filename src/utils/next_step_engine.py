"""下一步推荐引擎 — 根据当前项目资产状态推荐下一步操作。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NextStep:
    """一条下一步建议。"""

    step_id: str  # 唯一标识
    title: str  # 标题（中文）
    description: str  # 简要说明
    page_target: str  # 跳转目标页面名（与 app.py sidebar 对应）
    priority: int  # 1=紧急 2=重要 3=可选
    prerequisites: list[str] = field(default_factory=list)  # 依赖条件描述
    blocked: bool = False  # 是否被阻断


# ---------------------------------------------------------------------------
# 资产状态评估
# ---------------------------------------------------------------------------


def evaluate_project_state(session_state: dict) -> dict[str, bool]:
    """评估项目各阶段完成状态。返回 asset -> bool 映射。

    检查以下资产是否存在：
    - data_loaded: 数据已上传
    - variables_defined: 变量已定义（IV/DV）
    - method_recommended: 已获得方法推荐
    - analysis_done: 至少一个分析已执行
    - result_cards: 至少一张结果卡片
    - figures_generated: 有 APA 图表
    - paper_draft: 论文有任何章节内容
    - evidence_collected: 证据表有条目
    - consistency_passed: 一致性检查通过
    - export_ready: 交付包可导出
    """
    state: dict[str, bool] = {}

    # data_loaded: 检查 uploaded_df（旧入口）或 df（新 state_keys 入口）
    df = session_state.get("uploaded_df")
    if df is None:
        df = session_state.get("df")
    state["data_loaded"] = df is not None and (
        hasattr(df, "__len__") and len(df) > 0
    )

    # variables_defined: 从 workspace/upstream_state 的 candidate_vars 判断
    variables_defined = False
    upstream = session_state.get("upstream_state")
    if isinstance(upstream, dict):
        cv = upstream.get("candidate_vars", {})
        has_iv = bool(cv.get("independent_vars"))
        has_dv = bool(cv.get("dependent_vars"))
        variables_defined = has_iv or has_dv
    # 也检查 workspace dataclass（v3.5+）
    workspace = session_state.get("workspace")
    if not variables_defined and workspace is not None:
        try:
            cv = workspace.funnel.candidate_vars
            has_iv = bool(cv.get("independent_vars"))
            has_dv = bool(cv.get("dependent_vars"))
            variables_defined = has_iv or has_dv
        except (AttributeError, TypeError):
            pass
    state["variables_defined"] = variables_defined

    # method_recommended: 检查 method_recommendations 或 analysis_recipe
    recs = session_state.get("method_recommendations", [])
    recipe = session_state.get("analysis_recipe")
    state["method_recommended"] = bool(recs) or recipe is not None

    # analysis_done: 检查 analysis_output 或 analysis_history
    analysis_output = session_state.get("analysis_output")
    analysis_history = session_state.get("analysis_history", [])
    state["analysis_done"] = analysis_output is not None or bool(analysis_history)

    # result_cards: 检查 analysis_cards 列表
    cards = session_state.get("analysis_cards", [])
    state["result_cards"] = bool(cards)

    # figures_generated: 检查 apa_figures 列表
    figures = session_state.get("apa_figures", [])
    state["figures_generated"] = bool(figures)

    # paper_draft: 检查 paper_bundle 是否有章节
    paper_bundle = session_state.get("paper_bundle")
    has_paper = False
    if paper_bundle is not None:
        # PaperDraftBundle 有 .sections 属性
        try:
            has_paper = bool(paper_bundle.sections)
        except AttributeError:
            # 可能是 dict
            if isinstance(paper_bundle, dict):
                has_paper = bool(paper_bundle.get("sections"))
            else:
                has_paper = True
    state["paper_draft"] = has_paper

    # evidence_collected: 检查 evidence_store 或 evidence_records
    evidence_collected = False
    evidence_store = session_state.get("evidence_store")
    if evidence_store is not None:
        try:
            evidence_collected = bool(evidence_store.records)
        except AttributeError:
            evidence_collected = bool(evidence_store)
    if not evidence_collected:
        evidence_records = session_state.get("evidence_records", [])
        evidence_collected = bool(evidence_records)
    state["evidence_collected"] = evidence_collected

    # consistency_passed: 检查 consistency_issues（无 ERROR 级为通过）
    consistency_issues = session_state.get("consistency_issues")
    if consistency_issues is None:
        # 未运行过检查
        state["consistency_passed"] = False
    elif isinstance(consistency_issues, list):
        errors = [
            i
            for i in consistency_issues
            if (isinstance(i, dict) and i.get("level") == "ERROR")
            or (hasattr(i, "level") and getattr(i, "level", "") == "ERROR")
        ]
        state["consistency_passed"] = len(errors) == 0
    else:
        state["consistency_passed"] = False

    # export_ready: export_allowed 标志 + 有实际内容可导出
    export_allowed = session_state.get("export_allowed", False)
    has_content = state["result_cards"] or state["paper_draft"]
    state["export_ready"] = bool(export_allowed) and has_content

    return state


# ---------------------------------------------------------------------------
# 推荐规则定义
# ---------------------------------------------------------------------------

def _build_rules() -> list[tuple]:
    """构建推荐规则列表。每条规则是 (condition_fn, step_factory)。

    condition_fn(state) -> (should_recommend: bool, is_blocked: bool)
    step_factory() -> NextStep
    """
    rules = []

    # 规则 1: 没有数据 → 推荐上传数据
    def cond_no_data(s: dict) -> tuple[bool, bool]:
        return (not s["data_loaded"], False)

    def step_upload_data() -> NextStep:
        return NextStep(
            step_id="upload_data",
            title="上传研究数据",
            description="导入你的研究数据文件（CSV/Excel），这是所有分析的起点。",
            page_target="📈 数据分析",
            priority=1,
        )

    rules.append((cond_no_data, step_upload_data))

    # 规则 2: 有数据没定义变量 → 推荐定义变量
    def cond_no_variables(s: dict) -> tuple[bool, bool]:
        recommend = s["data_loaded"] and not s["variables_defined"]
        return (recommend, False)

    def step_define_variables() -> NextStep:
        return NextStep(
            step_id="define_variables",
            title="定义研究变量",
            description="指定自变量和因变量，系统才能为你推荐合适的统计方法。",
            page_target="📚 文献与选题",
            priority=1,
            prerequisites=["已上传数据"],
        )

    rules.append((cond_no_variables, step_define_variables))

    # 规则 3: 有变量没推荐方法 → 推荐获取方法推荐
    def cond_no_method(s: dict) -> tuple[bool, bool]:
        recommend = s["variables_defined"] and not s["method_recommended"]
        blocked = not s["data_loaded"]
        return (recommend, blocked)

    def step_get_recommendation() -> NextStep:
        return NextStep(
            step_id="get_method_recommendation",
            title="获取方法推荐",
            description="根据变量类型和研究设计，系统会推荐最适合的统计分析方法。",
            page_target="📈 数据分析",
            priority=1,
            prerequisites=["已定义研究变量"],
        )

    rules.append((cond_no_method, step_get_recommendation))

    # 规则 4: 有推荐没执行分析 → 推荐执行分析
    def cond_no_analysis(s: dict) -> tuple[bool, bool]:
        recommend = s["method_recommended"] and not s["analysis_done"]
        blocked = not s["data_loaded"]
        return (recommend, blocked)

    def step_run_analysis() -> NextStep:
        return NextStep(
            step_id="run_analysis",
            title="执行统计分析",
            description="运行推荐的统计方法，获取 p 值、效应量等核心结果。",
            page_target="📈 数据分析",
            priority=1,
            prerequisites=["已获得方法推荐", "已上传数据"],
        )

    rules.append((cond_no_analysis, step_run_analysis))

    # 规则 5: 有分析没结果卡片 → 推荐生成结果卡片
    def cond_no_cards(s: dict) -> tuple[bool, bool]:
        recommend = s["analysis_done"] and not s["result_cards"]
        return (recommend, False)

    def step_generate_cards() -> NextStep:
        return NextStep(
            step_id="generate_result_cards",
            title="生成结果卡片",
            description="将分析结果整理为标准化卡片，含 APA 格式文本和效应量。",
            page_target="📈 数据分析",
            priority=2,
            prerequisites=["已完成统计分析"],
        )

    rules.append((cond_no_cards, step_generate_cards))

    # 规则 6: 有结果卡片没图表 → 推荐生成图表
    def cond_no_figures(s: dict) -> tuple[bool, bool]:
        recommend = s["result_cards"] and not s["figures_generated"]
        return (recommend, False)

    def step_generate_figures() -> NextStep:
        return NextStep(
            step_id="generate_figures",
            title="生成 APA 图表",
            description="为统计结果生成符合 APA 规范的图表，增强论文可读性。",
            page_target="📈 数据分析",
            priority=2,
            prerequisites=["已有结果卡片"],
        )

    rules.append((cond_no_figures, step_generate_figures))

    # 规则 7: 没有文献/证据 → 推荐收集证据
    def cond_no_evidence(s: dict) -> tuple[bool, bool]:
        recommend = not s["evidence_collected"]
        return (recommend, False)

    def step_collect_evidence() -> NextStep:
        return NextStep(
            step_id="collect_evidence",
            title="收集文献证据",
            description="在证据表中添加支撑你研究假设和讨论的文献条目。",
            page_target="📝 论文写作",
            priority=2,
            prerequisites=[],
        )

    rules.append((cond_no_evidence, step_collect_evidence))

    # 规则 8: 有卡片+证据没论文 → 推荐开始写论文
    def cond_no_paper(s: dict) -> tuple[bool, bool]:
        recommend = (
            s["result_cards"]
            and s["evidence_collected"]
            and not s["paper_draft"]
        )
        blocked = not s["result_cards"]
        return (recommend, blocked)

    def step_write_paper() -> NextStep:
        return NextStep(
            step_id="write_paper",
            title="开始撰写论文",
            description="基于结果卡片和文献证据，生成论文各章节草稿。",
            page_target="📝 论文写作",
            priority=2,
            prerequisites=["已有结果卡片", "已收集文献证据"],
        )

    rules.append((cond_no_paper, step_write_paper))

    # 规则 9: 有论文没做一致性检查 → 推荐检查
    def cond_no_consistency(s: dict) -> tuple[bool, bool]:
        recommend = s["paper_draft"] and not s["consistency_passed"]
        return (recommend, False)

    def step_consistency_check() -> NextStep:
        return NextStep(
            step_id="consistency_check",
            title="运行一致性检查",
            description="检查论文中数据引用、统计结果与图表之间是否一致。",
            page_target="📦 交付包导出",
            priority=2,
            prerequisites=["已有论文草稿"],
        )

    rules.append((cond_no_consistency, step_consistency_check))

    # 规则 10: 一致性通过 → 推荐导出交付包
    def cond_ready_export(s: dict) -> tuple[bool, bool]:
        recommend = (
            s["consistency_passed"]
            and s["paper_draft"]
            and not s["export_ready"]
        )
        return (recommend, False)

    def step_export() -> NextStep:
        return NextStep(
            step_id="export_deliverable",
            title="导出交付包",
            description="将论文、图表、数据和证据打包为完整的交付文件。",
            page_target="📦 交付包导出",
            priority=3,
            prerequisites=["一致性检查通过"],
        )

    rules.append((cond_ready_export, step_export))

    # 规则 11: 全部完成 → 推荐最终检查
    def cond_all_done(s: dict) -> tuple[bool, bool]:
        recommend = s["export_ready"]
        return (recommend, False)

    def step_final_review() -> NextStep:
        return NextStep(
            step_id="final_review",
            title="最终审阅",
            description="所有资产已就绪，建议在提交前做最后的人工审阅。",
            page_target="📦 交付包导出",
            priority=3,
            prerequisites=["交付包可导出"],
        )

    rules.append((cond_all_done, step_final_review))

    return rules


# ---------------------------------------------------------------------------
# 推荐主逻辑
# ---------------------------------------------------------------------------


def recommend_next_steps(
    session_state: dict, max_steps: int = 3
) -> list[NextStep]:
    """根据当前状态推荐最多 max_steps 条下一步。

    推荐逻辑：
    1. 评估当前项目资产状态
    2. 遍历规则，收集所有满足条件的推荐
    3. 按 priority 排序，取 top-N 返回
    """
    state = evaluate_project_state(session_state)
    rules = _build_rules()

    candidates: list[NextStep] = []

    for condition_fn, step_factory in rules:
        should_recommend, is_blocked = condition_fn(state)
        if should_recommend:
            step = step_factory()
            step.blocked = is_blocked
            candidates.append(step)

    # 按优先级排序（1 最高）；同优先级保持规则定义顺序
    candidates.sort(key=lambda s: s.priority)

    # 返回前 max_steps 条未阻断的，加上阻断的（如果还有空间）
    unblocked = [s for s in candidates if not s.blocked]
    blocked = [s for s in candidates if s.blocked]

    result = unblocked[:max_steps]
    remaining_slots = max_steps - len(result)
    if remaining_slots > 0:
        result.extend(blocked[:remaining_slots])

    return result
