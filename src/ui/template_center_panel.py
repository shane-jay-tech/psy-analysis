"""模板中心 Streamlit 面板。

让用户浏览模板、查看说明、一键创建项目并进入分析流程。
"""

from __future__ import annotations

import json
from typing import Optional

import pandas as pd
import streamlit as st

from src.templates.registry import (
    list_templates,
    get_template,
    ProjectTemplate,
)


_CREATED_PROJECT_KEY = "template_created_project"
_SELECTED_TEMPLATE_KEY = "template_selected_id"


def render_template_center_panel(session_state: dict | None = None):
    """渲染模板中心面板。"""
    if session_state is None:
        session_state = st.session_state

    templates = list_templates()
    if not templates:
        st.warning("暂无可用模板")
        return

    created = session_state.get(_CREATED_PROJECT_KEY)
    if created:
        _render_created_success(created, session_state)
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        _render_template_list(templates, session_state)

    with col2:
        selected_id = session_state.get(_SELECTED_TEMPLATE_KEY)
        if selected_id:
            tpl = get_template(selected_id)
            if tpl:
                _render_template_detail(tpl, session_state)
        else:
            st.info("← 从左侧选择一个模板查看详情")


def _render_template_list(templates: list[ProjectTemplate], session_state: dict):
    """左侧模板列表。"""
    st.markdown("**可用模板**")
    for tpl in templates:
        icon = _get_research_icon(tpl.research_type)
        if st.button(f"{icon} {tpl.name}", key=f"tpl_btn_{tpl.template_id}", width="stretch"):
            session_state[_SELECTED_TEMPLATE_KEY] = tpl.template_id


def _render_template_detail(tpl: ProjectTemplate, session_state: dict):
    """右侧模板详情。"""
    st.markdown(f"### {tpl.name}")
    st.markdown(f"**研究类型**: {_translate_research_type(tpl.research_type)}")
    st.markdown(f"**描述**: {tpl.description}")
    st.markdown(f"**推荐方法**: {_translate_method(tpl.recommended_method)}")
    st.markdown(f"**样本量建议**: {tpl.sample_size_hint}")

    st.markdown("**变量角色**:")
    for role, desc in tpl.variable_roles.items():
        st.markdown(f"- `{role}`: {desc}")

    st.markdown("**论文章节**: " + " → ".join(tpl.paper_sections))

    data_path = tpl.get_path() / "data.csv"
    if data_path.exists():
        with st.expander("预览样例数据", expanded=False):
            df = pd.read_csv(data_path)
            st.dataframe(df.head(10), width="stretch")
            st.caption(f"共 {len(df)} 行, {len(df.columns)} 列")

    readme_path = tpl.get_path() / "README.md"
    if readme_path.exists():
        with st.expander("模板说明文档", expanded=False):
            st.markdown(readme_path.read_text(encoding="utf-8"))

    st.markdown("---")
    st.markdown("**包含资产**: 样例数据 · 论文骨架 · 证据种子 · 配置文件")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🚀 使用此模板创建项目", type="primary", key=f"create_{tpl.template_id}"):
            _create_project(tpl, session_state)
    with col_b:
        if st.button("↩️ 返回列表", key="back_to_list"):
            session_state.pop(_SELECTED_TEMPLATE_KEY, None)


