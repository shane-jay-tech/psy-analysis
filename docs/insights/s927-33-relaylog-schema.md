# `_relay_calls.jsonl` 日志粒度补齐 · 裁决材料（s927-33 · 2026-09-28）

> 性质：**只读位出材料**。本班 `scripts/`／`src/`／`data/`／`tests/` 零改动，零改账。
> 档位：本单属「实现改动 ＋ 隐私面」双域 ⇒ 数值与放行结论一律交人工，本文只给可批形状。

## 〇、最重要的一条：设计稿早已在世，本单缺的不是 schema 而是「没人把问题递上去」

| 事实 | 实测出处 | 读数 |
|---|---|---|
| 本单的「做什么」（字段 schema＋回填＋推荐）已由 **s923-16** 完整交付 | `docs/insights/psy-relay-log-schema-20260923.md`（19,748 B／178 行，已入库 `92805ff` @2026-09-23T12:17:44+08:00） | 含 A/B 两组字段表、向后兼容读法、体积评估、6 条风险、S0–S6 实施清单 |
| 该案设计稿的**现网读数今日逐位复现**（无漂移） | 本文第一节命令 | 38 行／单一键形状／`dff47515`／mean 244.6 B ⇒ 与 s923-16、s922-19 两处在册值全等 |
| 🔴 但该稿 S5 步要求的「在待人工台账登记 S0 两问」**从未发生** | `grep -n "relay\|err_body\|_relay_calls\|s923-16" D:/code/docs/insights/drain-20260923-pending-human.md` → **No matches**（该档现存 179 行账目、末号 **238**，mtime 2026-09-28 11:31 仍在被主班追记） | ⇒ 所以 s922-19 遗留 3／s922-104 遗留 1 至今「未结」的**根因是漏登记，不是缺设计** |
| 生产码至今仍是 v1 四键（无人绕过裁决先动手） | `git log --oneline -- scripts/benchmark_relay_shim.py` → 只有 `a411e65`（建）＋ `eec95c3`（路径一行修）；`git status --porcelain scripts/benchmark_relay_shim.py` → 空 | `_log()` 组装体（`:87-91`）仍写死 `{ts,model,status,usage}` |

**结论性判据（交主班）**：本单不需要第二份设计稿；需要的是一行台账账目（第四节 P0）＋ 一道**排序闸**（#L3 观测面去留）。

## 一、现网 schema 实测（本班 `.venv` 复跑，非转述）

```
N 38
SHAPES Counter({('model','status','ts','usage'): 38})     ← 单一形状，无历史异构
STATUS Counter({200: 37, 524: 1})    MODEL Counter({'gpt-5.6-sol': 38})
ts_first 2026-09-10T03:01:31.933848   ts_last 2026-09-10T03:19:38.266844
mono True                              ← 文件序＝ts 序（串行运气，见 R5）
bytes min 90 / mean 244.6 / max 263   file_size 9370
usage is None 的行 1（＝那条 524）
usage 子键覆盖计数 {prompt_tokens:37, completion_tokens:37, total_tokens:37,
                   completion_tokens_details:35, prompt_tokens_details:30}
sha256_8: 3d83f7e9 _latest_drift.md | dff47515 _relay_calls.jsonl
          092d61b0 benchmark_backfill_draft.json | 909b4799 socratic_benchmark_20260909T192139Z.json
```

`usage` 子键**不是恒定集**（35/38、30/38）⇒ 任何读者按 `usage["prompt_tokens_details"]` 直取都会在那 8 行上撞 `KeyError`，这是"扩字段不许动 `usage` 语义"（s923-16 R2）的实测支撑。

