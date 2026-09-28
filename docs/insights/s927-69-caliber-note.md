# s927-69 · 派单模板补文草案：writer 覆盖类判据的前置核查口径（2026-09-29，登记单）

> 取数时刻：`date` 现取 2026-09-29 06:50。**本档只登记，模板本体一行未改**
> （`D:\code\zcode-bridge\prompts\*`、`D:\code\scripts\night_brain.py`、`docs\night-plans\PROTOCOL.md` 均属规划班写权域）。
> 所有实例的单号／节号／行号均为本单现读，非转抄。

## 一、缺口在哪：现役四道关口**没有一道**管"覆盖叙述"

| 落点 | 现值（盘上原文，2026-09-29 现读） | 管不管覆盖叙述 |
|---|---|---|
| `zcode-bridge/prompts/planner.md:61` | 「完成标准中出现关键数字（计数/耗时/命中率/**覆盖率**）时，每条内联**可复跑命令**」 | 只管"附命令"，不管"命令跑出来的引用面与叙述是否同向" |
| `zcode-bridge/prompts/executor.md:52` | 动单前对目标路径跑 `inflight_probe.py`，命中 DIRTY 先确认归属 | 只管**在途态**，只管执行侧 |
| `D:\code\scripts\night_brain.py:575-583`（`PREFLIGHT_PROBE` 常量） | 三态口径 `DIRTY`／`BLIND`／`MISSING`（MISSING＝锚点路径磁盘上不存在） | 只管"路径在不在"，**没有"引用面/覆盖叙述为假"这一态** |
| `D:\code\scripts\night_brain.py:283-313`（`validate_task`） | 逐条查：id 合法性／id 重复／cwd 存在／`max_minutes` 1–40／正文长度／`BODY_REQUIRED=("完成标准","禁止")` 段齐／`anchors` 非空／title 非空 | **全机械项，无任何叙述真伪校验**（连"产出名是否已存在"都不查，见 l927-28） |

⇒ 派单侧写「X 仅被 Y 测试间接覆盖」这类**覆盖判据**时，四道关口一律放行；
真假要靠执行班开工后自己 grep 才发现——**发现成本被推到了最贵的位置**（执行班轮次）。

## 二、本批失真实例（单号＋节号现读，含方向相反的正例）

| # | 实例 | 现读位置 | 实况 |
|---|---|---|---|
| 1 | **s922-117（本单锚点，假前提型）** | `zcode-bridge/done/s922-117-section-writers-offline.result.md:16`（§执行摘要）＋`:142-143`（§遗留问题 第 1 条） | 任务书写「仅被 apa7_gate 测试**间接覆盖**」；执行班实跑 `grep -rl "section_writers" tests/ --exclude-dir=__pycache__` → **2 个文件**（`test_psychology_report_format_golden.py`／`test_ui.py`），**apa7_gate 零命中**，且段落生成器本体此前**零直接测试**。同件另有一条前提也失真（`PaperContext` 字段名 `title/variables/sample_size` 实为 `title_hint/topic/participants_n`） |
| 2 | **l927-55（陈旧半真型）** | `zcode-bridge/outbox/l927-55.result.md:15-16`（§执行摘要）＋`:71`／`:100`（§证据 E1） | 前单（l922-104）遗留的「`tests/` 下对 `_export_cache*` **零引用**」已被 `19f8e9c` 消化 ⇒ 引用面为"既件 9 处＋本件 24 处"。更硬的一层：**引用面存在≠分支被覆盖**——那些断言「都是次数/键的断言，没有分支级证据」，真缺口要用变异测试才照得出来 |
| 3 | **c927-77（锚点指向错档型）** | `zcode-bridge/outbox/c927-77.result.md:73` | 任务书把判据挂在某档上，实测该档「后半 **0 命中**」⇒ 不点名 `dayClamp`，判据实际在另一件的 `:17` |
| 4 | **k927-46（正例：先 grep 再写）** | `zcode-bridge/outbox/k927-46.result.md:50` | 派单侧先跑 `grep -rn "generateWeeklyPlan" src tests scripts` ⇒ 6 处定义＋**唯一消费者 `:1445`**，且**tests 与 scripts 零引用**——这条"零"是**测出来的**，不是推出来的。规则要做的就是把它变成默认动作 |
| 5 | **l927-28（生效面实例：补模板常量＝零效果）** | `D:\code\learning-system\docs\insights\l927-28-precheck-list.md:46`（§二 标题）＋`:162`（§四 第 3 条自带警告） | 模板常量 `night_brain.py:575 PREFLIGHT_PROBE` 写进了 `render_task_file()`（`:596` 插值），但**盘上任务书零命中** |

**本单对第 5 条做的现值复测**（同口径重新取数，分母已漂）：

```
$ for d in inbox done pending; do printf "%s: " "$d"; grep -rl "PREFLIGHT_PROBE" $d/*.task.md | wc -l; done
inbox: 0
done: 0
pending: 0
$ ls zcode-bridge/{inbox,done,pending}/*.task.md | wc -l  → 150 + 3441 + 0 = 3591 枚
```

⇒ l927-28 当时报 **3663**（inbox 164／done 3427／pending 72），今日 **3591**（pending 已清空、done 增 14、inbox 减 14）；
**结论方向不变**：改常量**不回填**已投递任务书 ⇒ 现役批次永远不会带新句。
（注：l927-28 的 3663 是它当时的分母，不是本单的读数。）

**覆盖措辞在现役队列的占比**（决定该规则的暴露面，不决定其必要性）：

```
$ grep -lE "间接覆盖|零引用|未被任何测试|无测试覆盖|覆盖缺口|直接覆盖|零直接测试" zcode-bridge/inbox/*.task.md | wc -l   → 1 / 150
$ 同一 grep 扫 done/  → 66 / 3441
$ grep -l ... inbox/*.task.md  →  zcode-bridge/inbox/s927-69.task.md     ← 唯一命中就是本单自己的锚点行
```

⇒ 历史面 **66 枚**任务书带覆盖类措辞（≈1.9%），现役 inbox 此刻仅 1 枚且即本单。
**规模小不等于安全**：实例 1 的代价是一枚执行单按假前提写完 19 例断言后返工（s922-117 §证据「首跑曾 2 failed，两条都是我按派单直觉写错断言」）。

## 三、补文草案（可直接粘贴；**本单一行未落**）

### R1（判据侧硬规则，建议进 `prompts/planner.md` §完成标准）

```markdown
> 【覆盖类判据前置核查】任务书正文/完成标准中出现「X 仅被 Y 间接覆盖」「无测试覆盖」「零引用」
> 「覆盖缺口」一类叙述时，**必须先跑并把读数原样写进任务书**：
> `grep -rl "<模块basename>" tests/ --exclude-dir=__pycache__`（跨仓面加 `src/ scripts/`），
> 未附读数的覆盖叙述一律改写为「待核查」占位，不当判据用。
> 反向禁令：**禁止用「没有被某测试引用」推断「零直接测试」**——两者相差的是引用面口径，不是同一件事。
```

### R2（判据强度分级，建议同节追加）

```markdown
> 【引用面≠分支面】"覆盖类"判据分三档，写单时标明落在哪档：
> ①**存在档**：模块被测试 import（grep -rl 可判）；
> ②**次数档**：断言某函数被调用 N 次／session_state 键不变（grep 判不出，需读断言体）；
> ③**分支档**：断言"命中/未命中各走哪条路"（只有变异测试或分支断言能钉）。
> 只有 ① 时不得写"已覆盖"；实例见 l927-55 §证据 E1（既件 9 处引用全是 ②，缺口在 ③）。
```

### R3（锚点真伪，建议进 `prompts/planner.md` 的锚点节）

```markdown
> 【锚点须点名到位】写「判据见 <文件>:<行>」前先 `grep -n "<符号名>" <文件>` 取现值：
> 行号会漂、文件会被拆、档可能不点名该符号（实例 c927-77：所引档后半对该符号 0 命中）。
> 路径**逐字复制**，不凭记忆补目录前缀（w60 §A.4 已把这条列为派单侧硬更正）。
```

### R4（跨域引数，与 w60 §A.3 同条不重复造）

```markdown
> 【按域分列】引"实测读数"进任务书时注明出处单号＋域（缓存域／key 规范域／命名域…），
> 不确定就不写。已发生的串案：w60 §A.3（learning 缓存域案 B 被当变式题 key 规范域发）。
```

### R5（机械闸建议，唯一对"未来投递"立刻生效的落点）

```python
# scripts/night_brain.py:validate_task()（:283-313）内追加，不改任何现有检查
COVERAGE_CLAIM_RE = re.compile(r"间接覆盖|零直接测试|无测试覆盖|零引用|覆盖缺口")
PROBE_READING_RE  = re.compile(r"grep\s+-rl|inflight_probe\.py|--collect-only")   # 附读数即放行
if COVERAGE_CLAIM_RE.search(body) and not PROBE_READING_RE.search(body):
    problems.append(f"含覆盖类判据但未附引用面读数: {tid}")
```

## 四、四条落点的生效半径（选型材料，不由本单裁决）

| 落点 | 生效面 | 依据 |
|---|---|---|
| `prompts/planner.md`（R1–R4 成文） | **未来批次**的出稿提示词；**需按 PROTOCOL「重建口径」重建自动化**才作用于运行会话（`README.md:130` 明写"改磁盘 ≠ 改运行会话"） | 现读 planner.md:61 已同格式承载 d913c-38 引用条，追加行成本≈0 |
| `night_brain.py:PREFLIGHT_PROBE`（常量补一句） | **对现役 3591 枚零效果**（本单 0/0/0 复测＝实例 5）；只影响今后 `render_task_file()` 产出的新件 | :575-583 与 :596 现读 |
| `night_brain.py:validate_task()`（R5） | **投递即拦**，不依赖执行班提示词被重建——是四条里唯一"绕开提示词代际"的机械落点 | :283-313 现读：全部检查都是机械项，与 R5 同形 |
| `prompts/executor.md:52` 侧（执行班自查） | 只影响**执行侧**，管不到"任务书把假前提写成判据"；且同样受"重建口径"约束 | :52 现读 |

⇒ 材料性建议（非裁决）：**R1–R4 成文进 planner.md ＋ R5 进 validate_task** 两处并落，
单补常量（第二行）等于没补。写权域属规划班，本单未动。

## 五、声明与待人工

- 本单**零改模板本体**：`prompts/*`、`scripts/night_brain.py`、`PROTOCOL.md`、`inflight_probe.py` 全部只读；
  `git status` 层面这些件不在任何工作树的脏件列表里（本会话未产生对其的写入）。
- 待人工：①R1–R5 是否并入、并入哪几处；②并入后是否按 PROTOCOL 重建自动化班（否则 planner/executor 两条不生效）；
  ③`validate_task` 的 R5 属"新增拦截"，会把现役含覆盖措辞但未附读数的单**挡在投递口**——
  拦得对不对属**判据收紧**，规划班＋人工签字，本单只给形状不给放行判断。
- 本会话另一条相关在册事实（供主班同笔入账，非本单结论）：`psy-analysis/docs/insights/s927-68-baseline3250.md` §3
  把"任何总数必附解释器／`-m`／时刻"落成了硬口径——它与 R2 的"存在档≠分支档"是同一族问题的两个面，
  建议规划班并成一节考虑。
