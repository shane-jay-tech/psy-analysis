# 2026-05-29 — 自学习模块 Phase 4c：LLM 抽取层

## 任务

按 Phase 4c 计划实现 `src/literature_feed/extract/`：
- 系统/用户提示词（构念 + 方法两套）
- evidence_quote grounding 校验（必须是摘要逐字子串）
- 月预算守门 + 摘要 hash 缓存
- 候选表 staging（人审才入正式 KB）

## 协作流程

按 CLAUDE.md，核心模块走 `/implement`：health_check → GPT 写 → DeepSeek ≥5 反对 → cross-critique → Opus 仲裁 → 落地。

### Health check（pre-flight）

`scripts/health_check.py` 三家全绿（gpt-5.5 / deepseek-v4 / kimi-k2.6 ≤13s）。

### GPT 主写（fallback to direct）

`gpt-coder` 子代理报告：今日 Responses API 端点对长输出请求持续 RemoteProtocolError，按 CLAUDE.md fallback 策略改为直接产出。最终代码骨架来自 GPT 子代理 + Opus 在 Issue 2 上的修补（self-review 写了但未真正落地的部分）。

### DeepSeek 评审（≥5 反对，全 5 维度）

收到 5 大 + 3 小：

| # | 维度 | 严重度 | 内容 |
|---|---|---|---|
| 1 | 并发 | blocker | `_candidate_exists` SELECT-then-INSERT 之间存在 race window |
| 2 | 设计/财务 | serious | 失败的 LLM 调用消耗 token 但未入预算账（累积变量到末尾才记，异常路径丢失） |
| 3 | 边界 | serious | NaN confidence 绕过 `< 0.4` 检查（IEEE754 NaN 比较恒为 False） |
| 4 | 安全 | serious | 摘要里出现 `>>>` 可截断 prompt 注入指令 |
| 5 | 设计 | minor | 未知 method_category 静默降级 'other'，无 log |
| nit-1 | 性能 | — | 缓存命中仍重做 grounding（保留：摘要被回填修正时是必要的安全网） |
| nit-2 | 性能 | — | 候选去重 N+1 SELECT |
| nit-3 | 可读 | — | `_call_and_ground` token 累加器变量名易误解 |

### Opus 仲裁

全部 5 大 + nit-2 采纳；nit-1 拒绝（保留 grounding 作为 abstract 修正后的安全网，已加文档说明）；nit-3 通过结构改造一并消除（不再累加，每次调用立刻入账）。

### 实施

**schema.sql**
- 加部分唯一索引 `idx_candidates_dedup` on `(article_id, kind, normalized_name, prompt_version) WHERE prompt_version IS NOT NULL`
- 部分索引让旧测试（prompt_version=NULL）继续正常插入多行

**feed_store.py**
- `insert_candidate` 改 `INSERT OR IGNORE`；`cur.rowcount==0` 返回 0 表示重复跳过

**extract/extractor.py**
- 引入 `math.isnan` 检查 + `0 ≤ conf ≤ 1` 范围校验
- 同响应内重名 LLM 输出去重（seen_norm set）
- 未知 method_category 触发 `logger.warning` 再降级
- `_call_and_ground` 拆出 `_record_call_budget`，每次 LLM 调用立刻入账（含失败前的成功调用）
- `_existing_candidate_norms` 一次拉齐已有 normalized_name 进 set，本地查重（去 N+1）
- 仍保留 INSERT OR IGNORE 作并发兜底（rowid=0 时记 race-skipped log）

**extract/prompts.py**
- 摘要分隔符改 `<<<ABSTRACT-{secrets.token_hex(8)}>>>`，每次调用随机
- 极罕见碰撞（摘要里出现同 token）→ 重摇

## 验证

- 52 个旧 literature_feed 测试全绿（schema 改动 + insert_candidate 改动无回归）
- 端到端 smoke：1 article × 3 runs 验证
  - Run 1：3 构念输入 → 1 通过（NaN 拦下、伪造 quote 拦下）；2 方法输入 → 2 通过（含 unknown category 降级）；budget 记 2 calls
  - Run 2：cache hit，0 LLM call，0 重复入库
  - Run 3：force=True 重抽，INSERT OR IGNORE 兜住，仍 3 行
- Console 中文 GBK 编码乱码仅日志显示问题，逻辑无异常

## 给用户的摘要

见会话末。
