# Cramér's V/Cohen's w 口径分叉裁决材料

> 产出单：s930-33（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-62 遗留第 6 条（post_hoc_power.py:353 标签、:171 透传）。
> **零码改动**；直调为纯数学演示（零生产调用）。

## 一、三处对照（原文逐字）

| 处 | 位置 | 原文 |
|---|---|---|
| 标签 | post_hoc_power.py:353 | `return "Cohen's w / Cramer's V"`（`_effect_name` 对 `chi_square` 族） |
| 透传 | post_hoc_power.py:171-174 | `w = getattr(result, "effect_size", None); df_chi = getattr(result, "df", 1); n = _extract_chi_square_n(result)` ⇒ `return w, df_chi, n` |
| 上游 | chi_square.py:16-17 | `effect_size` 字段注释自证两形态：**"Cramer's V" 或 "Cohen's w"**（上游按表形态二选一产出） |

## 二、只读直调数值分叉演示（可复跑）

```python
N, CHI2 = 200, 12.0
w = sqrt(CHI2/N)                    # 0.2449
V_df1 = w                           # df=1（2×2 表）时 V ≡ w
V_df4 = sqrt(CHI2/(N*4))            # 0.1225（df_min=4）
```

→ 同 χ²/N 下：`w = V_df1 = 0.2449`、`V_df4 = 0.1225`——**df>1 时两统计量数值差 50%**。标签斜杠并列「Cohen's w / Cramer's V」隐含「二者等价」，而等价只在 df=1（2×2）成立；上游 chi_square.py 的 effect_size 实际按表形态给 V 或 w（字段注释自证双形态），透传面把值原样带过但**标签不分形态**。

## 三、两案及统计含义

| 案 | 内容 | 统计含义 |
|---|---|---|
| **改标签对齐实现** | :353 按 `df_chi` 动态出标签：df=1 ⇒ "Cohen's w"；df>1 ⇒ "Cramér's V"（透传已带 df_chi，零新数据） | 报告诚实反映上游给的统计量——上游给 w 报 w、给 V 报 V（按 df 语义自洽）；不改任何数值 |
| **改传值对齐名义** | 统一上游一律产 w（`= sqrt(χ²/N)`，不管 df）——标签「Cohen's w」单一化 | w 是效应量家族的「标准化」形态（与 G*Power/post-hoc 惯例一致），跨表可比；但**改动上游 chi_square.py 的产出语义**（若上游本意给 V，改产 w=换统计量） |

## 四、建议（不代裁）

推荐**改标签对齐实现**（动态 df 分支）：零数值改动、零上游耦合、语义诚实（df=1 报 w、df>1 报 V 恰是两统计量的数学关系）；改传值案把 V 归一成 w 虽简化标签，但丢失「V 的效应量惯例界标（0.1/0.3/0.5）」与 w 界标（0.1/0.3/0.5 恰巧同值域但 df>1 时同 w 值代表不同关联强度）的可解释性。
