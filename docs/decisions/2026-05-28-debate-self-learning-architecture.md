# 自学习模块架构辩论与仲裁 (v4.7)

**日期**：2026-05-28
**辩论形式**：三方并行（GPT-5.5 Pro 实现派 / DeepSeek V4 Pro 风险派 / Kimi K2.6 经验派）→ Opus 仲裁
**关联**：[2026-05-28-research-top4-psy-journals.md](./2026-05-28-research-top4-psy-journals.md)（前置 Kimi 调研）
**输入与原始记录**：`.tmp_debate_gpt.out` / `.tmp_debate_deepseek.out` / `.tmp_debate_kimi.out`（见根目录归档）

---

## 三方提案要点对照

### GPT-5.5 Pro（实现派）— 456 行
完整 8 节架构提案 + 5 条自审风险。核心：SQLite + JSONL 混合存储；fetcher 共享基类 + 四独立模块；LLM 强制 evidence_quote 原文匹配；侧栏新增「文献雷达 / 知识库审核」mode；趋势用归一化频次（小样本不上 embedding）；IO/HR/OB 三层加权（抽取 + 聚合 + UI）；文件锁 + SQLite sentinel + 唯一约束三层防重；按 source 隔离失败。

### DeepSeek V4 Pro（风险派）— 109 行
8 条高优风险 + 5 条必须接受的开销 + 3 条不该过早优化。核心反对意见：
- staging gate 必须强制审核（不允许批量一键通过）
- 必须放弃裸 JSON 写入，强制 SQLite
- 必须有月预算 + token 缓存（防 LLM 财务黑洞）
- 测试必须用离线 fixtures + `@pytest.mark.online` 隔离
- 加权规则必须外部化 YAML + UI 可编辑（防研究方向漂移）
- 解析规则外部化 YAML（防期刊改版猝死）
- 抓取必须严格限频 + 真实 UA + 学术声明（避法律红线）

### Kimi K2.6（经验派）— 60 行
对比 Zotero / arXiv-sanity / Elicit / SciSpace / Connected Papers 等同类系统。核心建议：
- SQLite + WAL 是 15 年验证的标杆（Zotero）
- CSL-JSON 是事实中间标准（Zotero/Pandoc/Mendeley 共用）
- DOI + 归一化标题去重链（Zotero/Mendeley 验证）
- TF-IDF + Sentence-BERT 双轨趋势，半衰期 90 天
- LLM 用 grounding（强制原文证据）+ 2-shot，不做多轮投票
- 单一 cron + 启动懒检查（≥23h 才补拉），WAL 替代文件锁
- 硬编码 IO/HR/OB 词表 ×1.5，开反馈但不在线学习
- 严合规来源（管理世界）放弃定向爬，RSS/API 优先 + 手动兜底

---

## 关键分歧 → 仲裁

### 分歧 1：存储格式

| 方 | 方案 |
|---|---|
| GPT | SQLite 主库 + JSONL 原始快照 |
| DeepSeek | SQLite 必需（裸 JSON 一定撕裂）|
| Kimi | SQLite WAL + JSONL 归档 + CSL-JSON 中间表示 |

**仲裁**：取三家并集。
- 主库 SQLite 开 WAL 模式（Kimi 对）
- 原始抓取归档 JSONL（GPT 对，便于解析器修复后重放）
- `articles` 表的核心元数据字段命名对齐 **CSL-JSON 标准**：`title` / `author` (数组) / `abstract` / `issued` / `DOI` / `publisher` / `container-title` / `keyword`（Kimi 对，未来导入/导出 Zotero / Pandoc 零摩擦）
- 业务字段（`provenance` / `metadata_status` / `iohr_hits_json` / `fetch_run_id`）作为扩展，不破坏 CSL-JSON 兼容

### 分歧 2：领域加权（IO/HR/OB ×1.5）

| 方 | 方案 |
|---|---|
| GPT | YAML 词表 + 三层加权（抽取/聚合/UI）|
| DeepSeek | 必须 UI 可编辑 + 不阻断未加权候选 + 同时展示 raw / weighted |
| Kimi | 硬编码 ×1.5（小数据下硬编码最稳）|

**仲裁**：DeepSeek + GPT 对，**Kimi 错**。
- 用户研究方向**已经历过迁移**（量化 → 心理学 → 现在偏 IO/HR/OB），未来仍可能演化
- 词表 + 权重表存 `D:\code\psy-analysis\data\literature_feed\domain_weights.yaml`
- Streamlit 设置页提供编辑入口（上传/编辑 YAML）
- 加权只影响**优先级与排序**，**不阻断**未加权候选进入 staging
- UI 始终同时展示 raw frequency 和 weighted frequency