def _create_project(tpl: ProjectTemplate, session_state: dict):
    """从模板创建真实、独立且可自动保存的项目。"""
    try:
        # 先完整读取模板；任何解析失败都不会清空当前研究或切换项目。
        template_path = tpl.get_path()
        data_path = template_path / "data.csv"
        df = pd.read_csv(data_path) if data_path.exists() else None

        config = None
        config_path = template_path / "template_config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

        evidence_seeds = None
        evidence_path = template_path / "evidence_seeds.json"
        if evidence_path.exists():
            with open(evidence_path, encoding="utf-8") as f:
                evidence_seeds = json.load(f)

        inspector = None
        meta = None
        file_name = None
        if df is not None:
            from src.data.inspector import inspect_dataframe
            inspector = inspect_dataframe(df)
            meta = {
                "source_type": "template",
                "row_count": len(df),
                "col_count": len(df.columns),
            }
            file_name = f"{tpl.name}_样例数据.csv"

        from src.utils import project_manager as pm
        from src.utils.workspace import CURRENT_SCHEMA

        # 创建模板项目前先保存旧研究；保存失败则保持当前 session 与 active 项目不动。
        previous_project_id = pm.get_active_project_id(session_state)
        if previous_project_id:
            if session_state is st.session_state:
                from src.utils.workspace import build_workspace_snapshot
                previous_workspace = build_workspace_snapshot()
            else:
                previous_workspace = _build_core_workspace(session_state)
            if not pm.save_workspace(previous_project_id, previous_workspace):
                raise OSError("当前项目保存失败，已取消模板创建")

        import base64
        import io
        from datetime import datetime

        workspace = {
            "_schema": CURRENT_SCHEMA,
            "_version": CURRENT_SCHEMA.lstrip("v"),
            "_saved_at": datetime.now().isoformat(timespec="seconds"),
            "meta": meta,
            "inspector": inspector,
            "file_name": file_name,
            "analysis_history": [],
            "template_source": tpl.template_id,
        }
        if df is not None:
            buffer = io.StringIO()
            df.to_csv(buffer, index=False, encoding="utf-8")
            workspace["df_b64"] = base64.b64encode(
                buffer.getvalue().encode("utf-8")
            ).decode("ascii")

        # 先把新项目完整写好，之后才清空 session 并切换 active 项目。
        project = pm.create_project(tpl.name, note=f"由模板 {tpl.template_id} 创建")
        if not pm.save_workspace(project.id, workspace):
            pm.delete_project(project.id)
            raise OSError("模板项目初始工作区写入失败")

        from src.ui.session_reset import clear_research_session

        clear_research_session(session_state)
        pm.set_active_project(session_state, project.id)

        project_info = {
            "project_id": project.id,
            "template_id": tpl.template_id,
            "template_name": tpl.name,
            "template_path": str(template_path),
            "recommended_method": tpl.recommended_method,
            "variable_roles": tpl.variable_roles,
            "research_type": tpl.research_type,
        }

        if df is not None:
            project_info["data_path"] = str(data_path)
            session_state["uploaded_df"] = df
            session_state["current_file_name"] = file_name
            # 同步主分析入口使用的统一状态，模板创建后可直接继续分析。
            session_state["df"] = df
            session_state["meta"] = meta
            session_state["inspector"] = inspector
            session_state["file_name"] = session_state["current_file_name"]
            session_state["analysis_output"] = None
            session_state["plan"] = None
            session_state["analysis_cards"] = []

        if config is not None:
            project_info["config"] = config
        if evidence_seeds is not None:
            project_info["evidence_seeds"] = evidence_seeds

        session_state[_CREATED_PROJECT_KEY] = project_info
        session_state["project_id"] = project.id
        session_state["template_source"] = tpl.template_id

    except Exception as e:
        st.error(f"创建项目失败: {e}")


def _build_core_workspace(session_state: dict) -> dict:
    """为非 Streamlit 调用构建可验证的核心快照（正常 UI 使用完整快照）。"""
    import base64
    import io
    from datetime import datetime

    from src.utils.workspace import CURRENT_SCHEMA

    workspace = {
        "_schema": CURRENT_SCHEMA,
        "_version": CURRENT_SCHEMA.lstrip("v"),
        "_saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    for key in ("meta", "inspector", "file_name", "analysis_history"):
        value = session_state.get(key)
        if value is not None:
            workspace[key] = value
    dataframe = session_state.get("df")
    if dataframe is not None and hasattr(dataframe, "to_csv"):
        buffer = io.StringIO()
        dataframe.to_csv(buffer, index=False, encoding="utf-8")
        workspace["df_b64"] = base64.b64encode(
            buffer.getvalue().encode("utf-8")
        ).decode("ascii")
    return workspace


def _render_created_success(project_info: dict, session_state: dict):
    """项目创建成功后的引导。"""
    st.success(f"✅ 项目已创建 — 基于模板「{project_info['template_name']}」")

    st.markdown("**项目信息**:")
    st.markdown(f"- 研究类型: {_translate_research_type(project_info.get('research_type', ''))}")
    st.markdown(f"- 推荐方法: {_translate_method(project_info.get('recommended_method', ''))}")
    st.markdown(f"- 数据已加载: {'✅' if 'data_path' in project_info else '❌'}")

    st.markdown("---")
    st.markdown("**推荐下一步**:")
    st.markdown("1. 前往「📈 数据分析」查看并清洗样例数据")
    st.markdown("2. 在数据分析页描述研究问题，获取方法建议并执行统计")
    st.markdown("3. 前往「📝 论文写作」整理结果与文献证据")
    st.markdown("4. 前往「📦 交付包导出」完成检查并生成论文材料")

    if st.button("🔄 重新选择模板", key="reset_template"):
        session_state.pop(_CREATED_PROJECT_KEY, None)
        session_state.pop(_SELECTED_TEMPLATE_KEY, None)


def _get_research_icon(research_type: str) -> str:
    icons = {
        "correlational": "🔗",
        "experimental": "🧪",
        "pre_post": "📊",
    }
    return icons.get(research_type, "📄")


def _translate_research_type(rt: str) -> str:
    mapping = {
        "correlational": "相关研究",
        "experimental": "实验研究",
        "pre_post": "前后测实验",
    }
    return mapping.get(rt, rt)


def _translate_method(method: str) -> str:
    mapping = {
        "pearson_corr": "Pearson 相关分析",
        "independent_ttest": "独立样本 t 检验",
        "paired_ttest": "配对样本 t 检验",
    }
    return mapping.get(method, method)
