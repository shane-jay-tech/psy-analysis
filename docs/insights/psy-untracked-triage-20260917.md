# psy 全仓未跟踪文件盘点（r917-37，p917-37 重投）

- 生成时间：2026-09-20T12:48:29+08:00

## 一、porcelain 全量（命令与数字同段）

命令：
```
(git status --porcelain).Count ; git status --porcelain
```
输出：
```
8
---
 M app.py
 M pytest.ini
 M requirements-lock.txt
?? node_modules/
?? tests/test_analysis_contracts.py
?? tests/test_lock_alert_log.py
?? tests/test_perf_smoke_report.py
?? tests/test_startup_checks.py
```
**行数 = 8**（3 ` M» + 5 `??»）。

## 二、按目录分组 + 逐项判定（分组表 8 行 == porcelain 行数 8 ✅）

| # | 路径 | 组 | 判定 | 依据 |
|---|---|---|---|---|
| 1 | `app.py» | 根目录（已修改） | **待归属** | 应用主入口被改，改动语义未核（可能属 815ac64/d8cde5f 同批或在途） |
| 2 | `pytest.ini» | 根目录（已修改） | **应入库** | 测试配置；应在测试批次内提交 |
| 3 | `requirements-lock.txt» | 根目录（已修改） | **应入库** | 依赖锁文件；入库才有可复现性 |
| 4 | `node_modules/» | 第三方 | **应删（或 gitignore）** | JS 依赖目录，**绝不应入库**；建议加入 `.gitignore» |
| 5 | `tests/test_analysis_contracts.py» | tests/ | **应入库** | 新增测试（对应 916-04 literature_manager 盲区测试族） |
| 6 | `tests/test_lock_alert_log.py» | tests/ | **应入库** | 新增测试 |
| 7 | `tests/test_perf_smoke_report.py» | tests/ | **应入库** | 新增测试 |
| 8 | `tests/test_startup_checks.py» | tests/ | **应入库** | 新增测试 |

**判定计数：应入库 6 / 运行产物 1（node_modules）/ 应删 0（建议 gitignore 而非删）/ 待归属 1（app.py）。**
**算式校验：6 + 1 + 0 + 1 = 8 == porcelain 行数 ✅**

## 三、本批可收口清单与命令草案（**逐路径精确 add，不执行**）

```powershell
Set-Location D:\code\psy-analysis
# 建议批次 1：测试与配置（可机械复核、低风险）
git add pytest.ini requirements-lock.txt
git add tests/test_analysis_contracts.py tests/test_lock_alert_log.py tests/test_perf_smoke_report.py tests/test_startup_checks.py
# 建议批次 2（需先核 app.py 改动语义，本单未核）
# git add app.py
# 建议 gitignore（不入库）：node_modules/
```
**本单未执行上述任何一条**（禁止事项要求「不 add/commit/clean」）。

**`app.py» 不进本批**：其改动语义未经核验（属"待归属"），按纪律**不猜**。

## 四、与 `psy-uncommitted-signoff-20260917.md» 的关系

同族既有产物 `psy-uncommitted-signoff-20260917.md»（4988B, mtime 09-19 17:42）是**签核**；本单是**盘点 triage**——两者互补：签核给"是否放行"，本单给"每一行归到哪一类"。

## 五、只读证明（操作前后 porcelain 行数对照）

本单**未 add/commit/clean、未改文件**；操作前后 porcelain 行数对照：**8 → 8**（唯一写入为新增本报告文件，该文件在报告写完后才出现，不影响取证时点的 8 行读数）。

## 六、遗留

1. **`app.py» 归属不清**——需日间核其 diff 语义后才能决定是否入库。
2. `node_modules/» 出现在 porcelain 说明**未被 gitignore**；建议日间加规则（本单不改 `.gitignore»）。
3. 4 个新增测试文件是否全绿未跑（跑测试会产生副作用与耗时；本单只做**盘点**，不做测试核验）。