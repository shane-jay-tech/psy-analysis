# psy workspace 快照逐键体量运行时实测 + v35 同源重复度（s923-38，2026-09-24）

> 单号 `s923-38`；执行班 `qoder-executor-20260924-0955-psy22`（只读位）。
> 本档是 s922-129 设计稿（`psy-snapshot-planA-incremental-design-20260922.md`）§6 遗留 1/2 点名要补的
> **运行时测量**：把「25 键体量定性排序」换成实测表，把 `workspace_state_v35` 同源重复度从存疑项变成读数，
> 并据此修正 A-1 收益区间。
> 🔴 全程 `~/.psy_analysis` 零写（测前/测后逐件指纹复验，见 §7）。

## 0. TL;DR（四条）

1. **键数是 26 不是 25**：静态 AST 与运行时键集双向一致（`缺=[] 多出=[]`）。设计稿沿用「其余 25 键」是「26 − df_b64」口径，本节按 26 全键报。
2. **v35 与 tutor_histories 的重复＝不成立**（机制级否证：`WorkspaceState` 全部 dataclass 字段无任何 tutor 字段）；与 `upstream_state`/`literature_review_state` 的重复**成立且更大**——还连带 `wizard`/`analysis`/`ui`/`advanced` 三组镜像（设计稿没点名的）。busy 场景实测 v35 内部 **98.3%** 字节与顶层键内容逐字节相同。
3. **A-1 收益区间「−93%~−99%」按实测 S 收窄到 −97.9% ~ −99.99%**（S 真实值 0.97 KB ~ 305 KB，均低于设计稿假设下限 100 KB～1 MB 区间的中段）。设计稿「键级去重收益可能大于 A-2 全部增量」**不成立**：v35 去重只占全包写量的 0.4%，但它把 A-1 之后的 S 本身砍 20%——两者是叠加关系，不是替代关系。
4. **现存快照只有 1 件、1261 B、v2.9 时代、不含 v35/tutor 键**——「现存快照逐键测」的真实盘面样本极弱，全键读数必须由沙盒运行时构造（本文方法），繁忙态数字是**合成载荷形态演示**，不是本机真实使用量。

## 1. 任务前提复核（含否证）

| 卷宗前提 | 实测 | 判定 |
|---|---|---|
| `src/utils/workspace.py:387` = `ws["workspace_state_v35"] = wsv.to_dict()` | `sed -n '387p'` 输出与引文逐字相同 | ✅ 锚点 0 漂移 |
| `tmp/census_snapshot_keys_s922_129.py` 在盘可复用 | 跑通（改造复用其 AST 展开法） | ✅ |
| s922-129 result「未做运行时测量」「未验证 v35 重复度」在册 | done/ 件 grep 命中行 89/90 | ✅ |
| 「25 键」 | 静态 26 键、运行时 26 键 | ❌ 按磁盘实况修正为 26 |
| 「`~/.psy_analysis` 现存快照」（复数暗示） | 全目录仅 3 文件：`projects/9b2b71937e1d.json`(1261B) + `index.json`(170B) + `user_prefs.json`(97B)；工作区快照仅 1 件 | ❌ 样本 n=1，空闲机 |
| v35 疑与 `tutor_histories` 大面积重复 | v35 dataclass 字段扫描 `['funnel_history','analysis_history']`，无 tutor | ❌ 否证（§5） |

另一处盘态异常（登记不处置）：`projects/index.json` 在册 id 是 `fcc90a0fd0f4`，盘上工作区文件却是 `9b2b71937e1d.json`——索引与文件不一致，`_recover_index_from_workspaces()` 的触发条件在真实盘上成立。本单只读未动。

## 2. 方法与沙盒

- **副本法**：`copy2` 三件套到 `tmp/s923-38/home/`，测的全部是副本；测前/测后对源目录逐件取 `(size, mtime_ns, sha256_8)` 断言逐位相同（脚本守卫，漂移即 `rc=6`）。
- **运行时构造**：`sys.modules` 注入假 `streamlit` 模块（真 streamlit 全程未 import，`__file__ is None` 断言自证），把盘上快照真实内容 + 合成载荷灌进 `FakeSS`，调**生产函数** `build_workspace_snapshot()`（纯内存、无落盘路径，L226-396 人工核读 + 源目录复验双证），再对输出逐键 `len(json.dumps(v, ensure_ascii=False, default=str))`——与 `project_manager._atomic_write_json` 同参数。
- 第二道保险：`PSY_ANALYSIS_HOME` 环境变量指到 tmp 沙盒（`app_paths.py:18`）。
- 未调用 `save_workspace`/`trigger_autosave`/backup 脚本；未跑全量套件（只读位纪律）。
- 可复跑：

