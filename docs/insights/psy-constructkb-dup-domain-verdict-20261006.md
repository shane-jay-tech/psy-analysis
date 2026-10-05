# 构念库 name_en 撞车与域标签两写法数据口径裁决材料（s1002-38，只读）

- 承 s920-12 遗留 1/2。复现命令：`python -c "import sys;sys.path.insert(0,'.');from src.questionnaire.construct_kb import CONSTRUCTS; ..."`（读 dict 形态逐条列）。

## 一、name_en 撞车（51 条中恰 1 对）

| zh | name_en | domain | dimensions |
|---|---|---|---|
| 工作投入 | Work Engagement | 组织行为 | 活力/奉献/专注 |
| 员工敬业度 | Work Engagement | 组织行为 | 活力/奉献/专注 |

**两维度结构完全相同**（活力-奉献-专注，即 Schaufeli 三维）——实为同一构念的两种中文译名（工作投入 vs 员工敬业度/engagement 的两类汉译）。

**可区分英文名方案**（供日间定）：
- 方案 i：`Work Engagement (UWES)` vs `Job Engagement`——矿源原案；⚠ 学理注记：UWES 的官方英文名即 Work Engagement，标缩写不能消歧（两条 dims 同源）；Job Engagement 是**另一构念**（May et al. 2004 传统），硬改名会把重复问题变成语义错误。
- **方案 ii（推荐）**：保留同名 `Work Engagement`，靠 zh 键区分（dict 键本就不同）；若下游确需英文唯一键，用 `Work Engagement (Schaufeli)` vs `Work Engagement (Employee)` 后缀式消歧——消歧粒度落在「学术源流」而非「构念名」。
- 消费面影响：构造库 getter 全走 zh 键（`CONSTRUCTS[构念名]`），name_en 仅展示面 ⇒ 撞车**当前无运行时危害**，属展示/检索卫生。

## 二、域标签两写法（影响 3 条，非 51 条全量）

| 域写法 | 条数 | 成员 |
|---|---|---|
| 社会心理学 | 7 | — |
| **社会心理**（简写） | 2 | 社会支持、孤独感 |
| 认知心理学 | 5 | — |
| **认知**（简写） | 1 | 元认知 |
| 其余单写法域（组织行为 16/临床与健康 8/发展心理学 8/教育心理 2/人格 2） | 36 | — |

- **归一影响面订正**：矿源「会动 51 条」实为 **3 条**（社会支持/孤独感 → 社会心理学；元认知 → 认知心理学）——两写法中简写侧 3 条改全称即可，全称侧 20 条不动。
- **消费方清单**：`rg -n "domain" src/questionnaire/construct_kb*.py src/ui/*.py`——domain 消费面=侧栏分组/筛选（lr 构念面板）；归一后筛选桶 8→6，UI 无需改码（分组键自然合并）。
- **建议**：归一方向取**全称**（与 20 条主流写法一致），一行级数据改动×3，属低风险数据口径改动，可与 name_en 方案 ii 同笔实施。

## 三、零数据改动自证

本单命令面=python 读 CONSTRUCTS（只读 import）；data/ 与 src/ 零触碰。
