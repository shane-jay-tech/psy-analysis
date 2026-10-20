# codebook `scale` 字段与 ALL_TEMPLATES 五套模板名映射裁决材料（d598 遗留）——s1004-48

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T02:1x ｜ 性质：只出材料不落码（字典 schema 变更属版本面，随 _version 走）
> 矿源：`zcode-bridge/done/20260925-120655-d598.result.md` 遗留逐字核对在册（scale 只塞量表名、与五套模板名未建映射）。

## 一、现值对照表（rg 实证）

**五套模板名**（`src/questionnaire/item_templates.py:49-55`）：

| 模板键（ALL_TEMPLATES key） | 中文名（.name） |
|---|---|
| `likert_agreement` | Likert同意度量表 |
| `frequency` | 频率量表 |
| `semantic_differential` | 语义差异量表 |
| `situational` | 情境判断量表 |
| `behavioral` | 行为报告 |

**现 scale 值域**：`data_dictionary.py:239` → `scale=str(schema.get("title", ""))`＝**schema 标题自由文本**（每份问卷一个 title，与五套模板键/名均无结构化关联；title 可以是「焦虑自评量表 v2」这类任意串）。模板名的消费面在 design_engine.py:97／llm_engine.py:831（生成侧选模板），与字典侧 scale 无交集。

## 二、仓内消费方取证（两案兼容面的决定性事实）

`$ grep -rn "entry.scale|\.scale\b|[\"']scale[\"']" src/ tests/ --include="*.py"`（剔除 hlm.py 的 statsmodels `result.scale` 与 scale_min/scale_max/out_of_scale 干扰项）→ **仓内 0 消费方**。

⇒ `CodebookEntry.scale` 当前是**仓内写后即弃字段**：写入口唯一（:239），读入口零。真正的兼容约束只在**字典 JSON 工件的外部消费面**（dsh 侧/前端/历史导出件）与**版本标记机制**（`NO_VERSION_MARKER`＋`conflicts()` 报 `E_VERSION`，data_dictionary.py:223-226）。

## 三、映射方案两案

| 案 | 改法 | 仓内代码影响 | 字典工件影响 | 风险 |
|---|---|---|---|---|
| A｜scale 塞模板名（改写侧） | :239 改为 scale=模板键（schema 需带 template 键或按 items 形状推断） | 零（无读方） | **语义换血**：scale 从「量表名」变「模板键」——title 信息丢失；历史 v1 字典（scale=量表名）与新字典（scale=模板键）同键不同义＝跨版本串味 | 中：外部若有按 scale 显示量表名的消费方，直接显示成 `likert_agreement` 这类裸键 |
| B｜增 `scale_template` 键（双键过渡） | CodebookEntry 增可选字段 `scale_template: str \| None`（模板键或 None），scale 维持量表名 | 1 个 dataclass 字段＋:239 一行赋值（随版本面走） | v1 消费方**零感知**（新键附加）；老字典无该键＝None 语义自洽 | 低：双键期两键并存需在字典 docstring 声明寿命（模板映射成熟后 scale 是否收编待后裁） |

## 四、裁决建议（留主班，未实施）

- **推荐案 B**：仓内零消费方的事实使 B 的迁移成本≈一次带版本的 dataclass 扩展；A 的「同键换义」在无中央消费方清单的现状下不可控（外部面无法取证归零）。
- 前置事实：现 schema 侧本就没有「哪题用哪套模板」的结构化声明（模板选择发生在 llm_engine/design_engine 生成时）——B 落地前还需先定「模板键从哪来」（schema 增键 vs 生成时回写），属第二层裁决，材料已在案（design_engine.py:97 / llm_engine.py:831 两处选模板点）。
- 版本纪律：无论 A/B 均须随 `_version` 面走（d598/任务书禁令同款），新字典带 version、旧字典维持 NO_VERSION_MARKER＋E_VERSION 报错现状。

### 证据存根

- `$ sed -n 49,60p src/questionnaire/item_templates.py` → 五键逐字；`$ sed -n 235,250p src/questionnaire/data_dictionary.py` → :239 scale 赋值逐字。
- `$ grep -rn "ALL_TEMPLATES" src/ --include="*.py"` → design_engine.py:11,:97／llm_engine.py:20,:831（生成侧消费，与字典无交集）。
- `$ grep -rn "entry\.scale\|\.scale\b|\[\"scale\"\]" src/ tests/ --include="*.py"`（剔除干扰）→ 0 消费方。
- 不落码守约：本单仓内零触碰（仅本档）。
