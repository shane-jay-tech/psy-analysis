# psy feed `doi_prefix` 死配置处置裁决材料（s924-19 · 只读复核）

- 班：`qoder-executor-20260925-0450-psy41`（波次 11 补派）· 2026-09-25 · cwd `D:\code\psy-analysis`
- 前手锚：`zcode-bridge/done/s923-13.result.md`（09-23，s922-17 后续）
- 性质：**只读出稿**。零码改零库改；本文是净新增 1 件，未 `git add`。

## 0. 结论速览

1. **「`doi_prefix` 是死配置」成立，且比 s923-13 的表述更强**：全仓 **AST 轨 `.doi_prefix` 属性读取 0 处**——fetcher 根本没有"读它"的代码通路；20 处正则命中全部落在注册／透传／存储／测试钉值／文档归档五类，**消费方 0**。
2. crossref fetcher 请求构造实测（`crossref.py:65,70-71`）只拼 `issn:{issn},from-issued-date:{since}`，文件内 `doi_prefix` 字面串计数 **0**（判据②预期 0，命中）；`10.3724` 字面量在该文件只出现在模块 docstring `:7`，属文档注释非代码。
3. 库面（`backup()` 快照双开一致）：`sources` 8 行，`doi_prefix` 非 NULL 仅 2 行（两本心理所刊 `10.3724`），其余 6 行 NULL——它事实上已是"两行手记式元数据"。
4. 三方案对比后**倾向 A（冻结保留）**：B 接进过滤受"两刊共用前缀"先天限制（`crossref.py:7` docstring 自证），防脏价值与 ISSN 通道重复；C 删列要连改 6 个生产/测试文件＋迁移占号，改动面与收益不成比。**删/接仍超执行手授权，裁决交主班进人工闸。**

## 1. 锚点复核（判据先于结论）

| 卷宗锚 | 实测 | 漂移 |
|---|---|---|
| `done/s923-13.result.md`「`doi_prefix` 是死配置（注册、透传、存储、测试钉值，零消费方）」 | 该句在该档 :53 逐字在 | 无 |
| `src/literature_feed/fetchers/base.py:95` `doi_prefix: Optional[str] = None` | :95 逐字命中 | 无 |

## 2. 全仓扫描：双轨对数＋差额归因（§九.3／§十.3 口径）

- 正则轨（git 跟踪范围，排除 `data/`、`tmp/`、`node_modules/`、`__pycache__/`）：**20 命中**
- AST 轨（`git ls-files '*.py'` 555 份逐份 parse，取 `Attribute.attr=='doi_prefix'` ∪ `Constant=='doi_prefix'`）：**4 命中**
- 差额 16 处逐条归因：SQL 文本内嵌（列名不是独立常量/属性，9 处中 4 处在 `feed_store.py` 的三引号 SQL 与签名、1 处 `schema.sql` 非 py）、kwargs 形参名（`ast.keyword.arg` 不属本轨取的两个节点类）、docs 档非 py（5 处）、字段声明 `AnnAssign` 目标名（1 处）。**两轨无矛盾；AST 轨的独立承重结论是"全仓 `.doi_prefix` 属性读 0"**，这正是"零消费方"的形式化证明。

### 分类计数（20 处逐处行号，判据①）

| 类 | 处数 | 位置 |
|---|---|---|
| schema 列定义 | 1 | `src/literature_feed/storage/schema.sql:17` |
| 存储写路径（INSERT/UPSERT/签名/绑定） | 4 | `storage/feed_store.py:221,229,234,239` |
| 配置字段声明 | 1 | `fetchers/base.py:95`（`SourceConfig` dataclass） |
| 调度透传（读库行→config） | 1 | `scheduler/daily_runner.py:97`（`source.get("doi_prefix")` 塞进 `SourceConfig(...)`，**不读回**） |
| 注册（seed） | 3 | `scripts/seed_literature_sources.py:38,40`（钉值 `10.3724`×2）、`:64`（透传给 upsert） |
| 测试钉值 | 5 | `tests/test_literature_feed_fetchers.py:188`（夹具 kwargs）、`tests/test_literature_feed_storage.py:64,68`、`tests/test_seed_literature_sources.py:50`（`=="10.3724"`）、`:52`（`jap is None`） |
| 文档归档（前手产出） | 5 | `docs/insights/psy-feed-source-census-20260923.md:38,53,65,135,136` |
| **消费方（fetcher/UI 按值分支）** | **0** | —（AST 轨 `.doi_prefix` 0 命中背书） |

