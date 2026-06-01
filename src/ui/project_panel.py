"""项目管理 UI — 侧边栏的「📂 我的项目」面板。

提供：
- 当前项目名显示 + 切换下拉
- 新建 / 重命名 / 复制 / 删除 / 导出 / 备注
- 切换时自动保存当前 + 加载目标
"""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from src.utils import project_manager as pm


# --------------------------------------------------------------------------- #
# 切换项目
# --------------------------------------------------------------------------- #

def _save_active_then_load(target_id: str):
    """切换项目：把当前 session_state 写到旧项目 → 清空 → 加载新项目。"""
    from src.utils.workspace import build_workspace_snapshot, restore_workspace

    # 1. 保存当前
    active_id = pm.get_active_project_id(st.session_state)
    if active_id and active_id != target_id:
        try:
            ws = build_workspace_snapshot()
            pm.save_workspace(active_id, ws)
        except Exception:
            pass

    # 2. 清空当前 session（保留用户全局设置；v4.6 LLM 配置改为 quick_model_id 单键）
    preserved = {
        k: st.session_state[k] for k in [
            "quick_model_id",
            "privacy_accepted", "onboarding_completed",
            "startup_check_done", "env_status", "has_auto_cleaned",
            "_workspace_dismissed", "_autosave_dismissed",
        ] if k in st.session_state
    }
    st.session_state.clear()
    st.session_state.update(preserved)

    # 3. 加载目标
    pm.set_active_project(st.session_state, target_id)
    target_ws = pm.load_workspace(target_id)
    if target_ws:
        try:
            restore_workspace(target_ws)
        except Exception:
            pass


def ensure_active_project_on_first_visit():
    """首次访问时：检查 active_project_id，没有则做迁移或新建。

    在主入口（app.py）调用，确保任何时候都有一个"当前项目"。
    """
    active_id = pm.get_active_project_id(st.session_state)
    if active_id and pm.get_project(active_id):
        return  # 已有有效活跃项目

    # 1. 尝试迁移 v3.0 的 autosave.json
    migrated = pm.migrate_legacy_autosave()
    if migrated:
        from src.utils.workspace import restore_workspace
        ws = pm.load_workspace(migrated.id)
        if ws:
            try:
                restore_workspace(ws)
            except Exception:
                pass
        pm.set_active_project(st.session_state, migrated.id)
        return

    # 2. 找最近访问的现有项目
    projects = pm.list_projects()
    if projects:
        target = projects[0]
        from src.utils.workspace import restore_workspace
        ws = pm.load_workspace(target.id)
        if ws:
            try:
                restore_workspace(ws)
            except Exception:
                pass
        pm.set_active_project(st.session_state, target.id)
        return

    # 3. 全新用户：创建默认项目
    new_proj = pm.create_project(name="我的研究")
    pm.set_active_project(st.session_state, new_proj.id)


# --------------------------------------------------------------------------- #
# 侧边栏面板渲染
# --------------------------------------------------------------------------- #

