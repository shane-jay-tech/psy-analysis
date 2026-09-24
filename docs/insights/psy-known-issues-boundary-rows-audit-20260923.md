# psy KNOWN_ISSUES「已知功能边界」表逐行核销取证（2026-09-24 执行，单号 s923-43）

- 取证对象：`KNOWN_ISSUES.md:115-126` 的「已知功能边界」表（**10 行**）
- 本单面：**除 MANOVA / ICC 两行外的 8 行**（那两行由 `tests/test_result_card_registry_snapshot.py:150` 与 `:158` 双向锁住，
  卷宗与派单都点名除外，本文只登记其锁位、**不做判定**）
- 性质：**只读取证报告**。未改 `KNOWN_ISSUES.md` 正文、未改任何生产码、未写库、未放宽任何断言。
- 执行环境：`D:\code\psy-analysis`，HEAD 现取 `29d8ce0`（`.venv` 解释器，sklearn 1.5.2）
- 文件名字段写 20260923 是卷宗第 25 行指定的产出路径；实际执行日为 2026-09-24，**以本文内文日期为准**。

---

## 一、结论速览（10 行三列表）

判定口径：**已消解未销**＝文档说的限制代码里已经没有了，但行还挂着（该删行）；
**仍成立**＝限制确实存在（可含"比文档写得更严重"），行该留；
**表述需订正**＝限制存在与否不是重点，**这一行的文字与代码对不上**（数字/举例/归因错了）。