### 分歧 3：触发机制

| 方 | 方案 |
|---|---|
| GPT | 双触发 + 文件锁 + SQLite sentinel + 唯一约束（用户原始需求）|
| Kimi | 单 cron + WAL + 启动懒检查（更简单）|
| DeepSeek | 必须有可观测性（`last_fetch_status.json`）|

**仲裁**：GPT 对（**用户已明确决策双触发**），但融合 Kimi 的 SQLite WAL 与 DeepSeek 的可观测性。
- Task Scheduler 每日 + 应用启动 ≥36h 检查双触发都保留
- SQLite WAL 替代单纯文件锁（更现代，并发更顺）
- 但**仍保留** `feed_fetch.lock` 文件锁作为跨进程互斥（Task Scheduler 起的 Python 进程 vs Streamlit 进程，WAL 不挡）
- `fetch_runs` 表作为状态 sentinel，启动时检查长 running 转 abandoned
- `articles` 表 DOI / 标题日期唯一约束作为最终幂等

### 分歧 4：趋势聚合算法

| 方 | 方案 |
|---|---|
| GPT | 归一化频次 + 时间窗增长率 + IO/HR/OB ×1.5（小样本不上 embedding）|
| Kimi | TF-IDF + Sentence-BERT 双轨，半衰期 90 天 |

**仲裁**：GPT 对（v4.7 MVP），Kimi 留 v4.8。
- 4 本 × 年均 ~1000 篇属于小样本，TF-IDF 与 embedding 聚类容易制造伪热点
- v4.7 走加权频次 + 时间窗（30d 热点 / 90d 稳定 + 环比增长率），透明可解释
- 时间衰减半衰期采用 Kimi 的 **90 天**（与学术季度周期对齐）
- v4.8 评估是否引入 Sentence-BERT 中文 embedding 做"潜在新构念"二级发现

### 分歧 5：Staging 审核 gate 反疲劳

| 方 | 方案 |
|---|---|
| DeepSeek | 不允许批量通过 + 每项 ≥2 秒强制等待 + 驳回必填理由 |
| GPT | 4 tabs 独立 mode |
| Kimi | 待审核队列 + 肉眼拦截 |

**仲裁**：DeepSeek 方向对，强制等待 2 秒过僵硬，调整：
- 默认单条审核为主入口（每项展示原文 + LLM 抽取并排）
- **批量通过**仅对"高置信 ≥0.85 + 命中已有 KB 同义词"的候选开放（视为合并到现有，非新建）
- 驳回不强制理由但提供下拉（幻觉/重复/范围外/低质量），便于 LLM 抽取质量分析
- 单条停留时间不强制（用户单人使用，强制反疲劳过家长式）

### 分歧 6：预算控制

| 方 | 方案 |
|---|---|
| DeepSeek | 月预算（建议 $10）+ token 缓存 + 80%/100% 双阈值 |
| GPT/Kimi | 没提 |

**仲裁**：DeepSeek 对，**强制采纳**。
- LLM 抽取入口包装一层 budget check
- 月用量记录到 `D:\code\psy-analysis\data\literature_feed\llm_budget.json`
- 阈值默认 $5/月（4 本 × 8 篇 × 30 天 ≈ 960 调用，单调用 ~500 tokens，月成本估 $1-2，$5 留 2-3× 缓冲）
- 80% 弹警告，100% 阻断非必要（重抽 / 手动触发），保留必要（每日定时单跑）
- 摘要 hash 缓存：相同摘要不重抽（命中即返回上次结果）

### 分歧 7：测试策略

| 方 | 方案 |
|---|---|
| DeepSeek | 离线 fixtures + `@pytest.mark.online` 隔离 + CI 排除 online |
| GPT/Kimi | 没提 |

**仲裁**：DeepSeek 对，**强制采纳**。
- 单元测试用 `tests/fixtures/literature_feed/` 下保存的 HTML / Crossref JSON 快照 + mock
- 集成测试打 `@pytest.mark.online` 标签
- pytest 默认配置 `-m "not online"`
- 月度手动跑一次 `pytest -m online` 验证 4 个 fetcher 还活着（DeepSeek 提的"必须接受的工程开销"，逃不掉）

### 分歧 8：管理世界

| 方 | 方案 |
|---|---|
| GPT | 自动失败 → 手动补录入口 |
| DeepSeek | 严格限频 + 真实 UA + 不规避，作为合规避风港 |
| Kimi | **放弃定向爬**，RSS/API 优先 + 手动兜底 |

