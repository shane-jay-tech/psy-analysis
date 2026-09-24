# psy `def from_dict` 11 处散布 census 与收敛裁决材料（只读）

- 单号：s924-64　班：`qoder-executor-20260925-0730-psy55`　日期：2026-09-25
- 性质：**只读 census ＋ 两案对比**。零代码改动、零测试改动、零写库、未跑任何写盘路径。
- 探针：`tmp/qoder-executor-20260925-0730-psy55/s64_probe.py`（AST 特征度量 ＋ 运行时别名实验）。

---

## 〇、先纠卷宗前提（本单锚点零漂移，但两处口径要改）

| # | 卷宗前提 | 实测 | 结论 |
|---|---|---|---|
| 1 | 「`def from_dict` 共 **11 处**」 | **11 处** ✅ | 成立（`src/` 内与全仓内均 11，无 src 外散点） |
| 2 | 「散布 **8 文件**」 | 🔴 **7 文件** | **否证**。卷宗自己枚举的也只有 7 个文件（models/evidence_record/topic_funnel/figure_collection/state_store/workspace_state/project_manager），"8"与自身枚举矛盾 |
| 3 | 「签名**两种**风格（`data`/`d`）」 | 参数名确为 2 种（`data`×8、`d`×3），但**注解还有第 2 维**（`Dict[str, Any]`×9、`dict`×2）⇒ 实测 **4 种组合全部出现** | 低估一维 |
| 4 | 7 个行号锚点（`models.py:64/135/167/195/227`、`workspace_state.py:115`、`project_manager.py:60`）＋ 枚举 4 处（`evidence_record.py:49`/`topic_funnel.py:360`/`figure_collection.py:54`/`state_store.py:63`） | **11/11 全部逐字未漂** | ✅ 本单是今晚三张单里唯一零漂移的 |
| 5 | 预计「models.py 内部 5 处先收敛为私有公共解析」**局部案胜出** | 🔴 **不成立**（§三：5 处仅 6/13 项特征一致；§四：强行收敛会引入 session_state 写回污染，已运行时证成） | 推荐案改判（见 §五） |

复算：

```
$ rg -n --no-ignore 'def from_dict' src/                     # 11 行 / 7 文件
$ rg -l --no-ignore 'def from_dict' src/ | wc -l             # 7
$ rg -n --no-ignore -o 'def from_dict\(cls, (data|d): [^)]*\)' -r '$0' src/ | sed 's/.*def from_dict//' | sort | uniq -c
$ rg -n --no-ignore -g '!tmp/**' 'def from_dict' . | rg -v '^\./src/'   # 全仓面：仍是这 11 处
```

---

## 一、11 处清表（签名 / 容错行为 / 调用侧）

### 逐处明细

