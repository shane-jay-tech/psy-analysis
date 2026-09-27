# s927-16 四道统计护栏零调用：接线裁决材料（只读取证，零码改动）

- 班名：`qoder-executor-20260927-1940-psy79`（波次 28，只读采集子班）
- 取证时刻：2026-09-27T19:34:24+08:00（`date` 现取）；HEAD=`6cb3c96`；`git status --porcelain` 现值 12 项
- 判据：卷宗「完成标准」①调用面复核 ②三案矩阵 ③推荐 ④零码改动
- 红线：统计数值／效应量结论不落判定（brief §4），本文只出**材料与优先级建议**

---

## 0 一句话实况（锚点被收窄，不是路径搬家）

**「四道统计护栏零调用」不成立——四道里有三道在世接线且已经在阻断，只有第四道真零调用者。**

锚点 `20260925-154313-ae49.result.md` E3 的口径是 `rg src/ tests/ scripts/ --glob '!app.py'`，并自认「置信度上限止于『src/tests/scripts 除禁读件外』、无法排除 `app.py` 是调用方」（其遗留问题 1）。本班就是去补那个口子：`app.py` **既是调用方，而且是唯一调用方**。
⇒ 卷宗背景里「若确系未接线，`guardrails.py:148-325` 属统计建议链断点，**接线会改运行时行为（新增阻断）**」这句，对 148／199／240 三道**已是既成事实**（阻断正在跑），只对 275 一道仍是假设。

---

## 1 调用面复核（判据①）

### 1.1 四道护栏的在世状态（全仓 `rg --no-ignore`，含 `app.py`）

| 护栏函数 | 定义 | 全仓命中（除定义行） | 消费形态 | 运行时效果 |
|---|---|---|---|---|
| `check_variable_type_match` | `src/utils/guardrails.py:148` | `app.py:43`（import）、`app.py:1069`（调用） | `if not type_check.passed:` → `st.error` → **`st.stop()`（`app.py:1077`）** | **硬阻断**（分析不执行） |
| `check_sample_size` | `:199` | `app.py:42`、`app.py:1081` | `if sample_check.severity == "warn":` → `st.warning` | 黄灯提示，不阻断。⚠ 该函数**只产 `warn`/`info` 两态、无 `block` 分支**（`:224`／`:232`／`:237`），故 app 侧无吞态 |
| `check_multiple_comparisons` | `:240` | `app.py:42`、`app.py:1086` | `st.error` + 双按钮：「🔄 切换为 …」／「▶️ 仍然运行（我了解风险）」，二者皆未点 → **`st.stop()`（`app.py:1107`）** | **硬阻断，带人工放行出口** |
| `check_effect_size_present` | `:275` | **零处**（全仓唯一其它命中是 `docs/insights/psy-test-blindspot-audit-20260915.json:2226` 的在册符号清单，非代码） | 无 | 不产任何效果 |

复算命令（可逐条重放）：

```
cd D:/code/psy-analysis
for e in check_variable_type_match check_sample_size check_multiple_comparisons check_effect_size_present; do
  rg --no-ignore -n "$e" --glob '!node_modules/**' --glob '!tmp/**' . ; done
```

### 1.2 在途件 `app.py` 的对照（按卷宗「只 rg 引用形态、不读正文」执行）

- 工作树版：`app.py` size=130,298 B，mtime=**2026-09-26 11:47:36**（本班未读正文、未改；只用 `rg` 取引用行与缩进骨架）。
- HEAD 版对照：`git show HEAD:app.py` → 2433 行（工作树 2405 行），同一批引用**逐条在世**，行号为 `:41-43` / `:1097` / `:1109` / `:1114`，消费形态（`st.error` / `st.warning` / `st.stop` / 双按钮）与工作树**同形**。
- 在途 diff 是否动了接线：`git diff -U0 -- app.py | rg "guardrail|check_sample_size|check_multiple_comparisons|check_variable_type_match|type_check|sample_check|multi_check"` → **rc=1（零命中）**。在途改动量 `52 ++++---- / 12 insertions(+), 40 deletions(-)`，**不触碰本议题**。
⇒ 本档关于 app.py 的结论**HEAD 与工作树同时成立**，不依赖任何在途正文。