**仲裁**：三家共识强方向。**最终方案**：
- v4.7 第一刀：**不实现管理世界自动 fetcher**
- 走 OpenAlex API（免费、覆盖中文管理学论文且 ToS 友好）作为元数据源
- OpenAlex 失败时降级到手动补录（用户粘贴 CNKI 链接 / DOI / 题录，系统抽元数据）
- 不再尝试爬 mzworld.com 或 CNKI 页面（合规风险 + 技术成本太高）

---

## 最终仲裁架构（v4.7 自学习模块）

### 模块结构

```
src/literature_feed/
├── fetchers/
│   ├── base.py                   # SourceFetcher 抽象基类
│   ├── crossref.py               # 心理学报 + 心理科学进展（共享，按 ISSN 配置）
│   ├── psy_science_official.py   # 心理科学官网 SSR + meta 解析
│   └── manual_ingest.py          # 管理世界 + 兜底（粘贴链接/DOI/题录）
├── parsers/
│   ├── csl_normalizer.py         # 三种异构源 → CSL-JSON 统一
│   └── meta_tag_parser.py        # citation_abstract / citation_author 解析
├── extract/
│   ├── construct_extractor.py    # 摘要 → 候选构念（LLM）
│   ├── method_extractor.py       # 摘要 → 候选方法（LLM）
│   ├── prompts.py                # system prompt + 2-shot 示例 + JSON schema
│   └── grounding_validator.py    # evidence_quote 必须在原文中精确匹配
├── trend/
│   ├── keyword_aggregator.py     # 30d/90d 频次 + 环比增长 + 90d 半衰期衰减
│   └── domain_weighter.py        # IO/HR/OB 词表加权
├── storage/
│   ├── schema.sql                # SQLite WAL schema（articles 对齐 CSL-JSON）
│   ├── feed_store.py             # SQLite + 唯一约束 + 事务
│   ├── jsonl_archive.py          # 原始抓取归档（每日按 source 切分）
│   └── budget_tracker.py         # 月预算 + token cache
├── scheduler/
│   ├── daily_runner.py           # Task Scheduler 入口
│   ├── bootstrap_check.py        # 应用启动 ≥36h 补拉检查
│   └── lock_manager.py           # 文件锁 + sentinel 双层
└── ui/
    ├── feed_radar_mode.py        # 主 mode：今日 / 候选审核 / 趋势 / 手动补录
    ├── review_panel.py           # 候选审核 UI（单条 + 批量高置信）
    └── domain_weights_editor.py  # 设置页：YAML 词表 + 权重编辑
```

### 数据存储

- 主库：`D:\code\psy-analysis\data\literature_feed\feed.sqlite`（WAL 模式）
- 归档：`D:\code\psy-analysis\data\literature_feed\raw\YYYY-MM-DD\{source}.jsonl`
- 配置：`D:\code\psy-analysis\data\literature_feed\domain_weights.yaml`
- 预算：`D:\code\psy-analysis\data\literature_feed\llm_budget.json`
- 锁：`D:\code\psy-analysis\data\literature_feed\locks\feed_fetch.lock`

### 关键 SQL 表（CSL-JSON 兼容版）

```sql
CREATE TABLE articles (
  article_id INTEGER PRIMARY KEY AUTOINCREMENT,
  -- CSL-JSON 兼容字段
  title TEXT NOT NULL,
  author_json TEXT,                  -- JSON array of {family, given}
  abstract TEXT,
  issued_date TEXT,                  -- ISO 8601
  doi TEXT,
  container_title TEXT,              -- 期刊名
  publisher TEXT,
  keyword_json TEXT,                 -- JSON array
  -- 业务扩展
  source_id TEXT,
  provenance TEXT,                   -- crossref/official_site/openalex/manual
  metadata_status TEXT,              -- complete/partial/needs_review
  iohr_hits_json TEXT,
  raw_hash TEXT,
  fetched_at TIMESTAMP,
  fetch_run_id INTEGER,
  UNIQUE(doi),
  UNIQUE(source_id, title, issued_date)
);
```

### 数据流

