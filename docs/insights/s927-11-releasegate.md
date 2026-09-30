# s927-11 — scripts/research_release_gate.py 功能测绘与测试补位

- 日期：2026-09-30
- 任务：zcode-bridge/inbox/s927-11.task.md（result: outbox/s927-11.result.md）
- 对象：`scripts/research_release_gate.py`（141 行，untracked ?? 件）

## 一、功能测绘

**定位：研究线发布门禁（与产品线 release_gate.py 是姊妹件，不是重复建设）。**

- 五环节串联：①数据来源（`data/literature_feed/feed.sqlite` 只读完整性＋sources 非空）→ ②统计检查（test_golden_stats_v2＋effect_size_ci＋golden_delivery）→ ③图表（visualization_charts＋apa_figures_v2＋figure_collection）→ ④主张校准（evidence_quality）→ ⑤匿名化（guardrails_pii＋pii_probes）。
- **三态输出**（与 release_gate.py 的两态 0/1 相比的唯一结构性差异，也是存在价值）：任何环节失败→FAIL(1)；全绿但无人工签收→**BLOCKED(2)**（统计结论必须有人复核）；全绿＋`--confirm-review 姓名`→PASS(0) 且落 `HUMAN_REVIEW.json`（复核人＋时间戳）。
- 证据链：每环节的命令、退出码、输出尾（≤2000 字符）落 `tmp/gate-evidence/<时间戳>/<环节名>.json`——可复跑可审计。
- `--fail-probe`：注入必败环节（exit 3），演练 fail 态通路。
- 与既有件的关系：`release_gate.py`（tracked）管**产品**质量自检（测试/ZIP 导出/Word 导出/金标准，走 .venv）；本件管**研究结论**的发布（统计/图表/主张/PII），走全局 python。两者 stage 集合零重叠、退出码语义不同（本件多 blocked 态）、互不调用——与 result_card/interpretation 无直接代码耦合（环节④的 test_evidence_quality 间接受护主张文案面）。
- 可测性：良好——三态判定/证据落盘/数据源检查/run_cmd 边界全部可 monkeypatch 级单测；重 pytest 环节经 `run_cmd` 注入即可旁路。

## 二、三案与推荐

| 案 | 内容 | 评价 |
|---|---|---|
| **A 入库＋测试补位** | 脚本原样入库（`git add scripts/research_release_gate.py`），补 pytest 件钉契约 | ✅ **推荐**：功能自洽、与产品线门禁互补、零生产耦合；测试件 12 例已交付（本轮实测 12 passed / <2s，全 tmp 隔离不碰真库） |
| B 重写 | 按产品线 release_gate 的风格重写（.venv、argparse 子命令等） | 收益仅风格统一；三态语义/证据落盘/签收件是产品线件没有的增量，重写纯损耗 |
| C 弃置 | 删除 | 若研究线发布流程确不用可弃，但 141 行含完整证据链设计，弃置前须主班确认研究线另有一套等价门禁——目前没看到 |

**推荐 A。** 入库前缺陷登记见 §三（不阻塞入库，修法一行）。

## 三、缺陷登记（登记不修，任务书授权面）

- 🔴 **损坏库面崩**：`check_data_sources` 对损坏的 feed.sqlite（非 sqlite 文件）会抛 `sqlite3.DatabaseError`（:49 connect/pragma 段无 try/except），门禁以 traceback 崩溃而非按契约返回 `(False, detail)`→FAIL 态。修法：该段包 `try/except sqlite3.Error → (False, f"corrupt: {e}")`，一行级。tests/test_research_release_gate.py::test_数据源_库损坏_现缺陷登记 已按现行为钉桩并注明修后翻转为 `ok is False`。

## 四、测试补位（已交付）

`tests/test_research_release_gate.py`（12 例，全 tmp/monkeypatch 隔离，零真库/零网络/零重 pytest）：
- 三态判定 3 例（blocked/pass＋签收件内容/fail 压过签收）；fail-probe 1 例（必败压过签收）
- check_data_sources 4 例（缺失/完好/空表/损坏现状登记）
- run_cmd 4 例（退出码透传/尾截 2000/超时 124/非零透传）
- 隔离关键：`rg.BASE→tmp_path`（证据目录落 tmp）＋ `rg.run_cmd/rg.check_data_sources` 注入；main() 经 argparse 读 sys.argv，测试侧 argv 注入。

## 五、遗留问题

- 脚本入库与否由主班拍板（推荐 A）；若入库建议连同测试件与缺陷修（§三一行）同批。
- `release_gate.py` 硬编码 `.venv/Scripts/python.exe`（本机无 .venv 则跑不了）——产品线件自身问题，与本单无关，顺手点名。
- tmp/gate-evidence 累积无清理策略（tmp/ 已 gitignore，量级小，暂不需处置）。
