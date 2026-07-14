"""工作区序列化与恢复工具：将 session_state 关键数据持久化为 JSON"""
from __future__ import annotations

import json
import base64
import io
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from src.parser.intent_resolver import AnalysisPlan


# v3.2 上游漏斗默认状态
UPSTREAM_SESSION_KEY = "upstream_state"

_DEFAULT_UPSTREAM_STATE = {
    "tier": "beginner",          # beginner | advanced
    "phase": "funnel",            # funnel | literature_review | wizard | done
    "current_stage": 1,           # 1..5 (BEGINNER 漏斗) 或 5 (跳过)
    "stages": {},                 # {stage_id: {"interest_text", "ai_history", "output", "completed"}}
    "research_question": "",
    "candidate_vars": {           # 复用 AnalysisPlan schema
        "dependent_vars": [],
        "independent_vars": [],
        "grouping_var": "",
        "covariates": [],
    },
    "feasibility_results": {},    # {"falsifiable": str, "measurable": str|dict, "operability": dict}
    # v3.3 扩展
    "funnel_history": [],         # List[FunnelBranch.as_dict()]，最新在前
    "advanced_meta": {},          # ADVANCED 跳过留痕（来源/动机/最关心发现）
    "asked_themes": [],           # 跨阶段已覆盖反问主题（防退行）
    # v3.7: 断点续读位置标记
    "last_position": {            # {"phase": str, "step": int, "label": str, "timestamp": ISO str}
        "phase": "",
        "step": 0,
        "label": "",
        "timestamp": "",
    },
}


# v3.4 文献综述工作台默认状态
LITERATURE_REVIEW_SESSION_KEY = "literature_review_state"

_DEFAULT_LITERATURE_REVIEW_STATE = {
    "literature_items": [],       # List[LiteratureItem.to_dict()]
    "notes": [],                  # List[ReadingNote.to_dict()]
    "matrix": {                   # LiteratureMatrix.to_dict()
        "dimensions": ["样本量", "研究设计", "主要发现", "效应量", "局限"],
        "cells": {},
        "highlighted_keys": [],
    },
    "themes": [],                 # List[ThemeCluster.to_dict()]
    "gaps": [],                   # List[GapAnalysis.to_dict()]
    "last_search_query": "",
    "last_search_at": "",
}


def _default_literature_review_state() -> Dict[str, Any]:
    import copy
    return copy.deepcopy(_DEFAULT_LITERATURE_REVIEW_STATE)


def get_literature_review_state(session_state=None) -> Dict[str, Any]:
    """读取 session_state 中的 literature_review_state，缺失时返回默认值并写回。"""
    if session_state is None:
        session_state = st.session_state
    state = session_state.get(LITERATURE_REVIEW_SESSION_KEY)
    if not isinstance(state, dict):
        state = _default_literature_review_state()
        session_state[LITERATURE_REVIEW_SESSION_KEY] = state
        return state
    # 自愈：补全缺失键
    defaults = _default_literature_review_state()
    for k, v in defaults.items():
        state.setdefault(k, v)
    return state


def set_literature_review_state(session_state, state: Dict[str, Any]) -> None:
    session_state[LITERATURE_REVIEW_SESSION_KEY] = state


def _default_upstream_state() -> Dict[str, Any]:
    """返回 upstream_state 默认值的深拷贝（避免共享可变 dict）。"""
    import copy
    return copy.deepcopy(_DEFAULT_UPSTREAM_STATE)


def get_upstream_state(session_state=None) -> Dict[str, Any]:
    """读取 session_state 中的 upstream_state，缺失时返回默认值并写回。"""
    if session_state is None:
        session_state = st.session_state
    state = session_state.get(UPSTREAM_SESSION_KEY)
    if not isinstance(state, dict):
        state = _default_upstream_state()
        session_state[UPSTREAM_SESSION_KEY] = state
        return state
    # 自愈：补全缺失键
    defaults = _default_upstream_state()
    for k, v in defaults.items():
        state.setdefault(k, v)
    return state


def set_upstream_state(session_state, state: Dict[str, Any]) -> None:
    """写入 upstream_state（替换式）。"""
    session_state[UPSTREAM_SESSION_KEY] = state


