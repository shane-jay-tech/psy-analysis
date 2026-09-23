# psy 大快照超阈值方案 A 增量资产化设计稿（s922-129）

> 2026-09-22｜执行班 **s922-129**（只读设计单）｜基线 HEAD `f6fc82d`
> **本单零改码、零写库**：本单不触数据库；未新增/修改任何生产源码、测试或配置。
> 上游：`KNOWN_ISSUES.md:102`（P1 大工作区快照）· `docs/insights/h912-06-psy-snapshot-b-20260912.md`（阈值实测）· `docs/insights/psy-snapshot-plana-design-20260918.md`（方案 A 初版 s918-03）

---

## 0. 锚点复核（先复核，有漂移按磁盘实况修正并留痕）

| # | 任务书锚点 | 磁盘实况 | 判定 |
|---|---|---|---|
| 1 | `KNOWN_ISSUES.md:102` 全文 | 逐字一致（「已按方案 B 后台化（a02626c）＋『返回＝受理』语义与换案阈值已入码（h912-06，实测阈值=序列化 CSV 10MB≈worker 2s/内存峰值≈52MB）；残留：超阈值需评估方案 A 增量资产化」） | ✅ 无漂移 |
| 2 | 键清单 `workspace.py:226-391` | 函数实际 **L226–L396**；键赋值止于 **L394**（`_saved_at`/L392、`_version`/L393、`_schema`/L394），L396 为 `return ws` | ⚠️ **范围漂移**：引用区间少 5 行，恰好切掉 3 个 meta 键 |
| 3 | 「df_b64 占比 vs **其余 23 键**」 | 序列化输出实为 **26 键** ＝ df_b64 + 25 | ⚠️ **计数漂移**（口径调和见 §1.2） |
| 4 | `tmp/measure_snapshot_threshold_h91206.py` | 存在（1120 B，2026-09-12 23:41） | ✅ 无漂移 |
| 5 | `docs/insights/psy-snapshot-plana-design-20260918.md` | 存在（3869 B，2026-09-19 02:52） | ✅ 无漂移 |
| 6 | h912-06 报告「app.py:1067/1371 两处 force=True」 | 现为 **app.py:835**（数据上传后）与 **app.py:1139**（分析归档后）；处数仍为 2 | ⚠️ **行号漂移**（`app.py` 在工作树中被改过，见 §2.3），处数与语义未变 |
| 7 | `tests/audit_inplace_scan.py`（autosave.py:95 引用） | **存在**（本次首轮 glob 误判为缺失，经 `grep` 更正——glob 只匹配文件、且需含 `**/` 才跨层级，误判已留痕） | ✅ 存在，且已复跑（§3.5） |

> 漂移处置：本文所有引用一律改用**磁盘实况行号**；任务书原值在「任务书锚点」列保留，便于对账。

---

## 1. 键级资产分布（对 `build_workspace_snapshot()` 的**静态读数**，非运行时测量）

### 1.1 键清单（AST 静态清点，行号入稿）

复现命令（临时脚本：`tmp/census_snapshot_keys_s922_129.py`，tmp/ 已在 `.gitignore:29` 内故不入库）：

```
.venv/Scripts/python.exe -X utf8 tmp/census_snapshot_keys_s922_129.py
```

输出（实测，`# 赋值点(展开后) = 26   唯一键数 = 26`）：