```
$ cd D:\code\psy-analysis
$ PSY_ANALYSIS_HOME=tmp/s923-38/probehome PYTHONUTF8=1 .venv\Scripts\python.exe tmp\s923_38_key_sizing.py
（rc=0；stdout 即本报告全部读数，副本读数另存 tmp/s923-38/readings.json）
```

## 3. 盘上唯一现存快照逐键字节（`projects/9b2b71937e1d.json`，v2.9，1261 B）

| 键 | 字节 | 键 | 字节 |
|---|--:|---|--:|
| upstream_state | 292 | _schema | 6 |
| inspector | 288 | undergrad_mode | 5 |
| literature_review_state | 243 | _version | 5 |
| meta | 75 | analysis_history | 2 |
| df_b64 | 46 | undergrad_wizard_data | 2 |
| _saved_at | 21 | undergrad_step | 1 |
| app_mode | 19 | | |
| file_name | 10 | **Σvalue** | **1015** |

非 df 合计 **S_disk = 969 B**。其余 12 个 schema 键（plan/tutor_histories/v35/figure_collection/…）盘上**不存在**——该快照早于 v3.1–v3.5 全部特性。

## 4. 运行时全键实测（真实函数；light=盘上数据+最小合成，busy=合成活跃载荷）

| 键 | light B | busy B | light 来源 | busy 来源 |
|---|--:|--:|---|---|
| tutor_histories | 7,648 | 93,696 | 合成 3×20 轮 | 合成 4×60 轮 |
| figure_collection | 24,342 | 74,184 | 合成 3 图 | 合成 9 图(plotly json) |
| workspace_state_v35 | 1,399 | 61,249 | v35 镜像 | v35 镜像 |
| upstream_state | 292 | 30,993 | 盘上真实 | 真实结构+合成载荷 |
| literature_review_state | 243 | 27,234 | 盘上真实 | 真实结构+40 文献 |
| questionnaire_design | 4,147 | 9,748 | 合成 30 项 | 合成 60 项 |
| download_history | 710 | 2,920 | 合成 | 合成 30 条 |
| analysis_history | 2 | 2,160 | 盘上(空表) | 合成 8 条 |
| defense_qa_mastered | 1,083 | 1,083 | 合成 20 问 | 同 |
| experiment_design | 565 | 565 | 合成 | 同 |
| analysis_output | 402 | 402 | 合成(含 descriptive df) | 同 |
| inspector | 288 | 288 | 盘上真实 | 同 |
| paper_engine_state | 187 | 187 | 合成 | 同 |
| plan | 122 | 122 | 合成(unwrap 后与 v35 等值) | 同 |
| meta | 75 | 75 | 盘上真实 | 同 |
| df_b64 | 46 | 46 | 盘上真实(4 行 mini csv) | 同 |
| _saved_at/_version/_schema | 32 | 32 | 构建常量 | 同 |
| app_mode | 19 | 19 | 盘上真实 | 同 |
| file_name / quick_model_id / undergrad_path | 10/10/8 | 10/10/8 | 真实+合成 | 同 |
| undergrad_mode / wizard_data / step | 5/2/1 | 5/2/1 | 盘上真实 | 同 |
| **S（非 df 26 键合计）** | **41,592** | **304,993** | | |

双向自证：运行时键集 vs 静态 AST schema `缺=[] 多出=[]`（两场景均 26/26）。

## 5. workspace_state_v35 同源重复度

**方法**：① 机制级——枚举 `WorkspaceState` 及其 6 个子 dataclass 字段名；② 数值级——对 23 对「v35 子字段 ↔ 顶层键/字段」做 json 深等比对（`sort_keys=True`），深等字节计为重复；`plan` 按 unwrap（顶层 `{"__type__":"dict","data":…}` 的 data）比对。

- **① tutor：否证。** 含 `tutor`/`history` 的字段只有 `funnel_history`、`analysis_history`，v35 结构里**没有任何对话历史容器**。设计稿「v35 疑与 tutor_histories 大面积重复」不成立。
- **② 与 upstream/lr 的重复成立**，且**镜像面比设计稿猜的大**：`funnel.*`↔`upstream_state.*`（9 字段）、`literature_review.*`↔`literature_review_state`（7 字段）、`wizard.*`↔`undergrad_path/step/wizard_data`、`analysis.*`↔`plan/analysis_history(/analysis_output 形不同源同)`、`ui.undergrad_mode`↔`undergrad_mode`、`advanced.*`↔`upstream_state.advanced_meta`。
- **数值**：