def render_project_panel():
    """渲染侧边栏「📂 我的项目」面板。"""
    st.sidebar.divider()
    st.sidebar.header("📂 我的项目")

    active = pm.get_active_project(st.session_state)
    projects = pm.list_projects()

    if not active:
        st.sidebar.warning("⚠ 当前无活跃项目")
        if st.sidebar.button("➕ 新建项目", use_container_width=True, key="proj_new_empty"):
            new_proj = pm.create_project("我的研究")
            pm.set_active_project(st.session_state, new_proj.id)
            st.rerun()
        return

    st.sidebar.caption(f"**当前**：{active.name}")
    if active.note:
        st.sidebar.caption(f"📝 {active.note}")

    # 项目切换下拉
    if len(projects) > 1:
        names = [
            f"{p.name}（{p.updated_at[:10]}）"
            for p in projects
        ]
        ids = [p.id for p in projects]
        try:
            current_idx = ids.index(active.id)
        except ValueError:
            current_idx = 0
        chosen = st.sidebar.selectbox(
            "切换项目",
            options=ids,
            format_func=lambda i: names[ids.index(i)],
            index=current_idx,
            key="proj_switch_select",
        )
        if chosen != active.id:
            _save_active_then_load(chosen)
            st.rerun()

    # 操作按钮
    cols = st.sidebar.columns(2)
    if cols[0].button("➕ 新建", use_container_width=True, key="proj_new"):
        st.session_state["_proj_show_new"] = True
    if cols[1].button("✏️ 重命名", use_container_width=True, key="proj_rename"):
        st.session_state["_proj_show_rename"] = True

    cols2 = st.sidebar.columns(2)
    if cols2[0].button("📋 复制", use_container_width=True, key="proj_copy"):
        new_proj = pm.copy_project(active.id)
        if new_proj:
            _save_active_then_load(new_proj.id)
            st.sidebar.success(f"已复制为「{new_proj.name}」")
            st.rerun()
    if cols2[1].button("🗑 删除", use_container_width=True, key="proj_delete"):
        st.session_state["_proj_show_delete"] = True

    # ------- 新建对话框 -------
    if st.session_state.get("_proj_show_new"):
        with st.sidebar.form("proj_new_form", clear_on_submit=True):
            new_name = st.text_input("新项目名", key="_new_proj_name")
            new_note = st.text_input("备注（可选）", key="_new_proj_note")
            cols3 = st.columns(2)
            confirm = cols3[0].form_submit_button("创建", type="primary")
            cancel = cols3[1].form_submit_button("取消")
            if confirm and new_name.strip():
                new_proj = pm.create_project(new_name, note=new_note)
                _save_active_then_load(new_proj.id)
                st.session_state["_proj_show_new"] = False
                st.rerun()
            if cancel:
                st.session_state["_proj_show_new"] = False
                st.rerun()

    # ------- 重命名对话框 -------
    if st.session_state.get("_proj_show_rename"):
        with st.sidebar.form("proj_rename_form", clear_on_submit=True):
            renamed = st.text_input("新名称", value=active.name, key="_rename_input")
            new_note = st.text_input("备注", value=active.note, key="_rename_note")
            cols4 = st.columns(2)
            confirm = cols4[0].form_submit_button("保存", type="primary")
            cancel = cols4[1].form_submit_button("取消")
            if confirm:
                if renamed.strip() and renamed.strip() != active.name:
                    pm.rename_project(active.id, renamed.strip())
                if new_note != active.note:
                    pm.update_note(active.id, new_note)
                st.session_state["_proj_show_rename"] = False
                st.rerun()
            if cancel:
                st.session_state["_proj_show_rename"] = False
                st.rerun()

    # ------- 删除确认 -------
    if st.session_state.get("_proj_show_delete"):
        st.sidebar.warning(f"⚠ 确认删除「{active.name}」？此操作不可恢复。")
        cols5 = st.sidebar.columns(2)
        if cols5[0].button("✅ 确认删除", type="primary", key="proj_del_confirm"):
            target_id = active.id
            # 先切到另一个项目（或新建空的）
            others = [p for p in projects if p.id != target_id]
            if others:
                _save_active_then_load(others[0].id)
            else:
                # 删除最后一个项目，新建空项目
                new_proj = pm.create_project("我的研究")
                _save_active_then_load(new_proj.id)
            pm.delete_project(target_id)
            st.session_state["_proj_show_delete"] = False
            st.rerun()
        if cols5[1].button("取消", key="proj_del_cancel"):
            st.session_state["_proj_show_delete"] = False
            st.rerun()

    # ------- 导出当前项目 -------
    with st.sidebar.expander("📤 导出 / 导入项目", expanded=False):
        # 导出
        try:
            from src.utils.workspace import build_workspace_snapshot
            ws = build_workspace_snapshot()
            ws_json = json.dumps(ws, ensure_ascii=False, default=str, indent=2)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "📥 导出当前项目（JSON）",
                data=ws_json,
                file_name=f"{active.name}_{ts}.json",
                mime="application/json",
                use_container_width=True,
                key="proj_export_btn",
            )
        except Exception as e:
            st.caption(f"导出准备失败：{e}")

        # 导入
        uploaded = st.file_uploader(
            "导入项目 JSON（创建为新项目）",
            type=["json"], key="proj_import_uploader",
        )
        if uploaded is not None:
            try:
                imported_ws = json.loads(uploaded.read().decode("utf-8"))
                imported_name = (
                    uploaded.name.rsplit(".", 1)[0]
                    .replace("_", " ")[:40]
                ) or "导入的项目"
                new_proj = pm.create_project(imported_name, note="从 JSON 导入")
                pm.save_workspace(new_proj.id, imported_ws)
                _save_active_then_load(new_proj.id)
                st.success(f"✅ 已导入为「{new_proj.name}」")
                st.rerun()
            except Exception as e:
                st.error(f"导入失败：{e}")

    st.sidebar.caption(f"共 {len(projects)} 个项目")
