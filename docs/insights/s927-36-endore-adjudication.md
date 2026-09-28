# `s920-01…14` 终态补记 · 裁决材料（s927-36 · 2026-09-28）

> 性质：**只读位出材料，零改账**。本班未写 `claims.log`（仅按纪律追加本单自己的 claim/done 行）、未动信箱任何账本、未动 `psy-analysis` 生产码。
> 上游需求出处：`zcode-bridge/done/s922-11-psy-b064-endorse.result.md:76`（遗留 1）
> 「**交人工拍板（本单不代签）**：是否为 `s920-01…14` 补记终态行、以及『评审窗班名 `qoder-rev-*` 执行并只留 claim』要不要认定为 B-064 定档下的流程缺陷。补记属改账，纪律与任务书双重禁止，出口＝人工授权后由主班一次性做。」

## 〇、锚点复核（零漂移 ＋ 一处班名形状需按盘改读）

| 任务书前提 | 实测 | 判定 |
|---|---|---|
| 14 单「有 result 无终态行」 | `logs/claims.log` 全账扫 `^s920-0{1..9}\|s920-1{0..4}` → **每单 0 行**（claim 也 0） | ✅ 成立，且比"无终态行"更严：**零行**（连认领行都没有） |
| 同批 `s920-15…26` 有账 | 该窗唯一写入方 `qoder-rev-20260919-1020`：claim 11／done 13／畸形 1（`claim→done`），跨度 00:33–01:53 | ✅ 成立 |
| 「`qoder-rev-*` 执行」＝归属待裁 | 全账 `s920-*` 只被 `qoder-rev-20260919-1020` 一个班名写过（25 行） | ✅ 成立 ⇒ 14 单**无任何署名证据**，只有 result 自述＋commit 署名 |
| 14 单 result 是否齐 | 14/14 在 `done/`，frontmatter `status: done` ＋ `finished` 齐；`id:` 与文件名逐单一致；任务件 14/14 也在 `done/` | ✅ 交付痕迹完整，缺的只有账 |
| 〔新读数，非任务书所据〕这 14 单能不能机读结案 | `git log --all --since 2026-09-19 --until 2026-09-21` → 14/14 **各有且仅有 1 枚 commit**，message 内署名 `（s920-NN）` | ⇒ 可重建"做了没有"，**不可**重建"谁做的"（author/committer 集合单元素 `{psy-analysis}`，s922-11 已证） |

## 一、14 单终态现状表（现取，`HEAD fa3f41e`／claims.log 6,513 行 1,651,082 B）

| id | result（均在 `done/`） | 字节 | 自述 status/finished | 任务件 | claims 行 | psy commit（committer 时戳） |
|---|---|---|---|---|---|---|
| s920-01 | `-psy-psychopy-assembly.result.md` | 6,138 | done / 03:32 | done/ | **0** | `f4db3ef` 03:30:06 |
| s920-02 | `-psy-psychopy-reforder.result.md` | 5,668 | done / 03:22 | done/ | **0** | `c9ece6b` 03:16:19 |
| s920-03 | `-psy-reviewqueue-dualtable.result.md` | 4,472 | done / 03:10 | done/ | **0** | `29ae9c3` 03:08:24 |
| s920-04 | `-psy-review-msg-typed.result.md` | 4,747 | done / 03:12 | done/ | **0** | `cb21145` 03:04:42 |
| s920-05 | `-psy-reliability-bands.result.md` | 6,030 | done / 03:12 | done/ | **0** | `4d5db16` 03:00:16 |
| s920-06 | `-psy-guide-placeholder-4types.result.md` | 6,094 | done / 03:05 | done/ | **0** | `60377ce` 02:53:24 |
| s920-07 | `-psy-usagelogger-try3.result.md` | 6,174 | done / 03:05 | done/ | **0** | `64ba8c2` 02:46:28 |
| s920-08 | `-psy-lockbusy-pid.result.md` | 5,478 | done / 02:55 | done/ | **0** | `5fe7754` 02:38:15 |
| s920-09 | `-psy-paperui-charac.result.md` | 7,029 | done / 03:05 | done/ | **0** | `776a268` 02:32:30 |
| s920-10 | `-psy-qpanel-charac.result.md` | 6,971 | done / 02:36 | done/ | **0** | `dab28da` 02:22:01 |
| s920-11 | `-psy-i18n-zh-pin.result.md` | 4,522 | done / 02:22 | done/ | **0** | `f5de06c` 02:19:11 |
| s920-12 | `-psy-constructkb-census.result.md` | 5,198 | done / 02:28 | done/ | **0** | `5cefb71` 02:16:30 |
| s920-13 | `-psy-litpanel-helpers.result.md` | 5,426 | done / 02:18 | done/ | **0** | `09edaf5` 02:12:40 |
| s920-14 | `-psy-feedpanel-charac.result.md` | 6,294 | done / 02:22 | done/ | **0** | `c5ae1f9` 02:09:17 |

