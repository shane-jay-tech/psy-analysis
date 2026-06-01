# Phase 4f — UI 接入（📡 文献雷达 mode + 4 tabs + 设置页加权编辑）

**日期**：2026-05-29
**Slug**：`impl-self-learning-phase4f`
**前置**：Phase 4a-4e（存储/抓取/抽取/趋势/调度全部就位）
**后续**：Phase 4g（测试套件）

---

## 1. 任务

把前 5 个阶段的能力暴露到 Streamlit 主 app：
- `app.py` 顶部 `st.radio` 加 `📡 文献雷达` 模式
- `src/literature_feed/ui/feed_panel.py` 提供 `render_literature_feed()` 入口
- 4 个 tab：每日动态 / 趋势分析 / 来源管理 / 设置
- 设置页可视化编辑 IO/HR/OB 词表，保存写回 `data/literature_feed/domain_weights.yaml`

---

## 2. 实现要点

### 2.1 入口与生命周期

- 在 app.py 第 ~498 行的 `mode = st.radio([...])` 把 `📡 文献雷达` 加在 `🌱 选题与文献综述` 之后（按"先选题→雷达→设计→分析→写作"的真实科研时序）
- 在 mode 分发段（app.py ~2278 行）`elif mode == "📡 文献雷达"` lazy import 调用
- `render_literature_feed()` 顶部：FeedStore 短生命周期开/关（render 末 finally 关），避免连接积累
- session-scoped 一次触发：`_BOOTSTRAP_SESSION_KEY` 守门，bootstrap_check.maybe_trigger_async() 一个 session 内只触发一次

### 2.2 4 个 tab

| tab | 内容 |
|---|---|
| **📰 每日动态** | bootstrap 状态横幅（last_async_result/is_running/evaluate）+ 立即抓取按钮 + 高优先级 pending 候选 Top20 + 近 14 天文章 |
| **📊 趋势分析** | 时间窗口（7/30/90/180）+ Top N（5-50）+ domain_only 过滤 → IO/HR/OB/其他 4 卡片汇总 + 详情表（rank/keyword/domain/篇数/加权/最新） |
| **🛰 来源管理** | sources 表（source_id/期刊/抓取器/状态/last_success/启用）+ 最近 10 条 fetch_runs 审计 + 立即抓取所有按钮（启动 detached subprocess） |
| **⚙️ 设置** | LLM 月预算进度条 + 锁状态 + 域权重 data_editor（动态行/SelectBox 选 IO/HR/OB） + danger zone（重置 pending） |

### 2.3 子进程触发抓取（来源管理 tab 的"立即抓取所有"）

不能在 Streamlit 进程内同步跑 `run_daily()` —— UI 阻塞 + 锁占用。做法：`subprocess.Popen` 启动 `python -m src.literature_feed.scheduler --trigger ui_manual`，**Windows 用 `CREATE_FLAGS=0x00000008`（DETACHED_PROCESS）/ POSIX 用 `start_new_session=True`**，这样 Streamlit 关掉抓取还在跑。

### 2.4 域权重保存（设置页核心新功能）

UI 给的是 `st.data_editor` 的 list[dict]（domain/canonical/synonyms 三列）。`_save_domain_weights()` 反向构造成 YAML schema：

```yaml
version: 1
default_weight: 1.0
domain_multiplier: 1.5
domains:
  IO:
    concepts: [{canonical: ..., synonyms: [...]}]
  HR: ...
  OB: ...
```

写入用 `with open(tmp, "w") + tmp.replace(target)` 原子替换，避免半写状态被 reload 看到。

---

## 3. 验证

### 单测 & 回归
- `python -c "from src.literature_feed.ui import render_literature_feed"` → 导入 OK
- `python -c "import ast; ast.parse(open('app.py').read())"` → 语法 OK
- `pytest tests/test_literature_feed_*.py -q` → **52 passed**（前 5 阶段的回归全绿）

