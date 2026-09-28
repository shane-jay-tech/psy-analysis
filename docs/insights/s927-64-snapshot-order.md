# s927-64 · `perf_counter_ns` 快照排序语义债：三案材料 ＋ 推荐（2026-09-29，登记档·零码改动）

> 班：`qoder-executor-20260929-0532-psy104` · 单：`s927-64` · cwd `D:\code\psy-analysis` · 现取时间 `2026-09-29T05:43`
> 🔴 **本班零码改动**：`src/output/snapshot.py` 与 `tests/test_output_snapshot_roundtrip.py` 一字未动（`git status --porcelain` 两件均空 ⇒ 本班读数＝**HEAD 等价读数**）。产出只有本档 ＋ `tmp/` 下探针（无版本管，主班可删）。
> 上游：`zcode-bridge/done/s923-21.result.md` §遗留 1（债的原始登记）· `docs/insights/psy-snapshot-baseline-20260924.md`（s924-28／psy43 基线档，§〇.4 与本档同向否证）· `docs/insights/psy-test-baseline-20260921.md:129-135`（三出口原文）· `docs/insights/psy-instance-lock-clock-seam-20260925.md`（"内容戳改 tz-aware UTC"先例）。

---

## 〇、结论先说（五条，含两条对上游口径的否证）

1. **今天没有任何排序需求面。** `create_snapshot` 全仓调用点 **8 处，全在 `tests/test_output_snapshot_roundtrip.py`**（`:26/:36/:49/:67/:77/:122/:132/:139`），`src/`／`app.py`／`scripts/` **零生产调用方**；`snapshot_created` 的读者只有该测试件的 4 条断言，`load_snapshot` 只做 `json.load`、全仓无 `fromisoformat` 消费方 ⇒ **"按快照时间排序"这个需求在生产里不存在**。债之所以是债，是因为**它现在没有看守**，不是因为它现在被踩。
2. 🚩 **否证 s923-21 的"同值率 0.000%"**：紧采 `time.perf_counter_ns()` **N=20,000 ⇒ 相邻同值率 47.972%、严格递增=False**（本机 `.venv` 现测）。⇒ `+mono` 尾数提供的是**"调用间距 ≫ 计数器分辨率 100 ns 时的区分度"，不是"永不重复"**。实际余量本班直读：两次真 `create_snapshot` 的 mono 间距＝**1,785,200 ns 与 1,089,500 ns**（≈1.8 ms／1.1 ms，对 100 ns 有 10–18 倍余量）。此判定与 s924-28 档 §〇.4 的独立读数（5000 次紧采 **43.329%**）**同向同量级** ⇒ 两条独立测量共同否证原口径。
3. 🚩 **否证 s923-21 的"进程相对量、跨进程不可比"**：`perf_counter` 实现＝`QueryPerformanceCounter()`，本班实测它**在同一 boot 窗内跨进程可比**——父进程 `perf_counter_ns()=105,664,484,837,100` → 子进程 1 首枚 `105,665,872,151,400` → 子进程 2 首枚 `105,667,290,820,500`，差值 **1.387 s／1.419 s 与两次派生的真实经过时间同步**。⇒ 真正的不可比面是**跨 boot（重启归零）与跨机**，不是"跨进程"。附带订正 `psy-instance-lock-clock-seam-20260925.md:135` 那句"原点是**每进程**／每次 boot 各异"里的"每进程"三字（该段说的是 `time.monotonic()`＝`GetTickCount64()`，同为全系统自 boot 计数）。
4. **债的真实形状与登记时不同**：现值 `f"{datetime.now().isoformat()}+mono{time.perf_counter_ns()}"` 是**复合字典序串**，排序**由墙钟段完全主导**（mono 只在同墙钟 tick 内当破平子）。而 `time.get_clock_info('time')` → `implementation='GetSystemTimeAsFileTime()', monotonic=False, adjustable=True, resolution=0.015625` ⇒ **墙钟可被回拨**（本机横幅自记"时钟双向跳"）⇒ 一旦回拨，字典序当场错序，**mono 救不回来**（它按 boot 归零、跨机更是无意义）。这才是"禁排序"约定的物理理由。
5. **看守面为零**：`tests/test_output_snapshot_roundtrip.py:88/:89/:91/:92-93` 钉的是"相邻两次必不同＋墙钟段可 `fromisoformat`＋`+mono` 后必为纯数字"，**没有任何一条钉"不得按本键排序"或"本键可比"**。⇒ 谁将来在 UI 里按 `snapshot_created` 排序，**门禁不响**。