| # | 原文行（`KNOWN_ISSUES.md`） | 代码证据（含行号） | 判定 |
|---|---|---|---|
| 1 | :117 `\| Logistic 系列细分不完整 \| 二元/有序/多项 Logistic 解释有限 \| 标记为"高级方法"，使用基础卡片 \|` | `src/analysis/runner.py:311`（`@_register("ordinal_logistic")`）、`:323`（`@_register("multinomial_logistic")`）；`src/analysis/result_card.py:706` 定义 `_build_logistic_regression`、`:1378`/`:1379` 仅注册 `logistic_regression`/`binary_logistic` 两键（**有序/多项无专用键**）；`src/analysis/method_catalog.py:70-71` 把 ordinal/multinomial 的 `card` 别名指向 `logistic_regression`（＝"使用基础卡片"在册面上成立）；但端到端实测三变体**卡构建全部抛异常**（详见第二节），`app.py:1463-1467` 用 `except Exception: pass` 吞掉 | **仍成立（现状劣于文档描述：不是"解释有限"，是结果卡对整个 Logistic 族实际不渲染）** ⇒ **不可核销** |
| 2 | :120 `\| 部分 advanced 方法无 APA 表格 \| 中介/SEM 等需手动排版 \| 结果卡片仍可用 \|` | 路由实现 `src/output/apa_tables.py:763` `generate_tables_from_card`，`:768` 用 `resolve_method_id` 取 **canonical id** 后在 `:772-873` 的分支里逐个比元组；`:860-863` mediation **有**分支、`:847-855` `("cfa","sem")` **有**分支 ⇒ 本行举的两个例子**恰好都是有自动表的**；真正 `table_group=None` 的 advanced 只有 4 个：`method_catalog.py:47`(partial_corr) `:57`(ancova) `:84`(ave_cr) `:85`(discriminant_validity) | **表述需订正**（命题"部分 advanced 无表"成立，但举例与代码相反；且 `src/utils/method_exposure.py:5-6` 用 `table_group` 判"缺 APA 表格路由"，与 `apa_tables.py` 的实际分派**不同源**，见第五节新发现） |
| 3 | :121 `\| 无 Mac/Linux 支持 \| 仅限 Windows 用户 \| 未来版本计划 \|` | Windows 专属实测四处：`src/visualization/fonts.py:14`（`os.environ["WINDIR"]`）、`src/utils/env_check.py:235`、`src/output/pdf_exporter.py:62` 与 `:96-97`（Word COM，非 nt 直接 `error="非 Windows 环境"`）、`README.md:19`（桌面模式依赖 WebView2，Windows 10/11 自带）；**但** `src/utils/instance_lock.py:48-51` 明确写了 POSIX 分支（`if os.name != "nt": os.kill(pid,0)`），`src/literature_feed/ui/feed_panel.py:594` 也是 win/POSIX 双路；核心统计链路（`src/analysis/*`）无平台判定 | **表述需订正**（"无 Mac/Linux 支持"过强：跨平台缺的是 PDF 转换 / 桌面壳 / 中文字体注册 / 计划任务四个外围面，不是"不支持"） |
| 4 | :122 `\| 无云端部署 \| 必须本地安装 \| 提供安装指南 \|` | 现场 `ls` 六个常见部署描述件全部不存在：`Dockerfile`、`docker-compose.yml`、`fly.toml`、`Procfile`、`vercel.json`、`netlify.toml`；仓内零 CI 部署脚本命中；`app.py:662` 页脚文案 `"{APP_VERSION_LABEL} · 单轨 LLM · 本地项目存储 · 云端 AI 按需调用"` | **仍成立**（部署面确实只有本地）；建议给该行加一句限定，避免与"云端 AI 调用"混淆（`src/ui/pages/privacy_gate.py:23` 也在用"云端"字样） |
| 5 | :123 `\| 最大数据文件约 100MB \| 大文件读取 \| 提示选择部分列 \|` | 真实阈值在 `app.py:789` 算 `size_mb`、`app.py:792` `if size_mb > 20:`、`:793` 提示"文件较大（… MB），建议只加载分析所需的列"，随后 `:796-812` 走列多选（`st.multiselect` 在 `:804-805`） ⇒ 提示门槛是 **20MB 不是 100MB**；且全仓**没有任何拒绝加载的硬上限**（"100MB" 只出现在 `KNOWN_ISSUES.md:123` 与 `docs/KNOWN_LIMITATIONS.md:55` 两处文档，代码零锚点） | **表述需订正**（数字无锚点；"降级策略＝提示选择部分列"这半句与代码一致且真实门槛更小） |
| 6 | :124 `\| 最大行数约 100 万行 \| 大表运算变慢 \| 可能变慢但不崩溃 \|` | 全仓无行数守卫：`rg -n "MAX_ROWS\|maxrows\|1_000_000\|len(df) >"` 在 `src/` 的命中只有 LLM 计费（`src/llm_gateway/gateway.py:144-145`、`src/literature_feed/storage/budget_tracker.py:49`）与 CSS（`src/ui/accessibility.py:27`），数据面只有展示用 `src/ui/undergrad_wizard.py:2617` 与"小样本 n<30"提醒；最接近的守卫是**内存**而非行数：`src/utils/memory_manager.py:22-23`（512MB 告警 / 1GB 自动清理） | **表述需订正**（100 万行这个数字既无守卫也无在册实测证据；"不崩溃"是未验命题。不许为凑核销去跑大数据实测 ⇒ 交人工裁决是否降格为"经验值"） |
| 7 | :125 `\| 分类变量水平数 \| 超过 10 级时提醒 \| 无硬限制，仅提示 \|` | `rg -n "nunique()" src/` 共 9 处，全部不是"10 级"判据：`src/analysis/data_quality.py:214` 是 `nunique() <= 1` 的**常数列**告警；`src/ui/undergrad_wizard.py:1813-1814` 是 `iv_values > 2` 的**事后比较提示**；`src/analysis/anova.py:184/185/248/367/623-625` 只用于自由度/组数计算；`src/analysis/assumptions.py`、`src/ui/cleaning_wizard.py:133-146` 的 ">10%" 是**缺失率**不是水平数 | **表述需订正**（"超过 10 级时提醒"这个行为在代码里不存在；现存两个近邻提醒已列上）⇒ 未核销 |
| 8 | :126 `\| 缺失值默认 listwise \| 分析样本缩减 \| 提示缺失比例 \|` | 默认值双处一致：`src/analysis/data_quality.py:27` `strategy: MissingStrategy = "listwise"`（枚举 `:21`，实现 `:62-65`）与 `src/analysis/runner.py:885-886` `missing_strategy = getattr(plan, "missing_strategy", "listwise") or "listwise"`，实际丢弃在 `:926 handle_missing(...)`，策略回写 `:1042`；"提示缺失比例"有实现：`src/analysis/data_quality.py:180` 算 `missing_pct`、`:199-201` 总体缺失 >15% 时警告"列表删除可能造成较大样本损失"、`:76` 单列缺失提示，UI 侧 `src/ui/cleaning_wizard.py:213` 直接显示 `metric("总体缺失率")` | **仍成立（描述与代码逐位一致，属如实边界）** ⇒ 不需核销、也不必改行 |
| — | :118 MANOVA 结果卡片缺失 | **不在本单面**（卷宗/派单点名除外）。仅登记：双向锁在 `tests/test_result_card_registry_snapshot.py:150`（无反向锁）与 `:158`（文档行 ⇔ 注册表无键）；现读 `manova` 在 `AnalysisRegistry`（48 法）但 `card_id=None`、`level=experimental` | 本单不判定 |
| — | :119 ICC 评估卡片缺失 | 同上锁件覆盖 `icc`；现读 `icc` 同样 `card_id=None`、不在 `_CARD_BUILDERS`（44 键 / 29 个去重构建器） | 本单不判定 |

