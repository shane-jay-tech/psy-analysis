# psy relay 日志扩字段设计稿（case_id / 耗时 / 错误体）· s923-16 · 2026-09-23

> **性质：纯设计稿。** 本班 `scripts/` 与 `data/benchmark_history/` **零改动**（自证命令见第七节）。
> 上游需求出处：`zcode-bridge/done/s922-19-psy-benchmark-observe.result.md:85`
> 「`_relay_calls.jsonl` 只记 `ts/model/status/usage`，无 case_id/耗时/错误体 ⇒ 即便补够 3 批，现有日志粒度也撑不起逐题漂移追溯；是否扩字段属实现改动，超出本单只读范围，登记给 L3。」

## 〇、锚点复核（先证任务书，再谈设计）

| 任务书前提 | 实测命令（cwd `D:\code\psy-analysis`） | 读数 | 判定 |
|---|---|---|---|
| `scripts/benchmark_relay_shim.py:7` 记 `(ts/model/status/usage)` | `sed -n '7p' scripts/benchmark_relay_shim.py` | 原文逐字相符 | ✅ 成立 |
| `:20 LOG_PATH = ... parents[1] / "data/benchmark_history/_relay_calls.jsonl"` | `sed -n '20p' …` | 逐字相符（含 `s922-09/A5` 防回改注释） | ✅ 成立 |
| 现网日志「只记四键」 | 见下第一节 python 指纹 | 38 行、键形状**只有一种** `{ts,model,status,usage}` | ✅ 成立 |
| （任务书未提，但影响设计）该文件有内容消费者 | `rg -uu -n "_relay_calls" .` | `src/` 0 处；`tests/` 仅 `test_benchmark_relay_paths.py` **按名字钉路径、不解析行**；其余命中在 `docs/insights/*` 与 `tmp/*` | ✅ 「零内容消费者」成立，但**路径名有钉桩**（见风险 R1） |
| （新增否证）case_id 能零改动落进日志 | 读 `src/upstream/socratic_engine.py:381-396`、`src/paper_writer/ai_tutor.py:272-277` | 上游 payload 只有 `{model,messages,temperature}`，`ask_socratic()` 形参里**没有 case_id**，shim 结构上看不见它 | ❌ **任务书隐含前提被否证** ⇒ 本稿把它拆成「零改码可得」与「须授权改码」两档（见第二节 B 组） |

## 一、现状 schema（实测）

```
$ .venv/Scripts/python.exe -c "…见第七节 V2…"
总行数 38 / 键形状 {('model','status','ts','usage'): 38}   ← 单一形状，无历史异构
status 分布 {200: 37, 524: 1}        model 分布 {'gpt-5.6-sol': 38}
usage is None 的行 1（＝那条 524）    usage 子键 {prompt_tokens, completion_tokens, total_tokens,
                                     completion_tokens_details, prompt_tokens_details}
字节：文件 9370 B，单行 min 90 / mean 244.6 / max 263
ts：ISO 微秒、无时区后缀；文件序＝ts 严格递增（实测 True）；相邻行间隔 min 3.3s / 中位 9.9s / max 324.3s
```

生产者只有 `Handler._log()`（`benchmark_relay_shim.py:87-91`），单点写入 ⇒ 扩字段是**一处改动**，不是横切面。

## 二、新字段 schema（提案）

命名规则：一律 `snake_case`；凡时间量带单位后缀（`_ms` / `_s`）；**新增键全部平级、不改既有四键的类型与语义**（`usage` 继续是「dict 或 null」）。

### A 组 · 零改上游码即可得（只动 `Handler._log` + `do_POST`）

