# 越界拦截域声明（item_ranges）推广盘点与补齐工单草稿（s1025-03 出材件）

> 性质：**材料件＋工单草稿，零数值改动、零改码**。锚点 commit 218ec6c（s1023-01：handle_missing 可选 item_ranges 参＋AnalysisPlan 可选域声明字段＋runner.py:930 透传）。
> 盘点口径：`rg item_ranges` 全源码（2026-10-26 实测）；数值域（各量表具体 1-5/1-7 等）一律以用户维度定义为准，本件不发明任何量尺数值。

## 一、消费面现状（拦截执行端，全部已就位）

| # | 消费点 | 位置 | 入役批次 | 拦截时机 |
|---|---|---|---|---|
| C1 | `detect_invalid_responses(item_ranges=…)` | src/questionnaire/import_cleaning.py:156（调用 :261） | r5 B1 | 无效样本检测（越界计"无效作答"证据） |
| C2 | `compute_dimension_scores` 计分前校验 | src/questionnaire/import_cleaning.py:114 | 决议#17 案 a | 计分前越界**直接抛 ValueError**（最严） |
| C3 | `handle_missing(item_ranges=…)` 插补前拦截 | src/analysis/data_quality.py:29（判据 :100-104） | s1023-01 | mean_imputation 插补前把越界值归缺失（meta.oob_intercepted 留痕） |
| C4 | runner 透传 `getattr(plan,"item_ranges",None)` | src/analysis/runner.py:926-930 | s1023-01 | 统计链入口（缺省 None＝零行为变更） |

## 二、域声明生产面现状（声明从哪来——核心盘点结论）

| 生产点 | 现状 | 判定 |
|---|---|---|
| 问卷清洗链 `clean_questionnaire(dimensions=…)`（import_cleaning.py:205, :226-238） | **运行时从 `ScaleDimension.min_score/max_score` 现取**（逐题项；多维度冲突取交集留痕）——域声明静态源＝每份问卷的维度定义（用户配置面），无独立配置文件 | ✅ 已带面（问卷导入→清洗→计分全链覆盖） |
| 统计链 `AnalysisPlan.item_ranges`（intent_resolver.py:50） | 字段就位，但 **rg 全源码零生产面**：仅测试直填，生产路径恒 None | ❌ 未带面（跨链交接断点） |
| `intent_resolver` 三处构造 plan（:162/:180/:278） | 自然语言解析出 plan，用户话术不带结构化域声明 | ❌ 不接（有意维持，见工单-4） |
| `quick_entries.py:684` 快捷录入 UI 构造 plan | 不填 item_ranges | ❌ 未带面 |
| `workspace._serialize_plan`（:136）/_deserialize_plan（:163） | **手工白名单两侧均缺 item_ranges 字段**——plan 若带域声明，工作区保存→载入后即丢失 | ❌ 未带面（序列化丢域，双向） |

## 三、覆盖现状结论

1. **已带面**：问卷导入清洗→计分链（C1/C2）全量覆盖——域声明由维度定义运行时生成，无静态缺口。
2. **未带面**：统计链（C3/C4）的 plan.item_ranges **零生产面**。问卷链与统计链的域声明在交接处断开：问卷清洗现取的 item_ranges 是局部变量，进入统计分析（run_analysis）时 plan 是新解析对象，域声明不随行。当前 C3/C4 实际只在测试路径生效。
3. **静态源现状**：域声明唯一权威源是 `ScaleDimension`（用户配置面，会话级）；`item_templates.py` 锚点词表（anchors_5/anchors_7）与 `questionnaire_schema.json`（data_dictionary 适配载体）是模板/schema 面，均非结构化 item_ranges 注册表。**无需新建配置文件**——域声明应从维度定义随数据流携带，而非另立静态注册表（两源漂移风险）。

## 四、补齐建议（配置面，零数值改动）

原则：**域声明跟着数据走**（问卷维度定义是唯一源），统计链不另建量表配置库；补齐全部是"搬运/携带"性质，零数值发明。

## 五、补齐工单草稿（供主班立项，按优先序）

### 工单-1（高）｜问卷→统计链交接桥
- **落点**：问卷清洗面板→统计分析的调用侧（ui/questionnaire_import_panel 及同径路），把 `clean_questionnaire` 已现取的 item_ranges 塞进随后的 `AnalysisPlan.item_ranges`。
- **验收**：问卷链清洗后直接跑统计，`missing_meta.oob_intercepted` 有值当且仅当维度定义域外值存在；无域问卷零行为变更。
- **量级**：交接点 1-2 处，各 1-3 行＋钉桩测试 2 例。

### 工单-2（高）｜workspace 序列化补字段
- **落点**：src/utils/workspace.py `_serialize_plan`（白名单加 `"item_ranges": plan.item_ranges`）＋ `_deserialize_plan`（`item_ranges=data.get("item_ranges")`，注意 JSON 往返把 tuple 变 list、需转回 `Dict[str, Tuple[float,float]]`）。
- **验收**：带域 plan 保存→载入后 `plan.item_ranges` 等值往返；旧工作区文件（无该键）载入后仍 None＝零行为变更。
- **量级**：两处各 1-2 行＋往返钉桩 2 例。

### 工单-3（中）｜快捷录入面板可选域声明
- **落点**：src/ui/quick_entries.py:684 plan 构造处，可选输入面（如每题项 lo/hi 或选锚点模板带出默认域——**默认域数值展示属配置面文案，仍以用户确认为准，不代填**）。
- **验收**：不填＝现状零变更；填了＝C3 拦截生效。
- **量级**：UI 一小块＋1 例钉桩；依赖工单-1 先落（共用透传面）。

### 工单-4（登记·有意不接）｜intent_resolver 自然语言面
- **判定**：自然话术不适合携带结构化域声明（猜域＝数值发明风险），维持 None；用户话术说"1 到 5 分"时走既有量表配置面而非解析期塞域。
- **处置**：仅登记，不立项。

## 六、执行时点实测锚

| 锚 | 值 |
|---|---|
| 盘点命令 | `rg -n "item_ranges" --type py -g '!tmp/**'`（源码 4 文件 6 消费/生产点＋tests 2 文件） |
| AnalysisPlan 构造点 | intent_resolver.py:162/:180/:278、utils/workspace.py:170、ui/quick_entries.py:684（rg `AnalysisPlan\(` 实测） |
| 序列化白名单缺字段 | workspace.py:136 `_serialize_plan` 与 :163 `_deserialize_plan` 双侧无 item_ranges（2026-10-26 sed 实测） |
| 上游锚 commit | 218ec6c（s1023-01，2026-10-24 落地） |
