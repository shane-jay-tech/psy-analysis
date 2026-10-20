# 资产谓词四处写法单源化方案材料

> 产出单：s930-24（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-39 遗留（「资产谓词单源」若立案，范围至少 4 模块——含 project_health.py:98-112 的 hasattr 系第四种写法；勿按单行成本排期）。
> **零码改动**；写法分布为实查（grep 面+sampled 现读）。

## 一、四种写法分布（实查清单）

| 写法 | 形状 | 代表位置（实查） | 语义差异 |
|---|---|---|---|
| ① `is not None` 系 | `df is not None and inspector is not None` | `src/ui/quick_entries.py:243`、`app.py:767/841`（`_has_df`）、`src/utils/workspace.py:244`（s930-01 新增的成对判断同款） | 只认「值在」，不管类型（DataFrame 鸭子型） |
| ② `hasattr` 系 | `hasattr(paper_bundle, "warnings") and paper_bundle.warnings` | `src/utils/project_health.py:99/:111`（矿源点名第四写法）、`docx_exporter.py:602/1173/1183` | 鸭子型探测＋真值二级判断——对「对象缺属性」与「属性为空」分两步 |
| ③ `getattr(..., default)` 系 | `_v("ethics", "")`、`getattr(crawled, "year", 0) or 0` | `docx_exporter.py:651`（_v，s930-06 已做 list 归一）、`models.py:89/93`（s930-22 六处族） | 带缺省回退——缺失与缺省值同形 |
| ④ `st.session_state.get(k) is None` 系 | `st.session_state.get("inspector") is None`、四键闸（workspace.py:617 案 a） | `workspace.py:244/606-634`（快照/恢复面） | session 字典面专用，键级 None 判 |

## 二、单源化方案（两案）

| 案 | 设计 | 覆盖 | 成本与风险 |
|---|---|---|---|
| **案 1 谓词模块**（推荐形状） | 新 `src/utils/asset_predicates.py`：`has_df(state)`、`has_inspector(state)`、`is_populated(obj, attr)`（=hasattr+truthy 合一）、`get_or(obj, name, default)`——四写法各映射一个函数；四处调用面逐个替换 | ①②③④全覆盖 | 触面≈6 文件（quick_entries/app/项目健康/docx_exporter/models/workspace）×每文件 1-5 点＝20 点级替换；**风险＝四写法语义有微差**（hasattr 对「属性存在但为 None」与 is not None 判法不同；getattr default 与 hasattr+truthy 二段不同）——单源函数必须逐写法保真（不是一个万能谓词） |
| **案 2 只钉不变式不改写法** | 不动四处；加一条 AST/文本哨兵「新增文件不得再引入第五种写法」（白名单现有四文件×四形状） | 防扩散 | 不收敛存量；哨兵白名单维护面 |

## 三、建议（不签口径）

1. **案 1 按写法分四函数**（不是合一谓词）——单源化的价值在「语义各归其名」而非「消灭写法差异」；四处写法的语义差（§一列）是**真实的**，合一反而丢信息；
2. 排期按矿源提醒**勿按单行成本**：20 点级替换＋每点语义核对＋回归（panel/health/docx 三域测试族），建议独立小单串行走（类似 s930-15 的 harness 抽取，分文件落地每步全绿）；
3. 与 s930-22（models.py or-0 族）联动：`get_or` 帮助函数落地时 models 六处可同批迁移（第七处防分叉先例）。