| # | 类 → 位置 | 签名 | 容错契约（源码证据） | 调用侧 |
|---|---|---|---|---|
| 1 | `LiteratureItem` → `src/literature_review/models.py:64` | `(cls, data: Dict[str, Any]) -> "LiteratureItem"` | 15 个 `.get`；**7 处 `or` 兜底**；`int()`×2＋`float()`×1 强转；`list()` 拷贝×2；`key` 缺→`_new_id()`、`added_at` 缺→`_now_iso()`。🔴 **非空脏串抛 `ValueError`**（`int("约 2019")`） | `search.py:230`、`literature_review_panel.py:757`、`tests/test_literature_review_models.py:31`、`tests/test_lr_dirty_number_frozen_pins.py:37/44/51/62/72`、`tests/test_lr_list_coercion_twins.py:169` |
| 2 | `ReadingNote` → `models.py:135` | `(cls, data: Dict[str, Any]) -> "ReadingNote"` | 7 个 `.get`；3 处 `or`；**零强转、零拷贝**；`note_id`→`_new_id()`；`created_at`/`updated_at` 双 `_now_iso()` | `notes.py:157`、`tests/test_literature_review_models.py:92` |
| 3 | `ThemeCluster` → `models.py:167` | `(cls, data: Dict[str, Any]) -> "ThemeCluster"` | 5 个 `.get`；`list()` 拷贝×2；**无 id 生成器**；1 个 `_now_iso()` | `literature_review_panel.py:578/651`、`tests/…:104` |
| 4 | `GapAnalysis` → `models.py:195` | `(cls, data: Dict[str, Any]) -> "GapAnalysis"` | 7 个 `.get`；`float()`×1；`list()`×1；`gap_id`→`_new_id()`；`source` 缺→`"heuristic"`（**唯一带业务默认值的站点**） | `literature_review_panel.py:629/652`、`tests/…:117` |
| 5 | `LiteratureMatrix` → `models.py:227` | `(cls, data: Dict[str, Any]) -> "LiteratureMatrix"` | 3 个 `.get`；🔴 **唯一做「2 层深拷贝」的站点**：`cells={k: dict(v) for k, v in (data.get("cells") or {}).items()}`（:230）＋ `list()`×2；**无时间戳、无 id** | `literature_review_panel.py:480/612/650`、`tests/…:155` |
| 6 | `EvidenceRecord` → `src/literature/evidence_record.py:49` | `(cls, d: dict) -> "EvidenceRecord"` | 14 个 `.get`，🔴 **零 `or` 兜底、零 `list()` 拷贝** ⇒ `variables=d.get("variables", [])` **直接把调用方的 list 对象挂到实例上（别名）**；脏串不抛（无强转） | `evidence_record.py:150`（`json.loads` 后整体直转）、`tests/test_evidence_record.py:65/71` |
| 7 | `FigureEntry` → `src/utils/figure_collection.py:54` | `(cls, d: Dict[str, Any]) -> "FigureEntry"` | 🔴 **唯一含外部 I/O**：函数体内 `import plotly.io as pio` ＋ `pio.from_json(fig_json)`（:56-58）；id 缺→`str(uuid.uuid4())`（**不走共享 `_new_id`**）；`test_type` 缺→`"unknown"`、`title` 缺→`"未命名图表"` | `figure_collection.py:178` |
| 8 | `WorkspaceState` → `src/utils/workspace_state.py:115` | `(cls, data: Dict[str, Any]) -> "WorkspaceState"` | 🔴 **唯一"非 dict 不抛、返回空对象"**：`if not isinstance(data, dict): return cls()`（:116-117）；容错机制完全不同——走 `_safe_subset(cls, …)`×6 做 **dataclass 字段过滤**（:217-222，解的是"多余键 TypeError"，不是"缺键"） | `workspace_state.py:244`、`utils/workspace.py:698`、`tests/test_workspace_state.py:62/75/79`（:79 显式喂 `None`） |
| 9 | `Project` → `src/utils/project_manager.py:60` | `(cls, d: Dict[str, Any]) -> "Project"` | 🔴 **唯一必需键站点（严格契约）**：`id=d["id"], name=d["name"]` 裸下标 ⇒ 缺键抛 `KeyError`；余 3 键 `.get` | `project_manager.py:159`（在 `_read_index()` 的 `try` 内） |
| 10 | `FunnelBranch` → `src/upstream/topic_funnel.py:360` | `(cls, data: Dict[str, Any]) -> "FunnelBranch"` | 7 个 `.get`；**5 处 `or` 兜底**；3 个 dict 字段用 `or {}`；`branch_id`→本地 `_new_branch_id()`（:372，`uuid4().hex[:10]`，**与 models 的 `_new_id()` 是 `hex[:12]` 不同长**） | 🔴 **实测零调用侧**（`rg 'FunnelBranch\.from_dict|Branch\.from_dict' src/ tests/` ⇒ 无命中，rc=1）⇒ 见 §五.6"死反序列化器" |
| 11 | `PaperDiffSelectionState` → `src/ui/state_store.py:63` | `(cls, data: dict) -> PaperDiffSelectionState`（🔴 **唯一裸类名返回注解**；靠该文件 `from __future__ import annotations`（:8）才不炸） | 5 个 `.get`，零 `or`、零拷贝；两个 dict 字段 `data.get(..., {})` ⇒ **同样有别名面** | `state_store.py:79`（`get_diff_selection` 内，前置 `isinstance(raw, dict)` 守卫） |

