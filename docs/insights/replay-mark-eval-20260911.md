# psy golden 回放测试 mark 语义与 CI 接入评估（2026-09-11/12 夜间执行班，任务 p911r-32，零写库）

> 执行：GLM-5.3-Flash 夜间执行班 sweep-20260911-2300。**本单只出评估材料，未改 conftest.py 与任何测试文件；未联网。**

## 一、现状（file:line + 运行输出）

- 测试文件：`tests/test_socratic_quality.py`
  - `:22` `pytestmark = pytest.mark.benchmark`——**模块级标记，连坐全部测试**；
  - `:54` 原联网基准测试 `@pytest.mark.benchmark`（`:59` 无 `BENCHMARK_LLM_API_KEY` 即 `pytest.skip`）；
  - `:137-156` c448 新增**离线回放** `test_socratic_quality_replay_offline`（golden 报告 fixture 回放，30 案例、零真实调用、monkeypatch 断言 real=0）——同样被 `:153 @pytest.mark.benchmark` 标记。
- skip 机制：`tests/conftest.py:54`（`--run-benchmark` 选项）、`:62-68`（未传旗标 → 所有 benchmark 标记测试加 skip）。
- 运行证据：
  ```
  $ pytest tests/test_socratic_quality.py -v            → 3 skipped in 0.07s   ← 默认 CI：回放测试从不执行！
  $ pytest tests/test_socratic_quality.py --run-benchmark -v → 2 passed, 1 skipped in 1.18s
  ```

## 二、两种落法对比

| 维度 | 方案 A：独立 `replay` mark（可进常规 CI） | 方案 B：保持现状（skip） |
|---|---|---|
| 改动点 | ①conftest.py 注册 `replay` marker（`:74` markers 列表加一行）②`test_socratic_quality.py:153` 的 `@pytest.mark.benchmark` 改为 `@pytest.mark.replay`（不再连坐跳过） | 零改动 |
| 运行行为 | 离线回放进入**默认 CI 全跑**（纯本地 fixture、确定性、~1s）；联网首跑仍需 `--run-benchmark`+key（原路径不动） | 回放仍只在手动 `--run-benchmark` 时执行 |
| 风险 | fixture 文件（`tests/fixtures/_benchmark_reports/benchmark_20260910_031938.json`）必须随仓存在，缺失即 CI 失败（显性暴露，属期望保护）；golden 与功能演进脱节时需人工重录 | **CI 永不执行离线回放 → 回放测试的回归保护为零**（c448 的价值落空） |
| 影响面 | 全量 pytest 通过数 +1；无网络、无付费 | 无 |
| 推荐 | ✅ **推荐**（回放本就是零联网设计，跳过它违背 c448 初衷） | 仅当 fixture 暂不能入仓时临时采用 |

**第二 golden 快照需联网首跑**（设 `BENCHMARK_LLM_API_KEY` 后 `--run-benchmark` 产生新 golden 报告）——**本单不产生**（禁联网）。

## 三、零改动声明

`git status --short` 无测试文件与 conftest 变更（仅本班前序单的 crawler 文件）；未联网；未 commit/push。
