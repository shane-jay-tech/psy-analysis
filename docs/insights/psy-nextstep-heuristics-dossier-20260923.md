# psy next_step 引擎三反直觉判据裁决材料（s923-31，只读）

- 班次：`qoder-executor-20260923-0022-psy15` ／ 班日 2026-09-23（开工 17:08 claims 行）
- 被试件：`src/utils/next_step_engine.py`（392 行，纯 LF，**本单零改动**）
- 性质：**只读裁决材料**。未改引擎、未改测试、未启动 app、未跑 `AppTest`（故 `data/literature_feed` 三件不在风险面内，收工仍复核 sha8）。
- 探针：`tmp/s923-31/probe.py`（gitignored，`git check-ignore -v` → `.gitignore:29:tmp/`）；读数 `tmp/s923-31/probe.out`

## 0. 结论先行

1. **三判据现状行为已逐个复算并列表**（表 A）。卷宗点名的三条形态全部为真，且**各再往外扩了一格**：
   - `analysis_recipe` 只判 `is not None` ⇒ 不止空 dict `{}`，连 `False`／`0`／`""` 这类**假值非 None** 也算"已推荐方法"。
   - `paper_bundle` 的 `else: has_paper = True` ⇒ 不止"无 `.sections` 的对象"，连 `"draft"` 字符串、`0`、`False` 都算"有论文草稿"。
   - `consistency_issues` 非 list ⇒ 一律未通过，**空 tuple `()` 也在此列**（语义上是"跑过检查、零问题"却被判未通过）。
2. **三条在 UI 上都能造成可见错提示**——前提是"全链齐活"。app 唯一消费口是 `app.py:300-301 → next_step_panel.py:14` 的 **`max_steps=1`**，只渲染最上一条；`method_recommended`/`paper_draft` 的假值在链路前段会被 rule 3 遮蔽，在 S10/S11 全链场景下差分当场现形（表 C）。
3. 🔴 **对卷宗定性的否证（本材料最重要一条）**：卷宗按"前两条会影响 UI 提示正确性、第三条只是静默"的次序排风险，**盘上实况相反**——
   - `analysis_recipe` 有唯一生产写方（`src/ui/method_recommender_panel.py:194`，写的是 `AnalysisRecipe` dataclass 实例，**永不为 `{}`**）⇒ H1 目前是**潜伏**风险。
   - `paper_bundle` 这个**会话键全仓零生产写方**（只有 `tests/test_e2e_resultcard_paperpreview.py:46` 等测试写）⇒ H2 目前是**不可达**风险；连带后果是 `paper_draft` 在生产恒 False。
   - `consistency_issues` 同样**零生产写方**，而 `deliverable_center_panel.py:155` 已经算出了 `check_consistency(bundle)` 的结果**却就地丢弃、不回写会话态** ⇒ `consistency_passed` 在生产**永久 False**，rule 10 `export_deliverable` 与 rule 11 `final_review` 的"一致性通过"路径**在生产不可达**：用户即使在交付中心跑完一致性检查且零 ERROR，面板仍会**永远提示"运行一致性检查"**、永不提示"导出交付包"。这条**已经在发生**，且不是"非 list 静默"那个形态。
4. **修复建议**：H3 走"回写一行"路线（属行为改动，要授权，见 §5 方案 C）；H1/H2 属"收紧判据"，两条都**只需改引擎两处、且对生产真实对象零误判**（表 D），代价是必须**同笔翻正两条钉桩**（§6）。任一单独改都不如两笔一起改干净。

## 1. 前置复核：锚点与前提逐条（含否证）

```
$ cd /d/code/psy-analysis && rg -n "analysis_recipe|paper_bundle|consistency_issues" src/utils/next_step_engine.py
$ git log --oneline -1 && git status --porcelain | python -c "import sys;print(len([l for l in sys.stdin.read().splitlines() if l.strip()]))"
```