## 3. crossref fetcher 实测（判据②）

`fetchers/crossref.py` 内 `doi_prefix` 计数 = **0**（预期 0 ✓）。请求构造通路逐行：

- `:65` `issn = self.config.issn or self.config.extra.get("issn")` —— 只取 ISSN；
- `:70-71` `("filter", f"issn:{issn},from-issued-date:{since}")` —— filter 串两因子，无 prefix；
- 其余三个 fetcher 同理零引用：`psy_science_official.py`、`manual_ingest.py`、`base.py`（除字段声明外）正则均 0 命中（`base.py` 唯一命中即 :95 声明本身）。
- `crossref.py:7` docstring：「DOI 前缀 `10.3724` 由心理所主办两刊共用，靠 ISSN 区分 source」——**前人已把"为什么没接"写死在注释里**：前缀在两刊上不唯一，天然当不了区分键。
- 附带核查 `logs/`：`doi_prefix` 0 命中（rg rc=1 无匹配）。

## 4. 库面 census（`backup()` 快照，§十二.1 新配方）

- 配方：真库 `mode=ro`＋`PRAGMA query_only=ON` 连接 → `sqlite3.backup()` 出单文件快照 → 快照**开两次比对**。`copy2` 三件套形态本单一律不用。
- 快照 540,672 B（> 主文件 499,712 B，WAL 折叠进主文件的预期形态）；`PRAGMA integrity_check` = ok。
- 双开比对：`two_opens_identical: True`（census sha8 `e1d65a07`）。
  ⚠ 自纠留痕：探针首版打印 `STABLE False` 系**探针自身 bug**——`json.dumps(dict, sort_keys=True)` 只排 dict 顶层键、行内列序仍随 `sqlite3.Row→dict` 插入序漂移，且第二开漏传 `uri=True` 实际以读写模式打开了快照；换 `list(r)` 行＋sorted JSON 复比即 True。**数据从未不一致，勿据此判快照失真。**
- 读数：`sources` 8 行全 `fetcher_type='crossref'`、`enabled=1`；`doi_prefix` 非 NULL **2/8**：`acta_psych_sinica`、`adv_psych_science` 均 `10.3724`；其余 6 行 NULL（`jap` 的 NULL 被 `test_seed_literature_sources.py:52` 钉住）。

## 5. 三方案对比

