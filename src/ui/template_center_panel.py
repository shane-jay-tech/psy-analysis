"""模板中心 Streamlit 面板。

让用户浏览模板、查看说明、一键创建项目并进入分析流程。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from src.templates.registry import (
    list_templates,
    get_template,
    create_project_from_template,
    ProjectTemplate,
)


_CREATED_PROJECT_KEY = "template_created_project"
_SELECTED_TEMPLATE_KEY = "template_selected_id"


def render_template_center_panel(session_state: dict | None = None):
    """渲染模板中心面板。"""
    if session_state is None:
        session_state = st.session_state

    st.subheader("📋 项目模板中心")
    st.caption("选择一个模板快速启动你的研究项目，系统会自动准备数据和推荐方法。")

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
        if st.button(f"{icon} {tpl.name}", key=f"tpl_btn_{tpl.template_id}", use_container_width=True):
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
            st.dataframe(df.head(10), use_container_width=True)
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
    """创建项目并存入 session。"""
    try:
        target_dir = Path(tempfile.mkdtemp(prefix="psy_project_"))
        project_path = create_project_from_template(tpl.template_id, target_dir)

        project_info = {
            "template_id": tpl.template_id,
            "template_name": tpl.name,
            "project_path": str(project_path),
            "recommended_method": tpl.recommended_method,
            "variable_roles": tpl.variable_roles,
            "research_type": tpl.research_type,
        }

        data_path = project_path / "data.csv"
        if data_path.exists():
            project_info["data_path"] = str(data_path)
            df = pd.read_csv(data_path)
            session_state["uploaded_df"] = df
            session_state["current_file_name"] = f"{tpl.name}_样例数据.csv"

        config_path = project_path / "template_config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                project_info["config"] = json.load(f)

        evidence_path = project_path / "evidence_seeds.json"
        if evidence_path.exists():
            with open(evidence_path, encoding="utf-8") as f:
                project_info["evidence_seeds"] = json.load(f)

        session_state[_CREATED_PROJECT_KEY] = project_info
        session_state["project_id"] = tpl.template_id
        session_state["template_source"] = tpl.template_id

    except Exception as e:
        st.error(f"创建项目失败: {e}")


def _render_created_success(project_info: dict, session_state: dict):
    """项目创建成功后的引导。"""
    st.success(f"✅ 项目已创建 — 基于模板「{project_info['template_name']}」")

    st.markdown("**项目信息**:")
    st.markdown(f"- 研究类型: {_translate_research_type(project_info.get('research_type', ''))}")
    st.markdown(f"- 推荐方法: {_translate_method(project_info.get('recommended_method', ''))}")
    st.markdown(f"- 数据已加载: {'✅' if 'data_path' in project_info else '❌'}")

    st.markdown("---")
    st.markdown("**推荐下一步**:")
    st.markdown("1. 前往「数据导入清洗」查看数据状态")
    st.markdown("2. 前往「方法推荐」获得分析建议")
    st.markdown("3. 前往「数据分析」执行统计")
    st.markdown("4. 前往「交付包导出」生成论文材料")

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