| 卷宗前提 | 盘上实况 | 判定 |
|---|---|---|
| `src/utils/next_step_engine.py:74` `recipe = session_state.get("analysis_recipe")` | 实测 :74 逐字一致（判据写在 :75 `bool(recs) or recipe is not None`） | ✅ 成立 |
| `tests/test_next_step_engine_core.py` 注释写 `:75`／`:102 else`／`:131-132` | 实测 :75、:102、:131-132 三个锚点均未漂移 | ✅ 成立 |
| 「`analysis_recipe={}` 空字典即算已推荐」 | 实测 True；且 `False`/`0`/`""` 同为 True | ✅ 成立＋扩 |
| 「`paper_bundle` 任意非 dict 无 `.sections` 即算有草稿」 | 实测 True；且 `"draft"`/`0`/`False` 同为 True（`0`/`False` 走 `AttributeError→非 dict→True`） | ✅ 成立＋扩 |
| 「`consistency_issues` 非 list 时静默判未通过」 | 实测 `"weird"`/`{}`/`()`/generator 全 False | ✅ 成立＋扩（空 tuple 最阴险） |
| 「前两条属推荐漏项/虚高…**会影响 UI 提示正确性**」（隐含第三条不影响） | 前两条的触发形态在生产**当前不可达/潜伏**，第三条的**缺键形态已在生产常开** | 🔴 **否证：风险次序要反过来**，见 §0.3 |
| s922-119 「三处只钉不改」 | 三处现状确实各有一条断言钉着（`:184`、`:193`、`:213`），无第四处 | ✅ 成立 |

附带核掉的两条"疑似缺口"（**都不是缺口**，省得后人重查）：

```
$ python -c "print(open('src/utils/next_step_engine.py',encoding='utf-8',newline='').read().count(chr(13)+chr(10)))"
0
$ rg -n "page_target=" src/utils/next_step_engine.py | rg -o "数据分析|文献与选题|论文写作|交付包导出" | sort | uniq -c
      5 数据分析      3 交付包导出      2 论文写作      1 文献与选题      # 4 个目标页全在 PAGE_MODES 内
```
引擎用到的 4 个 `page_target` 全在 `src/ui/navigation.py:6-14 PAGE_MODES` 内 ⇒ `next_step_panel.py:18` 的"路由不存在就整块不渲染"这条静默出口**当前不会命中**。

⚠️ 另记一条不在本单范围的观察（**未坐实为缺陷、也未动手**）：`app.py:299-303` 用裸 `except Exception: pass` 包住整个面板渲染，面板内任何异常都会静默消失。`app.py` 是他班在途件（` M`，numstat `12/40`），本班不碰，只登记。

## 2. 表 A：三判据 × 输入形态现状读数