三列并排可读出的事实：**result 齐、任务件齐、commit 齐，只缺账**（14/14 同形）。且 commit 序与 id 序**反号**（`s920-14` 02:09 → `s920-01` 03:30），与 `s920-15` 02:04、`s920-16` 01:51 … `s920-26` 00:44 连成一条不间断的 6–10 分钟节奏链。

## 二、断供点定位（本单的新证据，替掉 s922-11 的"倾向性推断"）

s922-11 当时只有 cadence 论证（「采信后倾向连续，账目断供点正落在 s920-15 的 claim 与其 commit 之间」）。本单取到 26 枚逐笔 committer 时戳，断点变成**可指认的两段**：

| 段 | 覆盖 | 账行 | commit 时戳 |
|---|---|---|---|
| 甲段 | `s920-26 → s920-16`（11 枚） | 有（claim 11／done 13，00:33–01:53） | 00:44:19 → 01:51:30 |
| 断点 | `s920-15` | **只有 claim（01:53），无终态行** | 02:04:08 |
| 乙段 | `s920-14 → s920-01`（14 枚） | **零行** | 02:09:17 → 03:30:06 |

⇒ 不是"评审窗班忘了记账"，而是**从 01:53 之后账本对 psy 域整体断供 1 小时 37 分**，期间 commit 节奏未断（14 枚、约 6.5 分/枚）。同夜 `sweep-20260919-2300` 仍在 01:03–03:34 为 k919/l919/m919/n919 写了 88 行 ⇒ **写账机制在世，psy 侧没人用它**。这把"是否算 `qoder-rev-*` 的流程缺陷"问成了错的问法：**乙段执行者身份本身就未坐实**，把 14 单记到 `qoder-rev-*` 名下等于用未证事实当唯一留痕。

## 三、两案对照（含"补记到底付什么价"的实测）

| 维度 | 案甲：补记 14 条终态行 | 案乙：维持历史行不动（推荐） |
|---|---|---|
| 时戳语义 | 🔴 两难：回填 09-20 假时戳＝**造历史**（`claims.log` 无 provenance 列，注入行与真行不可区分）；用今日时戳＝账面出现「8 天前完成的单今天才 done」，吞吐/时效类读数永久污染。`claims_writer.py --ts` 的帮助文本自己就写着「不建议手填」 | 不动历史 ⇒ 现有 6,100＋ 行时序全部可信 |
| 一致性 | 🔴 个案会立刻变世代闸门：同代缺口远不止这 14 单。实测 `result_claims_recon.py --dry-run --json`：**X1（有 result 无闭合）378 单**（s 域 40，含 `s920-15`）、**X3（有 result 零账行）297 单**（s 域 38）；按域分布 k71／l29／n40／m20／c9／q9／p1／纯时间戳件 71／其它 9。补 14 后 X3 只从 297→283（**−4.7%**） | 缺口不改数，只在**台账与 recon 口径**上定性；不动案底 |
| 下游门禁 | 本班实找过、**未找到**："补记会弄红某门"不成立。`claims_ts_drift.py --check-drift` 现值 `checked=0 unparsed=2598 drift_rows=0` ⇒ 该探针当前对全账**零命中**，回填既不会被它抓、也不会因为它红（诚实读数：别把这条当"补记无代价"，代价在语义与取证面） | 同样零门禁影响 |
| 归属可证性 | 行里必须填班名 ⇒ 只能填 `qoder-rev-20260919-1020`（未坐实）或"主班补记"（那与案乙的 note 出口等价，何必造 14 条 done） | note 行不假装是执行痕迹，只声明账目定性 |
| 并发风险 | 一次写 14 行＝放大 `claims.log` 的读-改-写非原子窗口（纪律 §廿二②在册：该机制未修；本档实测另有 `claims_lines_raw 6513 / claims_rows_total 6097 / dropped 409` ＋ 幻影行 489 已被剔除、454 行 CRLF 污染）⇒ 批量写正是历史上挤掉别人行的形态 | 1 行，与每日 note 同量级 |
| 对账完整性 | 计数变好看（X3 −14），但仍非零 | 交付面完整性**本来就不依赖这 14 行**：result＋任务件＋commit 三件齐，缺的是"谁在何时认领"这一条，而它已不可证 |

## 四、推荐：案乙，并把它落成三件可批动作（全部由主班/人工执行，本班零改账）

**推荐案乙**，理由一句话：**补记能修好的是计数，修不好的是归属；而计数本来就不干净（297 单同代），单点放行等于给"回填历史行"开先例。**

可批形状（可直接粘）：