---

## 一、现状锚点复核（逐条现取）

| 锚点 | 现值 | 判定 |
|---|---|---|
| `src/output/snapshot.py:80` | `params["snapshot_created"] = f"{datetime.now().isoformat()}+mono{time.perf_counter_ns()}"` | ✅ 与 s923-21 落地一致，未漂移 |
| 是否已入库 | `git show HEAD:src/output/snapshot.py \| grep -c "mono{time.perf_counter_ns()}"` → **1**；`git log --oneline -1 -- src/output/snapshot.py` → **`66de52e`（s923-19/20/21 三单入账）** | ✅ 在 HEAD，非在途件 |
| 工作树 | `git status --porcelain src/output/snapshot.py tests/test_output_snapshot_roundtrip.py` → **空** | ✅ 本班读数＝HEAD 等价 |
| 看守测试 | `pytest tests/test_output_snapshot_roundtrip.py -q` → **`10 passed in 1.68s`，真 rc=0**（未接管道取码） | ✅ 现况绿 |
| `create_snapshot` 调用面 | 8 处全在测试件；生产零调用 | 🆕 本班实测 |
| 行号漂移 | s923-21 result 记的 `:79/:81` 两钉，现值在 **`:86`（成员级"唯一差异"）／`:88`（params 级"唯一差异键 == {snapshot_created}"）** | ⚠ 登记档口径按现值 |

三时钟现读（`time.get_clock_info`）：

```
time          monotonic=False adjustable=True  resolution=0.015625  impl=GetSystemTimeAsFileTime()
perf_counter  monotonic=True  adjustable=False resolution=1e-07     impl=QueryPerformanceCounter()
monotonic     monotonic=True  adjustable=False resolution=0.015625  impl=GetTickCount64()
```
（墙钟"15.625 ms 槽"这个措辞本身 s924-28 §〇.4 已实测登记为**不准**（实际步进≈1 ms）；本班不重复推翻，只引为"粗墙钟撑不住相邻必不同"，本班同值率现读 `datetime.now().isoformat()` **99.945%／N=20,000**，与其 99.940%／N=5,000 同向。）

---

## 二、三案对比（材料，非裁决）