复算命令（探针全文在 `tmp/s923-31/probe.py`，`rc=0`、只读、无文件写入）：

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-31/probe.py > tmp/s923-31/probe.out 2>&1; echo RC=$?
RC=0
$ rg -n '^\$ probe' tmp/s923-31/probe.out | head -3        # 单引号必须有：双引号里 \$ 会被 bash 吃成 $ ⇒ rg 当成行尾锚点，0 命中＝假"表是编的"
2:$ probe  method_recommended   analysis_recipe=空 dict {}（卷宗点名）                    -> True
3:$ probe  method_recommended   analysis_recipe=非空 dict                            -> True
4:$ probe  method_recommended   analysis_recipe=None / 缺键                          -> False
```

| 判据（资产） | 输入形态（只放该键，其余缺省） | 现状读数 |
|---|---|---|
| `method_recommended` ← `analysis_recipe` | `{}` 空 dict（卷宗点名） | **True** |
| | `{"method_id": "pearson"}` | True |
| | `None` / 键缺失 | False |
| | `False` / `0` / `""`（假值非 None，三例同读数） | **True / True / True** |
| | `AnalysisRecipe` 实例（生产唯一真实写入形态） | True |
| `method_recommended` ← `method_recommendations` | `[]` 空 list | False |
| `paper_draft` ← `paper_bundle` | `object()` 无 sections（卷宗点名） | **True** |
| | `PaperDraftBundle(sections={})` 替身：空 dataclass | False |
| | `Bundle({"intro": "x"})` 有章节 | True |
| | `{"title": "T"}` dict 无 sections | False |
| | `{"sections": []}` | False |
| | `"draft"` 裸字符串 / `0` / `False` | **True / True / True** |
| | `None` | False |
| `consistency_passed` ← `consistency_issues` | 键缺失（**生产常开形态**） | **False** |
| | `None` | False |
| | `[]` | True |
| | `[{"level": "ERROR"}]` | False |
| | `"weird"` 非 list（卷宗点名） | **False** |
| | `()` 空 tuple（"跑过且无问题"的 tuple 形态） | **False** ← 语义翻转，最阴险 |
| | `{}` 空 dict / `(i for i in ())` generator | False / False |

三条判据的**共同根因**：都用"存在性"代替"有效性"。`is not None` 与 `else: True` 是两种不同方向的偷懒——前者把假值读成真，后者把"结构不认识"读成"有内容"。第三条则相反，是"结构不认识 ⇒ 保守判未通过"，但它保守得**无出口**：没有任何日志或提示说明"我看不懂这个值"。

## 3. 表 B：现状 UI 读数（app 唯一消费口 `max_steps=1`）

链路：`app.py:300-301` → `src/ui/next_step_panel.py:14 recommend_next_steps(st.session_state, max_steps=1)` → 只渲染 `steps[0]`。
⇒ **任何被 rule 3（priority 1、定义序最前）占住的场景，都看不到后两条判据造成的错提示**；这解释了为什么 H2/H3 的可见面比 H1 隐蔽。

| 场景 | method_recommended / paper_draft / consistency_passed | 面板现状显示（max_steps=1） | max_steps=3 序列 |
|---|---|---|---|
| S1 数据+变量齐，`analysis_recipe={}` | True / False / False | **run_analysis「执行统计分析」** | run_analysis, collect_evidence |
| S2 同上但 recipe 为生产 dataclass | True / False / False | run_analysis「执行统计分析」 | run_analysis, collect_evidence |
| S3 数据+变量齐，recipe 缺键 | False / False / False | get_method_recommendation「获取方法推荐」 | get_method_recommendation, collect_evidence |
| S4 卡片+证据齐，`paper_bundle=object()` | False / **True** / False | get_method_recommendation | …, **consistency_check** |
| S5 同 S4 但 bundle 空章节 dataclass | False / False / False | get_method_recommendation | …, write_paper |
| S6 真草稿 + `consistency_issues="weird"` | False / True / False | get_method_recommendation | …, consistency_check |
| S7 真草稿 + `consistency_issues=()` | False / True / False | get_method_recommendation | …, consistency_check |
| S8 真草稿 + `consistency_issues=[]` | False / True / **True** | get_method_recommendation | …, **export_deliverable** |
| S9 **生产现状**（bundle 键永不写） | False / False / False | get_method_recommendation | …, write_paper |
| S10 全链齐活 + 垃圾 `paper_bundle=object()` | True / **True** / False | **consistency_check「运行一致性检查」** | consistency_check |
| S11 全链齐活 + 真草稿 + `consistency_issues=()` | True / True / **False** | **consistency_check** | consistency_check |
| S12 全链齐活 + 真草稿 + `consistency_issues=[]` | True / True / True | export_deliverable「导出交付包」 | export_deliverable |

读数要点：
- **S1 vs S3 是 H1 的 UI 实害**：用户从没点过"使用此方法分析"，但只要会话里有个空 dict 占位，面板就把"获取方法推荐"换成"执行统计分析"——**跳过前置步骤的直接后果是用户在没有方法方案的情况下被推向分析页**。
- **S10 是 H2 的 UI 实害**：垃圾对象冒充草稿 ⇒ 面板不再说"开始撰写论文"而说"运行一致性检查"（页内跳转目标 `📦 交付包导出`），把用户一路带到交付中心去检查一篇不存在的论文。
- **S11 vs S12 是 H3 的 UI 实害**：同样"零问题"的两种容器写法，得到"催你重跑检查"与"可以导出了"两种相反提示。
- **S9 是生产常开态**：`paper_draft` 恒 False ⇒ 面板恒停在"获取方法推荐/开始撰写论文"这一档，H2/H3 在 `max_steps=1` 上"看起来没事"只是因为触发面根本走不到。

## 4. 生产可达性判定（谁写这三个会话键）

```
$ rg -n "session_state\[_RECIPE_KEY\]\s*=" src/ app.py
src/ui\method_recommender_panel.py:194:        session_state[_RECIPE_KEY] = recipe   # recipe = recommendation_to_recipe(...)，AnalysisRecipe 实例
$ rg -c "PAPER_BUNDLE_KEY" --glob '!node_modules/**' --glob '!.venv/**' .
.\app.py:2  .\src\ui\{export_gate.py:4, deliverable_center_panel.py:2, session_reset.py:2, state_keys.py:1}
.\tests\{test_app_routes_v6_panels.py:2, test_deliverable_center_panel.py:2, test_export_gate_global_scan.py:1, test_ui_golden_research_flow.py:7}
.\docs\insights\psy-nextstep-heuristics-dossier-20260923.md:3          # ← 本档自己，非证据
                                                            # src/app 共 11 处：全是 .get()/import/常量定义/重置名单，零赋值