| # | 行号 | 键 | 来源形态 |
|---|---|---|---|
| 1 | L236 | `df_b64` | 字面量（df → CSV → base64，**唯一重资产**） |
| 2 | L238 | `analysis_history` | `for k in [...]` |
| 3 | L238 | `file_name` | `for k in [...]` |
| 4 | L238 | `inspector` | `for k in [...]` |
| 5 | L238 | `meta` | `for k in [...]` |
| 6 | L247 | `plan` | 字面量（经 `_serialize_plan`） |
| 7 | L253 | `analysis_output` | 字面量（经 `_serialize_analysis_output`） |
| 8 | L265 | `undergrad_wizard_data` | 字面量 |
| 9 | L267 | `undergrad_mode` | `for k in [...]` |
| 10 | L267 | `undergrad_path` | `for k in [...]` |
| 11 | L267 | `undergrad_step` | `for k in [...]` |
| 12 | L275 | `questionnaire_design` | 字面量 |
| 13 | L281 | `experiment_design` | 字面量（从 `experiment_engine.design` 摘 6 字段） |
| 14 | L292 | `paper_engine_state` | 字面量（摘 3 字段） |
| 15 | L299 | `app_mode` | `for k in [...]` |
| 16 | L299 | `quick_model_id` | `for k in [...]` |
| 17 | L309 | `figure_collection` | 字面量（`to_serializable()`） |
| 18 | L316 | `defense_qa_mastered` | 字面量 |
| 19 | L321 | `download_history` | 字面量 |
| 20 | L336 | `tutor_histories` | 字面量（聚合前缀族 `_tutor_history_*`） |
| 21 | L355 | `upstream_state` | 字面量（含 `stages[].ai_history` 对话） |
| 22 | L372 | `literature_review_state` | 字面量（含 `literature_items`/`notes`） |
| 23 | L387 | `workspace_state_v35` | 字面量（`wsv.to_dict()` **镜像态**） |
| 24 | L392 | `_saved_at` | 字面量（meta） |
| 25 | L393 | `_version` | 字面量（meta） |
| 26 | L394 | `_schema` | 字面量（meta） |

> 清点陷阱（如实留痕）：三个 `for k in [...]` 循环（L238/L267/L299）**共用循环变量名 `k`**。首版脚本按变量名做全局映射，被最后一个循环覆盖，得出「19 键」漏 7 键的错值；改为按**词法最近的 For 节点**配对展开后才得 26。任何后续自动清点都需按此配对，不能按变量名映射。

### 1.2 计数口径调和（解释任务书「23」与磁盘「26」）

| 口径 | 数 | 出处 |
|---|---|---|
| 序列化**输出**键（落盘 payload 的构成） | **26**（df_b64 + 25） | 本文 §1.1 AST 清点 |
| 快照**读取**输入键（扫描器的面） | 22 具名 + 1 前缀族 `_tutor_history_` = **23** | `tests/audit_inplace_scan.py -q` 实测打印 |

两者并不矛盾：`tutor_histories` 这一个输出键由前缀族聚合而来，另加 3 个 meta 键只在**写出侧**存在。核对：`23（读取口径）+ 3（meta）= 26`。

**本文采用输出口径 26（非 df 25）**——分片与写放大作用在落盘 payload 上，读取口径不含 meta 键，会低估「未变即跳过」的收益面。

### 1.3 占比：df_b64 的**结构性下界**（无需运行时测量）

触发判据在 `autosave_bg.py:85`：`if len(b64) > SNAPSHOT_WORKER_B64_BYTES_THRESHOLD`，而
`SNAPSHOT_WORKER_B64_BYTES_THRESHOLD = int(10.0 * 1048576 * 4 / 3) = 13981013` 字节（`autosave_bg.py:40-41`）。
即：**阈值一旦命中，`df_b64` 单独就 > 13.98 MB（十进制；=13.33 MiB）**，对应 CSV = 10485760 字节 = 10 MiB。

于是 df_b64 的体积占比有下界，只取决于其余 25 键合计 `S`：

| 其余 25 键合计 S | df_b64 占比 ≥ 13.98/(13.98+S) |
|---|---|
| 100 KB | 99.3% |
| 300 KB | 97.9% |
| 700 KB | 95.2% |
| 1 MB | 93.3% |
| 3 MB | 82.3% |

**这是由构造保证的硬结论（非测量）**：超阈值场景下 df_b64 占比 **≥ ~93%**，除非其余 25 键合计超过 1 MB。
（口径注：被比较的是字节数，阈值常量名写作「MB」实际按 10 MiB 换算、日志按 MiB 打印——两边单位自洽，无换算 bug，仅命名易误读。）

### 1.4 其余 25 键的静态定性排序（**估算，非测量**）

按「代码结构里承载什么」排序，绝对值须运行时确证（本单禁运行时测量；且 `~/.psy_analysis/` 在 `cwd` 之外，按任务书禁止触碰）：

