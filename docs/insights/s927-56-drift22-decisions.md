# s927-56｜22 处跨表措辞漂移「取哪侧」裁决清单（一次可勾选）

- 班次：`qoder-executor-20260929-0450-psy102`（信箱单 `s927-56`，只读／材料位）
- 取数现场：`D:\code\psy-analysis`，HEAD `4d3608e`（`git rev-parse --short HEAD`，2026-09-29T04:57 现取）
- 上游锚点：`zcode-bridge/done/s924-11.result.md` 遗留问题①——「22 处跨表措辞漂移取哪侧为权威名；`chi_square` 的符号 vs 名字口径；`app_pages_text` en/zh 对 EFA 抽取法互斥」。
- 性质：**纯材料**。🔴 本班零文案改动、零表项增删、零生产码／测试／配置改动；含统计口径的 4 个键（`ave`/`chi_square`/`efa` 长句面/`icc` 的范围描述）**只登记不判**，签字权在人工闸。
- 用法：每行一个 `[ ]` 勾；先看 §四的 6 个家族级选项（勾一次覆盖多行），再回到 §三处理被标 🔴 的孤行。

## 〇、结论先说

1. **22 这个数字复验成立**：按 s924-11 原口径（≥2 张标签表同持 → 值不一致）在 HEAD `4d3608e` 现读 `multi 39 / drift 22`，与 `done/s924-11.result.md` 逐字相同；工作树与 HEAD 的 22 键集合与逐字值**全等**（唯一在途源件 `src/output/interpretation.py`＝T9 的值两侧一致，见 §五）。
2. **22 键不是一种漂移，是三种**：① 6 键是「i18n 侧 vs settings 侧」，而且 settings 侧是**死值**（`get_test_name()` 先走 i18n，命中即返回）⇒ 取 i18n 侧对界面零改动，取 settings 侧要先删 i18n 键；② 4 键是「多数侧 vs 单侧」，多数侧被 `tests/test_i18n.py` 钉死；③ 12 键 i18n 根本没有该键 ⇒ 运行时走 settings，漂移全在 UI 局部表（T6/T7/T9/T10）之间，**同一屏可以两种措辞并存**。
3. **可机械统一的 15 键**＝纯空格/全半角括号/英文括注形态差（F1、F2 两族）；**需要人工签字的 7 键**＝名字里带不带方法学限定或统计口径（`ave`/`chi_square`/`spearman_corr`/`cronbach_alpha`/`icc`/`cohens_kappa`/`fleiss_kappa`/`split_half`/`mediation` 中的口径面，见 §五）。
4. **本清单不含任何"改了会怎样"的估值**：落令后的牵动面（哪些测试钉桩会红、哪些件在途不能动）只列事实，见 §六。

## 一、复现口径（命令原文，已本机复跑）

```
# 1) 22 键集合与逐字值（AST 轨，s924-11 同口径）→ 读数：multi 39 / drift 22
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s927-56/probe56.py | tee tmp/s927-56/out.json
# 2) 每条变体的全库出现频次 → 扫 581 个 .py／218 个 .md
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s927-56/freq56.py
# 3) 运行时到底哪侧生效（本次 22 键逐一实测）
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "from config.settings import get_test_name;print(get_test_name('cfa'),get_test_name('chi_square'))"
# → 现读：验证性因素分析 χ²（即 cfa 走 i18n 侧、chi_square 显示的是符号）
```

表清单沿用 s924-11 §一（T1 `config/settings.py::TEST_NAMES_ZH`／T2 `src/utils/i18n.py::TRANSLATIONS["zh"]`／T6 `undergrad_wizard` `method_templates`／T7 `quick_entries` `method_labels`（信度 8＋效度 6 同名合并）／T9 `interpretation._interpret_validity` `title_map`／T10 `template_center_panel._translate_method` `mapping`）。