```
Task Scheduler / 应用启动
    ↓
LockManager 抢锁（失败则提示"已在运行"）
    ↓
fetch_runs 写 running sentinel
    ↓
3 fetcher 并行：crossref ×2 + psy_science_official（管理世界走 manual_ingest）
    ↓
csl_normalizer 统一 CSL-JSON
    ↓
去重链：DOI → 归一化 title+year → 入 articles 表
    ↓
JSONL 归档原始抓取
    ↓
budget_tracker 检查预算 → LLM 抽取构念/方法 → grounding_validator 校验
    ↓
llm_candidates 表 status=pending
    ↓
keyword_aggregator + domain_weighter 更新趋势
    ↓
fetch_runs 写 completed
    ↓
释放锁
    ↓
（用户打开应用 → 文献雷达 mode → 审核候选 → approve → 写入 construct_kb）
```

### UI 接入

- 侧栏新增 mode：「📡 文献雷达」（与「🌱 选题与文献综述」并列）
  - tab `今日抓取`：状态 + 失败源 + 最新文章
  - tab `候选审核`：单条 + 批量高置信
  - tab `领域热点`：30d / 90d / 环比 / IO/HR/OB 高亮
  - tab `手动补录`：粘贴链接/DOI/题录
- 选题漏斗 step 2/3 注入"近期热点"提示（读趋势表）
- 设置页加「自学习」expander：YAML 词表编辑 + 月预算阈值 + 触发开关

### 测试策略

- `tests/fixtures/literature_feed/` 存 4 源的快照（HTML / Crossref JSON / OpenAlex JSON）
- `tests/test_literature_feed_fetchers.py`（mock 网络）
- `tests/test_literature_feed_extractors.py`（mock LLM，构造 evidence_quote 正反例）
- `tests/test_literature_feed_grounding.py`（grounding_validator 单测）
- `tests/test_literature_feed_storage.py`（SQLite WAL 并发测试）
- `tests/test_literature_feed_budget.py`（月预算阈值）
- `tests/test_literature_feed_lock.py`（多进程锁）
- `tests/test_literature_feed_trend.py`（频次 + 时间衰减 + 加权）
- `tests/test_literature_feed_online.py`（`@pytest.mark.online`，月度手动跑）

预计新增 ~80-100 个测试。

---

## 必须接受的工程开销（DeepSeek 提）

1. **月度人工 fetcher 在线验证**：`pytest -m online`，4 个源都跑通才发布 v4.8+
2. **强制 staging gate**：候选必须人工审核，禁止"自动入正式 KB"
3. **合规日志**：每次抓取记录时间/source/状态/速率（学术合理使用避风港）
4. **SQLite WAL + 锁双层**：单纯 WAL 不挡跨进程，必须配文件锁
5. **预算监控**：月限 + 阈值警告 + 摘要 hash 缓存，避免 LLM 账单黑洞

## 不该过早优化（v4.8+）

1. **embedding 聚类发现潜在新构念**：v4.7 走频次足够，embedding 在小样本下不稳定
2. **基于用户行为的兴趣权重自动漂移**：手动 YAML 配置够用
3. **跨刊构念知识图谱**：在基础数据质量稳定前是空中楼阁

---

## 待用户拍板（v4.7 落地前）

仲裁后剩余两个开放问题需要用户决定：

1. ~~**OpenAlex 的可行性是否提前验证**~~：✅ 2026-05-28 已验证完毕，**结论：放弃 OpenAlex**
2. ~~**月预算具体数字**~~：✅ 用户拍 **$10**（"完全不担心"），熔断线 80% / 100%

---

## 后续验证：OpenAlex 对管理世界覆盖（2026-05-28）

**结果**：直接 curl OpenAlex API 三轮验证：

| 查询路径 | 结果 |
|---|---|
| `filter=primary_location.source.issn:1002-5502` | count=0 |
| `search=Management World` | 31 hit，最像的 ISSN=2994-3191 是 Qatar/AI 主题英文刊（同名不同物） |
| `search=管理世界`（中文）| 命中 OpenAlex source `S4306556525`（1007 篇中文管理学，主题对路）|

**致命问题**：S4306556525 的 1007 篇里 100% **DOI=None + abstract=NO + 2024 年后 0 篇**。
- 没摘要 → LLM 抽不出构念
- 没 DOI → 去重链断
- 数据停在 2020 → 无法做趋势

**最终决策**：**v4.7 完全放弃 OpenAlex**，管理世界**只做手动补录**。
- 模块树删掉 `src/literature_feed/fetchers/openalex.py`
- v4.7 自动 fetcher 收敛为 3 个：crossref（心理学报+心理科学进展）+ psy_science_official（心理科学）+ manual_ingest（管理世界 + 兜底）
- 数据流图无变化（OpenAlex 本来就是降级链最末端）
- 节省约 250-300 行 fetcher + 解析代码

验证产物归档：`.tmp_openalex_*.json`（覆盖度 raw 数据）
