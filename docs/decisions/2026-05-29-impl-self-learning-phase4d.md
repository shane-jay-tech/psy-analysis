# 2026-05-29 — 自学习模块 Phase 4d：趋势聚合 + IO/HR/OB 加权

## 任务

按 Phase 4d 计划落地 `src/literature_feed/trend/`：
- 用户研究方向（工业心理学 / 人力资源 / 组织行为）相关构念在打分中加权
- 90 天半衰期指数衰减聚合 `article_keywords`
- 候选 priority_score 回填工具
- 加权词表 YAML 外部化（UI 设置页将来可编辑）

## 协作流程裁剪说明

按 CLAUDE.md，**核心模块**才走 `/implement` 多模型协作。Phase 4d 是纯确定性计算：
- 无 LLM 调用
- 无外部输入面（YAML 由用户自己写 / UI 编辑）
- 公式即规范（半衰期 90 天，priority = decay × conf × (1 + domain_score)）
- 不动 schema，不动并发面

所以本期采用**单方实现 + 自审 + 归档**模式，不打扰 GPT/DeepSeek/Kimi。仍然写决策文件留下审计痕迹。

## 设计决策

### YAML schema（`data/literature_feed/domain_weights.yaml`）

```yaml
version: 1
default_weight: 1.0
domain_multiplier: 1.5
domains:
  IO: {concepts: [{canonical: 变革型领导, synonyms: [...]}, ...]}
  HR: {concepts: [...]}
  OB: {concepts: [...]}
```

种子词表：IO 8 + HR 8 + OB 9 = **25 个 canonical**，覆盖工业/管理心理 + 人力资源 + 组织行为高频构念。

### 关键公式

| 项 | 公式 | 备注 |
|---|---|---|
| recency decay | `0.5 ** (days / 90)` | 无 issued_date → 1.0；未来日期 → 1.0（防钟差） |
| domain_score | `Σ (multiplier - default_weight)` per unique canonical | 默认 = 0.5/命中 |
| priority_score | `decay × confidence × (1 + domain_score)` | conf NaN → 0；conf clamp 到 [0,1] |
| trend.weighted_count | `Σ decay × multiplier` | 同义词折叠到 canonical |

### 边界约定

- **canonical 重复跨 domain**：YAML 顺序为准，首个生效（防御性，理论不该发生）
- **同义词命中**：自动反查到 canonical，不重复加分
- **YAML 不存在 / 解析失败**：fallback 到 `DomainWeights.empty()`，所有词条权重 1.0（不报错，方便首次启动）
- **conf NaN**：priority 视作 0（IEEE754 NaN 不能直接比较）
- **回填只刷 pending**：已审过的不动，避免覆盖人工记录

## 文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `data/literature_feed/domain_weights.yaml` | 70 | IO/HR/OB 25 个 canonical 种子词表 |
| `trend/domain_weights.py` | 175 | `DomainWeights` 不可变 dataclass + YAML loader + canonical/同义词反查 |
| `trend/scorer.py` | 130 | recency decay + priority 公式 + `update_candidate_scores` 回填 |
| `trend/aggregator.py` | 110 | `compute_keyword_trends` + `compute_domain_summary` |
| `trend/__init__.py` | 50 | 公开入口 + `load_default_weights()` |

## 验证

### 回归

- 52 个 literature_feed 旧测试全绿，trend 模块加入未触发任何回归

### Smoke（D:/tmp/smoke_trend.py，临时数据根）

1. **DomainWeights**：HR=engagement、IO=变革型、OB=OCB 三向命中；同义词→canonical 反查；同 canonical 跨同义词不重复加分（dedup）
2. **recency decay**：今日=1.0、90 天前=0.5、180 天前=0.25、未来=1.0
3. **priority 公式**：(decay=0.5, conf=0.8, hits=1) → 0.6；NaN conf → 0；conf>1 clamp 到 1
4. **候选打分端到端**（3 篇文章 × 3 候选）：
   - 工作敬业度（HR + 14d 前 + conf 0.9）→ priority 1.212（top）
   - 脑电（无 domain + 14d 前 + conf 0.6）→ priority 0.539
   - OCB（OB + 90d 前 + conf 0.7）→ priority 0.525
   - **结论**：近期 + IOHR 命中 > 近期无命中 > 老论文 IOHR，符合预期
5. **趋势聚合**：4 行结果，IOHR 关键词 weighted ≈ 1.347（0.898×1.5），非 IOHR ≈ 0.898（0.898×1.0），90 天前 OCB ≈ 0.75（0.5×1.5）
6. **domain_only 过滤**：3 行全部 IO/HR/OB
7. **domain_summary**：IO/HR/OB/其他 四桶汇总
8. **空词表 / 缺文件 fallback**：score_hits=0，不抛异常

## 自审 ≥3 个潜在问题

1. **race on update_candidate_scores**：YAML 改动时若同时正在抽取写入候选，有 race。当前用 `transaction()` 包整批 UPDATE，单连接序列化即可；多连接场景在 v4.7 不会出现（daily_runner 是单进程）。
2. **半衰期硬编码 90 天**：未来如果用户嫌"老论文沉得太快"想调，需要把 `half_life_days` 提到 YAML 顶层。本期保持 hardcoded + 函数参数化，留出口子。
3. **同义词大小写**：当前用 `.lower()` 折叠，对纯中文无影响，对英文 `OCB` / `ocb` / `Ocb` 都能命中。但 `Ḃurnout` 这种带变音符的英文不会归一化，依赖 `extract_iohr_hits` 已经把文本 `.lower()`。本期不处理。

## 反方意见

- 加权 1.5× 这个数值是拍的，没经验证。研究方向偏移大时可能不够锐，要看实际跑两周后的候选清单分布再调。
- priority 公式是乘法链，三项都低时容易堆在 0 附近难区分。如果未来候选量大、`status='pending'` 队列拉长，可能需要换成对数加权或改用排序而非分数。

## 给用户的摘要

见会话末。
