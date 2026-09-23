# psy 构念普查四数值只读复核（s923-02 · 2026-09-23）

> **性质：纯只读对账。** 不改普查档、不改 `construct_kb.py`、不写库、不调 LLM、不联网。
> 本文是该单唯一产物；`git status --porcelain` 除本文件外无本班新增项。

## 0. 声明所用 HEAD（s922-11 明确要求的口径）

| 项 | 读数 | 取值时刻 |
|---|---|---|
| 本仓 HEAD（短） | `f9b93c0` | 2026-09-23 02:0x |
| 本仓 HEAD（全） | `f9b93c099fe0fae950dd376f882f97542a3efa76` | 同上 |
| 被复核的原报 HEAD | `5cefb71`（`test(psy): construct_kb 全量普查钉桩（s920-12…）`） | s920-12 自述 |
| 祖先关系 | `git merge-base --is-ancestor 5cefb71 HEAD` → **成立** | 同上 |

⚠️ **取证期间 HEAD 本身在动**：本班 01:41 开工读到 `78693c6`，02:05 取本数时已是 `f9b93c0`
（同仓兄弟班 psy3 在这段窗口里持续提交，porcelain 也从 20 → 22 → 19 变过三轮）。所以本文所有读数
**只对 `f9b93c0` 这一个盘面负责**，复现者请先 `git rev-parse --short HEAD` 对齐。

## 1. 四个数值的复算命令与读数

### 主命令（一条命令出四个数）

```bash
cd /d/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import collections
from src.questionnaire.construct_kb import CONSTRUCTS as C
dims   = [d for v in C.values() for d in v['dimensions']]
scales = [s for v in C.values() for s in v['established_scales']]
refs   = [r for v in C.values() for r in v['references']]
print('构念     =', len(C))
print('维度     =', len(dims), ' item_count 合计 =', sum(d['item_count'] for d in dims))
print('成熟量表 =', len(scales))
print('参考文献 =', len(refs))
"
```

读数（原样，未四舍五入未调整）：

```
构念        = 51  键==name_zh 全中: True
维度        = 155  item_count 合计 = 732
成熟量表    = 98
参考文献    = 80
```

### 辅证一：钉桩门禁在同盘面复跑仍绿

```bash
.venv/Scripts/python.exe -m pytest tests/test_construct_kb_census.py -q
→ 9 passed in 0.07s
```
该文件 `:15/:19-22` 把四个数写成硬常量 `TOTAL = 51 / DIM_TOTAL = 155 / ITEM_COUNT_TOTAL = 732 /
SCALE_TOTAL = 98 / REFERENCE_TOTAL = 80`，跑绿即独立佐证这四项未漂。

### 辅证二：源文件在两枚 HEAD 之间**逐字节未变**

```bash
git --no-pager diff --stat 5cefb71 HEAD -- src/questionnaire/construct_kb.py   # → 空输出
git rev-parse 5cefb71:src/questionnaire/construct_kb.py HEAD:src/questionnaire/construct_kb.py
→ 6c150e1caece8428d10f3cafe86a4078e16a503b
→ 6c150e1caece8428d10f3cafe86a4078e16a503b        # 同一 blob
git --no-pager log --oneline 5cefb71..HEAD -- src/questionnaire/construct_kb.py  # → 无提交
```
⇒ 四数对得上不是巧合，而是**被数对象本身没动**。这条比"再数一次"更强：它排除了两班口径不同却偶然同数的可能。

## 2. 与 s920-12 原值逐项对照表

来源：`zcode-bridge/done/s920-12-psy-constructkb-census.result.md`（2026-09-20T02:28，HEAD `5cefb71`）。

| # | 口径 | s920-12 原值 | 本次复算（`f9b93c0`） | 判定 |
|---|---|---|---|---|
| **1** | **构念总数** | **51** | **51** | ✅ 一致 |
| | ↳ 子口径「键 == `name_zh`，无别名键」 | 51/51 全中 | `all(k==v['name_zh'])` → True | ✅ 一致 |
| **2** | **维度条数** | **155** | **155** | ✅ 一致 |
| | ↳ 子口径 `item_count` 合计 | 732 | 732 | ✅ 一致 |
| | ↳ 每构念维度区间 | 2–6，无零维度 | 2 ~ 6 | ✅ 一致 |
| **3** | **成熟量表条数** | **98** | **98** | ✅ 一致 |
| | ↳ 每构念区间 / 空串 | 1–4 / 全非空 | 1 ~ 4 / 空串 0 条 | ✅ 一致 |
| **4** | **参考文献条数** | **80** | **80** | ✅ 一致 |
| | ↳ 每构念区间 / 空串 | 1–3（无零文献）/ 全非空 | 1 ~ 3 / 空串 0 条 | ✅ 一致 |
| 5 | 字段完备率 | 51/51 = 100%，八键集合一致 | `{frozenset(v) for v}` 唯一，八键同 | ✅ 一致 |
| 6 | 域标签种数与分布 | 9 种：组织行为 16、临床与健康 8、发展心理学 8、社会心理学 7、认知心理学 5、人格 2、社会心理 2、教育心理 2、认知 1 | 逐桶完全相同 | ✅ 一致 |
| 7 | `name_en` 去重 | 50（唯一重复＝工作投入/员工敬业度共用 Work Engagement） | 50 | ✅ 一致 |
| 8 | `definition` 长度区间 | 78–174 字 | 78 ~ 174 | ✅ 一致 |
| 9 | `typical_scale` 非空 | 51/51 | 51/51 | ✅ 一致 |
| 10 | 锚点：`:13 CONSTRUCTS = {` ＋ 模块 1199 行 | 成立 | 行 13 逐字为 `CONSTRUCTS = {`，模块 **1199** 行 | ✅ 成立 |