### 机制分组（5 类，不是"1 类 11 份"）

| 机制 | 站点 | 特征 |
|---|---|---|
| M1 `.get` ＋ `or` 兜底 ＋ 类型强转 ＋ 防御性拷贝 | #1 LiteratureItem、#4 GapAnalysis、#10 FunnelBranch、#2 ReadingNote、#3 ThemeCluster | 仅 models 族＋funnel；强转/拷贝**逐站不同** |
| M2 `.get` 裸兜底（**无拷贝 ⇒ 别名**） | #6 EvidenceRecord、#11 PaperDiffSelectionState | 脏串不抛；容器字段与调用方共享 |
| M3 **必需键、抛 `KeyError`** | #9 Project | 🔴 承重的严格契约（§二） |
| M4 `_safe_subset` dataclass 字段过滤 ＋ 非 dict 返回空对象 | #8 WorkspaceState | 解"多余键"，别处解"缺键"——**问题域相反** |
| M5 含外部 I/O 反序列化 | #7 FigureEntry | 依赖 plotly |

⇒ **11 处只有 2 处（#2/#3）机制完全同类且字段数接近**，其余各带一条别人没有的语义。

---

## 二、逐条容错差异（决定"能不能收敛"的硬事实）

对同一份"坏输入"，11 处给出的**是三种互斥契约**，运行时实测：

| 输入 | #9 Project | #8 WorkspaceState | 其余 9 处（M1/M2/M5） |
|---|---|---|---|
| 缺必需键 | 🔴 **抛 `KeyError`** | 返回空对象/默认 | 返回默认值（静默补齐） |
| 喂 `None` | `TypeError: 'NoneType' not subscriptable` | ✅ **`return cls()`** | `AttributeError: 'NoneType' has no attribute 'get'` |
| 脏数字串（`year="约 2019"`） | n/a | n/a | #1 **抛 `ValueError`**；#6/#11 **静默留错类型** |
| 多余未知键 | 忽略（只读已知键） | ✅ 由 `_safe_subset` 过滤 | 忽略 |

**🔴 `Project.from_dict` 的 `KeyError` 是承重的，不是疏忽**：唯一调用侧 `project_manager.py:159` 位于 `_read_index()` 的 `try` 块内，而该 `except` 显式包含 `KeyError`（:160），命中后执行的是——

```
$ sed -n '150,172p' src/utils/project_manager.py
```
⇒ **把损坏的 `index.json` 改名隔离成 `index.corrupt.<时间>.bak`，再从 workspace 文件重建索引**（:163-168，注释还写明"隔离失败就抛出，防止后续 `create_project` 把唯一的损坏证据覆盖掉"）。

⇒ 若把 #9 收敛成"宽容助手"（`.get` 风格），**缺 id/name 的损坏索引会被静默读成合法 Project**，索引损坏检测当场失效 ⇒ 从"隔离＋重建"退化为"带着坏数据继续写"。**这是全 11 处里最不能碰的一处，且它的"容错口径不一致"恰恰是它的设计意图。**

---

## 三、"models.py 内部 5 处先收敛"这条局部案的前提实测

AST 提取 5 处的 13 项特征后逐列比对（复算：`PYTHONPATH=. .venv/Scripts/python.exe -B tmp/qoder-executor-20260925-0730-psy55/s64_probe.py`）：

