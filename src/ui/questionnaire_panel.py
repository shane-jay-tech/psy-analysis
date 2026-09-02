"""问卷设计页面面板 — 从 app.py 抽取的完整问卷设计流程。"""

import threading
import time

import streamlit as st

from src.questionnaire.design_engine import design_questionnaire
from src.questionnaire.llm_engine import (
    design_questionnaire_llm_async,
    cancel_design_request,
    CancelledLLMError,
)
from src.questionnaire.report_generator import (
    generate_design_report, generate_design_summary,
)
from src.utils.memory_manager import render_memory_manager_ui
from src.utils.i18n import t


class _DummyContext:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def render_questionnaire_page():
    """渲染问卷设计页面的完整流程。"""
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
                st.markdown(
                    f"""<div style="background:#f0f7ff;border-left:4px solid #2e86de;
                    padding:12px 16px;border-radius:6px;margin:8px 0;">
                    <strong>📋 系统对你研究问题的理解</strong><br>
                    <span style="font-size:0.9em;">
                    研究层次：<b>{rt_label}</b><br>
                    评估对象：<b>{rp.get('research_object', '?')}</b><br>
                    答题人群：<b>{rp.get('population', '?')}</b>（角色：{rp.get('respondent_role', '?')}）<br>
                    题目主语：<b>{rp.get('item_subject_template', '?')}</b><br>
                    {f"理论框架：<b>{rp['theoretical_framework']}</b><br>" if rp.get('theoretical_framework') else ""}
                    研究意图：{rp.get('summary', '')}
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
                col.markdown(
                    f"<div style='padding:8px 4px;'>"
                    f"<div style='font-size:0.85em;color:#666;'>{label}</div>"
                    f"<div style='font-size:1.5em;font-weight:600;'>{value}</div>"
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
            import base64
            try:
                if export_format.startswith("📄 Word"):
                    from src.questionnaire.exporters import export_to_docx
                    docx_bytes = export_to_docx(design)
                    b64 = base64.b64encode(docx_bytes).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}" download="{design["construct_name"]}问卷设计报告.docx">点击下载 Word 报告 (.docx)</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.success("✅ Word 报告已生成，可用 Microsoft Word 或 WPS 打开编辑。")

                elif export_format.startswith("📕 PDF"):
                    from src.questionnaire.exporters import export_to_pdf
                    pdf_bytes = export_to_pdf(design)
                    b64 = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/pdf;base64,{b64}" download="{design["construct_name"]}问卷设计报告.pdf">点击下载 PDF 报告 (.pdf)</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.success("✅ PDF 报告已生成。")

                else:
                    full_report = generate_design_report(design)
                    html = f"""<html><head><meta charset='utf-8'>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.8; }}
h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
h2 {{ color: #2980b9; margin-top: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; }}
th {{ background-color: #f2f2f2; }}
pre {{ background: #f8f8f8; padding: 1rem; border-radius: 4px; white-space: pre-wrap; }}
</style></head><body>
{full_report.replace(chr(10), '<br>').replace('## ', '<h2>').replace('# ', '<h1>').replace('---', '<hr>')}
</body></html>"""
                    b64 = base64.b64encode(html.encode("utf-8")).decode()
                    href = f'<a href="data:text/html;base64,{b64}" download="{design["construct_name"]}问卷设计报告.html">点击下载 HTML 报告 (.html)</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.success("✅ HTML 报告已生成。")

            except Exception as e:
                st.error(f"❌ 导出失败：{e}")

    st.divider()
    st.caption("💡 提示：生成的问卷为初稿，建议在此基础上根据具体研究目标和被试群体进行调整，并通过预测试检验题目质量。")