| 字段 | 类型 | 取值来源（精确到行） | 缺失时 | 用途 |
|---|---|---|---|---|
| `log_version` | int | 常量 `2`，每条新行都写 | 旧行无此键 ⇒ 读者按 `1` 解释 | 唯一必要的版本位；比「靠键存在性猜版本」稳 |
| `dur_ms` | int | `do_POST:64` 前 `t0=time.monotonic()`，`:79` `_log` 前落 `int((time.monotonic()-t0)*1000)` | 连接层异常也要写（异常分支已汇流到 `:71-72`） | 耗时分位、超时归因（524 那条现在无法区分「上游慢」还是「本地 300s 超时」） |
| `err_kind` | str\|null | 枚举 `null` / `http_error` / `conn_error` / `bad_upstream_json` / `no_usage`（判定点：`:68` `HTTPError`、`:71` 泛异常、`:76` usage 解析失败、`usage is None and status==200`） | 200 正常行为 `null` | **可聚合**的错误维度；隐私安全（不含原文） |
| `err_body` | str\|null | `resp_body`（`:67`/`:70`/`:72` 三处同一变量，已含错误体）**截断后**写入 | 200 正常行为 `null` | 逐题漂移追溯的根因面 |
| `err_body_trunc` | bool | `len(body) > CAP` 时 `true` | — | 让「截断」不伪装成「全量」 |
| `err_body_bytes` | int | 截断**前**的 `len(resp_body)` | — | 体积可核算；不重复存原文 |
| `user_sha8` | str | `sha256(json.dumps(last_user_content, ensure_ascii=False).encode()).hexdigest()[:8]`，取 `payload["messages"]` 最后一条 `role=="user"` 的 `content` | 无 messages 时 `null` | **离线反查 case_id 的 join 键**（可行性见下） |
| `n_msgs` | int | `len(payload.get("messages") or [])` | — | 区分「同一 input 不同 history 长度」的两次调用 |
| `rid` | str | `uuid4().hex[:8]`，每次 `do_POST` 一个 | — | 为将来「一请求多行」（如流式分片日志）预留；当前恒唯一 |

`err_body` 截断策略（设计决定，不是实现细节）：

- **CAP = 512 字符**（解码后按字符截，不按字节，避免把中文 UTF-8 截成非法字节序列）。
- 截断前先做**脱敏替换**：`re.sub(r"(?i)bearer\s+[A-Za-z0-9\-_\.]+", "Bearer <REDACTED>", s)` 与 `re.sub(r"sk-[A-Za-z0-9]{8,}", "sk-<REDACTED>", s)`。
  理由：`err_body` 是**上游回显的自由文本**，中转站在 401/403 时常回显请求头片段；本仓 shim 的 `:58` 明确把 `Authorization: Bearer {API_KEY}` 发出去，而 shim 的设计红线是「密钥绝不落日志」（`shim:6`）。不做这一步就是**新增凭据泄漏面**。
- 非纯文本响应体（gzip / 二进制）：先试 `body.decode("utf-8", "replace")`，替换符超过 20% 时只记 `err_kind="bad_upstream_json"` 且 `err_body=null`，避免把二进制灌进 jsonl。
- **禁止**整份成功响应体入日志（那是模型输出、含学生输入回显，属隐私面且体积无界）。

`user_sha8 → case_id` 的 join 为什么现在可行（实测）：

```
基准走 tests/test_socratic_quality.py:70 → ask_socratic(stage, user_input=case["input"], history=[], ...)
socratic_engine.py:376-379  history 为空 ⇒ prev_user 为假 ⇒ prefixed = user_input（逐字不加前缀）
报告 JSON 把 case["input"] 原样存进 results[].input（test_socratic_quality.py:84）
实测：30 条 case 的 input 30/30 唯一  ⇒ 反查表无歧义
```

⇒ 不需要碰生产码，就能事后把 relay 行挂回 case。**但**：它只在 `history=[]` 的基准场景等价；UI 真实路径有 history 时会命中 `:379` 的 `[学生上一轮说: …]` 前缀分支，指纹就不再等于 `input`。
所以本稿**坚持字段名叫 `user_sha8` 而不叫 `case_id`** —— 把「推得出来的近似键」冒充「调用方身份」正是这类日志最容易长出的假象。
另有一条必须写进文档的固有歧义：`src/upstream/socratic_benchmark.py:252` 的裁判 `n_runs=3` 会让同一 case 发 3 次**内容相同**的请求，`user_sha8` 在裁判调用上是 3:1 碰撞 —— 这不影响反查到 case，但意味着「按指纹数调用次数」必须配合 `rid` 或 `n_msgs` 才不重复计数。

### B 组 · 真 `case_id`（需要一次受控的生产码改动，未拍板前不做）

| 通道 | 落点 | 判定 | 依据 |
|---|---|---|---|
| A. OpenAI 标准 `user` 字段带 case_id | `src/paper_writer/ai_tutor.py:272-276` payload | **代价 = 触生产共用路径**：`chat_with_tutor` 同时服务 UI（`ai_tutor` 被 `socratic_engine` / `llm_gateway` 委托），加字段要给全部下游用例交代 | 实测 payload 现只有三键 |
| B. 自定义头 `X-Case-Id` | `ai_tutor.py:271` headers | 同上量级；优点是不进上游请求体、中转侧无未知字段风险 | — |
| C. 路径编码 `/v1/case/1-01/chat/completions` | 基准侧设 `BENCHMARK_LLM_BASE_URL` | ❌ **否证**：`_openai_chat_url`（`ai_tutor.py:210-220`）会把不以 `/v1` 结尾的 base_url 强制拼成 `<base>/v1/chat/completions`，注入的段被吃掉；要通就得改这个幂等函数（它自己有钉桩防回归） | 读码实测 |
| D. 按行序/时间窗 join | 无需改动 | ⚠️ 只可作降级证据：`shim:99` 用 `ThreadingHTTPServer`，落盘序＝**完成序不是发起序**；本次样本串行（最小间隔 3.3s）所以侥幸单调，一旦并发即错位 | 实测 `mono=True` + 读码 |