> 📌 口径注（对 s924-11 §一的一条订正）：T10 现读 **6 键**而非 3 键——`src/ui/template_center_panel.py` 里有两份同名 `mapping`（`:275` 按报告类型、`:284` 按方法 id），本口径与 s924-11 同型（同名 dict 合并），多出的 3 键不与任何表重叠 ⇒ **22 读数不受影响**（实测同口径复现 39/22）。复跑：`rg -n "mapping" src/ui/template_center_panel.py`。

## 二、判据（建议侧是按这三条排的，不是按语感）

| 判据 | 实测来源 | 权重说明 |
|---|---|---|
| ① 运行时生效侧 | `config/settings.py:68-74 get_test_name()`＝先 `t()`（i18n），命中即返回，否则回落 `TEST_NAMES_ZH`；本班用 22 键逐一走该函数取实值（§三「运行时」列） | 最高：另一侧若是死值，取它＝白改 |
| ② 测试钉桩侧 | `tests/test_i18n.py` 的 `parametrize("key,zh,en", …)`（AST 轨现读，命中 6 键：independent_ttest:55／paired_ttest:56／one_way_anova:58／pearson_corr:59／mediation:63／hierarchical_regression:64） | 次高：取反侧当场红 |
| ③ 持有频次 | 该变体在**标签表内**的持有表数 ＋ 全库字面出现次数（`"…"` 精确串，581 个 .py／218 个 .md 全扫） | 最低：只作多数派参考，不判对错 |

## 三、22 行逐条（勾选表）