### 1.3 门的位置与绕过面（影响面的真实形状）

三门全部嵌在：`app.py:738 if mode == "📈 数据分析":` → `:1050 if analyze_btn and st.session_state.df is not None and request.strip():` → `:1126 output = run_analysis(...)` **之前**。即：只闸 **Streamlit 主分析按钮这一条路**。

`run_analysis` 的其它调用点**一个护栏都没有**（`rg --no-ignore -n "run_analysis\(" src/ scripts/ app.py`）：

| 入口 | 位置 | 护栏 |
|---|---|---|
| UI 主分析按钮 | `app.py:1126` | 3 道（本文 1.1） |
| 快速入口 | `src/ui/quick_entries.py:693` | 0 |
| 新手引导 | `src/ui/onboarding.py:212` | 0 |
| 本科向导 ×2 | `src/ui/undergrad_wizard.py:1939`、`:3023` | 0 |
| 流水线管理器 | `src/utils/pipeline_manager.py:105` | 0 |
| 性能冒烟脚本 | `scripts/perf_smoke.py:120/141/164` | 0（脚本，本不该闸） |

两处额外的 fail-open 方向（只报读数，不判对错）：
1. 变量类型门整体在 `app.py:1059 if st.session_state.inspector:` 之内 ⇒ **无 inspector（未做列类型推断）时该门整段跳过**。
2. 多重比较门要求 `analysis_history` 非空且「最近 10 条里同类 ≥3 且 DV 重叠 ≤3」（`guardrails.py:246-258`）⇒ 白名单只有 `independent_ttest`／`mann_whitney`，与 `docs/insights/s927-03-star-caliber.md:74` 的在册口径一致（该档已独立复读确认，本班不重查）。

### 1.4 测试面（决定「接线」的爆炸半径）

- `rg --no-ignore -n "check_variable_type_match|check_sample_size|check_multiple_comparisons|check_effect_size_present" tests/` → **零命中** ⇒ 三道在世阻断门**无任何直接单测在册**；间接面只有 `tests/test_e2e_rendering.py`（`AppTest.from_file("app.py")`，11 处）会经过这段代码，但它是否驱动「数据分析」分支＋analyze 按钮，本班未逐例核。
- 直连 `run_analysis` 的测试件 **8 枚**（`tests/test_analysis_result_schema.py`、`test_golden_path_e2e.py`、`test_golden_delivery.py`、`test_golden_research_flow.py`、`test_post_hoc_power.py`、`test_robustness.py`、`test_template_golden_flows.py`、`test_two_way_anova_route.py`）⇒ **若在 runner 层新增阻断，这就是首波受冲击清单**。
- ⚠ 基线形态（硬交底①，避免误引）：**本仓没有 `--freeze`**（`git grep -in freeze -- '*.py'` 零命中；`conftest.py:57` 唯一 addoption 是 `--run-benchmark`；`pytest.ini` 的 `addopts = --strict-markers`，工作树版）。⇒ 所谓「重钉基线」在本仓的真实形态是**改硬编码全等快照／期望数据**，属人工闸。

---

## 2 三案矩阵（判据②）

三案按卷宗命名：A＝接线／补线；B＝维持现状；C＝删除。**逐护栏分别裁**，因为它们事实状态不同。