| 方案 | 动作 | 改动面 | 风险/成本 | 净收益 |
|---|---|---|---|---|
| **A 冻结保留**（推荐） | 码/库零动；在 `schema.sql:17` 列注与 `base.py:95` 字段 docstring 标「元数据备注列，非消费键」；`test_seed…:50/:52` 继续当语义锚 | 2 处注释（仍属 `src/` 面 ⇒ **本只读单不做**） | 无行为风险 | 消除"它该起作用"的误读复发（s922-17 就误判过一次"ISSN 选错"） |
| B 接进过滤 | fetcher 按 `config.doi_prefix` 对返回 DOI 做 `startswith` 守卫（Crossref `/works` filter 无 prefix 因子，实现形态只有本地校验或改走 `/prefixes/{p}/works` 路由） | `crossref.py` 请求/解析链＋`test_literature_feed_fetchers.py`＋（若走路由）URL 构造 | 两刊共用前缀 ⇒ 区分不了 source（`:7` 自证）；英文刊该值全 NULL ⇒ 需"NULL 跳过"分支；防脏价值与 ISSN filter 重复 | 近似零；徒增 fetcher 分支复杂度 |
| C 删列迁移占号 | `migrations.py` `MIGRATIONS` 追加 `("2026MMDD_retire_sources_doi_prefix", fn)`（现列 3 条，占第 4 号）；`sources` 表 DROP/重建；`schema.sql` 去列；`feed_store.upsert_source` 去签名；`seed` 去两值；连改 3 个测试钉值＋`daily_runner`/`base` 透传 | **6 生产/迁移文件＋3 测试文件**，全在他人/在途纪律交界（本单只读闸；测试族另涉 §十一.2 挂起面外但同仓无兄弟写位） | sqlite 3.45 支持 `DROP COLUMN`，但 `migrations.py:5` 在册约定"只用 ADD COLUMN"⇒ 破例需裁决；真删后 `test_seed…:50/:52` 两枚语义锚报废 | 减 1 列死字段；对运行行为零影响（正因为它是死的） |

### 裁决建议

- **推荐 A**；B 是"为活而活"，C 改动面与"删除一个从不被读的名字"的收益不成比，且会报废两枚在册测试钉值。
- 无论选哪案，**实施都是写码单**（涉 `src/` 或 `tests/`），超出本只读单与本执行手授权 ⇒ 落主班人工闸。

## 6. 复算命令（本档每个读数的出处）

```
$ MSYS_NO_PATHCONV=1 rg -n --no-heading -F "doi_prefix" -g '!node_modules' -g '!__pycache__' -g '!data' -g '!tmp' . | wc -l
20
$ git ls-files -z | xargs -0 -r grep -n -F "doi_prefix" | wc -l
20
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0450-psy41/probe_doi_prefix.py invariant
{"dir": [181, 21059126, "9de0fe56bb9f020d"], "db_sha8_size": ["6bf5776b", 499712], "wal_sha8_size": ["4f9f07db", 741632], "shm_sha8_size": ["144cf1db", 32768]}
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0450-psy41/probe_doi_prefix.py full   # backup() 快照＋双开 census（首版双开比对有探针 bug，见 §4 自纠）
$ # 稳健双开比对（list 行 + sorted JSON）：two_opens_identical: True, census sha8 e1d65a07, counts [8, 2]
$ # AST 轨：git ls-files '*.py' 555 份 ast.parse，Attribute/Constant 精确名 'doi_prefix' → 4 hits（seed:64 / daily_runner:97 / test_seed:50,52），.doi_prefix 属性读 0
$ MSYS_NO_PATHCONV=1 rg -n "10\.3724|config\.(issn|doi)|self\.config" src/literature_feed/fetchers/
$ MSYS_NO_PATHCONV=1 rg -c "doi_prefix" logs/    # rc=1，0 命中
```

## 7. 自证（只读承诺）

- `git status --porcelain` 收工＝开班 6 项他班在途（`M app.py`／`M pytest.ini`／`M requirements-lock.txt`／`M src/questionnaire/exporters.py`／`M tests/test_questionnaire_export_pdf_positive.py`／`?? tests/test_exporters_cjk_font_fallback_observability.py`、`?? node_modules/`）逐字不变；本班净增本档 1 件 `??`＋gitignored `tmp/` 探针，**未 add 未 commit**。
- 真库不变量三项：开班＝收工 `181 件 / 21,059,126 B / 9de0fe56bb9f020d`（件数与字节与主班参照吻合；摘要为本班口径 `sorted(relpath|size)` sha256 前 16 位，与 psy40 `ade4c241…` 不同源属已知多口径）。`feed.sqlite`/`-wal` sha8 逐位不变；`-shm` 32,768 B 尺寸不变（其内容哈希随只读连接漂移为 §十三 在册正常现象，不判污染）。