| ☐ | # | 键 | 家族 | 持有表 | 各侧逐字原文（文件:行） | 频次（表数／全库字面次数） | 运行时实测生效 | 建议侧 |
|---|---|---|---|---|---|---|---|---|
| [ ] | 1 | `ave` | F6 | T1,T7,T9 | T1 `config/settings.py:49`＝`平均方差抽取量（AVE）`<br>T7 `src/ui/quick_entries.py:431`＝`聚合效度 AVE（基于 CFA）`<br>T9 `src/output/interpretation.py:459`＝`聚合效度（AVE）` | `平均方差抽取量（AVE）` → 1 表／码内 1 处·1 文件／文内 4 处<br>`聚合效度 AVE（基于 CFA）` → 1 表／码内 1 处·1 文件／文内 3 处<br>`聚合效度（AVE）` → 1 表／码内 1 处·1 文件／文内 3 处 | `平均方差抽取量（AVE）`（settings 回落） | 🔴 不判（统计量名 vs 构念名，取侧会改变这一行"是什么"） |
| [ ] | 2 | `cfa` | F2 | T1,T2 | T1 `config/settings.py:35`＝`验证性因素分析（CFA）`<br>T2 `src/utils/i18n.py:82`＝`验证性因素分析` | `验证性因素分析` → 1 表／码内 2 处·2 文件／文内 10 处<br>`验证性因素分析（CFA）` → 1 表／码内 2 处·2 文件／文内 3 处 | `验证性因素分析`（i18n 命中） | 取 i18n 侧「验证性因素分析」（运行时生效） |
| [ ] | 3 | `chi_square` | F6 | T2,T6 | T2 `src/utils/i18n.py:54`＝`χ²`<br>T6 `src/ui/undergrad_wizard.py:3341`＝`卡方检验 (χ²)` | `χ²` → 1 表／码内 14 处·8 文件／文内 25 处<br>`卡方检验 (χ²)` → 1 表／码内 2 处·2 文件／文内 2 处 | `χ²`（i18n 命中） | 🔴 不判（符号 vs 名字，s924-11 已列为人工裁决项） |
| [ ] | 4 | `cohens_kappa` | F5 | T1,T7 | T1 `config/settings.py:45`＝`Cohen's κ 评分者一致性`<br>T7 `src/ui/quick_entries.py:318`＝`Cohen's κ（两评分者）` | `Cohen's κ 评分者一致性` → 1 表／码内 2 处·2 文件／文内 5 处<br>`Cohen's κ（两评分者）` → 1 表／码内 2 处·2 文件／文内 4 处 | `Cohen's κ 评分者一致性`（settings 回落） | 随 F5「κ 家族统一形态」一并勾 |
| [ ] | 5 | `criterion_validity` | F2 | T1,T7,T9 | T1 `config/settings.py:52`＝`效标效度`<br>T7 `src/ui/quick_entries.py:429`＝`效标效度（与外部标准的相关）`<br>T9 `src/output/interpretation.py:462`＝`效标效度` | `效标效度` → 2 表／码内 2 处·2 文件／文内 7 处<br>`效标效度（与外部标准的相关）` → 1 表／码内 1 处·1 文件／文内 2 处 | `效标效度`（settings 回落） | 取多数一致侧「效标效度」（T1+T9 同值，运行时走 T1） |
| [ ] | 6 | `cronbach_alpha` | F5 | T1,T6,T7 | T1 `config/settings.py:25`＝`克隆巴赫α信度`<br>T6 `src/ui/undergrad_wizard.py:3339`＝`Cronbach's α信度分析`<br>T7 `src/ui/quick_entries.py:312`＝`Cronbach's α（内部一致性）` | `Cronbach's α信度分析` → 1 表／码内 1 处·1 文件／文内 3 处<br>`Cronbach's α（内部一致性）` → 1 表／码内 1 处·1 文件／文内 3 处<br>`克隆巴赫α信度` → 1 表／码内 1 处·1 文件／文内 4 处 | `克隆巴赫α信度`（settings 回落） | 取原文名族「Cronbach's α…」，具体形态随 F5 一并勾 |
| [ ] | 7 | `cvi` | F2 | T1,T7,T9 | T1 `config/settings.py:48`＝`内容效度指数（CVI）`<br>T7 `src/ui/quick_entries.py:434`＝`内容效度 CVI（专家评分）`<br>T9 `src/output/interpretation.py:458`＝`内容效度指数（CVI）` | `内容效度指数（CVI）` → 2 表／码内 2 处·2 文件／文内 5 处<br>`内容效度 CVI（专家评分）` → 1 表／码内 1 处·1 文件／文内 2 处 | `内容效度指数（CVI）`（settings 回落） | 取多数一致侧「内容效度指数（CVI）」（T1+T9 同值，运行时走 T1） |
| [ ] | 8 | `discriminant_fl` | F2 | T1,T7,T9 | T1 `config/settings.py:50`＝`区分效度（Fornell-Larcker）`<br>T7 `src/ui/quick_entries.py:432`＝`区分效度 Fornell-Larcker`<br>T9 `src/output/interpretation.py:460`＝`区分效度（Fornell-Larcker）` | `区分效度（Fornell-Larcker）` → 2 表／码内 2 处·2 文件／文内 5 处<br>`区分效度 Fornell-Larcker` → 1 表／码内 1 处·1 文件／文内 2 处 | `区分效度（Fornell-Larcker）`（settings 回落） | 取多数一致侧「区分效度（Fornell-Larcker）」（T1+T9 同值） |
| [ ] | 9 | `discriminant_htmt` | F2 | T1,T7,T9 | T1 `config/settings.py:51`＝`区分效度（HTMT）`<br>T7 `src/ui/quick_entries.py:433`＝`区分效度 HTMT`<br>T9 `src/output/interpretation.py:461`＝`区分效度（HTMT）` | `区分效度（HTMT）` → 2 表／码内 2 处·2 文件／文内 5 处<br>`区分效度 HTMT` → 1 表／码内 1 处·1 文件／文内 2 处 | `区分效度（HTMT）`（settings 回落） | 取多数一致侧「区分效度（HTMT）」（T1+T9 同值） |
| [ ] | 10 | `efa` | F2 | T1,T2,T6 | T1 `config/settings.py:34`＝`探索性因素分析（EFA）`<br>T2 `src/utils/i18n.py:81`＝`探索性因素分析`<br>T6 `src/ui/undergrad_wizard.py:3340`＝`探索性因素分析 (EFA)` | `探索性因素分析` → 1 表／码内 3 处·3 文件／文内 15 处<br>`探索性因素分析 (EFA)` → 1 表／码内 2 处·2 文件／文内 3 处<br>`探索性因素分析（EFA）` → 1 表／码内 1 处·1 文件／文内 4 处 | `探索性因素分析`（i18n 命中） | 取 i18n 侧「探索性因素分析」（运行时生效） |
| [ ] | 11 | `fleiss_kappa` | F5 | T1,T7 | T1 `config/settings.py:46`＝`Fleiss' κ 多评分者一致性`<br>T7 `src/ui/quick_entries.py:319`＝`Fleiss' κ（≥3 评分者）` | `Fleiss' κ 多评分者一致性` → 1 表／码内 2 处·2 文件／文内 5 处<br>`Fleiss' κ（≥3 评分者）` → 1 表／码内 2 处·2 文件／文内 4 处 | `Fleiss' κ 多评分者一致性`（settings 回落） | 随 F5 一并勾（与 cohens_kappa 必须同族，否则两名互斥关系不清） |
| [ ] | 12 | `hierarchical_regression` | F4 | T1,T2 | T1 `config/settings.py:38`＝`层次回归`<br>T2 `src/utils/i18n.py:77`＝`分层回归` | `分层回归` → 1 表／码内 5 处·4 文件／文内 11 处<br>`层次回归` → 1 表／码内 5 处·4 文件／文内 10 处 | `分层回归`（i18n 命中）＋钉桩 `test_i18n.py:64` | 取 i18n 侧「分层回归」（运行时生效＋tests/test_i18n.py:64 钉死） |
| [ ] | 13 | `icc` | F6 | T1,T7 | T1 `config/settings.py:43`＝`组内相关系数（ICC）`<br>T7 `src/ui/quick_entries.py:316`＝`ICC 组内相关（评分者一致性）` | `ICC 组内相关（评分者一致性）` → 1 表／码内 1 处·1 文件／文内 3 处<br>`组内相关系数（ICC）` → 1 表／码内 1 处·1 文件／文内 5 处 | `组内相关系数（ICC）`（settings 回落） | 建议取 T1「组内相关系数（ICC）」为权威名（不限定用途），限定语进说明；⚠ 若人工裁定只按评分者场景暴露，则相反 |
| [ ] | 14 | `independent_ttest` | F1 | T1,T2,T6,T10 | T1 `config/settings.py:13`＝`独立样本t检验`<br>T2 `src/utils/i18n.py:59`＝`独立样本t检验`<br>T6 `src/ui/undergrad_wizard.py:3329`＝`独立样本t检验`<br>T10 `src/ui/template_center_panel.py:286`＝`独立样本 t 检验` | `独立样本t检验` → 3 表／码内 35 处·22 文件／文内 13 处<br>`独立样本 t 检验` → 1 表／码内 11 处·10 文件／文内 11 处 | `独立样本t检验`（i18n 命中）＋钉桩 `test_i18n.py:55` | 取多数一致侧「独立样本t检验」（T1+T2+T6 同值，tests/test_i18n.py:55 钉死） |
| [ ] | 15 | `known_groups_validity` | F2 | T1,T7,T9 | T1 `config/settings.py:53`＝`已知组别效度`<br>T7 `src/ui/quick_entries.py:430`＝`已知组别效度（差异化检验）`<br>T9 `src/output/interpretation.py:463`＝`已知组别效度` | `已知组别效度` → 2 表／码内 2 处·2 文件／文内 10 处<br>`已知组别效度（差异化检验）` → 1 表／码内 1 处·1 文件／文内 3 处 | `已知组别效度`（settings 回落） | 取多数一致侧「已知组别效度」（T1+T9 同值，运行时走 T1） |
| [ ] | 16 | `mcdonald_omega` | F1 | T1,T7 | T1 `config/settings.py:41`＝`McDonald's ω 综合信度`<br>T7 `src/ui/quick_entries.py:314`＝`McDonald's ω（综合信度）` | `McDonald's ω 综合信度` → 1 表／码内 1 处·1 文件／文内 5 处<br>`McDonald's ω（综合信度）` → 1 表／码内 1 处·1 文件／文内 4 处 | `McDonald's ω 综合信度`（settings 回落） | 取一形态后家族统一（T1「McDonald's ω 综合信度」 vs T7「McDonald's ω（综合信度）」） |
| [ ] | 17 | `mediation` | F3 | T1,T2,T6 | T1 `config/settings.py:32`＝`中介效应分析`<br>T2 `src/utils/i18n.py:79`＝`中介效应分析`<br>T6 `src/ui/undergrad_wizard.py:3337`＝`Bootstrap中介效应分析` | `中介效应分析` → 2 表／码内 10 处·10 文件／文内 12 处<br>`Bootstrap中介效应分析` → 1 表／码内 1 处·1 文件／文内 2 处 | `中介效应分析`（i18n 命中）＋钉桩 `test_i18n.py:63` | 取「中介效应分析」（T1+T2+method_recommender.py:229 同值，tests/test_i18n.py:63 钉死） |
| [ ] | 18 | `one_way_anova` | F2 | T1,T2,T6 | T1 `config/settings.py:16`＝`单因素方差分析`<br>T2 `src/utils/i18n.py:62`＝`单因素方差分析`<br>T6 `src/ui/undergrad_wizard.py:3331`＝`单因素方差分析 (One-Way ANOVA)` | `单因素方差分析` → 2 表／码内 10 处·10 文件／文内 8 处<br>`单因素方差分析 (One-Way ANOVA)` → 1 表／码内 3 处·3 文件／文内 2 处 | `单因素方差分析`（i18n 命中）＋钉桩 `test_i18n.py:58` | 取无英文括注侧「单因素方差分析」（T1+T2 同值，运行时生效＋tests/test_i18n.py:58 钉死） |
| [ ] | 19 | `paired_ttest` | F1 | T1,T2,T6,T10 | T1 `config/settings.py:14`＝`配对样本t检验`<br>T2 `src/utils/i18n.py:60`＝`配对样本t检验`<br>T6 `src/ui/undergrad_wizard.py:3330`＝`配对样本t检验`<br>T10 `src/ui/template_center_panel.py:287`＝`配对样本 t 检验` | `配对样本t检验` → 3 表／码内 9 处·9 文件／文内 6 处<br>`配对样本 t 检验` → 1 表／码内 4 处·4 文件／文内 3 处 | `配对样本t检验`（i18n 命中）＋钉桩 `test_i18n.py:56` | 取多数一致侧「配对样本t检验」（T1+T2+T6 同值，tests/test_i18n.py:56 钉死） |
| [ ] | 20 | `pearson_corr` | F1 | T1,T2,T6,T10 | T1 `config/settings.py:19`＝`Pearson相关`<br>T2 `src/utils/i18n.py:70`＝`Pearson相关分析`<br>T6 `src/ui/undergrad_wizard.py:3332`＝`Pearson相关分析`<br>T10 `src/ui/template_center_panel.py:285`＝`Pearson 相关分析` | `Pearson相关分析` → 2 表／码内 7 处·6 文件／文内 7 处<br>`Pearson 相关分析` → 1 表／码内 2 处·2 文件／文内 2 处<br>`Pearson相关` → 1 表／码内 6 处·4 文件／文内 11 处 | `Pearson相关分析`（i18n 命中）＋钉桩 `test_i18n.py:59` | 取 i18n 侧「Pearson相关分析」（运行时生效＋tests/test_i18n.py:59 钉死） |
| [ ] | 21 | `spearman_corr` | F5 | T1,T2,T6 | T1 `config/settings.py:20`＝`Spearman相关`<br>T2 `src/utils/i18n.py:71`＝`Spearman相关分析`<br>T6 `src/ui/undergrad_wizard.py:3333`＝`Spearman秩相关分析` | `Spearman相关` → 1 表／码内 1 处·1 文件／文内 10 处<br>`Spearman相关分析` → 1 表／码内 1 处·1 文件／文内 6 处<br>`Spearman秩相关分析` → 1 表／码内 1 处·1 文件／文内 4 处 | `Spearman相关分析`（i18n 命中） | 取 i18n 侧「Spearman相关分析」（运行时生效） |
| [ ] | 22 | `split_half` | F6 | T1,T7 | T1 `config/settings.py:30`＝`分半信度`<br>T7 `src/ui/quick_entries.py:313`＝`分半信度（Spearman-Brown）` | `分半信度` → 1 表／码内 5 处·4 文件／文内 14 处<br>`分半信度（Spearman-Brown）` → 1 表／码内 1 处·1 文件／文内 2 处 | `分半信度`（settings 回落） | 建议取 T1「分半信度」为权威名，「Spearman-Brown」进说明；⚠ 前提＝人工确认实现输出的确是 SB 校正系数（本材料未验） |

