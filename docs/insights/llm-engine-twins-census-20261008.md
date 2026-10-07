# llm_engine 双胞胎架构普查（s1010-37，只读材料零改码）

- 日期：2026-10-08 ｜ 对象：`src/experiment_design/llm_engine.py`（300 行/11 函数）vs `src/questionnaire/llm_engine.py`（866 行/24 函数）
- 锚复核零漂移：`diff | grep -c '^[<>]'` = **894** ✓；双件 porcelain 干净
- 防撞：s1010-13 只收编 cancel 三函数（三份同体＋gateway 第四变体，函数粒度）；本单整模块双胞胎普查（架构粒度）

## ①结构对照

| 类别 | 函数 | 占比 |
|---|---|---|
| **同体骨架**（同名且函数体逐字同，difflib ratio=1.00，5 枚） | `_alloc_cancel_id`(ED@43/QN@44,2行)、`_is_cancelled`(61/62)、`_cleanup_cancel_id`(66/67)、`_call_llm`(71/255,11行)、`_cleanup`(296/702) | ED 45%、QN 21% |
| **同名异体**（3 枚） | `_build_system_prompt`(ratio .50，域提示词异)、`_build_user_prompt`(.00，ED 8 行 vs QN 2 行载荷异构)、`cancel_design_request`(.50，同形异引擎) | — |
| **ED 独有**（3 枚） | `_parse_json_response`、`design_experiment_llm(_async)` 入口双件 | ED 27% |
| **QN 独有**（16 枚） | 缓存四件套(`_design_cache_get/put/_make_design_cache_key/_run_with_cache`)、质量门(`_run_local_quality_gate`)、修复链(`_try_repair_truncated_json`/`_parse_and_validate`)、逆向改写双件(`rewrite_reverse_item_llm/rewrite_all_reverse_items`)、追踪(`_record_design_trace`/`_default_scoring`/`_build_design_dict`/`_cleanup_imm`)、`clear_design_cache`、入口双件 | QN 67% |

重叠率：同名 8/11（ED 视角 73%）vs 8/24（QN 视角 33%）——**QN 是 ED 的超集演化体**（加缓存/质量门/修复/改写四能力），非平行分叉。

**同体族全景（超双胞胎）**：`_alloc_cancel_id` 仓内生产件共 **4 处**（ED、QN、paper_writer/literature_search_async、questionnaire/llm_engine_premium）＋gateway 第五变体（`llm_gateway/gateway` 自有 `_cancel_flags/_new_cancel_id` 族，测试件 test_llm_cancel.py 所指）；测试件 2 处引用（test_experiment_design_llm.py、test_literature_search_async.py）。s1010-13 收编面=其中三份＋premium 变体，gateway 族不在其内。

## ②归一两案（波及计数）

### 案 A：公共骨架下沉（新 `src/utils/llm_cancel.py` 收 5 同体函数≈19 行）
- 生产件波及：4（ED/QN llm_engine、literature_search_async、llm_engine_premium 改 import＋删除本地副本）
- 包出口兼容层：2（experiment_design/__init__.py:47、questionnaire __init__ 的 cancel_design_request 再出口保持——调用方可零改动）
- 直接调用方：4（experiment_design_ui.py:145、session_reset.py:143-146 双引擎双导入退路、questionnaire_panel.py:12、design_engine.py 间接）——**session_reset 的 try/except 双导入形态下沉后可简化为单导入**（顺带收益，非本单动作）
- 测试随动：3（test_llm_engine.py、test_experiment_design_llm.py、test_literature_search_async.py 的 import/打桩路径）
- 风险：`_call_llm` 同体但闭包依赖各自模块级配置（ED/QN 的常量与 client 构造），下沉需参数化注入——**实改工作量集中于此**；s1010-13 若先行下沉 cancel 三函数，本案改为对齐其公共件避免二次搬家
- 计数小计：**13 处**（4+2+4+3）

### 案 B：维持双轨＋防漂移钉
- 生产改动 0；新增 1 测试件（golden 钉：双文件 5 同体函数逐字比对，漂移即红）
- 计数小计：**1 处**
- 适用：s1010-13 尚未收编前，先钉住现状防继续漂

**裁决建议**：序＝**先 B 后 A**——B 的 golden 钉是 A 的安全网（钉住「下沉前零漂移」前提）；A 的启动前置＝s1010-13 落地形态明确（公共件落在哪、叫什么）。QN 独有 16 枚不参与下沉（各域私有能力）。

## ③零改码声明

本单零代码改动；唯一产出＝本普查档。锚点现值：ED 300 行/11 函数、QN 866 行/24 函数、diff 894 行，与本班实测逐项一致。

## 复现

```
$ wc -l src/experiment_design/llm_engine.py src/questionnaire/llm_engine.py   # 300 / 866
$ diff src/experiment_design/llm_engine.py src/questionnaire/llm_engine.py | grep -c '^[<>]'   # 894
$ python AST 函数清单对照（ast.walk FunctionDef，difflib.SequenceMatcher 比函数体）  # 同名 8、ratio 见①表
$ grep -rln '_alloc_cancel_id' src tests --include=*.py   # 4 生产件 + 2 测试件
```