| 维度 | **案甲：加单调序号列** | **案乙：改时间源** | **案丙：维持"禁排序"约定＋补看守** |
|---|---|---|---|
| 做什么 | `analysis_params.json` 另置一键（如 `snapshot_seq`）承担排序 | 另置 `snapshot_created_utc`（tz-aware ISO）或把现键墙钟段换成 UTC；排序按它 | 不动键、不动值；把"本键不承担排序语义"写成可断言的看守 |
| 能不能定时 | ❌ **只能定序不能定时**（裸序号无墙钟含义） | ✅ 能定时、跨机可比、跨 boot 可比 | — 不需要 |
| 能不能破同 tick | ✅ 天然唯一 | ❌ 粗墙钟下同一 tick 并列（本班 99.945% 同值率即其量级）⇒ 需与案甲/mono 组合 | — |
| 抗墙钟回拨 | ✅（与墙钟无关） | ❌ UTC 仍可被系统时间调整拖动；需另计 | ✅（不排序就不受害） |
| 跨机 / 跨重启 | ❌ 序号需持久化源，跨机要共享状态 | ✅ | — |
| 要新造什么 | **一个跨进程可比的序号源**：要么新增持久化计数器（＋并发写问题＋新盘面），要么改用 ULID/UUIDv7 ⇒ 那**等价于案乙**（本质仍是时间基准），单靠它做不到"既有绝对时间又严格单调" | 无新状态；`datetime.now(timezone.utc).isoformat()` 即可 | 无 |
| 牵动哪些在册钉（必改） | `:88` `== {"snapshot_created"}` **当场红**（新键同键不同值 ⇒ 差异集合变大）；若做成**独立 zip 成员**则同时炸 `:52` 的 `namelist()` 全等钉；`:89/:91/:92` 不受影响 | 换墙钟段格式 ⇒ `:91` `fromisoformat(...split("+mono")[0])` 仍可解析（tz-aware 也支持），**但 `.year>=2024` 那句与本地/UTC 语义无关，不炸**；新增键 ⇒ 炸 `:88`；**另有导出/交付面的字节确定性族**（s923-20 的 `test_docx_output_is_byte_deterministic` 三层断言）需复核是否吃本键 | 不炸任何现有钉；**加看守**要新写断言（属测试语义改动，需主班排窗） |
| 先例可引 | 无（仓内无持久化序号先例） | ✅ `docs/insights/psy-instance-lock-clock-seam-20260925.md` 推荐案 A 第 2 步：「内容戳改 tz-aware UTC」（同类"绝对时间戳"改造，已给出兼容性核对形状与 `:52/:54` 式格式钉的处置法） | ✅ 同仓 `psy-snapshot-baseline-20260924.md` R3 已把"摘尾数即红"的因果写进测试注释文字（`tests/test_output_snapshot_roundtrip.py:78-84`）＝同款"注释即看守"手法 |
| 成本 | 中—高（新状态＋并发＋`:88`/`:52` 同批改） | 低—中（一行赋值＋`:88` 同批；无新状态） | **最低**（本班授权内即可出材料） |
| 风险 | 引入"必须同笔"耦合；序号源本身是新的可写坏面 | 只解"可定时"，**不解"同 tick 并列"**；若误把现键整串换掉会撞 s923-21 已钉的"墙钟段必须可 `fromisoformat`" | 约定只活在文字里 ⇒ 将来有人排序**门禁不响**（§〇.5 即现状） |

**三案共同的盘上事实**：`params` 键集只有 `snapshot_created / title / author / description / n_rows / n_cols / columns / analyses` 八项（`src/output/snapshot.py:80-90` 现读），无任何序号／无任何 tz 信息 ⇒ 无论走甲或乙，都是**新增交付物字段**（`analysis_params.json` 是用户可解压看到的交付成员，s923-21 §遗留 2 已把这条定性为"可见输出改动，需放行"）。

---

## 三、推荐（一案）：**案丙「维持禁排序约定」＋ 把约定升级成看守**

理由（三条，全挂本班实测读数）：

1. **需求面为零**：生产侧 `create_snapshot` 零调用方（§一），今天没有"按快照时间排序"的消费者；为不存在的需求引入新键＝纯粹扩大交付物面与"必须同笔"耦合。
2. **案甲单独走是死路**：它只能定序不能定时，而"要一个跨进程可比的序号源"这件事的最低成本解就是 ULID/UUIDv7 —— 那**本质是案乙**；两案在这一点上会互相吞，说明现在不是拆案的时候。
3. **案乙解的不是当前痛**：现值已经"墙钟段可 `fromisoformat`"（`:91` 已钉），换成 tz-aware 只是把本地串换成 UTC 串，**同 tick 并列照旧**（本班实测 99.945% 同值率），真正缺的"抗回拨＋跨机可比＋严格单调"三件套它只给一件。

**但案丙不能停在"约定只在文档里"**——§〇.5 实测看守为零，所以案丙的落地必须含一步（**属测试语义改动，需主班排窗，本班不自作**）：

> 在 `tests/test_output_snapshot_roundtrip.py` 加一条**反向钉**：明确断言"`snapshot_created` **不保证**字典序＝时间序"（例：断言文档/注释里存在"不承担排序语义"口径，或直接钉住该键**不进任何排序键白名单**），使"有人开始按它排序"这件事在门禁上响。