## 四、6 个家族级选项（勾一次覆盖多行）

| ☐ | 家族 | 统一规则 | 覆盖键（行数） | 勾了它就不用逐行勾 |
|---|---|---|---|---|
| [ ] | **F1 空格/连接符** | 拉丁名与中文之间**不加空格**、`t 检验`→`t检验`（＝与 `tests/test_i18n.py` 钉桩同形） | independent_ttest, paired_ttest, pearson_corr, mcdonald_omega（4） | ✅ 4 行 |
| [ ] | **F2 括注/英文后缀** | 权威名**不带**英文括注（`（CFA）`/`(One-Way ANOVA)`/`（专家评分）` 等移出标签层，进说明或 tooltip） | cfa, one_way_anova, criterion_validity, cvi, known_groups_validity, discriminant_fl, discriminant_htmt, efa(仅括注面)（8） | ⚠ efa 的长句互斥面仍在 §五，别一并销账 |
| [ ] | **F3 估计法不进方法名** | `Bootstrap`/`Spearman-Brown` 一类**估计法/校正法**限定语一律移出权威名 | mediation, split_half（2） | ✅ 2 行（split_half 需先确认实现） |
| [ ] | **F4 同义术语二选一** | `层次回归` vs `分层回归` 取 **`分层回归`**（i18n 侧＋钉桩侧＋运行时侧三合一） | hierarchical_regression（1） | ✅ 1 行 |
| [ ] | **F5 人名/字母统计量形态** | 统计量权威名统一取**原文名＋形态**：`Cronbach's α`／`McDonald's ω`／`Cohen's κ`／`Fleiss' κ`（不音译），限定语（两评分者／≥3 评分者／内部一致性）统一放括号内 | cronbach_alpha, cohens_kappa, fleiss_kappa, spearman_corr(秩面)（4） | ⚠ κ 的人数口径与「秩」字保留与否仍需 §五 签字 |
| [ ] | **F6 口径面单独签字** | `ave`（统计量名 vs 构念名）、`chi_square`（符号 vs 名字）、`icc`（是否限定评分者）三键**不走机械规则**，逐键写结论 | ave, chi_square, icc（3） | ❌ 必须逐行处理 |