| 场景 | v35 字节 | 其中与顶层深等 | 重复率 |
|---|--:|--:|--:|
| light（盘上小数据） | 1,399 | 356 | 25.4% |
| busy（合成活跃载荷） | 61,249 | 60,206 | **98.3%** |

非重复的 1,043 B（busy）= lr 三个 `last_*_method` 新字段 + advanced 默认串 + 结构名开销 ⇒ **内容越肥，v35 越接近纯重复**（stages 24,950 B、literature_items 22,678 B 逐字节全等）。上限推论：活跃大项目 v35 重复率渐近 ~99%。
- **v35 未激活时的形态**：盘上 v2.9 快照根本没有该键——v35 键只在 `session_state[WORKSPACE_KEY]` 已是 `WorkspaceState` 实例时写入（`workspace.py:383-389`），存量文件不会自动长出来。

## 6. A-1 收益区间修正

现状「df 不变的一次保存」写整包 `13,981,013 + S`；A-1 后写 `S`（state.json）⇒ 降幅 = THR/(THR+S)：

| S 场景 | S (B) | 降幅 | 现状单次写量 |
|---|--:|--:|--:|
| S_disk 现存快照 | 969 | **99.99%** | 13.98 MB |
| S_light | 41,592 | 99.70% | 14.02 MB |
| S_busy（含 v35） | 304,993 | **97.87%** | 14.29 MB |
| S_busy 删整个 v35 键 | 243,744 | 98.29% | 14.22 MB |
| S_busy 留 v35 删顶层镜像 | 244,787 | 98.28% | 14.23 MB |

- 设计稿在册区间 −93%~−99%（对应 S=1MB~100KB）**整体偏悲观**：实测把区间改为 **−97.9% ~ −99.99%**（S ≤ 305 KB 的机器形态下）；−93% 下界只有当 26 键合计 >1 MB（超长对话/数百文献条目）才触及。
- 「键级去重（v35）收益大于 A-2 全部增量」**判定不成立**：v35 去重在整包写面只省 61 KB（0.4%）；但**叠加在 A-1 之后**时它砍的是 A-1 的全部剩余写量 S 的 20%（S_busy 305→244 KB）。正确排序：A-1 先行 → v35 去重作为 A-1 的第二刀（改 `build_workspace_snapshot` 让顶层镜像键改为引用 v35 或反向，二选一存 `sync_to_legacy_session` 现成通路）→ A-2 不必再谈。

## 7. userhome 零写自证

测前与测后 `fingerprint(~/.psy_analysis)` 逐件输出全等：

```
projects/9b2b71937e1d.json  size=1261  mtime_ns=1787507605892501700  sha8=1ae1b940
projects/index.json         size=170   mtime_ns=1790136914381718200  sha8=aa307860
user_prefs.json             size=97    mtime_ns=1790136920240784900  sha8=c5d100fe
TOTAL files=3 bytes=1528
```

披露一项边界外副作用：`_serialize_plan` 触发 `src.parser.intent_resolver` import → jieba 从 `%TEMP%\jieba.cache` **只读**加载词典缓存（文件 mtime 2026-09-22 21:14，早于本班接班，未改；位置在 OS temp，不在 `~/.psy_analysis`）。

## 8. 限制（别把这些读成结论）

1. 盘上快照 n=1、空闲机 v2.9，**S_disk/S_light 是真实读数，S_busy 是合成形态**（busy S 中 synthetic 夹具贡献 60%）；「活跃研究者真实 S」本机无法取得。
2. busy 载荷的文本长度/条目数是手拍的代表值，S_busy ±3 倍摆动不影响 §6 任何档位判定（降幅对 S 极不敏感，这正是 −97% 起跳的原因）。
3. 重复率深等比对不含 analysis_output 行（v35 存 raw、顶层存精简，形状不同源相同，未计入 dup 字节 ⇒ 重复率是**下界**）。
4. df_b64 盘上/运行时同为 46 B（mini csv 往返无损）；大 df 场景走设计稿 §1.3 构造性下界，本单不重测。

## 9. 产物与复跑

- 测量脚本：`tmp/s923_38_key_sizing.py`（仓根执行，rc=0 内建零写守卫）
- 原始读数：`tmp/s923-38/run_output.txt`、`tmp/s923-38/readings.json`、沙盒副本 `tmp/s923-38/home/`
- 本报告：`docs/insights/psy-snapshot-key-sizing-20260923.md`（文件名按卷宗点名）
