-- v4.7 自学习模块 SQLite schema（WAL 模式）
-- 设计决策见 docs/decisions/2026-05-28-debate-self-learning-architecture.md
-- articles 核心字段对齐 CSL-JSON 规范，业务字段作为扩展。

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

-- ---------------------------------------------------------------------------
-- 期刊源：4 本 + 未来扩展
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id        TEXT PRIMARY KEY,           -- e.g. "acta_psych" / "psy_science" / "mgmt_world"
    journal_name     TEXT NOT NULL,
    issn             TEXT,
    doi_prefix       TEXT,
    fetcher_type     TEXT NOT NULL,              -- "crossref" / "official_site" / "manual"
    enabled          INTEGER NOT NULL DEFAULT 1, -- bool
    last_attempt_at  TEXT,                        -- ISO 8601
    last_success_at  TEXT,
    probe_signature  TEXT,                        -- 解析器版本指纹
    status           TEXT,                        -- "ok" / "schema_changed" / "rate_limited" / "failed"
    notes            TEXT
);

-- ---------------------------------------------------------------------------
-- 抓取批次：每次 daily_runner 运行的 sentinel
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fetch_runs (
    run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger       TEXT NOT NULL,                  -- "scheduler" / "app_startup" / "manual"
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    status        TEXT NOT NULL DEFAULT 'running',-- "running" / "completed" / "failed" / "abandoned"
    summary_json  TEXT,                            -- {"acta_psych":{"new":3,"dup":2,"failed":0},...}
    error_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetch_runs_status ON fetch_runs(status, started_at);

-- ---------------------------------------------------------------------------
-- 文章：CSL-JSON 兼容字段 + 业务扩展
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS articles (
    article_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    -- CSL-JSON 兼容（导入/导出 Zotero/Pandoc 零摩擦）
    title             TEXT NOT NULL,
    author_json       TEXT,                       -- JSON array of {family, given}
    abstract          TEXT,
    issued_date       TEXT,                       -- ISO 8601 日期
    doi               TEXT,                       -- 归一化（lower-case，无 https:// 前缀）
    container_title   TEXT,                       -- 期刊全称
    publisher         TEXT,
    keyword_json      TEXT,                       -- JSON array<str>
    -- 业务扩展
    source_id         TEXT NOT NULL,
    provenance        TEXT NOT NULL,              -- "crossref" / "official_site" / "manual"
    metadata_status   TEXT NOT NULL DEFAULT 'complete', -- "complete" / "partial" / "needs_review"
    iohr_hits_json    TEXT,                       -- JSON array<str> 命中的 IO/HR/OB 词条
    raw_hash          TEXT,                       -- 原始抓取 payload 的 SHA-256
    fetched_at        TEXT NOT NULL,
    fetch_run_id      INTEGER,
    title_norm        TEXT NOT NULL,              -- 归一化标题（去标点 + lower）用于去重
    -- 约束
    UNIQUE(doi),
    UNIQUE(source_id, title_norm, issued_date),
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(fetch_run_id) REFERENCES fetch_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_articles_source_date ON articles(source_id, issued_date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at DESC);

-- ---------------------------------------------------------------------------
-- 文章关键词：作者关键词 + LLM 补充，加权聚合的源头
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS article_keywords (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id     INTEGER NOT NULL,
    keyword_raw    TEXT NOT NULL,
    keyword_norm   TEXT NOT NULL,                 -- 小写 + 去空白
    keyword_source TEXT NOT NULL DEFAULT 'author',-- "author" / "llm" / "manual"
    is_iohr_hit    INTEGER NOT NULL DEFAULT 0,    -- bool，命中 IO/HR/OB 词表
    UNIQUE(article_id, keyword_norm),
    FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_keywords_norm ON article_keywords(keyword_norm);
CREATE INDEX IF NOT EXISTS idx_keywords_iohr ON article_keywords(is_iohr_hit, keyword_norm);

-- ---------------------------------------------------------------------------
-- LLM 候选：构念 / 方法。staging gate，必须人审才能入正式 KB
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_candidates (
    candidate_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id       INTEGER NOT NULL,
    kind             TEXT NOT NULL,               -- "construct" / "method"
    name             TEXT NOT NULL,
    normalized_name  TEXT NOT NULL,
    definition       TEXT,
    method_category  TEXT,                        -- 仅 kind=method 时使用
    evidence_quote   TEXT NOT NULL,               -- 必须在原文摘要/标题/关键词出现
    evidence_valid   INTEGER NOT NULL DEFAULT 0,  -- grounding_validator 校验结果
    confidence       REAL,                        -- LLM 自评置信度 0-1
    novelty_hint     TEXT,                        -- "new_construct"/"new_measure"/"extension"/"unclear"
    domain_score     REAL DEFAULT 0,              -- IO/HR/OB 命中后的加分
    priority_score   REAL DEFAULT 0,
    iohr_hits_json   TEXT,                        -- JSON array<str>
    llm_config_hash  TEXT,
    prompt_version   TEXT,
    status           TEXT NOT NULL DEFAULT 'pending', -- pending/approved/rejected/merged
    rejection_reason TEXT,                         -- 用户驳回理由（下拉选项）
    reviewer         TEXT,
    reviewed_at      TEXT,
    target_kb_id     TEXT,                         -- 入正式 KB 后的 ID
    created_at       TEXT NOT NULL,
    FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON llm_candidates(status, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_kind ON llm_candidates(kind, status);
-- 幂等护栏：同一 article+kind+name+prompt_version 只允许一行（防并发抽取重复入库）
-- 部分索引：prompt_version=NULL 的旧测试数据不受影响
CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_dedup
    ON llm_candidates(article_id, kind, normalized_name, prompt_version)
    WHERE prompt_version IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 手动补录入口（管理世界 + 兜底）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manual_submissions (
    submission_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    input_type         TEXT NOT NULL,             -- "doi" / "url" / "citation_text"
    raw_input          TEXT NOT NULL,
    parsed_article_id  INTEGER,                    -- 解析成功后写入
    status             TEXT NOT NULL DEFAULT 'pending', -- pending/parsed/failed
    error              TEXT,
    created_at         TEXT NOT NULL,
    FOREIGN KEY(parsed_article_id) REFERENCES articles(article_id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------------
-- LLM 调用 / 摘要 hash 缓存：避免相同摘要重复抽
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_extraction_cache (
    abstract_hash    TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    model            TEXT NOT NULL,
    response_json    TEXT NOT NULL,
    cached_at        TEXT NOT NULL,
    PRIMARY KEY(abstract_hash, prompt_version, model)
);
