# 2026-05-30 — 心理分析系统三轮迭代优化

## 起源

用户：「对心理分析系统进行反复优化吧，至少三轮之后再通知我」。开放性指令，自主决定 3 轮做什么。

走单模型路径（不调多模型协作）：
- 用户给的是"持续优化"自主任务，不是某个具体决策点
- 三轮里两轮是纯数据填充 / API 扩展（不影响业务逻辑），一轮是 deprecation fix
- 任何可质疑的设计决策都偏小，单模型仲裁足够

3 轮路线（自主选定）：

| Round | 类别 | 内容 | 改动量 |
|---|---|---|---|
| 1 | 技术债清理 | datetime.utcnow() 弃用警告 | 1 行 |
| 2 | 功能扩展（I/O 方向加权延伸） | method_weights.yaml + MethodWeights scorer 集成 | ~250 行 + 25 测试 |
| 3 | 闭环 wiring | UI 编辑器 + scheduler 接入 | ~110 行 + 5 测试 |

## Round 1 — datetime.utcnow() 弃用警告

**`src/literature_feed/storage/jsonl_archive.py:18,45`**：
- `from datetime import datetime` → `from datetime import datetime, timezone`
- `datetime.utcnow().strftime(...)` → `datetime.now(timezone.utc).strftime(...)`

Python 3.12+ 把 `datetime.utcnow()` 标 deprecated。全仓 grep 只此一处，修完。22 个相关测试 + 全量 1376 仍全绿。

## Round 2 — method_weights.yaml + MethodWeights scorer

延续 [2026-05-30 I/O 域种子](2026-05-30-impl-io-domain-seed.md) 的 Out of Scope 项。该次只做了**构念**层加权（变革型领导 / 员工敬业度等），没动**研究方法**层。这一轮把方法层补上。

### 设计

**新文件**：

- `data/literature_feed/method_weights.yaml`：8 条种子方法 canonical
  - 纵向设计 / 多层模型 / 多源设计 / 经验取样 / 时间滞后设计 / 配对分析 / 元分析 / 准实验
  - schema 与 domain_weights.yaml 平行，但扁平（没有 IO/HR/OB 子族）
  - `method_multiplier=1.5`、`default_weight=1.0`，每命中 +0.5

- `src/literature_feed/trend/method_weights.py`：`MethodWeights` dataclass
  - API 镜像 `DomainWeights`：`from_yaml_path` / `canonical_for` / `score_hits` / `flat_synonyms` / `all_canonical`
  - `is_method` / `multiplier_for` 替代 `domain_for`（方法没有子域）

**改动**：

- `src/literature_feed/paths.py`：+ `METHOD_WEIGHTS_PATH`
- `src/literature_feed/trend/__init__.py`：导出 `MethodWeights / load_default_method_weights / compute_method_score`
- `src/literature_feed/trend/scorer.py`：
  - `compute_priority_score(... method_score=0.0)` — 默认 0 向后兼容
  - 公式从 `decay × conf × (1 + domain_score)` → `decay × conf × (1 + domain_score) × (1 + method_score)`
  - `update_candidate_scores(... method_weights=None)` — 给入时从 article.title/abstract/keyword_json 实时抽方法命中
  - 复用 `extract_iohr_hits(blobs, method_weights.flat_synonyms())` 做扫描，不重写匹配器

### 测试（25 新 case）

- YAML 加载 / 词表完整性（2）
- 同义词反查 parametrize（11）
- score_hits 数值校验（6）
- compute_priority_score 集成（3）—— 默认 0 向后兼容 / 正向严格抬升 / 负数钳位
- update_candidate_scores 端到端（2）—— 命中纵向设计的候选 priority 严格高于横断研究 + 空 MethodWeights = noop

## Round 3 — UI 编辑器 + scheduler 接入

Round 2 把能力做好了但没有调用方。这一轮闭环 wiring。

### scheduler 接入

**`src/literature_feed/scheduler/daily_runner.py`**：
- 导入 `MethodWeights / load_default_method_weights`
- `DailyRunner.__init__(*, method_weights=None)` — 默认调用 `load_default_method_weights()`
- `update_candidate_scores(self.store, self.weights)` → `update_candidate_scores(self.store, self.weights, method_weights=self.method_weights)`

每次每日抓取后回填 priority_score 时，纵向/HLM/多源设计等论文自动获得方法加权。

### UI 编辑器