断档现值（**日历事实，非统计结论**）：末条观测 → 本班取数 `2026-09-28T11:34:37` ⇒ **18.34 天**；路径修复 `eec95c3`（committer **2026-09-21T22:24:55+08:00**）→ 今日 **6.27 天，期间 0 次落观测**。
〔订正一条在册读数：s922-19 写「`eec95c3` 落地 ≈ 9/22 00:0x」，实测 committer 时戳是 **9/21 22:24**，差约 1.6 小时；由此「11.9 天结构性不可能落观测」应为 **≈10.3 天**（9/10 03:19 → 9/21 22:24）。该偏差不改变该案结论方向，但别再抄 11.9。〕

## 二、字段 schema：本单认可的在册形状 ＋ 三处必要修正

采 s923-16 的两组划分，本班只复核承重事实（命令见第六节）：

| 组 | 字段 | 零改生产码可得？ | 本班复核依据 |
|---|---|---|---|
| A（只动 shim） | `log_version` `dur_ms` `err_kind` `err_body(+_trunc/_bytes)` `user_sha8` `n_msgs` `rid` | ✅ 是——写盘点唯一：`Handler._log()`（`:87-91`），单点改动非横切面 | 读码：`do_POST` 已握有 `payload`（`:49`）、`status`（`:69`）、`resp_body`（`:67/70/72` 三径汇流）⇒ A 组全部字段**不需要新信息源**，只是没往下传 |
| B（真 `case_id`） | `case_id` | ❌ 否——需碰 `src/paper_writer/ai_tutor.py` 的共用 payload 或头 | 读码 `ai_tutor.py:272-277`：OpenAI 兼容 payload 现只有 `{model, messages, temperature}` 三键；`ask_socratic()` 形参无 case_id ⇒ shim 结构上看不见它 |

三处对 s923-16 的**补充/收紧**（本单唯一的增量设计内容）：

1. **`user_sha8` 的 join 前提要写成硬约束而非"实测可行"**：反查表成立依赖两件事同时成立——基准侧 `history=[]`（`socratic_engine.py` 空历史 ⇒ 不套 `[学生上一轮说: …]` 前缀）＋ 报告 JSON 原样存 `input`。本班实测 `tests/fixtures/_benchmark_reports/benchmark_20260910_031938.json`：`results 30 / unique_input 30`、每条带 `case_id`（形如 `1-01`）⇒ **当前 30/30 无歧义**。但这条只在基准通道成立，UI 真路径有 history 即失效 ⇒ 台账里请写「A 组只服务基准观测面，不得声称具备生产逐题追溯能力」。
2. **裁判调用会天然造 3:1 指纹碰撞**：`src/upstream/socratic_benchmark.py:94,117,233,256` 的 `n_runs` 默认 **3** ⇒ 同一 case 发 3 次**内容相同**的请求。故「按 `user_sha8` 数调用次数」是错的，必须配 `rid`；且若一并覆盖裁判面，单批行数会从 38 量级涨到 ≈128（30 生成＋重试＋90 裁判），s923-16 第五节的体积表要按此重算。
3. **`err_body` 的脱敏与 CAP 必须与写盘同 commit（红线，不可拆两步）**：`shim:58` 把 `Authorization: Bearer {API_KEY}` 发出去，而模块文档串 `:6` 的承诺是「密钥绝不落日志」；`err_body` 是上游自由回显 ⇒ 先落 `err_body` 后补脱敏＝**中间态存在凭据泄漏面**。⇒ 属隐私/凭据域，判「够不够严」不归子班，交人工。

钉桩代价（决定"只能加键、不能改名"）：`tests/test_benchmark_relay_paths.py:31` `RELAY_LOG_NAME = "_relay_calls.jsonl"` ＋ 3 正向／2 反向鉴别力用例。本班实跑：`6 passed in 0.18s`（`.venv`，零写盘）。

## 三、回填取舍（本案要拍的那一板）