$ rg -n "session_state\[\d*['\"]consistency_issues['\"]\]\s*=|\"consistency_issues\"\]\s*=" --glob '!node_modules/**' --glob '!.venv/**' --glob '!docs/insights/**' .
.\tests\test_readiness_scorer.py:108:        ss["consistency_issues"] = [FakeIssue()]   # 唯一赋值点，在 tests/
        # ⚠️ 不加 '!docs/insights/**' 会额外命中本档正文自身（2 处）＝§廿五 点名的"不排除本件 ⇒ 假阳"同型
$ rg -n "consistency_issues" --glob '!node_modules/**' --glob '!.venv/**' src app.py
src\ui\deliverable_center_panel.py:155:    consistency_issues = check_consistency(bundle)   # 局部量，无回写会话态
src\ui\session_reset.py:77:    "consistency_issues",                                          # 只在重置名单里
src\utils\readiness_scorer.py:248:    issues = ss.get("consistency_issues", [])               # 第二口径：缺键当 [] ⇒ 判"0 条警告/good"
```

| 键 | 生产写方 | 生产可达形态 | 判据风险等级 |
|---|---|---|---|
| `analysis_recipe` | 1 处（`method_recommender_panel.py:194`），写 `AnalysisRecipe` 实例 | 永不为 `{}`/`False`/`0` | **潜伏**（将来若有人改存 `to_dict()` 的部分字段、或写入"重置为 `{}`"，当场生效） |
| `paper_bundle` | **0**（键常量 `state_keys.py:20` 存在，但 src/app 只读不写） | 恒缺失 ⇒ `paper_draft` 恒 False | **不可达**（H2 是"给未来的写方准备的坑"） |
| `consistency_issues` | **0**（`deliverable_center_panel.py:155` 算完即弃） | 恒缺失 ⇒ `consistency_passed` 恒 False | **常开**（已造成 §0.3 的永久"运行一致性检查"死循环） |

同源第二坑（**口径漂移，非本单范围**）：同一个 `consistency_issues` 键，`readiness_scorer._score_consistency` 用 `ss.get(..., [])` 再 `if issues is None`（`:249`）——默认值已是 `[]`，那条 `None` 分支在缺键时**永不可达**，于是缺键在评分侧得 `score=100/status=good "0 条警告"`，在推荐侧得"未通过"。**一处判"通过"、一处判"未通过"，两头都是现状**。
（`readiness_scorer.py:227-241` 的 `paper_bundle` 又是第三种口径 `if paper:` 真值判断——对 `PaperDraftBundle(sections={})` 判"论文草稿已生成 score=100"，而引擎判 False。`feedback_logger.py:133` 用 `is not None`，`result_card_panel.py:144-146` 用 `is None` 后直接 `bundle.sections.get(...)`。⇒ **同一资产四种口径**，属另一单范围，此处只登记。）

## 5. 收紧方案（三案，全部只到"建议"，本单未实施）

### 方案 A（推荐，H1+H2 一处一行）
```
H1' :  state["method_recommended"] = bool(recs) or bool(recipe)
H2' :  sections = paper_bundle.get("sections") if isinstance(paper_bundle, dict) else getattr(paper_bundle, "sections", None)
       state["paper_draft"] = bool(sections)
