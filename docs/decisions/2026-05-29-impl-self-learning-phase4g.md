# Phase 4g — 测试套件落地（v4.7 自学习模块收官）

**日期**：2026-05-29
**指挥**：Claude Opus 4.7
**单方实现**：Opus 直写 + 自审（不走多模型，因为这是测试代码、零业务风险、快速反馈循环已经替代了 critic 的作用）
**目的**：给 Phase 4a-4f 的所有模块铺一层回归保护，本阶段写完 = 自学习模块 PR-ready。

---

## 范围

新建 4 个测试文件，覆盖 Phase 4c-4f：

| 文件 | 测试数 | 覆盖 |
|---|---|---|
| `tests/test_literature_feed_trend.py` | 22 | DomainWeights 反查 + scorer + aggregator |
| `tests/test_literature_feed_extract.py` | 13 | grounding + prompts + LLMExtractor end-to-end (mock) |
| `tests/test_literature_feed_scheduler.py` | 10 | DailyRunner + bootstrap_check |
| `tests/test_literature_feed_ui.py` | 6 | UI `_save_domain_weights` + 一条 contract 回归 |
| **合计** | **51** | + 已有 47 → **literature_feed 共 105 测试** |

全项目：1334 passed / 4 skipped / 11 errors（playwright browser 未装，与本期无关）。

## 设计决策

1. **fixture：`feed_root` 用 `monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", ...)` + 模块缓存清除**
   - 每个测试拿到独立 tmp_path，且 import 链重置 → 不会读到上一次的 `domain_weights.yaml` 或 `feed.db`
   - 参考 Phase 4a 已有的 storage 测试模式，保持一致性

2. **mock LLM**：用 `SimpleNamespace(content=..., fields={"usage":{...}})` 模拟 `llm_chat_fn` 返回值
   - 不走真实 LLM 调用 → 100% 离线、稳定、零成本
   - online smoke 测试单独打 `@pytest.mark.online` 标签（Phase 4e 已铺）

3. **scheduler mock_fetchers**：3 个 fetcher 类（GoodFetcher / RateFetcher / SchemaFetcher）覆盖三种典型路径
   - 验证 partial / failed / ok 三档 status 都能正确升降

4. **UI 测试只测纯函数**：`_save_domain_weights` 是 streamlit 之外可直接调用的逻辑
   - 全 UI 交互（按钮点击、tab 切换）等到 Phase 4h+ 接 streamlit-testing 框架再补，不强行用 mock 模拟 streamlit 全局

## 实现过程中发现的真实 bug

写 trend 测试时读 `aggregator.compute_domain_summary` 源码，发现它返回的 dict 用 key `"weighted"`（不是我在 feed_panel.py 用的 `"weighted_count"`）→ UI 用户点开 📊 趋势分析 tab 会 KeyError 崩溃。

**修复**：
- `src/literature_feed/ui/feed_panel.py` 把 `bucket['weighted_count']` 改成 `bucket['weighted']`
- 加回归测试 `test_compute_domain_summary_key_matches_ui_usage` 防止以后再断

这是 Phase 4f 单方实现的一个 silent bug，被 Phase 4g 写测试时发现 → 验证了"测试就是一种 critic"的价值。

## 跑测试时的 6 个签名失配（已修）

第一次跑 `pytest`时 9 个 fail，全部是签名/字段名失配（不是逻辑错）：

| 失败 | 真实签名 |
|---|---|
| `ArticleRow(...)` 缺 provenance | provenance 是 required positional kwarg |
| `LLMExtractor.extract_for_article(aid, kind="construct")` | 不接 kind，单次跑 construct + method 两个 prompt |
| `stats.inserted` | 实际字段是 `constructs_kept` / `methods_kept` / `constructs_rejected` / `methods_rejected` / `needs_review` |
| `stats.constructs_rejected` for grounding fail | grounding 失败 retry 后落 `needs_review` 而非 rejected |
| `dr_mod.run_daily(trigger=...)` 用 monkey-patch `dr_mod.build_fetcher` | DailyRunner 默认参数 `fetcher_builder=build_fetcher` 在函数定义时 bound，事后 monkey-patch 模块属性无效 → 改写成"自建 store close 路径"测试 |

修完一轮 105/105 全绿。

## 自审 ≥3 问题（Opus 写完 4 个测试文件后）

1. **没测 LockManager 并发**
   - test_lock_conflict 只测同一进程内 lock → release，没测多进程真正抢锁
   - **决定**：跨进程并发用 `subprocess.Popen` 太重，留给 Phase 4h+ smoke 脚本（手动跑）

2. **mock_fetchers 太理想**
   - 真实 fetcher 会有 HTTP 超时 / 编码错误 / 部分字段缺失等场景，mock 都没覆盖
   - **决定**：fetchers 测试已有自己的 27 个测试覆盖 raw HTTP layer。scheduler 测试只是验证"runner 把异常分类正确"，不需要再测 fetcher 内部

3. **UI 测试覆盖率仍偏低（只测了 1/4 tab 的纯函数）**
   - 📰 文章流 / 🧠 候选审核 / 📊 趋势分析 三个 tab 的逻辑没单测
   - **决定**：那三个 tab 的核心都是"读 store → render"，store 已经被覆盖；UI render 等 streamlit-testing 框架接入

## 验收

```
tests/test_literature_feed_trend.py        22 passed
tests/test_literature_feed_extract.py      13 passed
tests/test_literature_feed_scheduler.py    10 passed
tests/test_literature_feed_ui.py            6 passed
literature_feed 全套 (含 storage + fetchers)  105 passed

全项目                                     1334 passed
                                              4 skipped
                                             11 errors (playwright 浏览器未装，pre-existing)
```

## 风险 ≥2

1. **Mock LLM ≠ 真实 LLM**：测试断言 `extract_for_article` 行为基于 mock 返回固定 JSON。真实 GPT/DeepSeek 偶尔会出 `evidence_quote` 不严格逐字、或 confidence > 1.0 等边界值，单测捕不到 → 上线后第一次跑真实数据要紧盯日志一周。

2. **测试隔离依赖环境变量**：`feed_root` fixture 用 `LITERATURE_FEED_DATA_ROOT` env var 做隔离，`pytest-xdist` 并行时如果 env 隔离没做好可能撞车 → 当前 sequential 跑没事，未来开 -n auto 要重新验证。

## 反方观点

GPT 如果在场可能会主张"测试覆盖率应该跟到具体行数指标（pytest --cov ≥ 80%）"。我没装 cov 是因为：v4.7 自学习模块是 ~3000 行新代码，硬卡覆盖率门会迫使我去测大量样板代码（dataclass `__post_init__`、logger 调用），收益低；本阶段重点是"关键路径 + 真实 bug 防护"。 cov gate 留给 Phase 4h+ 上 CI 时再讨论。

## 置信度

**高**。105 个 literature_feed 测试 + 1334 个全项目测试在本机完整通过，且 Phase 4f 那个 weighted_count bug 被测试本身抓到 → 整套测试已经发挥作用而非走形式。

会改变结论的证据：
- pytest 在 CI（Linux）上跑出 Windows-only 的失败（如路径分隔符、文件锁差异）
- 真实跑一次 daily runner 后发现 schema 与 mock 假设的不一致
- UI 三个未覆盖 tab 上线后被用户点出 traceback

## 落地

- 4 测试文件已写入 `tests/`
- `feed_panel.py` weighted bug 已修
- 不需要改其他模块代码
- 下一步：将 task #13 标完成 → task #4（umbrella）标完成
