# generate_missing_report 零调用方判死与处置裁决材料（ae49 遗留）——s1004-39

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T10:2x 实测（日间续班段）｜ 性质：不删不接，只出材料
> 矿源：任务书引 ae49 遗留逐字：「`generate_missing_report` 零调用者（`inspector.py:100` 定义后无任何消费者，死码）。删除或接线都属改被跟踪文件，交主班裁。」

## 一、零调用方复核（三域＋宽口径，全部实跑）

| 域 | 命中 | 说明 |
|---|---|---|
| src/ | **1**（=定义行本体） | `src/data/inspector.py:100 def generate_missing_report(df) -> str` |
| tests/ | **0** | 无测试引用 |
| scripts/ | **0** | 无脚本引用 |
| 宽口径 `missing_report`（src/tests/scripts/app.py） | **1**（仍是 def 本体） | 部分名匹配也零命中 ⇒ 零消费者铁证 |

与矿源对账：ae49 判「零调用者」**复核成立且更严**（宽口径亦零）。
**锚点漂移修正留痕**：任务书未指目录；实位 **`src/data/inspector.py:100`**（行号与 ae49 吻合；src/utils/ 下无此件）。

## 二、能力面（函数本体实测）

`$ sed -n 100,115p src/data/inspector.py` → **16 行**：读 df → 输出中文纯文本缺失报告（首行「总样本量： N」，无缺失时「✓ 无缺失值」，否则逐列「{col}: {count} 个缺失 ({pct:.1f}%)」）。

**同能力活实现在世**：cleaning_wizard.py:259-261 缺失值 expander 已逐列展示「缺失数＋缺失率」UI 表（s1004-41 同窗已钉行号）——判死函数的信息能力已被在世实现覆盖。

**模块本身是活的**：`$ grep -rn "from src.data.inspector import" src tests app.py` → 5 进口方，**全部 import 的是同模块另一函数 `inspect_dataframe`**（intent_resolver.py:148／onboarding.py:166／undergrad_wizard.py:15／template_center_panel.py:126／workspace.py:246）。⇒ 死的是这一个函数，不是模块；删除必须只摘函数、不动模块。

**git 史**：`$ git log --oneline -- src/data/inspector.py` → 仅初始化笔 ec45485，入库后零改动（无演化包袱）。

## 三、两案最小波及清单

| 案 | 动作 | 波及面 |
|---|---|---|
| A 删除（推荐） | 摘 `src/data/inspector.py:100-115` 的 16 行函数（模块其余零动） | 生产波及=0（宽口径唯一命中=def 本体实证）；测试波及=0（tests 0 命中）；git 可随时取回 |
| B 接线 | 落点候选：①清洗向导缺失值 expander 内加「生成文字报告」按钮（同能力第二入口）；②DQ report 面附加文本输出 | 能力与在世 UI 表重叠 ⇒ 接线=同信息第二入口，价值低；属产品判断 |

## 四、裁决建议（留主班）

- **推荐案 A**：零波及（双域实证）＋能力已被活实现覆盖＋入库后零演化；属无争议死码。
- 若主班判保留待接线：建议先在 docstring 加 1 行「当前无调用方（ae49/s1004-39 判死材料在册）」，防下批普查重复耗单。

### 证据存根（全部实跑）

- `$ for d in src tests scripts; do grep -rn "generate_missing_report" $d --include="*.py" | wc -l; done` → 1/0/0。
- `$ grep -rn "missing_report" src tests scripts app.py --include="*.py"` → 唯一命中=def 本体。
- `$ grep -rn "from src.data.inspector import" src tests app.py` → 5 行（全为 inspect_dataframe）。
- `$ sed -n 95,130p src/data/inspector.py` → 函数体逐字；`$ sed -n 100,116p ... | wc -l` → 16。
- `$ git log --oneline -2 -- src/data/inspector.py` → ec45485 初始化后零笔。
- `$ git check-ignore src/data/inspector.py` → 非 ignored，tracked 在册。
- 禁令守约：不删不接，仓内仅本档。
