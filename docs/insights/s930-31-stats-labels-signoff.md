# 7 处统计标签实现实况签字材料

> 产出单：s930-31（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-56 遗留（7 处需人工签字，本材料只出事实）。
> 零改动；逐点实况=磁盘实读。

## 一、七点实况逐条

| # | 标签 | 矿源疑点 | 实现实况（file:line 原文） | 签字建议材料 |
|---|---|---|---|---|
| 1 | `ave`（统计量名 vs 构念名） | 「ave」可能撞构念名 | catalog :84 `_m("ave_cr", aliases=("ave",), card="ave_cr")`——**方法 id 是 ave_cr**，"ave" 只是别名；实现=result_card.py:1264 `_build_ave_cr`（消费 construct.get("AVE"/"ave")） | 实现侧无歧义（AVE=平均方差抽取量，:1276 中文标签自证）；「vs 构念名」的撞名若存在，只在**数据面**（构念名恰好叫 Ave 时 UI 混淆）——实现面可签 |
| 2 | `chi_square`（符号 vs 名字） | χ² 符号 vs chi_square 名 | catalog :62/:63（id=chi_square/chi_square_gof）；formatter.py:159 `_format_chi_square`；interpretation.py:12 同源 import ChiSquareResult——**全链用同一 id**，χ² 符号只出现在展示文案（result_card :1139「χ²({df})」） | 展示层 χ² + 代码层 chi_square 双轨一致；可签 |
| 3 | `icc`（标签把 ICC1/2/3 全族写窄成「评分者一致性」） | 标签窄化 | 实现=reliability.py:263-277 **支持 6 型**（ICC1/2/3/1k/2k/3k，docstring 全列）；「评分者一致性/重测」只出现在注释 :260（模块级说明）——**窄化点需定位到 UI/卡片文案**（catalog :77 `_m("icc")` 无 label 字段，_m 无 label 参数 ⇒ 窄化不在 catalog） | 窄化文案面在别处（UI/报告模板）；实现面支持全族——**实现可签，窄化文案另点**（需先定位消费方） |
| 4 | `cohens_kappa` 人数口径 | 未验实现 | reliability.py:386-400：sklearn `cohen_kappa_score`；**两评分者**、n_cases≥10 硬闸（<10 raise） | 实现口径实证：两 rater/n≥10——签字材料就绪 |
| 5 | `fleiss_kappa` 人数口径 | 未验实现 | reliability.py:443-460：statsmodels `aggregate_raters`+`fleiss_kappa(method="fleiss")`；**≥3 评分者**硬闸（<3 raise）、n≥10 | 实现口径实证：≥3 rater/n≥10——与 Cohen 的分界明确（<3 引导用 Cohen） |
| 6 | `split_half`（Spearman-Brown 是否即实现输出） | 未验 | reliability.py:91-119：奇偶分半 → `r_half=pearsonr(odd,even)` → **`sb_r = 2r/(1+r)` Spearman-Brown 校正** → **输出 alpha=sb_r**（!）＋split_half_r=r_half 分开两字段 | **验毕：输出主值即 SB 校正后值**（放 alpha 字段——字段名借位是语义小瑕）；split_half_r 保留原相关。可签＋注字段名借位 |
| 7 | `spearman_corr`（是否保留「秩」） | 是否真秩相关 | correlation.py:71 `stats.spearmanr(x_clean, y_clean)`（scipy 秩相关本体） | **验毕：保留秩**（scipy.spearmanr）。可签 |
| 附 | `efa` T4/T5 双语抽取法互斥 | 统计内容 | s927-56-drift22 :81 已登记（T4 en=principal axis factoring vs T5 zh=主成分法——**两种不同抽取法**，双语互斥） | **维持人工闸**（选哪种抽取法=统计方法口径，非翻译问题） |

## 二、签字摘要（交人工）

- **可直接签**：#4（两 rater/n≥10）、#5（≥3 rater/n≥10 分界明确）、#6（SB 校正即输出，附「alpha 字段借位」注）、#7（scipy 秩相关）——四点实现与标签语义实质相符；
- **实现可签但文案另点**：#1（AVE 实现面清晰；构念撞名在数据面）、#2（双轨一致）、#3（实现全族支持；「评分者一致性」窄化文案的消费方需另点定位）；
- **维持人工闸**：efa T4/T5（统计方法口径二选一）。
