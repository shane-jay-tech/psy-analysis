# cancel-id 注册表三胞胎归一裁决材料（s1010-13，只读零改码）

- 日期：2026-10-08 ｜ 对象：`_alloc_cancel_id/_is_cancelled/_cleanup_cancel_id` 三份生产拷贝＋gateway 第四变体
- 性质：**材料单零改码**；取消语义行为零变更；LLM 取消链路属交互红线面，裁决权留主班

## ①三份逐行对照表（证同体，ast 逐行 diff）

| 函数 | ED llm_engine | QN llm_engine | LSA literature_search_async | 对照结论 |
|---|---|---|---|---|
| `_alloc_cancel_id` | :43 | :44 | :26 | ED≡LSA 逐字；QN 仅注册表名 `_cancel_flags` 差（ratio .857） |
| `_is_cancelled` | :61 | :62 | :44 | ED≡LSA 逐字；QN 同上命名差（ratio .667） |
| `_cleanup_cancel_id` | :66 | :67 | :49 | ED≡LSA 逐字；QN 同上命名差（ratio .667） |

- 注册表声明：ED `cancel_flags: dict = {}` @26、LSA 同名 @17、QN `_cancel_flags: dict = {}` @27；三件均有模块级 `_cancel_lock = threading.Lock()`（ED@27/QN@28/LSA 对应行），全部读改在锁内。
- 公开名差：ED/QN `cancel_design_request`（ED@52/QN@53）、LSA `cancel_search_request`（@35）——函数体亦同构（锁内 `in` 判断＋置 True）。
- **锚点漂移核验**：任务书称三份——实核 `grep -rln _alloc_cancel_id src` 另命中 `questionnaire/llm_engine_premium.py`，逐查为 **import 消费方非拷贝**（:26 `from .llm_engine import (_alloc_cancel_id, _cleanup_cancel_id, _is_cancelled)`），生产拷贝确为 3 份，锚点无漂移。

## ②归一两案材料

### 案 A：抽 `utils/cancel_registry` 单源＋三处薄壳转调
- 新建 `src/utils/cancel_registry.py`：注册表 dict＋Lock＋三函数（int 轴）；三引擎改为薄壳（`def _alloc_cancel_id(): return registry.alloc()` 形，公开名 cancel_design_request/cancel_search_request 保留本地壳转调）。
- 波及面（rg 复核命令见③）：
  - 生产改动：3 件（三引擎函数体换壳）＋1 新件
  - 兼容面零改：premium 的 `from .llm_engine import …` 经 QN 薄壳继续可用；包出口（experiment_design/__init__.py:47 等）与 session_reset.py:143-146 双导入退路零触碰；测试 3 件（test_experiment_design_llm 4 处、test_literature_search_async 4 处、test_llm_cancel 11 处属 gateway 自有机制）零改动
  - 公开名消费 20 处（rg cancel_design_request|cancel_search_request）经壳保持签名不变
- 线程锁语义等价论证：三份现均为「模块级 Lock＋锁内 dict 读改」；单源后锁随注册表走（一把全局锁），**正确性等价**（互斥域不变），代价为三域取消操作共享锁的轻微争用变化（低频路径，无热循环）；QN 另有 `_design_cache_lock` 不受影响。
- 风险：交互红线面（LLM 取消链路）——壳层签名逐字保持可回退；建议落地时带 s1010-37 案 B 的同体 golden 钉先行。

### 案 B：仅同步漂移＋防漂钉（零合并）
- QN 侧 `_cancel_flags`→`cancel_flags` 改名（声明@27＋引用 8 处），三份函数体达逐字同体；新增 1 golden 测试钉三份逐字同体（读源码比对，漂移即红）。
- 波及面：1 件改名（QN）＋1 新测试件；premium/包出口/session_reset/测试零改动。
- 适用：主班暂不动取消链路时的最小防漂动作；案 A 的前置安全网。

**裁决建议**：先 B 后 A（与 s1010-37 双胞胎普查同序）；A 落地窗须独占（交互面）， B 可随时做。

## ③波及计数复核

```
$ grep -rc '_alloc_cancel_id\|_is_cancelled\|_cleanup_cancel_id' src tests --include=*.py | grep -v ':0'
→ ED 6 ／ gateway 9(自有) ／ LSA 6 ／ premium 8(import 消费) ／ QN 8 ／ tests 4+4+11
$ grep -rn 'cancel_design_request\|cancel_search_request' src tests --include=*.py | grep -v 'def ' | wc -l
→ 20
$ grep -rln '_alloc_cancel_id' src --include=*.py
→ 4 命中＝3 拷贝＋premium(消费方)
```

## ④gateway 第四变体收编边界（一行判定）

**不收编**：gateway `_is_cancelled`（gateway.py:442）为 `Optional[str]` 轴＋`_cancel_flags: dict[str, Event]`＋`evt.set()` 事件语义，与三胞胎的 `int` 轴＋`dict[int, bool]` 布尔语义**不同构**（test_llm_cancel.py 11 处归属其自有机制），并档只会造出双轴分支件。

## ⑤零改码声明

本单零代码改动；唯一产出＝本材料档。git status 除本档（untracked）外零改动。