| 档 | 键 | 依据（代码结构） |
|---|---|---|
| 大（可至 10²–10³ KB） | `tutor_histories` | 每个 location 一份完整对话历史（role/content 列表，L324-336） |
| | `upstream_state` | 每 stage 一份 `ai_history` 对话 + `funnel_history` + `feasibility_results`（L342-367） |
| | `literature_review_state` | `literature_items`/`notes`/`matrix`/`themes`/`gaps` 五类列表（L372-380） |
| | `workspace_state_v35` | `wsv.to_dict()`——**v3.5 镜像态，疑与上面多键同源重复**（L382-389；去重收益待运行时确证） |
| 中（10⁰–10² KB） | `analysis_history`、`analysis_output`、`plan`、`undergrad_wizard_data`、`figure_collection`、`download_history` | 逐次分析/图表/向导累积的列表与 dict |
| 小（<10 KB） | `meta`、`inspector`、`file_name`、`undergrad_mode/path/step`、`questionnaire_design`、`experiment_design`(摘 6 字段)、`paper_engine_state`(摘 3 字段)、`app_mode`、`quick_model_id`、`defense_qa_mastered` | 标量或定长小结构 |
| 极小（字节级） | `_saved_at`、`_version`、`_schema` | 三个常量字符串 |

> ⚠️ 上表是**结构定性排序**，不是体量结论；不构成本单的数值结论。任何「`S` 到底多大」的判定必须由后续运行时测量（在允许触碰 `~/.psy_analysis/` 的单子里）给出。

---

## 2. 现状写放大链路（file:line 入稿）

### 2.1 链路

```
调用点 app.py:835 / app.py:1139        _autosave_current_workspace(force=True)
  └ src/utils/autosave.py:169-175      节流：DEFAULT_THROTTLE_SECONDS = 30（同 session 同项目 30s 内不重复写；force 绕过）
  └ src/utils/autosave.py:185-190      _capture_refs → autosave_bg.submit（引用级捕获，零序列化）→ 立即返回 True（受理）
      └ src/utils/autosave_bg.py:82    ws = mod.build_workspace_snapshot()   全量序列化（df → CSV → base64）
      └ src/utils/autosave_bg.py:85    超阈值 → WARNING（当前**仅告警**，大快照仍整包入库）
      └ src/utils/autosave_bg.py:92    pm.save_workspace(project_id, ws)
          └ project_manager.py:303     _atomic_write_json(proj.file_path, workspace)
              └ project_manager.py:99-116   同目录 NamedTemporaryFile → json.dump 整包 → fsync → os.replace
```

### 2.2 存储布局（现状）

- 每项目**一个 JSON 文件**：`PROJECTS_DIR / f"{id}.json"`（`project_manager.py:52-54`），`PROJECTS_DIR = APP_HOME / "projects"`（`app_paths.py:19`，即 `~/.psy_analysis/projects/`）
- 写入是**整包重写**：`json.dump(payload, ...)`（`indent=None` 紧凑、`ensure_ascii=False`、`default=str`）+ `fsync` + `os.replace`
- 即：**任何一个键变化 ⇒ 含 df_b64 的整个 ~14 MB payload 全量重写一次**

### 2.3 两个 force 调用点 = 两种变化形态（本设计的锚）

| 调用点 | 触发语义 | 变化形态 | 对分片的意义 |
|---|---|---|---|
| `app.py:835` | 数据上传成功后 | **df 变**（其余键多半不变） | 资产写不可避免，但可省 b64 膨胀（改存 CSV，−25%） |
| `app.py:1139` | 分析归档后（紧邻 `app.py:1137` 的 `analysis_history.append(...)`） | **非 df 变**（df 完全不变） | **当前白写整个 14 MB**；分片后仅需写小分片 |

> `app.py:1137` 的 `st.session_state.analysis_history.append(history_entry)` 是一处**就地 append**，且落在快照键 `analysis_history`（本文 §1.1 #2）上——`tests/audit_inplace_scan.py` 首跑基线把它列为「严格可证」之一（脚本注释：`app.py:1137`）。这条同时是 §3.5 风险项的现实来源。

### 2.4 写放大基线（算术，非测量）

节流下限 30 s ⇒ 单 session 最坏 ≤ 2 次/分钟：