def _extract_vars_from_wizard(wizard_data: Dict[str, Any]) -> Dict[str, Any]:
    """从老的 wizard_data 反向填充 candidate_vars（迁移老项目用）。"""
    if not isinstance(wizard_data, dict):
        return _default_upstream_state()["candidate_vars"]
    # 优先级：wizard_results_context（Step 5 产物）> 顶层字段
    ctx = wizard_data.get("wizard_results_context") or {}
    dv = ctx.get("dv") or wizard_data.get("dv") or ""
    iv = ctx.get("iv") or wizard_data.get("iv") or ""
    return {
        "dependent_vars": [dv] if dv else [],
        "independent_vars": [iv] if iv else [],
        "grouping_var": iv if iv else "",
        "covariates": [],
    }


def _serialize_plan(plan: Any) -> Optional[Dict]:
    """将 AnalysisPlan 或字典序列化为可 JSON 的字典"""
    if plan is None:
        return None
    from src.parser.intent_resolver import AnalysisPlan
    if isinstance(plan, AnalysisPlan):
        return {
            "__type__": "AnalysisPlan",
            "test_type": plan.test_type,
            "dependent_vars": plan.dependent_vars,
            "independent_vars": plan.independent_vars,
            "grouping_var": plan.grouping_var,
            "covariates": plan.covariates,
            "scale_items": plan.scale_items,
            "blocks": plan.blocks,
            "test_value": plan.test_value,
            "confidence_level": plan.confidence_level,
            "raw_request": plan.raw_request,
            "parsed_keywords": plan.parsed_keywords,
            "ambiguity_score": plan.ambiguity_score,
            "suggested_followups": plan.suggested_followups,
        }
    if isinstance(plan, dict):
        return {"__type__": "dict", "data": plan}
    return None


def _deserialize_plan(data: Dict) -> Any:
    """反序列化 AnalysisPlan"""
    if data is None:
        return None
    t = data.get("__type__")
    if t == "AnalysisPlan":
        from src.parser.intent_resolver import AnalysisPlan
        return AnalysisPlan(
            test_type=data.get("test_type", "descriptive"),
            dependent_vars=data.get("dependent_vars", []),
            independent_vars=data.get("independent_vars", []),
            grouping_var=data.get("grouping_var"),
            covariates=data.get("covariates", []),
            scale_items=data.get("scale_items", []),
            blocks=data.get("blocks", []),
            test_value=data.get("test_value"),
            confidence_level=data.get("confidence_level", 0.95),
            raw_request=data.get("raw_request", ""),
            parsed_keywords=data.get("parsed_keywords", []),
            ambiguity_score=data.get("ambiguity_score", 0.0),
            suggested_followups=data.get("suggested_followups", []),
        )
    if t == "dict":
        return data.get("data", {})
    return None


def _serialize_analysis_output(ao: Dict) -> Dict:
    """将 analysis_output 字典精简序列化，保留可重建的关键信息"""
    if not isinstance(ao, dict):
        return None
    out = {}
    # 保留纯文本/数值字段
    for k in ["test_type", "test_name_zh", "p_value", "effect_size", "ci_lower", "ci_upper"]:
        if k in ao:
            v = ao[k]
            if isinstance(v, (str, int, float, bool, type(None))):
                out[k] = v
            else:
                out[k] = str(v)
    # 保留 errors/warnings
    for k in ["errors", "warnings"]:
        if k in ao:
            out[k] = ao[k]
    # descriptive 转为 records
    desc = ao.get("descriptive")
    if desc is not None and hasattr(desc, "to_dict"):
        out["descriptive"] = {"__type__": "dataframe", "data": desc.to_dict(orient="records")}
    # assumptions 简化保存
    assumptions = ao.get("assumptions")
    if isinstance(assumptions, dict):
        out["assumptions"] = assumptions
    return out if out else None


def _deserialize_analysis_output(data: Dict) -> Dict:
    """反序列化 analysis_output，将 DataFrame 字符串还原为对象"""
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    desc = out.get("descriptive")
    if isinstance(desc, dict) and desc.get("__type__") == "dataframe":
        out["descriptive"] = pd.DataFrame(desc["data"])
    return out


