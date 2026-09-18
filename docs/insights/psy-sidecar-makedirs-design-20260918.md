# psy side-car 落盘「目录不存在自动创建」增强设计稿（s918-13，只读不落码）

生成：2026-09-19 01:2x｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
**零源码改动**（本单只出本文件）。锚点 `docs/insights/psy-benchmark-sidecar-edges-20260916.md:17`
原文「实现无 makedirs＝任务书期望『创建目录后成功』不成立——按『不改生产实现』锁定现状」**逐字命中** ✓。

## 一、写盘点定位（file:line）

被测实现不在 psy 仓内，而在**桥侧草案脚本** `D:/code/zcode-bridge/tmp/d913d-11/backfill-draft.py`（6768 B，mtime 2026-09-16 01:20）。
`apply_sidecar`（:83）里有**两处写盘**，两处都可能因父目录不存在而失败：

| 位置 | 语句 | 失败面 |
|---|---|---|
| **:104** | `sidecar_path.write_text(text, encoding="utf-8")` | 主写点。父目录缺失 → `FileNotFoundError` |
| **:100** | `backup.write_bytes(sidecar_path.read_bytes())`（`.json.bak`） | 仅当 side-car 已存在时触发；此时父目录必然已存在 ⇒ **实际不会因目录缺失失败** |

默认路径不会踩坑：`:92` `sidecar_path = sidecar_path or (bench_path.parent / "benchmark_backfill_draft.json")`
——不显式传参时 side-car 与 bench 同目录，父目录必然存在。**只有显式传 nested `sidecar_path` 才暴露**（测试正是这么打的）。

## 二、现状复现命令（附卷）

```
cd /d/code/psy-analysis
.venv/Scripts/python.exe -m pytest tests/test_benchmark_backfill_sidecar.py::test_sidecar_in_uncreated_directory_currently_fails -q
```
→ 该用例（:96-106）以 `pytest.raises(FileNotFoundError)` **主动锁定**「不建目录」的现状，
docstring 自注为「契约↔实现差异记录」。
另有 `:87 test_missing_bench_source_fails_loudly` 锁定「源缺失也抛 FileNotFoundError 且不落半成品」。

## 三、若要补：注入位置与异常面

建议**一处**加在 `:98` 的 `if sidecar_path.exists():` **之前**：

```
sidecar_path.parent.mkdir(parents=True, exist_ok=True)
```

- 为什么放 :98 前而不是 :104 前：放 :104 前也能修主写点，但会把「建目录」与「判存在」割裂，
  读代码的人无法立刻看出 `.bak` 分支也依赖目录就绪；放 :98 前一次覆盖 :100 与 :104 两个写点。
- 幂等安全：`parents=True, exist_ok=True` 对已存在目录是 no-op，二次运行不报错。
- **异常面变化**：失败原因从 `FileNotFoundError`（找不到路径）变为 `OSError`（权限／只读盘／路径非法）。
  两者都是 `OSError` 家族（`FileNotFoundError` 是子类），所以现有 `pytest.raises(FileNotFoundError)` 的两条用例里，
  `:96` 那条会**转为失败**（不再抛 FNF），`:87` 那条不受影响（它测的是 bench 读取，早于写盘）。
- 原子性：现状 `write_text` 失败时不会留下半成品（`open` 阶段即抛），补 mkdir 后仍成立；
  但 mkdir 成功、write 失败时会**留下一个空目录**——副作用面略增（可接受，side-car 本就允许重跑）。

## 四、与 `.bak` 守卫的交互

`:98-101` 的语义是「side-car 已存在 → 先整份备份为 `.json.bak`」。加 mkdir 后：

- 全新 nested 目录：`mkdir` 建出目录 → `sidecar_path.exists()` 仍为 **False** → **不走 `.bak` 分支** → 直接首写。✅ 语义正确，无多余备份。
- 既有 side-car：目录早就存在，`mkdir(exist_ok=True)` no-op → 行为与现在逐字一致。✅
- 唯一新暴露：`.bak` 用 `with_suffix(".json.bak")`，若 side-car 名不含 `.json` 后缀，`with_suffix` 会替换而非追加
  （例：`foo.txt` → `foo.json.bak`）——**这是既有实现的既有行为，与 mkdir 无关**，本单只登记不处置。