| 案 | 内容 | 代价／不可行处 | 本班读数 |
|---|---|---|---|
| **R-A 不回填（推荐）** | 旧 38 行原样留，新行带 `log_version: 2`；读侧 `row.get("log_version", 1)` 分版本解释，"缺键"与"`null`"语义分开 | 历史 38 行永久无耗时/无错误体 ⇒ 9/10 那一批不可逐题追溯 | ①`dur_ms`／`err_body` **物理不可恢复**（当时没测、没留），回填只能造数；②那条 524 连 `usage` 都是 `null`，可恢复上限＝零；③改写会毁 `sha256` 不变量（`dff47515` 是 s922-19／s922-104／s923-16 **三个班跨日互证**的锚，动它等于抹掉三件在册证据）；④`data/` 被 gitignore ⇒ 回填**无还原点** |
| R-B 重开一份 v2 文件 | `_relay_calls.v2.jsonl` 起新格式，旧件归档 | **直接弄红 6 例钉桩**（R1）＋ sidecar 命名要过 `evaluate_socratic_benchmark.py:132-134` 的 `_` 前缀约定 | 已实测否证，不建议列进选项 |
| R-C 回填「可得字段」 | 只补 `user_sha8`/`n_msgs`（当时请求体可推）—— 但请求体并未留存 | 无从推：shim 不落 request body（这是设计优点，别改） | 不可行 |

⇒ 三案合起来只有一案可批：**R-A 不回填**，并把「历史 38 行＝v1、不参与耗时与错误分布统计」写成读者契约（s923-16 第三节已给 `read_relay()` 形状，可直接用）。

## 四、推荐处置（分档，含可批形状）

**P0（零改码，本单真缺口）**：把两问补进待人工台账（末号 238 ⇒ 追加 **239**）。主班可直接粘的条目形状：

> | 239 | 🔴 **psy relay 日志粒度：设计已交付、裁决从未登记**（s927-33 复点）。事实：`psy-relay-log-schema-20260923.md`（`92805ff`）已给 A/B 两组 schema＋`read_relay` 兼容读法＋S0–S6 步骤，其现网读数今日逐位复现（38 行／`dff47515`／mean 244.6 B）；但该稿 S5 要求的「登记 S0 两问」未做 ⇒ 待人工台账全文 grep `relay` 零命中。断档 **18.34 天**，路径修复 `eec95c3`（**9/21 22:24**，非在册写的「≈9/22 00:0x」）后 **6.27 天 0 次落观测** ⇒ 补字段与补观测必须同批裁。另订正：s922-19 的「11.9 天结构性不可能」按真时戳应为 **≈10.3 天**。 | A：只做 A 组（shim 单文件、约 25 行、含脱敏＋CAP 同 commit）并**紧跟一次受控缩样实跑**，否则等于给死水管贴标签；B：判「观测面收摊」（承接 #L3 出口 B），则本项与 `_latest_drift.md`／drift_tracker 10 例同批处置，**不要再开 S1** | 待人工 |

**排序闸（本单最该被看见的一条）**：S1（扩字段）**必须排在 #L3「观测面去留」之后**。理由：`psy-benchmark-observe-20260922.md` §6 已给三出口，其中 **B＝停 shim、日志归档为一次性产物**。若 L3 选 B，S1 的全部改动直接变死码——届时"补齐粒度"这单又会以「无人跑基准」原样结案。故：**L3 未答之前不批 S1**。

**逐处推荐**：

| 议题 | 推荐 | 理由（一句话） |
|---|---|---|
| A 组 9 键 | **批**（前置于 L3＝A） | 单点改动、零上游码风险、撑起「这批到底跑得慢在哪」 |
| B 组真 `case_id` | **暂不批** | `user_sha8` 在基准面已 30/30 可用，B 组要动 UI 共用路径，边际收益不抵面 |
| 回填 | **不回填**（R-A） | 见第三节 ①–④ |
| `err_body` 口径 | **交人工定严** | 凭据/隐私域，子班不背书 |
| 只加 `dur_ms` 的最小集 | 可作降级出口 | 若人工否掉 `err_body`（隐私），`dur_ms`+`err_kind`+`log_version` 三键零隐私面，仍解掉「524 分不清上游慢还是本地 300s 超时」这个具体缺口 |