## 五、需人工签字的口径面（执行手不判）

- **`cohens_kappa`**（`Cohen's κ 评分者一致性` / `Cohen's κ（两评分者）`）：T1「Cohen's κ 评分者一致性」讲用途、T7「Cohen's κ（两评分者）」讲人数。实测 reliability.py:25 只有 kappa_method="cohen"/"fleiss" 分流，**是否按评分者人数校验本材料未验** ⇒ 选「两评分者」前需人工确认。
- **`efa`**（`探索性因素分析（EFA）` / `探索性因素分析` / `探索性因素分析 (EFA)`）：🔴 本键另有一处**不属取侧范围**的口径冲突：T4(en) 写 principal axis factoring、T5(zh) 写主成分法（同一渲染双语互斥），属统计方法口径，交人工闸，本材料不判。
- **`fleiss_kappa`**（`Fleiss' κ 多评分者一致性` / `Fleiss' κ（≥3 评分者）`）：T1「Fleiss' κ 多评分者一致性」／T7「Fleiss' κ（≥3 评分者）」。同上，人数下限属口径，未验实现。
- **`icc`**（`组内相关系数（ICC）` / `ICC 组内相关（评分者一致性）`）：实测实现面：src/analysis/reliability.py:263 icc_type 默认 "ICC2"，:274 接受 ICC1/ICC2/ICC3/ICC1k/ICC2k/ICC3k ⇒ T7「（评分者一致性）」把可用范围**写窄了**；此条属口径描述准确性，签字权在人工。
- **`known_groups_validity`**（`已知组别效度` / `已知组别效度（差异化检验）` / `已知组别效度`）：T7 括注「（差异化检验）」＝实现口径描述，本材料未验实现，建议先降为说明。
- **`mcdonald_omega`**（`McDonald's ω 综合信度` / `McDonald's ω（综合信度）`）：纯排版（括注 vs 后缀），无口径差。
- **`spearman_corr`**（`Spearman相关` / `Spearman相关分析` / `Spearman秩相关分析`）：T6「Spearman秩相关分析」多一个「秩」字＝方法学完整名，**是否保留属口径选择**（无测试钉桩，改动不破桩）；本材料给三侧频次，不判优劣。