## 五、正反两案影响表

| 维度 | 案 A：**补** mkdir | 案 B：**不补**（维持现状锁定） |
|---|---|---|
| 契约一致性 | 与任务书期望「创建目录后成功」一致；调用方无需自建目录 | 契约与实现长期不一致，靠测试注释兜住 |
| 现有测试 | `:96` 用例必须改写（从「断言抛 FNF」改为「断言自动建目录并成功」）——**这是改测试去追实现**，需留痕 | 0 改动 |
| 失败信号 | 由「路径不存在」变成「建不出来（OSError）」，排障更准 | 保持 FNF，语义清晰但要求调用方自备目录 |
| 副作用 | 写失败时可能留下空目录 | 无 |
| 幂等/并发 | 不变（`exist_ok=True`；同路径并发仍是 `.bak` last-writer-wins，既有语义） | 不变 |
| 迁移成本 | 一行代码＋一个测试改写 | 无 |
| 谁受影响 | 只有显式传 nested `sidecar_path` 的调用方；默认路径（同目录）**今天就不受影响** | 同左 |

**本单倾向**：影响面窄（默认路径根本不受影响），而「契约↔实现不一致」是靠一条自注测试硬锁着的——
这种锁定态越久越容易被后人误读成"设计如此"。若日间无其它优先项，**案 A 的净收益为正且成本极低**；
但**属行为增强，需授权**，故本单不落码。

## 六、比 makedirs 更要紧的一件事（结构性风险）

`tests/test_benchmark_backfill_sidecar.py:13-19` 用 `importlib` **在收集期执行**
`D:/code/zcode-bridge/tmp/d913d-11/backfill-draft.py`，且 `SCRIPT` 与 `BENCH` 两个路径**硬编码绝对路径**。
实测：

- 根仓 `.gitignore:46` 就是 `tmp/` ⇒ `git check-ignore -v` 确认 `zcode-bridge/tmp/d913d-11/backfill-draft.py` **被忽略、未跟踪**；
  它同时躺在名字带 `tmp` 的目录里，**`git clean -fdx` 或任何一次 tmp 清理都会把它抹掉**；
- 被依赖的基准文件 `psy-analysis/data/benchmark_history/socratic_benchmark_20260909T192139Z.json`（14643 B）
  也落在 psy 被忽略的 `data/` 段里；
- 一旦草案丢失，`_spec.loader.exec_module(mod)` 在**收集阶段**就抛错，**psy 全量 pytest 直接 collection error**（不是单个用例失败）。

⇒ 建议日间优先处理这条，而不是 makedirs：把草案**转正**（挪进 psy `scripts/` 或 `src/` 并去掉连字符名，
测试改为经包路径 import），或在测试里加 `pytest.skip` 守卫（草案不存在时跳过而非炸收集）。
这与本夜班 `s918-15`（README 无 `.env.example`）、`s918-17`（相对路径嵌套残骸）同属「产物/依赖住在易逝位置」一族。

## 七、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 报告含写盘点 file:line ＋ 现状复现命令附卷 | 写盘点 `:104` 与 `:100`（§一），复现命令 §二 | `cd /d/code && grep -n "write_text\|write_bytes" zcode-bridge/tmp/d913d-11/backfill-draft.py` |
| 零源码 diff | 本单只新增本报告一个文件。**注意**：`tests/test_benchmark_backfill_sidecar.py` 当前是 `M `（**他人 staged 未提交**，属 n916x-32 那批），本单未写它——它的 mtime 是 **2026-09-18 01:21**，早于本会话起点（09-19 00:06）。草案 `backfill-draft.py` mtime 仍 09-16 01:20 | `cd /d/code/psy-analysis && stat -c '%n %y' tests/test_benchmark_backfill_sidecar.py`；`stat -c %y /d/code/zcode-bridge/tmp/d913d-11/backfill-draft.py` |

## 遗留问题

1. §六 的「测试依赖 git-ignored 的 tmp 草案」是本单最高价值发现，建议单开一列进 BACKLOG。
2. `.bak` 的 `with_suffix` 行为（第四节末）属既有实现细节，本单未验证其是否曾在真产物上发生过（只看代码）。
3. 本单未跑 `-k sidecar` 全 7 例（不在完成标准内，且它会 import 草案）；只锁定定位与两案分析。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