**验收形状（若将来放行 S1，定向即可，不必全量）**：新建 `tests/test_benchmark_relay_log_schema.py`（纯函数断言、零网络零写盘）＋ 必跑 `tests/test_benchmark_relay_paths.py`（6 例不许红）；实施侧别忘了同步 `shim:7` 的模块文档串——它现在写死「(ts/model/status/usage)」，不改就是注释说谎。

## 五、遗留问题

1. **本单的「新发现」只有两处**：①设计稿已存在但其裁决请求从未进台账（漏登记）；②S1 与 #L3 去留的**先后顺序**在册材料里没写死。schema 本体不重复登记，引 s923-16。
2. `psy-knownissues-v512-20260920.md:30` 仍说 `LOG_PATH`「少一层」——该描述已陈旧（`psy-data-hygiene-20260924.md:281` 已点名），别据它重复开单。
3. 断档根因是否仍含「shim 根本没被拉起」这一层，只读路径无法判定（需进程/计划任务面，属越域），未查。
4. 「补 3 批样本」＝带网基准实跑＝统计结论域＋成本档 ⇒ 本班未跑、不背书。

## 六、复跑命令（本文所有数字的出处）

```bash
cd D:/code/psy-analysis                                    # HEAD fa3f41e（现取）
.venv/Scripts/python.exe - <<'PY'                          # 第一节：现网 schema 指纹
import json,collections,pathlib,statistics
p=pathlib.Path('data/benchmark_history/_relay_calls.jsonl'); raw=p.read_text(encoding='utf-8')
rows=[json.loads(l) for l in raw.splitlines() if l.strip()]
print('N',len(rows)); print('SHAPES',collections.Counter(tuple(sorted(r)) for r in rows))
print('STATUS',collections.Counter(r['status'] for r in rows)); print('MODEL',collections.Counter(r['model'] for r in rows))
print('mono',all(rows[i]['ts']<=rows[i+1]['ts'] for i in range(len(rows)-1)))
L=[len(l.encode()) for l in raw.splitlines() if l.strip()]
print('bytes',min(L),round(statistics.mean(L),1),max(L),p.stat().st_size)
PY
.venv/Scripts/python.exe -c "import hashlib,pathlib;[print(hashlib.sha256(f.read_bytes()).hexdigest()[:8],f.name) for f in sorted(pathlib.Path('data/benchmark_history').iterdir())]"
.venv/Scripts/python.exe -c "import json,pathlib;r=json.loads(pathlib.Path('tests/fixtures/_benchmark_reports/benchmark_20260910_031938.json').read_text(encoding='utf-8'));print(len(r['results']),len({x['input'] for x in r['results']}))"   # → 30 30
.venv/Scripts/python.exe -m pytest tests/test_benchmark_relay_paths.py -q                                   # → 6 passed
grep -n '"model"\|"messages"\|"temperature"' src/paper_writer/ai_tutor.py                                   # → 三键 payload
grep -n "n_runs" src/upstream/socratic_benchmark.py                                                         # → :94 :117 :233 :256 默认 3
grep -n "relay\|err_body\|_relay_calls\|s923-16" D:/code/docs/insights/drain-20260923-pending-human.md       # → 零命中
git --no-pager log --oneline -- scripts/benchmark_relay_shim.py; git status --porcelain scripts/benchmark_relay_shim.py
```

零改动自证（本班收口前取）：`git status --porcelain` 开工 12 项 → 本单收口 13 项，增量恰为本文件一项（同班后两单各再带一份文档，本班终值 15）；原 8 枚 ` M` 与另 4 枚 `??` 在途件逐件原样；`data/benchmark_history/` 四件 `sha256_8` 见第一节，本班全程 `read_text`/`read_bytes` 只读。