**建议裁决案**：先只上 A 组（shim 单点、零生产码风险、零隐私新增面），把 B 组 `case_id` 作为「A 组跑通一个真实批次、确认 `user_sha8` 反查命中率 = 30/30」之后的第二笔。理由：A 组已能撑起 s922-19 要的「逐题漂移追溯」，B 组的边际收益不抵它要动的共用面。

## 三、向后兼容（旧行无新键怎么读）

读侧统一口径（旧 38 行不改写、不回填 —— 回填会毁掉 `sha256` 不变量，见第七节 V4）：

```python
import json, pathlib
def read_relay(path):
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)                 # 未知键自动忽略 ⇒ 前向兼容
        ver = row.get("log_version", 1)        # 缺键 ⇒ v1
        yield {
            "ts":    row.get("ts"),
            "model": row.get("model"),
            "status": row.get("status"),
            "usage": row.get("usage"),          # v1 里可能是 None，语义不变
            "dur_ms": row.get("dur_ms") if ver >= 2 else None,      # None = 无观测
            "case_id": row.get("case_id") if ver >= 2 else None,    # B 组未上恒 None
            "user_sha8": row.get("user_sha8") if ver >= 2 else None,
            "err_kind": row.get("err_kind", "http_error" if row.get("status", 200) >= 400 else None),
        }
```

三条硬规定：

1. **`null` 与「无此键」不等价**：`dur_ms=null` 表示「写了但未测到」，缺键表示「v1 旧行」。统计侧要分开，否则耗时分布会被旧行拉平。
2. **禁止按位置取键**（`list(row.values())[2]`）：现行形状单一（实测 38/38 同形状），加键后位置全变，而名字不变。
3. **禁止把「新日志出现异构」当损坏**：v1/v2 混排是设计结果，`test_output_snapshot_roundtrip` 那类「整文件等值」式断言不许套到本文件上。

## 四、对既有统计脚本的兼容影响

| 读者 | 现状（rg 实测） | 扩字段后 | 需要动作 |
|---|---|---|---|
| `tests/test_benchmark_relay_paths.py`（6 例） | 只钉 `LOG_PATH` 文件名与父目录、`evaluate.HISTORY_DIR` 同根，**不读内容** | 全绿不受影响 | 无。**前提是不改文件名/落点**（R1） |
| `scripts/evaluate_socratic_benchmark.py` | **完全不读本文件**（只读 `_benchmark_reports/*.json` 与 `benchmark_history/*.json` 归档，`:132` 的 glob 是 `*.json`，jsonl 天然被排除） | 不受影响 | 无。⚠️ 反过来说：relay 日志**从没进过漂移计算**，扩字段不会自动让 drift 报告变好，得另写聚合 |
| `scripts/analyze_usage_logs.py` | 读 `logs/usage_events_*.jsonl` / `error_events_*.jsonl`，与本文件无交集 | 不受影响 | 若将来合并分析要处理键名分歧（R3） |
| `src/utils/usage_logger.py` | 另一条日志通道（`timestamp` 秒级 + `event` 键），`_ENABLED` 开关 | 不受影响 | 别把 relay 行误投进 `logs/`：通道语义不同（生产 UI 事件 vs 一次性基准观测） |
| `docs/insights/psy-benchmark-observe-20260922.md:81` 等复算命令 | 文档里贴的是 `rows=[json.loads(l)…]` 式 ad-hoc 片段 | 命令仍可跑，但**派生口径（38 行 / 9370 B / mean 244.6 B）会随新批次变** | 在历史文档不必回改，**新报告须标注「口径取于 2026-09-23、38 行」** |

## 五、体积评估

