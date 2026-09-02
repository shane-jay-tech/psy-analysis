# v5.9 升级报告：交互性能深化 + 图表崩溃修复 + 误触防护

**版本**：v5.8 → v5.9
**日期**：2026-08-15
**主题**：每次交互的固定开销、两个"最常用路径必崩"的图表 Bug、破坏性操作误触防护

---

## 一句话总结

v5.8 解决了启动与首屏；v5.9 深入每次 rerun 的固定开销（Streamlit magic AST
重写 0.4~0.6s/次 → 关闭），修掉了**独立样本 t 检验与配对检验渲染图表必崩**
两个 P0 Bug（此前靠用户"关掉图表"才能看到结果），并给三处不可恢复的破坏性
操作加了两步确认。

---

## 一、交互性能（每次点击的固定开销）

### 1.1 关闭 magic AST 重写 — rerun 0.31s → 0.10s

**问题**：Streamlit 每次执行脚本前都会跑 magic 命令 AST 转换。对 2600+ 行的
app.py，这个转换实测占 **0.4~0.6s/次**（cProfile：ast._fix 0.21s + 
iter_child_nodes 0.16s + compile 0.08s），与大文件无关、每次交互必付。

**修复**：新增 `.streamlit/config.toml`，`[runner] magicEnabled = false`。
安全性：AST 扫描确认 app.py 全文**没有任何** magic 语法（无裸字符串/裸表达式）。
附带 `[browser] gatherUsageStats=false` 与 `[server] fileWatcherType="none"`。

**实测**（50 万行 × 4 列 ≈ 26MB 数据）：
| 场景 | 关闭前 | 关闭后 |
|---|---|---|
| 数据分析模式 rerun | 0.31s | **0.10~0.13s** |
| AppTest 首跑 | ~7.4s | ~6.7s |

### 1.2 调研结论：session_state 大数据序列化不是瓶颈（无需改造）

按 v5.8 遗留项深入验证 Streamlit 1.59 内部实现：
`ScriptRunner` 结束时只向浏览器回传 **WidgetStates**（widget 绑定的值），
非 widget 的 session_state 值（df/analysis_output）**只存服务端**，
不随 rerun 序列化到浏览器。26MB df 的 rerun 实测 0.10s 亦证实序列化不在热点。
**结论**：「大数据会话序列化改服务端缓存」没有必要，不引入 cache_resource 
+ token 的复杂度；等价真实瓶颈（magic 编译）已消除。

### 1.3 use_container_width 迁移（179 处，防 2.0 升级崩）

Streamlit 官方弃用 `use_container_width`（2025-12-31 后移除），当前版本
每次渲染刷 stderr 警告。迁移全部 179 处 → `width="stretch"`（17 个文件，
覆盖 button/dataframe/download_button/data_editor/form_submit_button/
plotly_chart，均已在 1.59 验证支持）；`requirements.txt` streamlit 下限
1.28 → **1.50**（width 参数全量可用版本），锁定 1.57.0 已实测。

### 1.4 文献抓取启动检查确认无阻塞

`literature_feed.scheduler.bootstrap_check.maybe_trigger_async` 已在后台线程
执行，不阻塞启动——按目标核查并确认。

---

## 二、P0 Bug 修复：最常用分析路径图表必崩

### 2.1 独立样本 t 检验：每次渲染图表都崩

**现象**：`bar_with_error` 对 t 检验的 group_stats（组别/N/M/**SD，无 SEM 列**）
执行 `data.get("SEM", [0]*n).tolist()`——默认值是个 list，对 list 调
`.tolist()` 抛 AttributeError。独立样本 t 检验是系统最高频路径。

**修复**（`src/visualization/charts.py::bar_with_error`）：
- SEM 缺失时由 **SD/√N** 推导（统计上正确）；
- 列名兼容 组别/组/group/Group/分组，均值列兼容 M/mean；
- 输入兼容 DataFrame / list[dict]，数值 pd.to_numeric 归一；
- 空输入返回空图不崩。

### 2.2 配对检验：渲染图表必崩

**现象**：`render_charts` 配对分支调 `box_plot(df, col1, None)`，
`box_plot` 内 `df[iv] → df[None]` 抛 TypeError——配对 t 检验结果页必崩。

**修复**：`box_plot` 支持 `iv=None`（多列各一个箱）；配对分支改传两列，
渲染「前测 vs 后测」双箱图。

### 2.3 render_charts 单图隔离

图表工厂调用全部包进 `_safe()`：任一图构建失败只跳过该图，折叠展示
「⚠️ 部分图表未能生成 + 原因」，**绝不再因一张图让整页结果白屏**。

---

## 三、体验改进（反人类设计清除）

1. **卡方检验从此有图**：新增 `contingency_heatmap`（列联表频数热力图）。
   此前卡方做完 charts_data 里有 contingency 却没渲染分支，用户一张图都看不到。
2. **三处不可恢复操作加两步确认**：
   - 侧栏「🗑️ 清除会话数据」（一键清空数据+结果）
   - 选题历史「删除分支」（永久丢选题轨迹）
   - 「清空整个收藏夹」（跨会话累积的图表收藏）
   均改为「点击 → ⚠️确认/取消」，确认文案写明后果与不可恢复。
3. 收藏夹清空确认里显示**将删除的张数**，让用户知道代价。

---

## 四、测试基线

| 项目 | 数量 |
|---|---|
| 新增测试 | +11（`tests/test_visualization_charts.py`：bar_with_error 5 / box_plot 3 / render_charts 隔离 1 / 热力图 2）|
| 全量回归 | **2507 passed, 59 skipped, 0 失败**（208.4s），`logs/junit_v59.xml` 可查 |

新增文件：
- `.streamlit/config.toml` — magic 关闭 + 统计关闭 + 无热重载
- `tests/test_visualization_charts.py`
- `UPGRADE_REPORT_V5.9.md`（本文）

修改文件：
- `app.py` / `requirements.txt`
- `src/visualization/charts.py`（bar_with_error 重写 / box_plot 配对支持 / contingency_heatmap）
- `src/ui/renderers.py`（单图隔离 + 列联表分支 + 配对分支）
- `src/ui/upstream_panel.py` / `src/ui/undergrad_wizard.py`（两步确认）
- 17 个 UI 文件 ×179 处 width 迁移

---

## 五、留给 v5.10 的事

1. autosave 大工作区（含全量 df.to_csv）仍在点击后同步写盘（30s 节流内首次
   约 1~2s 卡顿）；可改为增量快照（只存变更键）或快照缓存。
2. 意图解析器对「题1到题4」「三组在XX上的差异」等自然表述的变量识别仍偏弱，
   失败时已有友好报错，但可加启发式（列名枚举展开、组别优先）。
3. KNOWN_ISSUES #L2（F1 论文写作双入口）、#L3（judge 漂移观测）、#L4（自评报告）继续跟踪。