| 场景 | 每次落盘字节（≈） | 每分钟 | 每小时 |
|---|---|---|---|
| 超阈值 + 连续交互（节流打满） | ≥ 13.98 MB（+JSON 转义/其余键） | ≥ 28 MB | ≥ 1.68 GB |

其中**只有极小一部分是有用变更**：按 §1.3 下界，`app.py:1139` 这类「非 df 变」场景里 ≥93% 的写入是**原样重写未变的 df_b64**——纯写放大。

---

## 3. 两方案对比（完成标准 1）

设：`S` = 其余 25 键合计字节，`D` = df 资产字节（CSV 口径 10 MiB，b64 口径 13.33 MiB）。

### 3.1 方案 A-1：按键分文件（项目目录化）

```
~/.psy_analysis/projects/<id>.json          # v1 单体（保留为回退点，不删）
~/.psy_analysis/projects/<id>/              # v2 资产目录（提交点 = manifest）
    manifest.json     # {"schema":"v2-dir","keys":{k:{"file":…,"sha256":…,"bytes":…}}}
    df.csv            # df 资产：CSV 原文（**不再 base64**，省 33%）
    state.json        # 其余 25 键（含 3 个 meta）
```

### 3.2 方案 A-2：单文件 + 内容寻址 blob 仓（仅写变更键 / 校验和跳过未变键）

```
~/.psy_analysis/blobs/<sha256[:2]>/<sha256>  # 每个键值一个 blob，内容寻址
~/.psy_analysis/projects/<id>.json          # 原位不变，退化为**小 manifest**
    {"schema":"v4-blob","keys":{
        "df_b64":{"ref":"sha256:…","bytes":13981013,"enc":"csv-base64"},
        "plan":  {"ref":"sha256:…","bytes":2301}, … }}
```

规则：写出前对每个键**先算校验和**；命中已有 blob ⇒ **零写**；仅变化的键产生新 blob；最后原子替换 manifest（提交点）。

### 3.3 对比表

| 维度 | 现状 v1（单体整包） | **A-1 按键分文件** | **A-2 blob 仓 + 校验和跳过** |
|---|---|---|---|
| 存储布局 | 1 文件：`<id>.json` | `<id>/` 目录：manifest + df.csv + state.json | `<id>.json`(manifest) + `blobs/<前2>/<sha256>` |
| 跳过规则 | 无 | 按**文件**粒度：未变的文件不动 | 按**键**粒度：校验和命中即不写 |
| df 落盘开销 | 13.33 MiB（b64 膨胀） | 10 MiB（CSV 原文，**−25%**） | 10 MiB（同 A-1，blob 内可存 CSV） |
| 「非 df 变」一次保存 | **≥13.98 MB** | `S`（≈0.1–1 MB）→ **−93%~−99%** | 同 A-1，且**跨项目去重**（同值 blob 共享） |
| 「df 变」一次保存 | ≥13.98 MB | 10 MiB + `S` | 10 MiB + `S`（其余未变键仍零写） |
| 读放大/恢复延迟 | `json.load` 整包（含 14 MB base64 解析） | **可懒加载**：仅读 state.json 即可渲染非数据页 | 需按 manifest 逐个解引用；命中热 blob 快，冷启动更碎 |
| 迁移步骤 | — | ①读侧 resolver（目录优先，无目录回落 v1）②首写时拆包：写 df.csv（临时名+fsync+rename）→ 写 manifest（原子）→ 校验 hash ③校验通过后删旧单文件（或保留 N 天） | ①写侧加「算校验和→查 blob→未命中先写 blob」②manifest 原子替换 ③惰性迁移：仅把**发生变化的**键搬到 blob，其余保持裸值即可读 ④GC：mark-sweep |
| 回退 | — | 常量切回 v1 + **v2 目录留而不删**；或 `--regroup` 把目录合成单文件 | manifest 带版本；裸值 = v1 可直读；`--deblob` 把 ref 解引用回裸值重写单文件 |
| 崩溃一致性 | 单 `os.replace`，天然原子 | **多文件** ⇒ 以 manifest 为提交点；崩溃只留孤儿资产（懒清理，不损数据） | 同 A-1（先 blob 后 manifest）；孤儿 blob 由 GC 收 |
| 新增风险 | — | `Project.file_path` 单文件假设被打破 ⇒ 导出/删除/备份路径需同步（`project_manager.py:52-54`） | **GC 误删 = 不可逆数据丢失**；且新 blob 无原地覆盖 ⇒ **磁盘持续增长** |
| 磁盘占用趋势 | 稳定（原地覆盖） | 稳定（原地覆盖） | **单调增长**（每版本一个 blob，需 GC 或容量观测） |
| 改动面（估） | — | `project_manager`(读/写/删/导出) + `autosave_bg` 落盘处 | `project_manager` + 新 blob 层 + GC 任务 |