```
- 安全性已由表 D 逐项验证：**生产真实对象读数不变**（`AnalysisRecipe` 实例、有章节的 Bundle 均保持 True）⇒ 纯收紧，不动正常路径。
- 判别力：12 场景里 3 处 top-1 差分（S1/S10，见 §0.2）。
- ⚠️ H2' 的写法要保证"有 `.sections` 属性但值是空 dict"仍判 False（现状如此，别顺手改成 `hasattr` 判存在）。

### 方案 B（H3，最小改动：只让"看不懂"可见）
把 `else: state["consistency_passed"] = False` 前加一行 `warnings.warn`／`logger.warning("consistency_issues 类型异常: %s", type(...))`，**判据不变**。零行为风险、零测试翻正，只消掉"静默"这一半。

### 方案 C（H3 的真实病灶，属行为改动 ⇒ 必须另单授权）
在 `src/ui/deliverable_center_panel.py:155` 之后回写 `st.session_state["consistency_issues"] = consistency_issues`（`docs/insights/psy-dualentry-instrumentation-design-20260922.md:155` 早已把这行点名为"零新语义、只补死链"的候选接线）。
- 收益：解开"永远提示运行一致性检查、永不提示导出"的死循环。
- 连带面（**要主班裁决**）：① 回写后 `paper_draft` 恒 False 会让 rule 9 依旧不触发（需与 §4 的 `paper_bundle` 写方问题一起看）；② `readiness_scorer._score_consistency` 与 `professional_consistency` 会同时开始消费这份真实数据 ⇒ **就绪分数会变**，这属"计分口径"，不属"UI 提示"；③ 一旦回写，`check_consistency` 的返回若是 list 则 H3 判据正常，非 list 形态仍不可达。
- 🔴 本班**未做**：它同时改 UI 提示与就绪评分，超出"只读裁决材料"授权。

### 不建议
把 `is not None` 改成 `bool(...)` 却**不同笔翻正钉桩**（会当场 2 红）；或往 `consistency_issues` 塞 `[]` 作默认值来"消除"第三条（那是用假数据骗过判据，会把"未跑检查"和"跑了且零问题"两个语义并成一个）。

## 6. 需同步翻正的用例清单（两笔一体配对）

| 收紧项 | 必红用例 | 断言位置 | 翻正方向 |
|---|---|---|---|
| H1' | `test_method_recommended_quirk_empty_recipe_still_counts` | `tests/test_next_step_engine_core.py:184-185` | `{"analysis_recipe": {}}` 期望 `is True` → `is False`；用例名里的 "quirk" 要一起改（名实在说反话） |
| H2' | `test_paper_draft_three_bundle_shapes` | `tests/test_next_step_engine_core.py:193-194` | `{"paper_bundle": object()}` 期望 `is True` → `is False`，并删掉 `"钉住现状"` 尾注；建议补 `"0"/False/裸 str` 三例（本材料表 A 已给读数） |
| H3'（仅当归一 tuple 时才需要） | `test_consistency_passed_levels` | `tests/test_next_step_engine_core.py:213-214` | 若把 `isinstance(..., list)` 放宽为 `(list, tuple)`，则 `"weird"` 那条仍 False、但需新增 `()` → True 的断言；**走方案 B（只加告警）则本用例不必动** |

⇒ 卷宗说"需同步翻正的**两**用例名"：按"只收 H1/H2"的方案 A 成立（前两行）。若 H3 走 tuple 归一则实为**三**处，本材料按实况标出，别让后人以为卷宗漏计。
```
$ rg -n "钉住现状|改判据前先改码|非 list 一律未通过" tests/test_next_step_engine_core.py
```
三句尾注都在源码里指回引擎行号（`:75`、`:102`、`:131-132`），**改引擎后这三句注释也会同时失真** ⇒ 翻正时要连注释一起改，否则留下"按行号指向已不存在代码"的误导锚点。

另需知会（**不构成阻塞**）：`tests/test_next_step_engine_core.py:361-364 test_engine_source_mentions_no_streamlit` 读引擎**源码全文**并断言 `"streamlit" not in src`。收紧方案 A/B 都不引入 streamlit，安全；但若有人日后想"在引擎里加 st.toast 提示类型异常"，会同时踩这条。

## 7. 复算命令汇总（全部本班真跑过）

```
$ cd /d/code/psy-analysis && git check-ignore -v tmp/probe.py                     # .gitignore:29:tmp/ → 探针落 tmp/ 不脏工作树
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-31/probe.py > tmp/s923-31/probe.out 2>&1; echo RC=$?     # RC=0
$ rg -n "自检|差分场景数" tmp/s923-31/probe.out                                   # 自检 通过（12 场景 ×2 档，mismatch=0）／差分场景数 = 3/12
$ rg -n "analysis_recipe|paper_bundle|consistency_issues" src/utils/next_step_engine.py
$ rg -n "PAPER_BUNDLE_KEY" --glob '!node_modules/**' --glob '!.venv/**' .
$ rg -n "consistency_issues" --glob '!node_modules/**' --glob '!.venv/**' .
$ git diff --numstat src/utils/next_step_engine.py tests/test_next_step_engine_core.py   # 空输出 = 两件零改动
$ git diff --cached --numstat                                                            # 空 = 未夹带任何暂存
```

**探针判别力自证**（防"探针自己坏了却打出像样的表"）：`_select()` 是本探针复刻的引擎选择器，跑真 `recommend_next_steps` 之前先对 12 场景 ×2 档（`max_steps=1/3`）逐位比对，`mismatch=0` 才继续；不一致则 `sys.exit(9)` 拒绝出表。
另附一条被这条纪律救回来的实现坑：`print("$ evaluate_project_state({}) ...")` 写成 f-string 时 `{}` 会被当空替换域，当场 `SyntaxError`——第一版探针就是这么死的，改普通字符串后才 rc=0。**整行变异先验语法**这条在 print 面上同样成立。

## 8. 未坐实 / 遗留

1. `paper_bundle`「零生产写方」的结论建立在 **rg 字面匹配键名与 `PAPER_BUNDLE_KEY` 常量**上。若存在经由 `st.session_state.update(**payload)` 之类**动态键展开**写入，本次扫描看不到 ⇒ 未坐实为"绝对零写方"，只坐实为"未发现写方"。
2. 方案 C 对就绪评分的具体分差**未量化**（`readiness_scorer` 的 8 维权重不在本单范围）。
3. `AnalysisRecipe` 若日后改存 `recipe.to_dict()`（`src/analysis/method_recommender.py:408`），H1 从"潜伏"直接转"常开"——`to_dict()` 在非空 dict 上真值判断仍 True，但**空 dict 分支会变成日常可达**。建议把它作为 H1' 收紧的动因写进裁决语。
4. 同一资产四口径（引擎／`readiness_scorer:227`／`feedback_logger:133`／`result_card_panel:144`）只登记，未展开成表——超出本单"三判据"范围。