**8 行小结**：0 行「已消解未销」、**3 行仍成立**（#1 含"劣于描述"、#4、#8）、**5 行表述需订正**（#2/#3/#5/#6/#7）。
⇒ 按卷宗第 22 行给的三分类口径，**本表没有任何一行可以划掉**；#1/#6/#7 三行还各带一处需要另立单的现实缺陷。

---

## 二、行 #1 的端到端实测（本档最重要的新证据）

合成数据纯内存（`np.random.default_rng`，零库、零文件写入），跑**真**分析函数再喂**真**卡构建器：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-43/audit3.py
[binary] 分析 OK -> LogisticResult; odds_ratios=DataFrame; pseudo_r2=dict
[binary] 卡构建抛 ValueError: The truth value of a DataFrame is ambiguous. ... @ generic.py:1513
[multinomial] 分析 OK -> LogisticResult; odds_ratios=NoneType; pseudo_r2=dict
[multinomial] 卡构建抛 TypeError: unsupported format string passed to dict.__format__ @ result_card.py:727
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-43/audit4.py      # 3 级有序因变量
[ordinal 3 级] 分析 OK -> LogisticResult; odds_ratios=DataFrame; pseudo_r2=dict
[ordinal] 卡构建抛 ValueError @ generic.py:1513
[ordinal] generate_tables_from_card 自动表数 = 0
[binary 同对象改 method] 自动表数 = 1
```

抛点定位（读源码即得，不需再跑）：

- `src/analysis/result_card.py:716` `odds_ratios = getattr(result, "odds_ratios", None) or getattr(result, "OR", None)`
  —— 真 `LogisticResult.odds_ratios` 是 **DataFrame**（`src/analysis/logistic_regression.py:17` 类型标注、`:97` 与 `:238` 两处 `pd.DataFrame([...])` 构造），
  `X or Y` 触发 `DataFrame.__bool__` → ValueError。binary / ordinal 走这一条。
- `src/analysis/result_card.py:727` `apa += f", Nagelkerke R² = {pseudo_r2:.3f}"`
  —— 真 `pseudo_r2` 是 **dict**（`logistic_regression.py:109-113`、`:243`、`:350`），dict 不支持 `.3f` → TypeError。multinomial（`odds_ratios=None`）越过上一条后撞这一条。
- 文案本身也只写二元：`result_card.py:722` `"二元 Logistic 回归分析以{dv}为结局变量"`、`:741` `"...对{dv}（二分类）的预测效果"`
  ⇒ 即便异常被绕过，ordinal/multinomial 也会被标成"二元/二分类"——这才是原文"解释有限"三个字的实际内容。
- UI 侧不会报错只会**什么都不显示**：`app.py:1463-1467`
  ```
  try:
      from src.ui.result_card_panel import render_result_card
      render_result_card(output)
  except Exception:
          pass
  ```
  （`src/ui/result_card_panel.py:21` 直接 `build_card_from_output(analysis_output)`，无中间序列化。）

**为什么现有测试没红**（§廿七「静默失明的绿」同族）：`tests/test_result_card_v2_methods.py:228-233` 喂的是
`SimpleNamespace(chi2=15.3, p_value=0.001, pseudo_r2=0.22, accuracy=0.78, odds_ratios={"自尊": 1.45, ...})`
——这四个字段里 `chi2`/`p_value` 在真 `LogisticResult` 上**根本不存在**（真值只在 `model_summary` DataFrame 里），
`pseudo_r2` 真是 float 而生产是 dict，`odds_ratios` 真是 dict 而生产是 DataFrame。
⇒ 该桩钉的是**夹具形状**，不是生产形状。**本单未动这个断言**（放宽断言＝违令），只如实登记。

---

## 三、可复算命令清单（本文每个读数都能这样重取）

```
$ rg -n 'ordinal_logistic|multinomial_logistic' src/analysis/runner.py           # -> 311/323（卷宗锚点，无漂移）
$ rg -n '_build_logistic_regression' src/analysis/result_card.py                 # -> 706/1378/1379（卷宗点名）
$ rg -n 'def _truncate' src/                                                      # 与本单无关，仅盘态核对
$ rg -n "100MB|100 MB|约 100" --glob '!node_modules/**' .                          # 仅 KNOWN_ISSUES.md:123 与 docs/KNOWN_LIMITATIONS.md:55 两处文档
$ rg -n "size_mb|文件较大|> 20" app.py                                             # -> 789/792/793（真实门槛 20MB）
$ rg -n "MAX_ROWS|maxrows|1_000_000|len\(df\) >" src/ app.py                       # 数据行数守卫 0 处
$ rg -n "nunique\(\)" src/                                                          # 9 处，无一处 ">10 水平"
$ rg -n "listwise|handle_missing" src/analysis/data_quality.py src/analysis/runner.py
$ rg -n "缺失比例|missing_pct" src/analysis/data_quality.py src/ui/cleaning_wizard.py
$ rg -n "get_table_route_group|generate_tables_from_card" src/ tests/               # table_group 的消費方只有 method_exposure 与一致性测试，apa_tables 不读它
$ rg -n "sys\.platform|os\.name|WINDIR" src/                                          # 平台面
$ ls Dockerfile docker-compose.yml fly.toml Procfile vercel.json netlify.toml          # 六个部署描述件全部不存在（共看 6 个候选名，命中 0）
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-43/audit.py               # 注册表/catalog 全景读数，输出留 tmp/s923-43/audit_out.txt
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-43/audit3.py
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-43/audit4.py
```

现场锚点计数（不抄任务书，§廿五第 3 条）：`docs/insights/*.md` 现 **99** 份（含本文；本文落盘前 98 份）；`KNOWN_ISSUES.md` 现 **157** 行；
`AnalysisRegistry` 现 **48** 法；`_CARD_BUILDERS` 现 **44** 键 / **29** 个去重构建器；`validate_method_contracts(...)` 返回 **`[]`**（三张注册表自洽）。
psy 侧**没有** insights 索引件、也没有 `tests/test_insights_index_closure.py` 式哨兵 ⇒ 本文不需同步索引（§廿二 的口径只对 learning/colony 成立）。

---

## 四、否证掉的任务书前提（卷宗第 22 行的两处）

1. 卷宗：「ordinal/multinomial logistic 已在 runner 注册但**无专用卡**（仅 binary 有 `_build_logistic_regression`）」——
   前半句成立，后半句**不准确**：`_build_logistic_regression` 的注册键是 `logistic_regression` **和** `binary_logistic` 两个
   （`result_card.py:1378-1379`），而 ordinal/multinomial 是靠 `method_catalog.py:70-71` 的 **card 别名**复用它，
   所以"无专用卡"是真的、"仅 binary 有"是错的。⇒ 已按磁盘实况订正，判定不变（仍成立）。
2. 卷宗：「其余 8 行（… 100MB/100 万行、水平数>10、listwise 等）**无任何同步锁**」——
   **不完全成立**：`tests/test_method_id_consistency.py:29-39` 与 `tests/test_method_exposure.py` 锁住了 `table_group`/level 的
   **目录级**一致性（`validate_method_contracts` 也会拒未登记方法，`runner.py:46-48` 直接 `raise RuntimeError`），
   只是**没有任何一把锁把 `KNOWN_ISSUES` 的这 8 行文字与代码对上**。⇒ 收窄为"缺文档↔代码同步锁"，不是"零锁"。

---

## 五、顺带坐实的新缺陷（不属本单面，只登记不处置）

`method_catalog.py` 的 `table_group` 与 `src/output/apa_tables.py` 的实际分派**是两套口径**：

- `generate_tables_from_card`（`apa_tables.py:763`）只把 `card["method"]` 过 `resolve_method_id`（`:768`）后与硬编码元组比对，
  **从不读 `get_table_route_group`**（全仓 `table_group` 的消费方只有 `src/utils/method_exposure.py:24-28` 与 `tests/test_method_id_consistency.py:29-39`）。
- 于是 `ordinal_logistic` / `multinomial_logistic` 在 catalog 里声明了 `table_group="logistic_regression"`（`:70-71`），
  实际路由 `:870` 的元组却只有 `("logistic_regression","binary_logistic")` ⇒ **实测 0 张表**（第二节 audit4 末两行读数）。
- 连带影响 UI 分级文案：`method_exposure.py:47-48` 按 level 出"高级方法：结果卡片可用，但 APA 表格可能需要手动排版"，
  这句话对 ordinal/multinomial 恰好**同时错了两件事**（卡实际抛异常、表路由声明与实现不符）。

⇒ 建议主班另开两张单：① `KNOWN_ISSUES` 8 行的文档↔代码同步锁（照 `test_result_card_registry_snapshot.py:158` 的双向锁形状做）；
② Logistic 族结果卡的形状缺陷（`result_card.py:716`/`:727`）＋ `table_group` 与 apa 路由并轨。
**本单未动任何一处**：改生产码／放宽 `test_result_card_v2_methods.py` 断言都超出执行手授权，且违令「不许为了让某行核销通过而改生产码」。