| 场景 | 单行 | 一批（现观测 38 行） | 3 批（s922-19 的最低样本量） |
|---|---|---|---|
| 现状 | mean 244.6 B / max 263 B | 9,370 B | ≈ 28 KB |
| A 组最小集（+`log_version/dur_ms/err_kind/user_sha8/n_msgs/rid`，正常行 `err_body=null`） | mean ≈ **244.6 + 96 ≈ 341 B**（键名+分隔实测折算：`"log_version":2,`=16、`"dur_ms":12345,`=14、`"err_kind":null,`=17、`"user_sha8":"a1b2c3d4",`=25、`"n_msgs":2,`=12、`"rid":"deadbeef",`=18，含逗号与空格的 `"err_body":null,`=16、`"err_body_bytes":0,`=21、`"err_body_trunc":false,`=27 ⇒ 合计 166 B；保守取含 `err_body` 三键的 166 B 与省略 `err_body_bytes/trunc`（仅错误行写）的 96 B 两档） | ≈ 13.0 KB（+38%） | ≈ 39 KB |
| 全部错误行带 512 字符错误体（上界，现网错误率 1/38 ≈ 2.6%） | +≤530 B | 现网比例 ≈ **10.0 KB**；最坏 38 行全错 ≈ 29 KB | 最坏 ≈ 88 KB |
| 若一并接 B 组 `n_runs=3` 的裁判调用 | 一行不变 | 行数 38 → **128**（30 生成 + 8 重试 + 90 裁判） | ≈ 44 KB / 批 |

结论：**体积不是否决项**（三批最坏 <0.1 MB）。真正的上界纪律是「`err_body` 必须有 CAP」——无界的自由文本才是唯一能把这个文件写爆的字段。单行上界 ≈ 263+530 ≈ 800 B，仍远小于 4 KB，`open("a")` 单次 `write` 在常见文件系统上不被撕裂；**不得**为了「看全貌」把 CAP 抬到 KB 级（并发追加的原子性前提就会被破坏，且 Windows 上 append 语义本就弱）。

## 六、兼容性风险点（≥3，本稿给 6 条，按危害排序）

- **R1 文件名/落点有钉桩，改名即红。** `tests/test_benchmark_relay_paths.py:31` `RELAY_LOG_NAME = "_relay_calls.jsonl"`，并有 3 条正向 + 2 条**反向鉴别力**用例锁住「仓根 `data/benchmark_history/`、不得落回 `scripts/`」。⇒ 「新开 `_relay_calls.v2.jsonl` 分文件」这种看似最干净的方案**会直接弄红 6 例**，只能在同名文件内加键。
- **R2 「usage 是 dict 或 None」是既有语义。** 把错误体塞进 `usage`（省一个键）会让现有读者在 `usage["prompt_tokens"]` 上撞 `KeyError`；实测 `usage` 已有 5 个子键且含 `completion_tokens_details` 嵌套。⇒ 新键一律平级。
- **R3 键名与本仓另一条日志通道分歧。** `src/utils/usage_logger.py:85` 用 `timestamp`（`timespec="seconds"`、无时区），shim 用 `ts`（微秒、无时区）。合并两路做「一次运行的时间线」时，秒级行与微秒行同序会**看起来**对（字符串序恰好单调）但精度语义不同。⇒ 新增时间量一律带单位后缀，且**不要**顺手把 `ts` 改成 `timestamp`（那是 R1 之外的第二次断档：历史 38 行会永久失联）。
- **R4 隐私 / 凭据泄漏面（红线相关，本稿最高危）。** `err_body` 与 `messages` 原文都是上游可控回显：`Authorization: Bearer …` 片段可被 401 响应体带回，`messages` 含学生输入。shim 现在的设计承诺是 `shim:6`「绝不落日志」。⇒ 落 A 组之前，**脱敏 + CAP + 不记 request body** 三条要在同一个 commit 里，不可拆成两步「先记了再收」。
- **R5 时钟与顺序。** 实测 `ts` 单调但那是**串行运气**；`ThreadingHTTPServer`（`:99`）下多行会按完成序落盘。任何「按行号推 case 顺序」的下游假设都不成立 ⇒ 反查只认 `user_sha8` / `rid`，不认行序。另：`dur_ms` 必须用 `monotonic()`，用 `ts` 差值会把「上一条到这一条的排队/人工等待」算进耗时（实测相邻行间隔最大 324.3 s）。
- **R6 「补字段」不等于「补观测」。** 本文件自 9/10 起 0 追加（`psy-benchmark-history-recheck-20260918.md:9` 已证），根因是 `LOG_PATH` 曾指向不存在目录（`eec95c3` 才修好）。路径修好后**仍无一次带网实跑** ⇒ 扩字段若不同时仍没人跑基准，得到的仍是 38 行旧格式。⇒ 实施步骤里 S4（真跑一批）不是可选项，否则这单只是给一条死水管贴新标签。