另有两处**不属于「取侧」**但同表并存的已知冲突，登记以免被误当成措辞漂移一并改掉：
1. `efa` 的 T4/T5 双语互斥：`src/ui/app_pages_text.py:190`(en) 写 `principal axis factoring`、:207(zh) 写「主成分法」——同一函数同一次渲染，属统计抽取法口径（s924-11 §3.3 已登记，本班同样不判）。复跑：`rg -n '"efa":' src/ui/app_pages_text.py`。
2. `pearson_corr` 的 T1「Pearson相关」与 `ave`/`icc` 等的 T1 值一样，**在 i18n 无同键时才会被读到**；裁「取 i18n 侧」时若不删 T1 同键，死值仍留在表里，下一次盘点还会报同一处漂移。

## 六、落令后的牵动面（事实清单，本班未动）

- **钉桩面**：裁反 ② 判据会当场红的 6 例见 §三「运行时实测」列（`tests/test_i18n.py` 的 parametrize 行号已给）。
- **计数钉桩**：`tests/test_i18n.py:112` 钉 `len(TRANSLATIONS["zh"]) == 106`——**删 i18n 键会红**；只改值不删键不破。本班实测当前值：`PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "from src.utils.i18n import TRANSLATIONS;print(len(TRANSLATIONS["zh"]))"` → `106`。
- **键集对拍**：`tests/test_i18n.py:203` 起的 s924-22 新例钉 `TEST_NAMES_ZH` 键数 48 ＋ 交集 9／差集 2；**往 settings 表补/删键会红**，与取侧无关的改动也会触发，别误读成并轨失败。
- **在途件锁位**（本班未碰，落令时请按 HEAD／工作树双报）：`app.py`（含 `:33` import 面与 `get_test_name` 调用位 `:1167`）、`src/output/interpretation.py`（T9 源件，现为 ` M` 未归因在途）。实测：`rg -n -w "get_test_name" -g '*.py' -g '!tmp/**' .` → 生产位 app.py:1167／runner.py:992-993／intent_recognizer.py:537-539／undergrad_wizard.py:13,2976,3028,3063。
- **非 dict 面（T11）**：`src/analysis/method_recommender.py` 的 `primary_method_zh=` 硬编码，本清单里 3 键在此另有第 3/4 形态：`中介效应分析`(:229，与权威侧一致)、`Cronbach's α 信度分析`(:273，带空格)、`卡方独立性检验`(:317)。只裁 T1–T10 会漏这三处 ⇒ 复跑：`rg -n "primary_method_zh=|primary_zh=" src/analysis/method_recommender.py`。

## 七、本班实况与未做项

- 未做任何文案/表项/代码改动；产出仅本档 1 件（`git status --porcelain` 净加 1 行，见 result 证据节）。
- 未跑任何测试套件（本单判据不含测试读数；全量更是禁跑）。
- 探证件在 `tmp/s927-56/`（`probe56.py`／`freq56.py`／`out.json`／`freq.json`），`tmp/` 已 gitignore，主班可清；需复算时按 §一 两条命令重建。
- `chi_square`／`ave`／`icc`／`efa` 四条按红线只出材料，未下判定。