### 3.4 倾向与理由（工程参数，非数值结论）

**建议 A-1 先行**，理由：
1. A-1 用最小机制吃到 §2.4 里最大的那块收益——「df 未变却重写整个 14 MB」；
2. A-1 顺带拿掉 base64 的 33% 膨胀（落盘改 CSV 原文），且**原地覆盖**、无垃圾堆积、无 GC 误删风险；
3. A-1 的「目录 vs 单文件」是唯一需要改 `project_manager` 导出/删除路径的地方，改动面可枚举；
4. A-2 的收益增量（跨项目去重 + 键级跳过）**只有在 df 与其余键在容器内交错变化时才兑现**——而 §2.3 表明两个 force 点各自基本只动一侧，A-1 已能区分；
5. A-2 引入**不可逆的 GC 风险**与**单调磁盘增长**，属「先有容量观测再上」的形态。

若后续确证 `workspace_state_v35` 与 `tutor_histories`/`upstream_state`/`literature_review_state` 大面积同源重复（§1.4 存疑项），则**先去重**（键级去重收益可能大于 A-2 的全部增量），再谈 A-2。

### 3.5 两方案共担的一个校验口径风险（重要）

`autosave_bg.py:16-17` 与 `autosave.py:93-95` 明说：快照键按 Streamlit 惯例「**整体替换、不就地改**」，`_capture_refs` 捕获的是**活引用**；就地的当前基线由 `tests/audit_inplace_scan.py` 报告。本次复跑（只读、报告型、退出码恒 0）：

```
.venv/Scripts/python.exe tests/audit_inplace_scan.py -q
→ 扫描生产 .py 文件数：252（解析失败 0）
  快照读取键：具名 22 个 + 前缀族 ['_tutor_history_']
  [严格命中 strict] 20   可证就地写 且 键 in 快照
  [键不在快照 not_in_snap] 35
  [宽口径召回 recall] 68
```

**20 处严格命中说明「整体替换」并不成立**（至少对部分键）。这对 **A-2 的校验和语义是直接威胁**：若校验和算在**对象**上，而某个键被就地改后 serialize 结果不变（例如被 `default=str` 吞掉的非序列化对象），就会**误判「未变」而漏写**——静默丢数据。
**对策（写进设计）**：校验和一律算在**序列化后的字节**上（b64/CSV 文本字节），不算在 Python 对象上——这恰是现状 `df_b64` 的既有口径，零新语义。A-1 按文件哈希同理。

---

## 4. 成本模型（复用 h912-06 实测口径）

**已测（h912-06，本文只引用，不重测）**：`tmp/measure_snapshot_threshold_h91206.py` 口径（`DataFrame.to_csv` + `base64`，与 `build_workspace_snapshot` 配方一致，.venv 单线程）

| df 规模 | CSV | b64 | 序列化+编码 | tracemalloc 峰值 |
|---|---|---|---|---|
| 1000×50 | 0.37 MB | 0.49 MB | 94.6 ms | 3.5 MB |
| 3000×200 | 5.20 MB | 6.93 MB | 1118.7 ms | 27.0 MB |
| 6000×400 | 21.84 MB | 29.12 MB | 4252.6 ms | 113.8 MB |
| 12000×400 | 44.87 MB | 59.83 MB | 8410.4 ms | 233.5 MB |

拟合：**≈190 ms/MB CSV（线性）**；**内存峰值 ≈5.2× CSV 体量**。阈值 = CSV 10 MiB ⇒ **单次序列化 ~2 s、峰值 ~52 MB**。