**结论（只做对账，不作处置）：四个待核数值 51 / 155 / 98 / 80 在 HEAD `f9b93c0` 全部复核通过，
连带的 6 项子口径也一项不差。s922-11 记的那笔"未复核"欠账到此结清。**

**对不上的项：无。** 因此本节不提任何改档建议——没有差异需要裁决。

## 3. 复核顺带发现的两个「看守强度」问题（登记，不修）

这四数是**被谁看着**的？全仓普查"还有谁断言了构念数"，结果如下。

| 文件 | 断言形态 | 能不能拦住漂移 |
|---|---|---|
| `tests/test_construct_kb_census.py:15,19-22,26,52,73` | 硬常量 `== 51 / 155 / 98 / 80 / 732` | ✅ 精确，增减都红 |
| `tests/test_construct_kb_extended_placeholder.py:42,104` | 硬常量 `CENSUS_TOTAL = 51` | ✅ 精确（只拦构念数这一维） |
| `tests/test_questionnaire_design.py:101` | `assert len(CONSTRUCTS) >= 40` | ⚠️ **松下界**：掉到 40–50 之间的任何缩减、或涨过 51，**全都不红** |
| `tests/test_llm_engine.py:15` | `print(f"All {len(CONSTRUCTS)} constructs …")` | ❌ 只打印，非断言 |

1. **`tests/test_questionnaire_design.py:101` 的 `>= 40` 是一扇虚掩的门**。
   现值 51，下界 40 ⇒ 有 11 个构念的静默消失空间。与纪律档 §十二 记的 learning 仓
   `test_paths.py:29`（`>= 3` 而现值 6，让 README 口径存活 68 天）同族。
   **收紧它 = 改测试语义，本单不动**，交主班定：要么并到 census 的硬常量上，要么显式保留宽松意图并注明理由。
2. **普查四数只有 `test_construct_kb_census.py` 一个文件在硬钉**（外加扩展件的 51）。
   文档面反而干净：`git --no-pager grep -n --no-index -E "\b(51|155|98|80)\b" -- docs/ README.md KNOWN_ISSUES.md`
   配合"构念/维度/量表/文献"过滤 → **0 命中** ⇒ 这些数值**没有以文字形式散落到任何 md**，
   也就不存在"改了数据忘了改文档"的漂移面。这是个好消息，不是问题。

### 关于「跳过标记」的自查（纪律档 §四 要求）

纪律档提醒"判某件有无单测要先查它是否被标记跳过"。逐个查了四个声称件：

```
.venv/Scripts/python.exe -m pytest <四件> -q -rs
→ 36 passed, 1 skipped
SKIPPED [1] tests\test_construct_kb_extended_placeholder.py:118: got empty parameter set for (construct_name)
```
该 skip **不是"假装有测试"**：`EXTENDED_CONSTRUCTS` 今天是空 dict，`:118` 的 parametrize 因此拿到空参数集；
而同文件 `:133 test_census_schema_case_is_currently_vacuous_by_design`（docstring 原文即"上一条今天是
1 例 skipped……不是静默消失"）＋ `:140 assert sorted(EXTENDED_CONSTRUCTS) == []` 把这个空态**显式钉住**了。
⇒ 属已由前人登记的刻意设计，本次不重复登记，仅在此说明以免后来人误判为漏检。

## 4. 本单的完成标准自证

| 完成标准 | 状态 | 证据 |
|---|---|---|
| 报告含 HEAD sha（`git rev-parse --short HEAD` 内联） | ✅ | 第 0 节，短＋全两值，并声明取值时刻 |
| 四个数值的复算命令与读数 | ✅ | 第 1 节主命令＋读数原样贴出；另有两条辅证 |
| 与 s920-12 原值逐项对照表 | ✅ | 第 2 节 10 行对照（4 主口径＋6 子口径） |
| 零写库零改档（porcelain 除新报告外无变化） | ✅ | 见下 |

### 零副作用自证

```bash
git status --porcelain -- src/questionnaire/construct_kb.py tests/test_construct_kb_census.py
→ （空）                    # 被数对象与钉桩件都未改
git --no-pager diff --name-only -- src/questionnaire/   # → （空）
不变量 data/benchmark_history/ 逐文件 sha256_8 = 3d83f7e9 / dff47515 / 092d61b0 / 909b4799（与开工基线逐位相同）
```
产物只有本文件一件。全班（含前两单）未 commit、未 add，`git diff --cached --name-only` 保持 0 行。

## 5. 红线声明

本单数的是**知识库条目的形状与个数（元数据）**，不是任何被测数据的统计量；
不对任何构念定义的文字作学术有效性判断，也不为 `domain` 分桶背书内容含义。
"临床与健康"仅作为计数分桶出现，其条目文字未读未评。零 LLM 调用、零网络、零写库、零积分。
