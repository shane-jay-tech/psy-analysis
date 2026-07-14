"""分析 Pipeline 保存与复跑

将分析历史记录为可重放的 pipeline，支持：
- 保存当前分析计划到 pipeline
- 复跑整个 pipeline（重新执行所有分析步骤）
- 导出/导入 pipeline（JSON）
"""
from __future__ import annotations

import json
import base64
import io
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from src.parser.intent_resolver import AnalysisPlan

from src.utils.workspace import _serialize_plan, _deserialize_plan


@dataclass
class PipelineStep:
    """Pipeline 中的单个分析步骤"""
    plan: AnalysisPlan
    result_summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class AnalysisPipeline:
    """可保存、可复跑的分析 Pipeline"""
    name: str = "未命名Pipeline"
    steps: List[PipelineStep] = field(default_factory=list)
    created_at: str = ""
    source_df_hash: str = ""  # 用于验证数据源是否一致


def _get_df_hash(df: pd.DataFrame) -> str:
    """计算 DataFrame 的简易 hash（用于一致性验证）"""
    try:
        import hashlib
        sample = df.head(5).to_csv(index=False)
        return hashlib.md5(sample.encode()).hexdigest()[:8]
    except Exception:
        return ""


def save_current_analysis_to_pipeline(name: str = "") -> bool:
    """将当前 analysis_output 和 plan 保存到 pipeline。

    返回是否保存成功。
    """
    plan = st.session_state.get("plan")
    output = st.session_state.get("analysis_output")
    df = st.session_state.get("df")

    if plan is None or output is None:
        return False

    if "analysis_pipeline" not in st.session_state:
        st.session_state.analysis_pipeline = AnalysisPipeline()

    pipeline = st.session_state.analysis_pipeline
    if not pipeline.steps:
        pipeline.source_df_hash = _get_df_hash(df) if df is not None else ""

    step = PipelineStep(
        plan=plan,
        result_summary={
            "test_type": output.get("test_type", ""),
            "test_name_zh": output.get("test_name_zh", ""),
        },
        timestamp=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    pipeline.steps.append(step)
    return True


def replay_pipeline(df: pd.DataFrame = None) -> List[Dict]:
    """复跑当前 pipeline 中的所有步骤。

    参数：
        df: 用于复跑的数据集，默认使用 session_state.df

    返回：
        每个步骤的结果列表
    """
    pipeline = st.session_state.get("analysis_pipeline")
    if pipeline is None or not pipeline.steps:
        return []

    if df is None:
        df = st.session_state.get("df")
    if df is None:
        raise ValueError("没有可用数据，无法复跑 Pipeline。")

    results = []
    for i, step in enumerate(pipeline.steps):
        try:
            from src.analysis.runner import run_analysis
            output = run_analysis(df, step.plan)
            results.append({
                "step": i + 1,
                "test_type": step.plan.test_type,
                "success": True,
                "output": output,
            })
        except Exception as e:
            results.append({
                "step": i + 1,
                "test_type": step.plan.test_type,
                "success": False,
                "error": str(e),
            })
    return results


def export_pipeline() -> str:
    """将当前 pipeline 导出为 JSON 字符串。"""
    pipeline = st.session_state.get("analysis_pipeline")
    if pipeline is None:
        return "{}"

    steps_data = []
    for step in pipeline.steps:
        steps_data.append({
            "plan": _serialize_plan(step.plan),
            "result_summary": step.result_summary,
            "timestamp": step.timestamp,
        })

    data = {
        "name": pipeline.name,
        "created_at": pipeline.created_at,
        "source_df_hash": pipeline.source_df_hash,
        "steps": steps_data,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_pipeline(json_str: str) -> bool:
    """从 JSON 字符串导入 pipeline。"""
    try:
        data = json.loads(json_str)
    except Exception:
        return False

    steps = []
    for step_data in data.get("steps", []):
        plan = _deserialize_plan(step_data.get("plan"))
        if plan is None:
            continue
        steps.append(PipelineStep(
            plan=plan,
            result_summary=step_data.get("result_summary", {}),
            timestamp=step_data.get("timestamp", ""),
        ))

    pipeline = AnalysisPipeline(
        name=data.get("name", "导入的Pipeline"),
        created_at=data.get("created_at", ""),
        source_df_hash=data.get("source_df_hash", ""),
        steps=steps,
    )
    st.session_state.analysis_pipeline = pipeline
    return True


def clear_pipeline():
    """清空当前 pipeline。"""
    st.session_state.analysis_pipeline = AnalysisPipeline()


def render_pipeline_ui():
    """在 Streamlit 中渲染 Pipeline 管理 UI"""
    pipeline = st.session_state.get("analysis_pipeline")
    if pipeline is None:
        st.session_state.analysis_pipeline = AnalysisPipeline()
        pipeline = st.session_state.analysis_pipeline

    st.subheader("📊 分析 Pipeline")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ 保存当前分析", use_container_width=True, key="pipe_save"):
            if save_current_analysis_to_pipeline():
                st.success("已保存到 Pipeline！")
                st.rerun()
            else:
                st.warning("没有可保存的分析结果。")
    with col2:
        if st.button("▶ 复跑 Pipeline", use_container_width=True, key="pipe_replay"):
            try:
                results = replay_pipeline()
                success = sum(1 for r in results if r["success"])
                st.success(f"Pipeline 复跑完成：{success}/{len(results)} 步成功。")
                for r in results:
                    if not r["success"]:
                        st.error(f"步骤 {r['step']} ({r['test_type']}) 失败：{r['error']}")
            except Exception as e:
                st.error(f"复跑失败：{e}")
    with col3:
        if st.button("📤 导出", use_container_width=True, key="pipe_export"):
            json_str = export_pipeline()
            b64 = base64.b64encode(json_str.encode("utf-8")).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="analysis_pipeline.json">点击下载 Pipeline JSON</a>'
            st.markdown(href, unsafe_allow_html=True)
    with col4:
        if st.button("🗑 清空", use_container_width=True, key="pipe_clear"):
            clear_pipeline()
            st.success("Pipeline 已清空。")
            st.rerun()

    if pipeline.steps:
        st.markdown(f"**当前 Pipeline**：{len(pipeline.steps)} 步")
        for i, step in enumerate(pipeline.steps):
            test_name = step.result_summary.get("test_name_zh", step.plan.test_type)
            st.caption(f"步骤 {i+1}：{test_name} ({step.timestamp})")
    else:
        st.info("暂无保存的分析步骤。执行分析后点击「保存当前分析」即可构建 Pipeline。")