def build_workspace_snapshot() -> Dict[str, Any]:
    """从当前 session_state 构建可序列化的工作区快照"""
    ws = {}

    # 核心数据
    df = st.session_state.get("df")
    if df is not None and hasattr(df, "to_csv"):
        # 使用 base64 编码 CSV，保留原始类型
        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding="utf-8")
        ws["df_b64"] = base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")

    for k in ["meta", "inspector", "file_name", "analysis_history"]:
        v = st.session_state.get(k)
        if v is not None:
            ws[k] = v

    # 分析计划
    plan = st.session_state.get("plan")
    serialized_plan = _serialize_plan(plan)
    if serialized_plan is not None:
        ws["plan"] = serialized_plan

    # 分析输出（精简）
    ao = st.session_state.get("analysis_output")
    serialized_ao = _serialize_analysis_output(ao)
    if serialized_ao is not None:
        ws["analysis_output"] = serialized_ao

    # 向导状态
    wiz_data = st.session_state.get("undergrad_wizard_data")
    if isinstance(wiz_data, dict):
        # 过滤掉不可序列化的对象
        clean_wd = {}
        for wk, wv in wiz_data.items():
            if isinstance(wv, (str, int, float, bool, type(None), list, dict)):
                clean_wd[wk] = wv
            elif hasattr(wv, "to_dict"):
                clean_wd[wk] = {"__type__": "dataframe", "data": wv.to_dict(orient="records")}
        ws["undergrad_wizard_data"] = clean_wd

    for k in ["undergrad_mode", "undergrad_path", "undergrad_step"]:
        v = st.session_state.get(k)
        if v is not None:
            ws[k] = v

    # 模块设计结果
    qd = st.session_state.get("questionnaire_design")
    if isinstance(qd, dict):
        ws["questionnaire_design"] = qd

    ed = st.session_state.get("experiment_engine")
    if ed is not None and hasattr(ed, "design") and ed.design is not None:
        from src.experiment_design import ExperimentDesign
        d = ed.design
        ws["experiment_design"] = {
            "title": d.title,
            "design_type": d.design_type,
            "design_type_zh": d.design_type_zh,
            "background": d.background,
            "hypotheses": d.hypotheses,
            "n_subjects": d.n_subjects,
        }

    pe = st.session_state.get("paper_engine")
    if pe is not None:
        ws["paper_engine_state"] = {
            "topic": pe.state.topic,
            "hypotheses": pe.state.hypotheses,
            "participants_n": pe.state.participants_n,
        }

    # 用户设置（v4.4: llm_* 字段已移除，仅保留 app_mode；老项目读到 llm_* 会被忽略）
    for k in ["app_mode", "quick_model_id"]:
        v = st.session_state.get(k)
        if v is not None and v != "":
            ws[k] = v

    # v2.9: 图表收藏夹
    try:
        from src.utils.figure_collection import FigureCollection, SESSION_KEY
        coll = st.session_state.get(SESSION_KEY)
        if isinstance(coll, FigureCollection):
            ws["figure_collection"] = coll.to_serializable()
    except Exception:
        pass

    # v2.9: 答辩问答掌握状态（map: question_text → bool）
    mastery = st.session_state.get("defense_qa_mastered")
    if isinstance(mastery, dict):
        ws["defense_qa_mastered"] = mastery

    # v2.9: 下载历史
    download_history = st.session_state.get("download_history")
    if isinstance(download_history, list):
        ws["download_history"] = download_history

    # v3.1: AI 助教对话历史（每个 location 独立）
    tutor_histories = {}
    for key in list(st.session_state.keys()):
        if key.startswith("_tutor_history_"):
            history = st.session_state[key]
            if isinstance(history, list):
                # 序列化 ChatMessage
                tutor_histories[key] = [
                    {"role": m.role, "content": m.content}
                    if hasattr(m, "role") else m
                    for m in history
                ]
    if tutor_histories:
        ws["tutor_histories"] = tutor_histories

    # v3.2: 上游漏斗状态（选题/分层/可研究性等）
    upstream = st.session_state.get(UPSTREAM_SESSION_KEY)
    if isinstance(upstream, dict):
        # stages 内可能含 ChatMessage 对象，序列化处理
        clean_stages = {}
        for sid, sdata in (upstream.get("stages") or {}).items():
            if not isinstance(sdata, dict):
                continue
            entry = dict(sdata)
            history = entry.get("ai_history") or []
            entry["ai_history"] = [
                {"role": m.role, "content": m.content}
                if hasattr(m, "role") else m
                for m in history
                if (isinstance(m, dict) or hasattr(m, "role"))
            ]
            clean_stages[str(sid)] = entry
        ws["upstream_state"] = {
            "tier": upstream.get("tier", "beginner"),
            "phase": upstream.get("phase", "funnel"),
            "current_stage": upstream.get("current_stage", 1),
            "stages": clean_stages,
            "research_question": upstream.get("research_question", ""),
            "candidate_vars": upstream.get("candidate_vars") or _default_upstream_state()["candidate_vars"],
            "feasibility_results": upstream.get("feasibility_results") or {},
            # v3.3 字段（已是 dict/list 形式存储，可直接序列化）
            "funnel_history": list(upstream.get("funnel_history") or []),
            "advanced_meta": dict(upstream.get("advanced_meta") or {}),
            "asked_themes": list(upstream.get("asked_themes") or []),
        }

    # v3.4: 文献综述工作台状态
    lr_state = st.session_state.get(LITERATURE_REVIEW_SESSION_KEY)
    if isinstance(lr_state, dict):
        ws["literature_review_state"] = {
            "literature_items": list(lr_state.get("literature_items") or []),
            "notes": list(lr_state.get("notes") or []),
            "matrix": dict(lr_state.get("matrix") or {}),
            "themes": list(lr_state.get("themes") or []),
            "gaps": list(lr_state.get("gaps") or []),
            "last_search_query": lr_state.get("last_search_query", ""),
            "last_search_at": lr_state.get("last_search_at", ""),
        }

    # v3.5: 顶层 WorkspaceState 视图（如已激活）— 与 sync_to_legacy_session 镜像
    try:
        from src.utils.workspace_state import WORKSPACE_KEY, WorkspaceState
        wsv = st.session_state.get(WORKSPACE_KEY)
        if isinstance(wsv, WorkspaceState):
            ws["workspace_state_v35"] = wsv.to_dict()
    except Exception:
        pass

    # 元信息
    ws["_saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws["_version"] = "3.5"
    ws["_schema"] = "v3.5"

    return ws


# ===========================================================================
# 跨版本迁移
# ===========================================================================

CURRENT_SCHEMA = "v3.5"


class FutureSchemaError(Exception):
    """工作区文件版本高于当前系统版本，无法加载。"""
    pass


def _migrate_v3_2_to_v3_4(data: Dict[str, Any]) -> Dict[str, Any]:
    """v3.2 → v3.4: 添加 literature_review_state（v3.3 未变 schema，沿用此迁移到 v3.4）。"""
    if "literature_review_state" not in data:
        data["literature_review_state"] = {
            "literature_items": [],
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
    return data


def _migrate_v2_9_to_v3_2(data: Dict[str, Any]) -> Dict[str, Any]:
    """老项目（v2.9 / v3.0 / v3.1）→ v3.2:
    添加 upstream_state，phase=wizard 让老项目跳过漏斗，从 wizard_data 反向填充。
    """
    if "upstream_state" in data:
        return data
    wizard = data.get("undergrad_wizard_data") or {}
    has_research_q = bool(wizard.get("research_q") or "")
    data["upstream_state"] = {
        "tier": "beginner",
        # 老项目（已有 research_q 或已开始走 wizard）→ phase=wizard 跳过漏斗
        # 新建空项目（无 research_q）→ phase=funnel 进漏斗
        "phase": "wizard" if has_research_q else "funnel",
        "current_stage": 5 if has_research_q else 1,
        "stages": {},
        "research_question": wizard.get("research_q", ""),
        "candidate_vars": _extract_vars_from_wizard(wizard),
        "feasibility_results": {},
    }
    return data


MIGRATIONS: Dict[str, list] = {
    "workspace_v1": [
        # v1 → v2: 添加实验设计和论文引擎状态占位
        lambda data: data.setdefault("experiment_design", None) or data,
        lambda data: data.setdefault("paper_engine_state", None) or data,
    ],
    "v2.5": [
        # v2.5 → v2.6: 若旧版缺少新字段 pipeline_config，填充默认值 None
        lambda data: data.setdefault("pipeline_config", None) or data,
        # 重命名字段路径: old_field → new_field (示例)
        lambda data: data.update({"undergrad_wizard_data": data.pop("wizard_data", data.get("undergrad_wizard_data", {}))}) or data,
    ],
    "v2.5.1": [
        # v2.5.1 → v2.6: 补充 pipeline_config 默认值
        lambda data: data.setdefault("pipeline_config", None) or data,
    ],
    "v2.6": [
        # v2.6 → v2.9: 初始化空的图表收藏夹、空的答辩掌握状态、空的下载历史
        lambda data: data.setdefault("figure_collection", []) or data,
        lambda data: data.setdefault("defense_qa_mastered", {}) or data,
        lambda data: data.setdefault("download_history", []) or data,
    ],
    "v2.7": [
        lambda data: data.setdefault("figure_collection", []) or data,
        lambda data: data.setdefault("defense_qa_mastered", {}) or data,
        lambda data: data.setdefault("download_history", []) or data,
    ],
    "v2.8": [
        lambda data: data.setdefault("figure_collection", []) or data,
        lambda data: data.setdefault("defense_qa_mastered", {}) or data,
        lambda data: data.setdefault("download_history", []) or data,
    ],
    "v2.9": [
        # v2.9 → v3.2: 添加 upstream_state（v3.0/v3.1 未变更 schema，沿用此迁移）
        _migrate_v2_9_to_v3_2,
        # v3.2 → v3.4: 顺带补 literature_review_state
        _migrate_v3_2_to_v3_4,
    ],
    "v3.2": [
        # v3.2 → v3.4: 添加 literature_review_state（v3.3 未变 schema，沿用此迁移）
        _migrate_v3_2_to_v3_4,
    ],
    "v3.3": [
        # v3.3 → v3.4: 添加 literature_review_state（向前兼容标签）
        _migrate_v3_2_to_v3_4,
    ],
    "v3.4": [
        # v3.4 → v3.5: 无字段变更（仅新增 WorkspaceState 视图，不动底层结构）
        # 占位 lambda 确保版本号被推进
        lambda data: data,
    ],
}


def _migrate_workspace(data: Dict[str, Any]) -> Dict[str, Any]:
    """应用迁移，将旧版本快照升级至当前版本。

    版本号高于系统当前版本时，拒绝加载并抛出异常。
    """
    schema = data.get("_schema", "workspace_v1")

    # 规范化旧版本号
    if schema == "workspace_v2":
        schema = "v2.5"

    if schema == CURRENT_SCHEMA:
        return data

    # 检查是否为未来版本（版本号高于当前系统）
    schema_parts = schema.lstrip("v").split(".")
    current_parts = CURRENT_SCHEMA.lstrip("v").split(".")
    try:
        schema_num = tuple(int(p) for p in schema_parts)
        current_num = tuple(int(p) for p in current_parts)
        if schema_num > current_num:
            raise FutureSchemaError(
                f"工作区文件版本（{schema}）高于当前系统版本（{CURRENT_SCHEMA}），"
                f"请升级系统后打开此工作区。"
            )
    except (ValueError, TypeError):
        pass

    # 按顺序执行迁移链
    migration_chain = _build_migration_chain(schema, CURRENT_SCHEMA)
    for migrate_fn in migration_chain:
        try:
            data = migrate_fn(data)
        except Exception:
            pass

    data["_schema"] = CURRENT_SCHEMA
    data["_migrated_from"] = schema
    return data


def _build_migration_chain(from_schema: str, to_schema: str) -> list:
    """构建从 from_schema 到 to_schema 的迁移函数链。

    使用显式有序版本列表（避免字典序错位，例如 'workspace_v1' > 'v2.6'）。
    """
    # 显式版本顺序（旧 → 新）
    VERSION_ORDER = [
        "workspace_v1",
        "v2.5",
        "v2.5.1",
        "v2.6",
        "v2.7",
        "v2.8",
        "v2.9",
        "v3.2",
        "v3.3",
        "v3.4",
        # v3.5 是 CURRENT，无需迁移函数（终点）
    ]
    chain = []
    started = False
    for key in VERSION_ORDER:
        if key == from_schema:
            started = True
        if started:
            chain.extend(MIGRATIONS.get(key, []))
    return chain


def restore_workspace(loaded: Dict[str, Any]) -> int:
    """从已加载的字典恢复 session_state，返回恢复的数据项数"""
    restored = 0

    # 迁移（可能抛出未来版本错误）
    loaded = _migrate_workspace(loaded)

    # 迁移成功提示
    if loaded.get("_migrated_from"):
        from_version = loaded["_migrated_from"]
        # 记录到 session_state，UI 层可读取并显示
        st.session_state.setdefault("_workspace_migration_info", {})
        st.session_state["_workspace_migration_info"] = {
            "from_version": from_version,
            "to_version": CURRENT_SCHEMA,
        }

    # DataFrame
    df_b64 = loaded.get("df_b64")
    if df_b64:
        try:
            csv_bytes = base64.b64decode(df_b64)
            st.session_state.df = pd.read_csv(io.BytesIO(csv_bytes))
            restored += 1
        except Exception:
            pass

    # 简单字段
    # v4.4: llm_provider / llm_model / llm_temperature 已从 session_state 移除；
    # 老项目文件中如有这些键，restore 阶段静默忽略（不写回 session_state）。
    for k in ["meta", "inspector", "file_name", "analysis_history",
              "undergrad_mode", "undergrad_path", "undergrad_step",
              "app_mode", "quick_model_id"]:
        if k in loaded:
            st.session_state[k] = loaded[k]
            restored += 1

    # 向导数据
    wd = loaded.get("undergrad_wizard_data")
    if isinstance(wd, dict):
        clean_wd = {}
        for wk, wv in wd.items():
            if isinstance(wv, dict) and wv.get("__type__") == "dataframe":
                clean_wd[wk] = pd.DataFrame(wv["data"])
            else:
                clean_wd[wk] = wv
        st.session_state.undergrad_wizard_data = clean_wd
        restored += 1

    # 分析计划
    plan_data = loaded.get("plan")
    if plan_data is not None:
        st.session_state.plan = _deserialize_plan(plan_data)
        restored += 1

    # 分析输出
    ao_data = loaded.get("analysis_output")
    if ao_data is not None:
        st.session_state.analysis_output = _deserialize_analysis_output(ao_data)
        restored += 1

    # 问卷设计
    qd = loaded.get("questionnaire_design")
    if isinstance(qd, dict):
        st.session_state.questionnaire_design = qd
        restored += 1

    # v2.9: 图表收藏夹
    fc_data = loaded.get("figure_collection")
    if fc_data is not None:
        try:
            from src.utils.figure_collection import (
                FigureCollection, SESSION_KEY,
            )
            st.session_state[SESSION_KEY] = FigureCollection.from_serializable(fc_data)
            restored += 1
        except Exception:
            pass

    # v2.9: 答辩掌握状态
    mastery = loaded.get("defense_qa_mastered")
    if isinstance(mastery, dict):
        st.session_state["defense_qa_mastered"] = mastery
        restored += 1

    # v2.9: 下载历史
    download_history = loaded.get("download_history")
    if isinstance(download_history, list):
        st.session_state["download_history"] = download_history
        restored += 1

    # v3.1: AI 助教对话历史
    tutor_histories = loaded.get("tutor_histories")
    if isinstance(tutor_histories, dict):
        try:
            from src.paper_writer.ai_tutor import ChatMessage
            for key, msgs in tutor_histories.items():
                if not isinstance(msgs, list):
                    continue
                rebuilt = []
                for m in msgs:
                    if isinstance(m, dict) and "role" in m and "content" in m:
                        rebuilt.append(ChatMessage(role=m["role"], content=m["content"]))
                st.session_state[key] = rebuilt
            restored += 1
        except Exception:
            pass

    # v3.4: 文献综述工作台状态
    lr = loaded.get("literature_review_state")
    if isinstance(lr, dict):
        defaults = _default_literature_review_state()
        for k, v in defaults.items():
            lr.setdefault(k, v)
        st.session_state[LITERATURE_REVIEW_SESSION_KEY] = lr
        restored += 1

    # v3.5: 顶层 WorkspaceState 视图（如有则恢复）
    wsv_dict = loaded.get("workspace_state_v35")
    if isinstance(wsv_dict, dict):
        try:
            from src.utils.workspace_state import WORKSPACE_KEY, WorkspaceState
            st.session_state[WORKSPACE_KEY] = WorkspaceState.from_dict(wsv_dict)
            restored += 1
        except Exception:
            pass

    # v3.2: 上游漏斗状态
    upstream = loaded.get("upstream_state")
    if isinstance(upstream, dict):
        # 反序列化 stages 中的 ChatMessage
        try:
            from src.paper_writer.ai_tutor import ChatMessage
            stages = {}
            for sid, sdata in (upstream.get("stages") or {}).items():
                if not isinstance(sdata, dict):
                    continue
                entry = dict(sdata)
                history = entry.get("ai_history") or []
                rebuilt = []
                for m in history:
                    if isinstance(m, dict) and "role" in m and "content" in m:
                        rebuilt.append(ChatMessage(role=m["role"], content=m["content"]))
                    else:
                        rebuilt.append(m)
                entry["ai_history"] = rebuilt
                stages[str(sid)] = entry
            upstream = dict(upstream)
            upstream["stages"] = stages
        except Exception:
            pass
        # 自愈：补全缺失键
        defaults = _default_upstream_state()
        for k, v in defaults.items():
            upstream.setdefault(k, v)
        st.session_state[UPSTREAM_SESSION_KEY] = upstream
        restored += 1

    return restored


# ===========================================================================
# v3.7: 断点续读位置标记
# ===========================================================================

# 友好 phase 显示名
_PHASE_LABEL_ZH = {
    "funnel": "选题漏斗",
    "literature_review": "文献综述工作台",
    "wizard": "数据分析向导",
    "done": "已完成",
}


def update_last_position(
    phase: str,
    step: Optional[int] = None,
    label: Optional[str] = None,
    session_state=None,
) -> None:
    """v3.7: 记录用户最后访问的位置，供下次启动一键回到这里。

    Args:
        phase: funnel | literature_review | wizard | done
        step: 阶段内步数（funnel: 1-5, wizard: 0-7）
        label: 友好显示名（可选；不填则按 phase 推断）
        session_state: 测试注入；默认 st.session_state
    """
    if session_state is None:
        session_state = st.session_state
    state = session_state.get(UPSTREAM_SESSION_KEY)
    if not isinstance(state, dict):
        state = _default_upstream_state()
        session_state[UPSTREAM_SESSION_KEY] = state

    if not label:
        phase_zh = _PHASE_LABEL_ZH.get(phase, phase or "未知")
        if step is not None and step > 0:
            if phase == "funnel":
                label = f"{phase_zh} stage {step}"
            elif phase == "wizard":
                label = f"{phase_zh} 第 {step} 步"
            else:
                label = phase_zh
        else:
            label = phase_zh

    state["last_position"] = {
        "phase": phase or "",
        "step": int(step) if step is not None else 0,
        "label": label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def get_last_position(session_state=None) -> Optional[Dict[str, Any]]:
    """v3.7: 读取最后访问的位置；为空或未设置时返回 None。"""
    if session_state is None:
        session_state = st.session_state
    state = session_state.get(UPSTREAM_SESSION_KEY)
    if not isinstance(state, dict):
        return None
    pos = state.get("last_position") or {}
    if not isinstance(pos, dict) or not pos.get("phase"):
        return None
    return {
        "phase": pos.get("phase", ""),
        "step": int(pos.get("step") or 0),
        "label": pos.get("label", ""),
        "timestamp": pos.get("timestamp", ""),
    }


def humanize_elapsed(timestamp: str) -> str:
    """格式化 ISO 时间戳为「N 分钟前 / N 小时前 / N 天前」。"""
    if not timestamp:
        return ""
    try:
        ts = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return ""
    delta = datetime.now() - ts
    secs = delta.total_seconds()
    if secs < 60:
        return "刚刚"
    if secs < 3600:
        return f"{int(secs / 60)} 分钟前"
    if secs < 86400:
        return f"{int(secs / 3600)} 小时前"
    return f"{int(secs / 86400)} 天前"


def is_at_last_position(session_state=None) -> bool:
    """判断当前 session_state 的 phase/step 是否就是 last_position（避免重复显示 banner）。"""
    pos = get_last_position(session_state)
    if not pos:
        return True   # 没记录就当作"在原地"
    if session_state is None:
        session_state = st.session_state
    state = session_state.get(UPSTREAM_SESSION_KEY) or {}
    cur_phase = state.get("phase", "")
    cur_step = int(state.get("current_stage", 0) or 0)
    if pos["phase"] == "wizard":
        # wizard step 单独读 undergrad_step
        cur_step = int(session_state.get("undergrad_step", 0) or 0)
    return pos["phase"] == cur_phase and pos["step"] == cur_step