**将来真要排序的唯一入口（预先钉死，免后人重议）**：案乙（`snapshot_created_utc`，跨机可比的绝对时间基准）**＋**案甲的破平件（同 UTC tick 内用 mono/序号破平）**两键并列**，并且**必须与 `:88`（＋若新增文件则 `:52`）同笔改**——分开提＝HEAD 当场红。这条是给主班的入库耦合提示，不是裁决。

---

## 四、登记口（本班不写台账，只给行文本）

待人工台账 `D:\code\docs\insights\drain-20260923-pending-human.md` 中**检索不到"排序语义／快照排序"任何行**（`grep -n "排序语义"`、`grep -n "快照排序"` → **各零命中**）⇒ **这条债目前只活在 `s923-21.result.md` 的遗留节里**。⚠ 但要区分：台账 **#216（L165）已登记机理那一半**（原文含「`perf_counter_ns()` 紧采同值率 **43.329%** ⇒ 加单调尾数只在 ms 级间距才有效」与「`snapshot.py:76-79` 注释『15.625ms 槽』数值不准」），**那是 s924-28 的时钟机理更正，不是排序债的登记行**。建议主班补一行（文本本班只拟不写）：

> **psy 快照 `snapshot_created` 的排序语义债未入台账**：`src/output/snapshot.py:80` 现值是"本地墙钟 ISO + `+mono{perf_counter_ns}`"复合串，字典序由墙钟段主导而 `get_clock_info('time').adjustable=True` ⇒ 回拨即错序；`mono` 实测**同 boot 内跨进程可比**（差值与真实经过时间同步，**否证 s923-21"进程相对量"口径**）但跨 boot/跨机不可比；紧采同值率 47.972%／N=20k（**否证"0.000%"**，与 s924-28 的 43.329% 同向）⇒ 尾数只提供"调用间距≫100ns"的区分度。**生产侧 `create_snapshot` 零调用方**、**看守测试零条涉及排序**。出口：①维持禁排序＋加反向钉（本班推荐）；②案乙＋案甲两键并列（须与 `test:88` 同笔）。| 待人工（涉交付物字段可见改动＋测试语义改动）

---

## 五、零改动自证 ＋ 复算命令

```
$ git status --porcelain src/output/snapshot.py tests/test_output_snapshot_roundtrip.py   → 空（两件 HEAD 等价）
$ git show HEAD:src/output/snapshot.py | grep -c "mono{time.perf_counter_ns()}"           → 1
$ PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest tests/test_output_snapshot_roundtrip.py -q
  10 passed in 1.68s        # 真 rc 用重定向取，未接管道：PYTEST_RC_TRUE=0
$ PYTHONUTF8=1 .venv/Scripts/python.exe tmp/qoder-executor-20260929-0532-psy104/s927-64_clock_probe.py   → PROBE_RC=0
```

- **探针不落盘**：`create_snapshot(..., output_path=None)` 只在 `io.BytesIO` 里产 bytes（`src/output/snapshot.py:58-97`），全部 zip 读取打在返回的 bytes 上；探针**未写任何仓库文件、未启动 app、未碰 `data/`**（同域另一路 `s927-63` 的 181 件基线仍 ZERO-DIFF，见其 result）。
- 未执行：任何 `src/`／`tests/` 编辑、任何 git 写、任何全量 pytest（只跑了卷宗口径允许的**定向单件**，1.68 s）。
- 红线：本档数值全是**时钟属性／同值率／纳秒间距／断言行号**，**无一条统计或经济结论**；未碰医疗／PII／鉴权／凭据；未挂白名单、未标 `NEEDS_MIGRATION`。
- ⚠ **主班复跑的局限**：① 同值率随解释器负载浮动（本班 20,000 次＝47.972%，s924-28 5,000 次＝43.329%，**两者都远大于 0 才是结论**，别拿单个百分数当常数）；② 跨进程连续性读数只在**同一 boot 窗内**成立，重启后 mono 归零无法在本机自证（本班按 Win32 `QueryPerformanceCounter` 语义登记为"跨 boot 不可比"，**未实测重启**）；③ 复跑探针会新建两个子进程，pid 每次不同，比对时看差值量级不看 pid。
