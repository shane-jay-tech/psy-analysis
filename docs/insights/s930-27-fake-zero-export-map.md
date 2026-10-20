# 假 0 族与 result_card 效应量出口对照材料

> 产出单：s930-27（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-47 遗留（台账 187/188/189 未消；result_card 效应量出口关系）。
> **零改动**；result_card.py/cfa.py 为在途 M 件只读（行号按工作树现点）。

## 一、假 0 源 → 出口 → 用户可见字段对照表

| 假 0 源（产生点） | 出口（result_card 消费点） | 用户可见形态 | 假 0 当真值展示？ |
|---|---|---|---|
| `srmr`：cfa.py:130 `getattr(result_cfa,'SRMR',0)` → **0.0**（semopy 2.3.11 不出 SRMR——s930-17 实测定谳） | :1142 `fit_indices.get("SRMR"/"srmr")` ⇒ **0.0 非 None** ⇒ :1162-1164 | apa_text「SRMR = 0.000」＋effect_sizes 追加 `{"SRMR", 0.0}` | **是（最险）**——0.000 在 SRMR 语义＝完美拟合，读报告者会当真 |
| `chi2_p`：cfa.py:36 默认 **0.0** | :1134 `get("p"/"p_value")` ⇒ 0.0 非 None ⇒ :1139 「p = 0.000」 | apa_text「p = 0.000」 | **是**——p=0.000 读作「极显著」，与真值可能天差地别 |
| `rmsea_ci_lower/upper`：cfa.py:40-41 默认 **0.0** | result_card **未消费**（只读 rmsea 主值 :1148） | 不出现 | 否（未出口，安全面） |

链路自证：fit_indices 为空 ⇒ :1128-1130 「缺少拟合指标」warning 早退——假 0 问题只发生在 fit_indices **非空**（semopy 有真拟合）时：真键在场+假 0 键（SRMR/p）伴飞。

## 二、哪些出口会把假 0 当真值展示

1. **SRMR 双出口全中**：apa_text 文本（:1163）＋card.effect_sizes 数组（:1164）——后者进卡片结构化字段，下游 UI/导出按效应量清单渲染时 SRMR=0.0 与 Cohen's d 等真效应量并列展示；
2. **chi2_p 单出口**：apa_text（:1139）；「p = 0.000」紧邻 χ² 真值（χ² 是真拟合值）⇒ 真假混排最迷惑；
3. effect_sizes 数组的「效应量」语义污染：SRMR 是拟合指数非效应量——在册的语义错位（0.0 假值叠加在错位语义上，双重误导）。

## 三、两选项材料（显式不提供标注 vs 出口拦截）

| 选项 | 实现 | 效果 | 与 s930-17 裁决②的关系 |
|---|---|---|---|
| **显式不提供**（上游治，推荐） | cfa.py 的 srmr/chi2_p 数据类默认改 **None**（:36/:42），「semopy 不提供」语义显式化 | result_card 的 `is not None` 守卫**天然跳过**——SRMR/p 段不展示、effect_sizes 不污染；下游零改动 | **同一裁决的两面**——s930-17 已定谳 semopy 无 SRMR，本选项即其落地形态；fit_acceptable 判定需同步 None 感知（srmr 不参与判等） |
| **出口拦截**（下游治） | result_card :1162 加「0 值 sentinel 白名单」（如 `if srmr is not None and srmr > 0`） | 不动上游 | ❌ 破绽：**真 SRMR 真可能极小**（饱和模型≈0）——`>0` 拦截会误杀真值；且 chi2_p 无类似阈值可用（p=0 与假 0 不可分）⇒ **出口拦截在本域不可行** |

## 四、建议

显式不提供（上游 None 化）＝唯一不误杀真值的形态；实施面＝cfa.py 两行默认值＋fit_acceptable 的 None 感知＋展示面「（semopy 不提供）」文案——随 s930-17 裁决②同批（两单的落地是同一笔改动的两段描述）。
