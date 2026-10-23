# psy 文档偏离对账清单（s1023-10 出材件：README / KNOWN_ISSUES vs 现值）

> 性质：**只读对账件，零改动**。实测时点 2026-10-24 03:2x（系统 python 3.12.9，与 KNOWN_ISSUES:40 三读注记同侧口径）；`.venv` 口径数字未混入（两口径不可混比约定见 docs/TESTING.md）。近批落码锚点：s1012/s1014 批及本班 s1023-02~07。

## 一、README.md 档（6 项核对）

| # | 文档声称 | 实测 | 判定 |
|---|---|---|---|
| R1 | 目录节「tools/ 开发者工具（unused_import_census 死 import 普查，只报不改）」 | `tools/unused_import_census.py` 在档 | 一致 |
| R2 | 「方法目录（method_catalog.py）、方法 ID（method_ids.py）、分析契约（contracts.py）」 | 三件均在 `src/analysis/` | 一致 |
| R3 | 验证节 `scripts.release_gate`／`scripts.perf_smoke` | 两脚本在 `scripts/` | 一致 |
| R4 | 「本文不抄列任何测试计数，改口径只改 docs/TESTING.md」 | 全文零测试计数 | 一致（自守设计，滞后免疫） |
| R5 | `src/literature*/` 文献模块 | literature_feed／literature_review 等在档 | 一致 |
| R6 | 环境变量示例（DEEPSEEK_MODEL=deepseek-v4-flash 等） | 示例性质，未核 src 默认值 | 不判漂 |

**README 结论：零实质漂移。**

## 二、KNOWN_ISSUES.md 档（8 项核对；s1023-07 刷新后现值）

| # | 文档声称 | 实测（2026-10-24） | 判定 |
|---|---|---|---|
| K1 | :40-45 三读数：全量 5636／`not online` 5606（deselect 30）／`not (e2e or playwright)` 5600（deselect 36）＠2026-10-02 | 全量 **5792**／`not online` **5792（deselect 0）**／`not (e2e or playwright)` **5756（deselect 36）** | **漂移①（数字滞后）**：全量 +156；`not online` deselect 30→**0**（online 围栏已清空：`-m "online"` 现收 0 项，`pytest.mark.online` 仅剩 test_literature_feed_fetchers.py 一处非标记引用；pytest.ini:12 s1007-24「自 online 围栏改标」注记佐证）；deselect 36 稳定 ✓ |
| K2 | #L2 :63「paper_writing_ui.py (678 行独立 mode，2026-09-21 复测)」 | `wc -l` = **682** | **漂移②（数字滞后）**：+4 行 |
| K3 | #L3 :70 末次归档 `socratic_benchmark_20260909T192139Z.json`；9/16 backfill 草稿未入库；`.github/workflows` 不存在 | 末次归档同件 ✓；`benchmark_backfill_draft.json` 在档未入库 ✓；workflows 目录不存在 ✓ | 一致 |
| K4 | #L1 :58「bootstrap_check.py 的 DEFAULT_STALE_HOURS = 24」 | `src/literature_feed/scheduler/bootstrap_check.py:31` = 24.0 | 一致（文档未限定路径，实际在 scheduler/ 子包——补注级，不计漂） |
| K5 | #L1 :59「src/literature_feed/ 已实现（fetchers/parsers/extract/scheduler 全链路）」 | 四子包在档（s1023-09 实读） | 一致 |
| K6 | P1 E2E 行「26 skip 条目＝25 标记用例＋1 模块级 importorskip（.venv 口径）」；归因 tests/test_playwright_e2e.py:24 | :24 importorskip 在档 ✓；本对账系统侧 `-m "playwright or e2e"` 收 **36 项**（playwright 已装侧，=25+11 与「补装后待重跑 36 例」自洽） | 一致（口径注记：36≠25 系两口径差，非漂移） |
| K7 | P1 多实例行／P2 交付入口行／P2 编排层拆分（「app.py 体量较大」） | 多实例行 s1023-07 已刷新（0ff50a6）；app.py = 2427 行（定性一致） | 一致 |
| K8 | :43「`-m "not slow"` 已成空口径（mark.slow 注册与使用均零命中）」 | `mark.slow` 计数 = 0 | 一致 |

**KNOWN_ISSUES 结论：实质漂移 2 处（K1 测试计数三读滞后＋online 围栏清零未记、K2 678→682）；其余 6 项一致。**

## 三、两档之外连带发现（登记不扩写）

1. `docs/insights/psy-thresholds-module-design-20261006.md:24` 登记表行号指针（:22/:91/:121 等）指向 46 行 thresholds.py 的虚无行——s1023-04 已留痕，属设计稿滞后，非两档范围。
2. KNOWN_ISSUES:114 所引 `psy-multiprocess-lock-design-20260912.md` 缺失——**已由 s1023-07 闭合订正**（0ff50a6），本次复核确认现值正确。
3. KNOWN_ISSUES:135 执行纪律注（s930-09 案例）引用 `zcode-bridge/done/` 两 result——桥内文件，未核（跨 cwd 只读限锚点，不扩）。

## 四、处置建议（留主班/下批，本件不改档）

- K1：三读注记为**时点值**性质，建议下批 KNOWN_ISSUES 单补 2026-10-24 读数（5792/5792/5756）并把「online 围栏清空（deselect 0）」显式入注——继续沿用「三数并列勿混用」格式。
- K2：#L2 行 678→682 行号注刷新（或改「约 680 行」防再漂）。