## 七、落实施步骤清单

- **S0 前置裁决（不动码）**：把本稿交 L3 裁决两问 —— ① 是否允许为真 `case_id` 碰 `src/paper_writer/ai_tutor.py`（A/B 通道）；② `err_body` 是否接受「脱敏 + 512 字符」口径。未拍板只做 S1。
- **S1 shim 单点改动（A 组，最小可交）**：`do_POST` 记 `t0=monotonic()` → 抽 `err_kind` → `_log()` 签名扩为 `_log(status, model, usage, *, dur_ms, err_kind, err_body, user_sha8, n_msgs, rid)`。改动面：`scripts/benchmark_relay_shim.py` 一个文件、约 25 行；`:7` 的模块文档串同步（它现在写死了「(ts/model/status/usage)」，不改就是**注释说谎**）。
- **S2 测试（只测纯函数，零网络零写盘）**：新建 `tests/test_benchmark_relay_log_schema.py`；把 `_log` 的行组装抽成 `build_record(...) -> dict` 以便无 IO 断言。必含 ① 旧行读法 `read_relay` 对现网 38 行**逐行不抛**；② 新行含 `log_version==2` 且四旧键语义不变；③ `err_body` 超长必截且 `Bearer`/`sk-` 样式在输出中**不出现**（鉴别力：把脱敏函数摘掉必须红）；④ 现有 6 例路径钉桩仍绿。跑法：`-k 'relay or shim'` 与 `-k 'download_buttons or export_gate'` 都跑（后者是 psy 全局账本门，见纪律档 §十五）。
- **S3 读侧统一**：把第三节 `read_relay()` 落成 `scripts/` 内一个小工具或直接进 `evaluate_socratic_benchmark.py --relay-summary`（**新参数**，不动 `--track-drift` 语义）。禁止用行序 join（R5）。
- **S4 一次受控带网验证（需人工授权）**：`BENCHMARK_LLM_BASE_URL=http://127.0.0.1:8791/v1` 跑**缩样**（3 case 即可，不必 30），核对：① `user_sha8` 反查命中 3/3；② `dur_ms` 非空；③ 制造一次 4xx 看 `err_kind/err_body` 形状与脱敏。
- **S5 不变量核对 + 归档**：跑第八节 V4，确认 `data/benchmark_history/` 除 `_relay_calls.jsonl` 外三件 sha256 逐字未变、mtime 未动；把本稿结论 + 实测读数折进 `docs/insights/psy-relay-log-schema-20260923.md` 的后续修订段，并在待人工台账登记 S0 两问。
- **S6 反悔出口**：若 S4 显示 `user_sha8` 命中不满（例如范例注入改了 messages 结构），**不要**退化成「记 request body 前 200 字符」——那直接踩 R4。正确出口是回到 S0 要 B 组授权。

## 八、自证命令（本单零改动）

```bash
cd /d/code/psy-analysis
# V1 现网 schema 指纹
.venv/Scripts/python.exe - <<'PY'
import json,collections,pathlib
p=pathlib.Path('data/benchmark_history/_relay_calls.jsonl')
rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
print(len(rows), collections.Counter(tuple(sorted(r)) for r in rows))
PY
# V2 join 可行性：fixture input 唯一性
.venv/Scripts/python.exe -c "import json,pathlib; r=json.loads(pathlib.Path('tests/fixtures/_benchmark_reports/benchmark_20260910_031938.json').read_text(encoding='utf-8')); print(len(r['results']), len({x['input'] for x in r['results']}))"
# V3 消费者面（本机 rg 可用；-uu 才能看见 gitignored 的 tmp/）
rg -uu -n "_relay_calls" --glob '!node_modules/**' --glob '!.git/**' .
# V4 不变量：data/benchmark_history/ 逐文件 sha256 前 8 位（本单执行前后必须一致）
.venv/Scripts/python.exe -c "import hashlib,pathlib;[print(hashlib.sha256(f.read_bytes()).hexdigest()[:8], f.name) for f in sorted(pathlib.Path('data/benchmark_history').iterdir())]"
# V5 scripts/ 与 data/ 零改动
git status --porcelain scripts data ; git diff --stat -- scripts
```

V4 基线（本班 2026-09-23T11:4x 现取，`_relay_calls.jsonl` = `dff47515…` 与 `psy-benchmark-observe-20260922.md:11` 在册值一致）：

```
3d83f7e9 _latest_drift.md          dff47515 _relay_calls.jsonl
092d61b0 benchmark_backfill_draft.json   909b4799 socratic_benchmark_20260909T192139Z.json
```