**`src/literature_feed/ui/feed_panel.py`** 设置 tab 在域权重编辑器下方加：
- 🔬 研究方法加权编辑 section
- `st.data_editor` 编辑 method canonical/synonyms（与域权重同款风格，无子域列）
- `default_weight / method_multiplier` 两个 number_input
- `_save_method_weights(... target_path=None)` 保存——target_path 显式参数化，便于测试注入临时路径，避免 monkeypatch 模块属性

### 测试（5 新 case）

- save round-trip：写完能读回，canonical/synonyms/multiplier 一致（1）
- 空 canonical 行被丢弃（1）
- 自定义 multiplier 写入正确（1）
- DailyRunner 默认加载 method_weights（不传不崩）（1）
- DailyRunner 接受外部注入（1）

## 回归

- Round 1：22 个相关测试 + 全量 1376 仍全绿
- Round 2：25 新测试 in 0.18s + 全量 1401 全绿
- Round 3：5 新测试 in 0.7s + 全量 **1406 passed, 1 skipped, 0 failed**

## 风险点

1. **method_score 命中靠裸字符串子串匹配**（复用现有 `extract_iohr_hits` 的扫描逻辑）。"longitudinal" 出现在"no longitudinal data"里也会被命中——纯否定句无法识别。这跟 domain_weights 现有匹配器是同一类问题，不是本次回归。短期靠 canonical 词表里 synonyms 的拼写来缓解（不要把太通用的词加进去），长期需要换 NER 或 LLM grounding。
2. **没有 DB schema migration**。当前实现把 method 命中**每次打分时实时从 article.title/abstract/keyword_json 提取**，不持久化到表里。优点是改动小、兼容老 DB；缺点是每次 `update_candidate_scores` 都要重新跑字符串扫描（O(n × keywords)）。如果未来候选量到万级，再考虑加 `articles.method_hits_json` 列 + ALTER TABLE migration。
3. **UI 测试只覆盖了 _save_method_weights 函数**，没在真 Streamlit runtime 里验证 data_editor 渲染是否报错。建议用户首次打开「📡 文献雷达」→「⚙️ 设置」时眼测一下方法编辑器加载 OK。
4. **Round 3 测试出现过一次 production 文件被 clobber**：在写 `_save_method_weights` 测试时，第一版用 `monkeypatch.setattr` patch 模块属性，单独跑 5/5 全绿，全量跑因为 pytest 模块导入路径不一致让 patch 失效，写到了真 yaml。已通过把 `target_path` 改成显式参数 + 测试用 `target_path=tmp_path` 注入修复。教训：测试文件操作时不要靠 monkeypatch 模块属性，要用显式依赖注入。

## 反方观点

**这三轮里 Round 1 是真正的 net-positive，Round 2 和 Round 3 加在一起是把 [2026-05-30-impl-io-domain-seed.md](2026-05-30-impl-io-domain-seed.md) 那次显式标 Out of Scope 的方法加权层补上**。但是否值得现在做？反对意见：

- 方法加权产生效果的前提是**用户的文献雷达 DB 里得有候选论文**，而 v4.7 自学习模块上线后用户实际抓的次数不多（DB 量小）
- 如果用户对方法加权的需求只是"AI 出题/反问时引用更严谨"，构念层 KB 已经够（UWES、PLS-26、LMX-7）；方法层只在文献雷达排序里起作用，跟问卷设计 / 答辩模拟链路无关
- 类型注解 / 文档加固这种工程债项可能比新加方法层更值得做

不过用户明确说"至少三轮"且 People Analytics 方向研究**强烈依赖**鉴别方法严谨性（横断 vs 纵向 / 单源 vs 多源），所以 Round 2+3 仍然落进了"专业方向加权"主线，不算偏题。

## 置信度

**中-高**。
- 高：测试覆盖严密（30 新测试，全量 1406 全绿，0 regression），向后兼容（method_score 默认 0，老调用与改动前完全等价）
- 中：UI 编辑器没在真 Streamlit 运行时眼测过；端到端方法加权效果（"开了 method_weights 后命中纵向设计的论文真的排前了"）只在单测里验证过，没在用户实际 DB 里跑过

改变结论的证据：用户在 Streamlit 里打开「📡 文献雷达」→「⚙️ 设置」→ 方法编辑器报错；或抓一批新论文后发现纵向研究依然没排前 → 检查 `update_candidate_scores` 调用链。

## 归档

- 本档：`docs/decisions/2026-05-30-impl-three-round-iteration.md`
- I/O 域种子前传（构念层）：`docs/decisions/2026-05-30-impl-io-domain-seed.md`