1. **1 条 note 行**（不是 14 条 done 行）——沿用盘上既有惯例：`claims.log` 现存 **647 条 note 行**（两种独立算法互证：字段切分法与位置正则法同为 647），且纪律档 `tmp/executor-drain-discipline-20260924.md:444` 已写明「③ 发现自己或他班终态行缺失 ⇒ **立刻以 note 追加补记（不改历史行）**，并把缺行时刻写进台账」。最贴近的先例同盘在世：09-22T01:25 主班为 `c918-21`／`c918-23` 各写一行 note，原文即「该单 claims 只有 claim 无终态行（属开口认领，非记错终态）… 按只追加纪律以本…」——**处理缺终态行，历史上就是走 note、不走回填**。
   形状：`<现取时戳> | s920-01..14（14 单合并一条） | <主班班名> | note | [wNN-s920-close] 14 单零账行定性：乙段（02:09–03:30）psy 域账目断供、执行者未坐实 ⇒ 不回填历史行；交付面以 result＋done 任务件＋commit 三件为准（逐单 hash 见 docs/insights/s927-36-endore-adjudication.md 第一节）`
2. **待人工台账结案 s922-11 遗留 1**（末号现为 **238** ⇒ 追加 **239/240**）：
   - 问 1「是否为 s920-01…14 补记终态行」⇒ 建议**否**，出口＝上面那条 note。
   - 问 2「`qoder-rev-*` 只留 claim 是否认定 B-064 定档下的流程缺陷」⇒ 建议改定性为「**乙段执行者未认领**（而非评审窗班署名问题）」；B-064 本身不违反（s922-11 已判 `qoder-rev-*` 属 Qoder 系、在 9/20–9/30 执行手主＝Qoder 窗口内）。**修法在写端不在回填**：派单前/交件前校验「该 id 存在 claim 行」，缺即拒收（属 `zcode-bridge/scripts/*.py` 改动＝信箱自身域闸①＋主班独占件，**须人工放行**，本档不实现）。
3. **可选（若人工坚持要机读闭环）**：给 `result_claims_recon.py` 增"世代豁免名单"（把 9/20 前那批 pre-gate 单整体标 `legacy`、从 X3 移出计数），**零历史改写**。旁证这批评次确实属世代而非个体：官方 `_validate` 对 14 单每单报 4 条缺节（合计 56 条），而格式门按批次统计给 **`s920 0/26（0.0%）`**——同代还有 `l918 0/28`、`m918 0/20`、`n918 11/48`、`s919 11/22`；`EVIDENCE_REQUIRED_SINCE` 为 **2026-09-23**，这 14 份 result 全部早于该线（五节判据本身对它们是追溯翻红）。

## 五、复跑命令与零改账自证

```bash
cd D:/code/zcode-bridge
PYTHONIOENCODING=utf-8 python D:/code/tmp/qoder-executor-20260928-0210-psy85/probe_s920_ledger.py   # 逐单账行计数＋全账 s920 扫描
PYTHONIOENCODING=utf-8 python D:/code/tmp/qoder-executor-20260928-0210-psy85/probe_s920_files.py    # 第一节的表
python scripts/result_claims_recon.py --dry-run --json      # X1=378 / X3=297 / dropped=409 / phantom=489（本脚本无写路径）
python scripts/claims_ts_drift.py --check-drift             # checked=0 drift_rows=0
python scripts/result_format_gate.py --since 2026-09-19 --days 2 --per-file | grep s920
cd D:/code/psy-analysis
git --no-pager log --all --format="%h|%cI|%s" --since=2026-09-19 --until=2026-09-21   # 26 枚署名 commit
```

零改账自证：`claims.log` 本班只按收口纪律追加**本单自己的** claim/done/note 行（写端唯一口径 `claims_writer.py`），14 单的历史行**一行未增一行未改**；信箱 `logs/`、`consumed.jsonl`、`000-QUEUE.md`、待人工台账、纪律档全部只读；`psy-analysis` 工作树 `git status --porcelain` 计数 12 → 14，两处增量＝本班两份文档（s927-33 档与本档），`data/` 未碰。

## 六、遗留问题

1. 台账 `claims_note_rows` 读数与本班实测不符：`result_claims_recon.py --json` 报 **7**，本班两种独立算法均得 **647**。属信箱自身域脚本口径（闸①），**未定性、未改**，交主班复核后再决定是否单开。
2. 「谁在 02:09–03:30 执行乙段」在只读路径上不可判（元数据单元素、无班名行）⇒ 本文按"未坐实"处理；若人工另有旁证（如当日会话日志），问 2 的定性需重开。
3. 探针脚本与 `recon.json` 落在 `D:\code\tmp\qoder-executor-20260928-0210-psy85\`，收口自删；仓根零残留。
4. 完成标准④「零改账」由本班自证为真；但"补记 vs 维持"本身仍是**人工拍板项**，本文只把两案代价钉平，不代签。