| 案 | 最小改动面 | 运行时冲击 | 回滚成本 | 复算入口 | 红线归属 |
|---|---|---|---|---|---|
| **A 接线**（把 4 道下沉到 `runner.run_analysis` 层，覆盖 1.3 的 6 个入口） | 改 `src/analysis/runner.py:867` 前置段（被跟踪文件） | **新增阻断**：非 UI 入口（快速入口／新手向导／本科向导／流水线）从「能出结果」变「可能被停」；`tests/` 8 枚直连件首波受冲击；无 `--freeze` ⇒ 快照／期望数据要人工逐枚复核 | 中：改一处即回退，但已发布的用户结果卡可能已含被阻断过的分析 | 上述 8 枚测试＋`-m "not online"` 定向跑（⚠ 硬交底④：`tests/test_paper_writer.py::TestLiteratureManager::test_online_search_graceful` 无 `online` 标记，禁联网口径会**静默外呼 CrossRef**，须跳过） | **统计判定域**：阻断阈值／效应量缺失即失败＝口径决策 ⇒ 人工裁 |
| **B 维持现状**（UI 三道继续跑，`check_effect_size_present` 继续零调用） | **零改** | 零 | 零 | 现状可复算：本文 1.1 命令 | 现状本身有缺口（1.3 的 6 个入口无门、`inspector` 前置 fail-open），是否接受需人认 |
| **C 删除未接线件** | 删 `guardrails.py:275-323`（**只能删这一道**） | 零运行时变化（真死码）；但 `psy-test-blindspot-audit-20260915.json` 的在册符号清单会失配，该清单自身被当判据使用 ⇒ 需同步（见 1.4 坑：普查档自命中数会漂） | 低（git revert） | `rg --no-ignore -c "check_effect_size_present"` 前后对照 | 无（不涉及数值） |

**对三道在世护栏（148/199/240）**：C 案**不成立**——删了会直接砍掉 UI 主路径上正在生效的两个 `st.stop()` 阻断与一个黄灯。
**对 `check_effect_size_present`（275）**：A 案当前实现有**双向失真**证据（见 2.1），故 A 的前置是先改判据；否则先 B/C。

### 2.1 A 案（接线效应量护栏）的既有失真读数——只报读数，不下判定

函数契约（`guardrails.py:275-323`）：`output.get("result")` 上 `getattr` 九个字段名（`effect_size`/`eta_squared`/`partial_eta_squared`/`cohens_d`/`hedges_g`/`cramers_v`/`omega_squared`/`r_squared`/`adj_r_squared`），再回落查 `output` 字典三键，皆无 → `severity="block"`；`test_type == "descriptive"` 豁免。

- **假阻断面（偏大）**：`src/analysis/` 32 个模块里 **8 个产出结果对象但全文无 `effect_size` 字样** ⇒ 这些方法族在接线后会落进 block 分支：
  `sem.py`、`cfa.py`、`hlm.py`、`manova.py`、`logistic_regression.py`、`reliability.py`、`factor_analysis.py`、`descriptive.py`。
  其中 `cfa.py` 是在途件，已按 HEAD 对照：`git show HEAD:src/analysis/cfa.py | rg -c "effect_size"` → **0**，与工作树同（`__init__.py` 亦 0；`result_card.py` 56 命中，无关本结论）。
  ⇒ 对照 `runner.py` 注册表 **48 个 test_type**（`rg -o "@_register\(\"[a-z_]+\""`），**至少 SEM／CFA／HLM／MANOVA／logistic／信度族／探索性因子族在册方法会受伤**；逐方法精确归属需一次端到端探针（涉效应量口径，本班**未跑**，见遗留 2）。
- **假放行面（偏小）**：判据是 `is not None` ⇒ `effect_size = nan` 视为「存在」。锚点 `20260925-154314-4290` 验收表 D 段实测过独立 t 的 `Cohen's d = nan`（退化组 n=1）⇒ 该形态下护栏会**放行**。「nan 算不算报告了效应量」是统计口径题，交人裁。
- 豁免只按 `test_type == "descriptive"` 字面量比对；`test_type` 由 `output.get("test_type","")` 取，而 `AnalysisResult`（`src/analysis/contracts.py:11`，dict 子类）另有 `canonical_method_id` 属性（`:27-29`）⇒ 双口径下豁免名单是否漏方法，需人认。