| 特征 | LiteratureItem / ReadingNote / ThemeCluster / GapAnalysis / LiteratureMatrix | 一致 |
|---|---|---|
| 参数名 | data, data, data, data, data | ✅ |
| 必需键下标数 | 0,0,0,0,0 | ✅ |
| isinstance 守卫 | 0,0,0,0,0 | ✅ |
| `**` 解包 | 0,0,0,0,0 | ✅ |
| 外部 I/O | 0,0,0,0,0 | ✅ |
| 返回注解形态 | 5× 字符串引号式 | ✅ |
| **`.get` 次数** | **15, 7, 5, 7, 3** | ❌ |
| **int/float 强转** | **3, 0, 0, 1, 0** | ❌ |
| **list() 拷贝** | **2, 0, 2, 1, 2** | ❌ |
| **dict 拷贝/推导** | **0, 0, 0, 0, 1** | ❌ |
| **`or` 兜底数** | **7, 3, 3, 4, 3** | ❌ |
| **id 生成器** | **1, 1, 0, 1, 0** | ❌ |
| **时间戳生成器** | **1, 2, 1, 1, 0** | ❌ |

⇒ **全一致项只有 6/13，且 7 个不一致项全部是"语义载荷"（要补哪些默认值、要不要拷贝、要不要强转）**。一致的 6 项全是"形状无关"项（参数名/注解/守卫有无）。
⇒ 结论：**这 5 处不是"同一段代码抄了 5 遍"，而是"同一个套路写了 5 份不同的 schema"**。收敛成"私有公共解析"必须引入**逐字段 spec 表**（默认值/是否拷贝/是否强转/id 生成器），那已经是重写一个迷你 dataclass 反序列化层，**不是"抽公共函数"**。

---

## 四、收敛案与影响面

### 🔴 已运行时证成的合并退化（这条是本单最有价值的产出）

现状 #5 `LiteratureMatrix.from_dict` 对 `cells` 做 **2 层深拷贝**；`set_cell()`（:234-237）就地写 `self.cells[k][d]`。若换成"通用助手只做 `data.get(k, default)`"（即 #6/#11 的 M2 形态），实验读数：

```
$ PYTHONPATH=. .venv/Scripts/python.exe -B -c "
from src.literature_review.models import LiteratureMatrix
raw={'dimensions':['a'],'cells':{'k1':{'a':'v'}},'highlighted_keys':[]}
m=LiteratureMatrix.from_dict(raw); m.set_cell('k1','a','CHANGED')
m.dimensions.append('X'); m.highlighted_keys.append('Y')
print(raw)"
```
- **现状**：`raw` 逐字段不变 ⇒ 隔离成立（实测 `隔离OK = True`）。
- **naive 助手**（夹具类同构复现）：`raw2['cells']['k1']['a'] == 'MUTATED'`、`'POLLUTED' in raw2['dimensions']` ⇒ **调用方 dict 被就地污染**。
- 🔴 而 #5 的真实调用方是 `literature_review_panel.py:480/612/650`，传进去的是 **`lr_state.get("matrix")`（session_state 里的 dict 本体）** ⇒ 合并会把"改一个矩阵单元格"变成"直接写穿 session_state 原始 dict"，绕过 `to_dict()` 快照语义。**这是数据安全问题，不是风格问题。**
- 同理 #6 `EvidenceRecord`（`variables`/`measurement_tools`/`statistical_methods`/`tags` 四个 list 字段**无 `list()` 拷贝`**）已经处在 M2 别名形态 ⇒ **收敛若以 models 族为准，会顺手修好 #6；若以"最少改动"的统一助手为准，会把 models 族 5 处全部降级成 #6 的别名形态。** 方向不同，收益/风险完全反过来 ⇒ 必须逐站定 spec，无法一把梭。

### 案 A：全局统一助手（一个 `from_dict` 基类/mixin 管 11 处）

