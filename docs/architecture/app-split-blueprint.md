# app.py 拆分蓝图（psy-E，2026-09-04 夜间产出）

> 本任务**不写任何实现代码**，蓝图供 v5.10 后路线日间决策排期。
> 证据基线：app.py 现为 2712 行、模块级过程式代码、7 个顶层函数（其中 5 个 `def` 于模块顶部：
> 76 `_get_onboarding_text`、153 `_build_homework_package`、222 `_generate_method_description`、
> 377 `_preload_heavy_deps`、410 `_autosave_current_workspace`），六个 mode 分支巨型 if/elif。

## 1. 现状调用图（文字版）

```
app.py 模块级执行流（Streamlit 每次重跑全文件）
├── 1-75    imports（std + src.*；重依赖经 _preload_heavy_deps 懒加载）
├── 76-376  三个纯函数工具（onboarding 文案 / 作业包构建 / 方法说明生成）
├── 377-409 _preload_heavy_deps（scipy/jieba/statsmodels 预热线程）
├── 410-~460 _autosave_current_workspace + workspace 快照/恢复
├── ~460-962 共享壳：页面配置、侧栏模式选择器、onboarding、跨模式状态迁移
│   └── 关键分支 if mode != _prev_mode（:541）做模式切换清理
├── 963-1773  📈 数据分析（811 行，最大分支；懒加载 parser/analysis.runner/output.formatter/
│             output.interpretation/ui.renderers/data.demo_datasets 六个子系统）
├── 1774-1780 🧪 实验设计（7 行薄壳 → src.ui.experiment_design_ui）
├── 1781-2590 📋 问卷设计（810 行；design_engine + llm_engine(_premium) + 报告生成）
├── 2591-2621 📝 论文写作（31 行薄壳）
├── 2622-2657 📚 文献与选题（36 行薄壳 → src.ui.literature_review_panel）
├── 2658-2701 📦 交付包导出（44 行）
└── 2702-2712 🗂️ 模板中心（11 行薄壳）
```

共享状态：`st.session_state` 约 30 个键；跨分支共享最广的为
`analysis_output`（数据分析产物被论文写作/交付包消费）、workspace 系列键
（`_workspace_last_saved`/`_ws_export_*`/`_clear_session_confirm`）、问卷侧
`q_request_input`/`_recipe_prefill_text`/`undergrad_*`。

共享 src 模块（被 ≥2 分支引用）：`src.version`、`src.utils.workspace`、
`src.utils.user_prefs`、`src.utils.usage_hooks`、`src.llm_gateway.active_config`。

## 2. 目标结构

```
app/
├── __init__.py
├── main.py               # 入口：页面配置 + 侧栏 + mode 路由（~200 行）
├── shell.py              # onboarding、模式切换清理、自动保存、预热线程（~350 行）
├── shared_state.py       # session_state 键名常量 + 读写助手（~120 行）
├── tools.py              # _build_homework_package/_generate_method_description（~220 行）
├── analysis_mode.py      # 📈 数据分析（~830 行）
├── experiment_mode.py    # 🧪 实验设计（~20 行）
├── questionnaire_mode.py # 📋 问卷设计（~830 行）
├── paper_mode.py         # 📝 论文写作（~40 行）
├── literature_mode.py    # 📚 文献与选题（~45 行）
├── export_mode.py        # 📦 交付包导出（~55 行）
└── template_mode.py      # 🗂️ 模板中心（~15 行）
app.py                    # 过渡期保留：from app.main import main; main()
```

原则：各 mode 模块暴露统一入口 `render(session)`；session_state 只经
shared_state.py 的键名常量访问（消灭裸字符串键漂移）。

## 3. 迁移顺序（从小分支到大分支，每步独立可验收）

| 步 | 内容 | 预估行数 | 工作量 |
|---|---|---|---|
| S1 | 建 app/ 包 + shared_state.py（键名常量，app.py 改引常量，行为零变化） | ~130 | S |
| S2 | tools.py：迁 3 个纯函数（无 session 依赖，最安全） | ~230 | S |
| S3 | shell.py：_preload_heavy_deps + _autosave + onboarding | ~360 | M |
| S4 | 四个薄壳分支（实验/论文/文献/模板）→ 4 个 mode 模块 | ~130 | S |
| S5 | export_mode（交付包，依赖 analysis_output 契约） | ~60 | S-M |
| S6 | questionnaire_mode（810 行，含 LLM 异步状态机） | ~840 | L |
| S7 | analysis_mode（811 行，依赖面最广，放最后） | ~840 | L |
| S8 | main.py 路由成型，app.py 变 2 行入口；删除过程式残留 | ~210 | M |

## 4. 每步验收标准

1. `python -m pytest tests/ -q` 全绿（现基线 ~2486 项，exit 0）；
2. `streamlit run app.py` 冷启动可用：AppTest 冒烟（`streamlit.testing.v1.AppTest`）跑一遍六个 mode 各一次主路径；
3. 冷启动时间不劣化（现基线启动自检 740ms 量级 + 懒加载设计，S3 后用 `_preload_heavy_deps` 计时断言 ±10%）；
4. `git diff --stat` 仅显示移动（`--find-renames` 下相似度 ≥95%）；
5. 每步一个 commit，可独立 revert。

## 5. 风险清单

- **session_state 跨模块共享**：analysis_output 被论文/交付包消费——若各自拷贝键名常量会静默脱钩（S1 的 shared_state 是唯一事实源，review 时重点查）。
- **Streamlit 执行模型**：全文件每轮重跑 → 迁移后模块级副作用（如预热线程启动）必须收敛到显式函数；`if mode != _prev_mode`（:541）的清理逻辑依赖"上一轮也执行过同段代码"，拆分后要保证清理段仍在 main.py 每轮执行。
- **懒加载语义**：数据分析分支的分支内 import 是启动性能的关键（740ms 冷启动的来源），迁移时必须保持 import 在函数内，不得提升到模块顶。
- **LLM 异步线程**（问卷分支）：threading + CancelledLLMError 与 session 生命周期耦合，S6 需要专测取消路径。
- **AppTest 覆盖缺口**：现有测试对 UI 分支覆盖有限，S6/S7 前先补两分支的 AppTest 冒烟作为迁移安全网。

## 6. 工作量估算

S1-S5 合计 ~1.5 个日间工作块（半天）；S6/S7 各半天到一天（含安全网测试）；S8 半天。
总计约 2.5-3.5 个日间工作块，建议排 v5.11-v5.12 两个版本窗口，S6/S7 之间留一版观察。