---

## 3 推荐（判据③；材料排序，不是裁决）

按「改动面 ÷ 收益」排序，**最终选择交主班／人工闸**：

1. **先修事实档**：把「四道护栏零调用」这条在册表述改窄为「**三道在 app.py UI 层在世接线并阻断，`check_effect_size_present` 零调用**」。这是纯文档订正、零码风险，且能防止后续班次照抄锚点做无效裁决。（涉及的在册表述：`20260925-154313-ae49` 摘要④／E3／遗留 1，`20260925-154314-4290` E3。）
2. **A 案降级为「入口对齐」而非「下沉 runner」**：把 UI 主路径已有的三道门以**同一函数调用**补进 `src/ui/quick_entries.py:693`、`onboarding.py:212`、`undergrad_wizard.py:1939/3023`、`pipeline_manager.py:105`。收益＝消除「换入口即无门」的不对称；代价＝四个 UI 件的行为变化＋各自测试。**比在 runner 造全局阻断的回滚成本低**，且不触碰 2.1 的效应量失真。
3. **`check_effect_size_present` 单独立项，暂不接线也不删**：它的阻断语义要求「哪些方法必须有效应量」这张表先存在（2.1 假阻断面覆盖 ≥7 个方法族），而这张表属统计口径 ⇒ 红线。删除案（C）风险最低但会永久埋掉 APA7 这条在册需求，建议**保留源码＋在档里明写「未接线，勿当护栏引用」**。
4. **顺手但要人点头的一条**：`app.py:1059` 的 `if st.session_state.inspector:` 前置会让变量类型门在无列类型推断时整段跳过。把该前提是否成立写进裁决即可，**本班未改**。

---

## 4 零码改动自证（判据④）

- 本班对 psy-analysis 工作树**只读**：无 `add`/`commit`/`checkout`/`restore`/`stash`/`clean`；未改任何被跟踪文件（含在途 `app.py`／`pytest.ini`／`src/**`）。
- 探针与 HEAD 对照件只落沙盒 `D:\code\tmp\qoder-executor-20260927-1940-psy79\`（仓根零残留）。
- `data/` 零写自证（整层 gitignore，无还原点）：跑前指纹 `find data -type f -printf '%p %s\n'` → **187 文件／21,103,172 B**（与在册基线逐字符相符），跑后同命令复点见 result「证据」节。
- 本班**未跑 pytest**（三案矩阵全部由 `rg`／`git show`／`git diff` 静态取证闭合），故不涉及硬交底④的 CrossRef 静默外呼风险，也未撞在册红 `test_export_gate_global_scan::test_all_download_buttons_accounted_for`（未跑任何测试 ⇒ 该件既未复跑也未归因）。

---

## 5 交人工／遗留

1. 三案选择（尤其 2.1 的两项统计口径：哪些方法必须有效应量、`nan` 是否算存在）＝**统计判定域，本班不签**。
2. 精确「方法 × 效应量字段」映射需一次端到端探针（`run_analysis` 直调，构造 48 test_type 用例）＝**涉统计数值 ⇒ 只出材料，需另派带人工裁的班**；本班按静态字段扫描给出下界（≥7 方法族）。
3. 全量套件读数缺位：并发窗（同刻 kaoyan79／colony42／quant50 在他仓）禁跑全量，收班由主班统一取数并附时刻与 HEAD。
4. 锚点路径搬家（`outbox/` → `done/`）本班复核为真：两张锚点在 `outbox/` 命中 0 枚、在 `done/` 均在世（`20260925-154313-ae49.result.md` 16,322 B／`20260925-154314-4290.result.md` 16,793 B），按 brief §3a 用 `done/` 版，非缺陷。