| 项 | 读数 |
|---|---|
| 涉及文件 | **7 个**（全部）＋新助手件 ⇒ ≥8 |
| 必须表达的语义维度 | ≥7（缺键默认 / `or` 兜底 / 类型强转 / list 拷贝 / dict 2 层拷贝 / id 生成器（**3 种不同实现**：`_new_id` hex[:12]、`_new_branch_id` hex[:10]、`uuid.uuid4()` 全串）/ 时间戳格式） |
| 🔴 不可跨越的阻塞 | #9 的 `KeyError` 必须**保留为抛错**（§二 承重）；#8 的问题域是"多余键"（`_safe_subset`）与其余 10 处相反；#7 必须留在能 `import plotly.io` 的位置 |
| 会打断的既有钉桩 | `tests/test_lr_dirty_number_frozen_pins.py`（s922-105，其 docstring 明写"修复落地后本用例应翻红，**禁止悄悄删桩**"）、`tests/test_lr_list_coercion_twins.py`（s922-106，docstring 明写"**只钉现状＋登记孪生漂移，不合并实现**……**合并属人工裁决**"）、`tests/test_workspace_state.py:79`、`tests/test_literature_review_models.py` 5 处 round-trip |
| 净收益 | 少 11 段样板；代价是把 3 种互斥容错契约压成一种 |

⇒ 🔴 **不推荐**。且**本族的合并问题此前已被两班显式判为人工裁决项**（s922-105/106 的 docstring 就是裁决记录），执行班不该重新起案。

### 案 B：不合并实现，只做「三件零风险整理」（推荐）

1. **B-1 统一签名注解**（纯注解、零行为）：把 #6 `d: dict`、#11 `data: dict` 的注解补成 `Dict[str, Any]`，#11 的裸返回注解 `-> PaperDiffSelectionState` 补引号或保留（该文件有 `from __future__ import annotations`，二者等价，但全仓另 10 处都用引号式）。涉及 2 文件；🔴 **注意 #11 在 `src/ui/state_store.py`，改动会进 UI 面门禁族视野**（纪律 §八：触及导出/新增 UI 入口需加跑 `download_buttons`/`export_gate`），建议只在无并发窗时做。
2. **B-2 逐站在 docstring 写死容错契约**：尤其给 #9 补一句「**缺 id/name 必须抛 `KeyError`：`_read_index()`（:160）以该异常作为索引损坏信号触发隔离重建，勿改成 `.get`**」——这一行注释能防掉未来最可能发生的误"收敛"。**零行为变更，收益最高的一条。**
3. **B-3 登记 `LiteratureMatrix` 的深拷贝不变量为门禁**：新增 1 例断言"`from_dict` 后 `set_cell` 不改调用方 dict"。属**纯增量 ＋1 例**（纪律 §五.4 允许），把 §四 的实测不变量从"恰好如此"升格为"钉住"。
4. 涉及文件：**2–3 个**（project_manager.py 注释 ＋ 新测试件；B-1 可选）。

### 推荐：**案 B（B-2 ＋ B-3 优先）**；案 A 不推荐落地

理由：① 容错契约有 **3 种互斥形态**，其中 #9 的抛错是**承重的数据恢复机制**（§二），#5 的深拷贝**已运行时证成为 session_state 隔离层**（§四）⇒ "收敛"在语义上不是同一件事的 11 次重复；② 11 处里 5 处的合并前提（"models 内部同构"）被 13 项特征实测否证为 6/13（§三）；③ 本族合并此前已被 s922-105/106 两班显式记为**人工裁决项**，且 `test_lr_list_coercion_twins.py` 的 docstring 就写着"不合并实现"；④ B-2/B-3 两条能拿到案 A 想要的全部可读性收益，零行为变更、零基线重钉。

---

## 五、需要主班裁决／待人工的出口