**未测（本文标注为估算，勿当结论）**：`json.dump` 对 ~14 MB 字符串的编码、`fsync`、`os.replace` 三段的耗时与峰值。h912-06 只测了 to_csv + base64，**不含** JSON 落盘这一段；故现状 worker 单次真实耗时 **> 2 s**，超出量未知。

**分片后的收益口径（用上式外推，估算）**：
- 「非 df 变」场景：序列化成本从 `190ms/MB × 10 MiB ≈ 2 s` 降到 `S` 对应的毫秒级；写盘从 ≥13.98 MB 降到 `S`。
- 「df 变」场景：序列化成本不变（df 仍须全量序列化），仅省 b64 编码与 25% 落盘体量。
- **注意**：A-1/A-2 都不减 df 的**序列化 CPU**（那需要 §5 讨论的行级 delta 或增量编码），只减**写盘体量与写放大**。若瓶颈是 CPU 而非磁盘，两方案都不对症。

---

## 5. 与 psy-snapshot-plana-design-20260918.md 的关系（完成标准 3）

**结论：补充（supplement），不是替代（replace）；且建议把两者的落地顺序对调。**

| 轴 | 20260918 稿（s918-03） | 本文（s922-129） |
|---|---|---|
| 粒度 | **DataFrame 行级** delta（baseline 资产 + append/patch 增量） | **快照键级**分片（df 一个资产 + 其余 25 键） |
| 定的是 | 触发/边界/**回退语义**（snapshot.version=2、增量条数 >50 重打基线、hash 不符告警） | **存储布局与写放大**（资产怎么摆、什么条件下不写） |
| 未定 | 「落地改动点预估：worker 循环 + 读取端两处」——**布局本身没定** | 行级 diff 实现（本文不涉） |

**为什么是补充且顺序应对调**——`autosave_bg.py:16-17` 与 `autosave.py:93-95` 明说快照键按「整体替换、不就地改」：**df 每次都是整体换新的对象**。既然是整体替换，**行级 diff 在 df 轴上的收益趋近于零**——比对结果是「全行变更」，退化为整份重写，却要背上行级 diff 的实现与一致性负担。
真正反复发生的是 §2.3 的 `app.py:1139` 形态：**df 纹丝不动、小键在变**，而当前每次都重写 14 MB。**键级分片正好打在收益最大的轴上，行级 delta 打在收益最小的轴上。**

故：**先键级（本文 A-1），行级 delta（20260918 方案 A）降为 df 内部的第二阶段**，仅当未来 df 引入真正的就地追加/局部更新语义时再启用。20260918 稿的**回退语义与边界条件表仍然有效**，可作为 A-1 边界表的模板直接复用（把「增量条数 >50」换成「分片未变即跳过」）。

---

## 6. 建议与遗留

### 6.1 建议（工程参数，供日间拍板）
1. 先落 **A-1**（按键分文件 + CSV 原文 + 文件级跳过），以 manifest 为提交点、保留 v1 单文件作回退点。
2. 落 A-1 前，先在**允许触碰 `~/.psy_analysis/`** 的单子里补一次运行时测量，把 §1.4 的 `S` 与 `workspace_state_v35` 同源重复度确证——这直接决定 A-1 的收益是 −93% 还是 −99%。
3. A-2 暂缓，前置条件：`S` 确证 + 磁盘容量观测基线 + GC 的「持锁 mark-sweep + 延迟删除」方案评审。
4. 任一方案落地时，校验和一律算在**序列化字节**上（§3.5）。

### 6.2 遗留（本单未做，如实列出）
- **未做运行时测量**：任务书要求键级分布来自静态读数，故本文不含实测体量；§1.3 是构造性下界，§1.4 是定性排序。
- **未触碰 `~/.psy_analysis/`**（cwd 之外，任务书禁止）⇒ 真实项目文件的键级体量未取。
- **未验证 `workspace_state_v35` 的重复度**（§1.4 存疑项），需运行时确证。
- **未测 `json.dump`/`fsync`/`os.replace` 段**（§4），现状 worker 真实耗时 >2 s 的确切值未知。
- **`app.py:1137` 就地 append 与 audit 基线 20 处严格命中的逐条处置**不在本单范围（属 `KNOWN_ISSUES.md:156` 的跟进项）。
- 本单未改动任何生产代码/测试/配置，未触库。