### 域权重 round-trip smoke
脚本：load YAML → 转 editor rows → `_save_domain_weights()` 写回 → reload → 比较 canonical 数 / multiplier。结果：25 canonical 不丢、multiplier=1.5 不丢、文件原子替换成功。**SMOKE PASS**。

### 没做的（留给 Phase 4g）
- 没跑 streamlit 实例做 e2e（用户主动跑 `streamlit run app.py` 后视觉验证）
- 没用 `mock` 单测 panel 函数本身（依赖 `st.*` 全局，Phase 4g 用 `streamlit-testing` 框架补齐）

---

## 4. 自审（Opus 主动追加；本轮没走 DeepSeek 多模型审）

为什么不走多模型？UI wiring 不引入新业务逻辑，只是把已经测过的模块接到 Streamlit。CLAUDE.md "When NOT to trigger collaboration" 明确说"读/总结/纯 wiring"可以单 pass。

自查的问题点：
1. **`load_default_weights.cache_clear()` 调用是 no-op**：当前 `load_default_weights` 不是 `lru_cache` 装饰的，所以那行 `if hasattr` 检查永远 False。**保留**，因为未来给它加 cache 就不用改 UI 代码；但这是死代码味道，记一笔。
2. **danger zone 直接 SQL 写 `UPDATE llm_candidates ... rejected`，绕过 `update_candidate_status`**：FeedStore 没暴露 batch update 方法，绕过是为了避免 200+ 候选逐条事务。短期 OK；如果后续 update_candidate_status 加了审计/钩子，这里会漏。
3. **bootstrap_check.maybe_trigger_async() 每个 session 触发一次**：用户开 N 个 tab 等于触发 N 次。当前 `_BACKGROUND_THREAD` 单例守住了，但这是"靠下游守门"。如果有人把单例守门挪走，UI 这边就会失控。
4. **subprocess.Popen 启动后没记录 PID**：UI 看不到子进程是否真启起来；按"立即抓取"再点一次会启第二个，被锁挡住但白启一次。可以接受（锁会拦），但用户体验可以更好——下版本加"已启动一次"session flag。

### 风险点 ≥ 2
1. **Streamlit 多 tab 同时改域权重 = race**：A tab 改完保存，B tab 没刷新就保存覆盖 A 的改动。当前没加文件锁/版本号；用户单人单 tab 编辑没事，多 tab 要警惕。
2. **`_spawn_scheduler_subprocess` 路径推断**：`Path(__file__).resolve().parents[3]` 假设 `src/literature_feed/ui/feed_panel.py` 永远是这个相对深度。如果有人重构目录层级，subprocess cwd 会跑偏。

### 反方观点
最强反对：**这套 UI 默认所有用户都看得懂"IO/HR/OB"标签**，但用户的本科同学/老师看到这个 mode 时大概率不知道这是啥。如果未来给非 IO/HR/OB 方向的用户用，这个 mode 应该藏在 advanced tier 后面或加一行说明。**当前用户=本人单人使用**，可以接受。

### 置信度
中—高。
- 高的部分：所有依赖模块都已 52 测试覆盖、回归全绿、关键路径 round-trip smoke 通过
- 中的部分：没跑 streamlit 实例视觉验证；UI 的真实交互行为（rerun 时序、表单提交后状态）只在 Phase 4g 装上 streamlit-testing 后才能机器验证
- 改变结论的事件：用户实际跑 `streamlit run app.py` 进入 📡 文献雷达，发现某 tab 抛 KeyError 或 data_editor 行为异常 → 立即修

### 归档路径
`docs/decisions/2026-05-29-impl-self-learning-phase4f.md`（本文件）。

---

## 5. 文件清单

```
src/literature_feed/ui/__init__.py            +5 行（新增）
src/literature_feed/ui/feed_panel.py          +400 行（新增）
app.py                                         +5 行（mode list 加 📡 文献雷达 + dispatch）
docs/decisions/2026-05-29-impl-self-learning-phase4f.md  本文件
```