| # | 事项 | 为什么本单不做 |
|---|---|---|
| 1 | 案 A（全局助手）要不要做 | `tests/test_lr_list_coercion_twins.py` docstring 已写"**合并属人工裁决**"；`test_lr_dirty_number_frozen_pins.py` 的 A/B/C 修法"**尚未拍板**"且"禁止悄悄删桩"。本单不重开已归档裁决 |
| 2 | #6 `EvidenceRecord` 的 list **别名字段**（4 个容器字段无拷贝）是否要补 `list()` | 改它会改变"实例与调用方是否共享"的可见语义 ⇒ 属数据取舍，且 #6 唯一调用侧是 `json.loads` 直转（`evidence_record.py:150`），影响面小但要人点头 |
| 3 | B-1 触碰 `src/ui/state_store.py` | UI 面 ⇒ 纪律 §八 导出/下载/UI 入口门禁族；且 psy 当前有挂起在途件，**并发仓里不该动 UI 侧文件**。建议排无并发窗 |
| 4 | B-3 新增门禁测试件 | 本单被派为只读班；交写位执行 |
| 5 | 🔴 **红线自查**：本单 11 处均无统计阈值/凭据/资金/医疗内容，**未触发红线**。但 §四 的"脏数字 `int()` 强转是否该静默回退 0"这一支属 s922-05 系**数值处理口径**裁决，本单只登记现状、未判 | 纪律 §五.3 |
| 6 | 🔴 **`FunnelBranch.from_dict`（:360）是死反序列化器**：归档侧 `archive_current_branch` 只做 `history.insert(0, branch.as_dict())`（`topic_funnel.py:462`），而 `funnel_history` 全程以**裸 dict** 流转（`workspace_state.py:46` 声明 `List[Dict[str, Any]]`、`:144` 直取、`workspace.py:364` 直取、UI 经 `get_funnel_history`（`topic_funnel.py:421`）读裸 dict 给 `upstream_panel.py:681`）⇒ **没有任何路径把归档分支还原成 `FunnelBranch` 对象**。这不是风格问题：要么"修订选题后恢复旧分支"功能未接通，要么该助手可直接删 | 删代码＝减范围外文件；"功能未接通"是产品判断 ⇒ 交主班核需求后定 |

---

## 六、完成标准对照（逐条实测）

| 标准 | 读数 | 判定 |
|---|---|---|
| ① 档内 11 处与 `rg -n "def from_dict" src/` 实测一致（行号全列） | §一 表内 11 行号 = `rg` 11 条读数全集（models 64/135/167/195/227、evidence_record 49、figure_collection 54、project_manager 60、workspace_state 115、topic_funnel 360、state_store 63）；`rg -l \| wc -l` ⇒ **7 文件**（卷宗"8 文件"否证） | ✅ |
| ② 每处容错行为有代码证据行 | §一"容错契约"列每条都带源码行号（如 #9 `d["id"]`→:62、#8 守卫→:116-117、#5 深拷贝→:230、#7 I/O→:56-58），并由 §一末 AST 特征表（`.get`/强转/拷贝/`or` 计数）给出机器读数 | ✅ |
| ③ 零代码改动 | `git diff --name-only` 对 7 个涉事文件逐件点名 ⇒ 0 行（见 result「验收情况」③） | ✅ |
| ④ 推荐案含影响面估算（涉及文件数） | 案 A：**≥8**（7 涉事文件＋新助手件）；案 B：**2–3**。均含打断钉桩清单与阻塞点 | ✅ |

**口径说明（调用侧已逐站坐实，无留白）**：调用面反查读数——`rg -c '\.from_dict\(' src/` 合计 **16 行**（全部是真实调用）、`tests/` 合计 **19 行**，其中 **3 行是 docstring 里的自述引用**（`tests/test_lr_list_coercion_twins.py:6/8/10`）⇒ 测试真实调用 16 处。11 站的归位见 §一"调用侧"列。
其中 **#10 `FunnelBranch.from_dict` 实测零调用点**（`rg 'FunnelBranch\.from_dict|Branch\.from_dict' src/ tests/` ⇒ 无命中、rc=1）⇒ 升为一条独立发现，见 §五.6。
⇒ 本单**不以任何"未追至"名义留白**。
