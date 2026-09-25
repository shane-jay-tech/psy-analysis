# psy 数据字典 v1 · 题号／变量名／量表／维度／量尺／反向题／缺失值编码

- 信箱单：`20260925-120655-d598`（风险档 B／工作类型 docs）
- 执行班：`qoder-executor-20260925-1300-psy67`，2026-09-25
- 字典版本：**`psy-analysis/codebook/v1`**（单一事实源：`src/questionnaire/data_dictionary.py:CODEBOOK_VERSION`）
- HEAD 基线（改前取证钉短号，非 `HEAD:`）：**`fe763a4`**

> 🔴 **本字典只统一"字段怎么书写"，不统一任何统计数值。**
> alpha／omega／项目数／样本量／效应量／置信区间的数值一律不经此模块，
> 本模块也不改写数据取值（缺失值编码只被**报告**，不被静默替换）。

## 一、七族字段的规范书写（v1）

| 族 | 字典里的规范字段 | 类型 | 唯一性 | 改前的现存载体与书写（实测） |
|---|---|---|---|---|
| 题号 | `item_no` | `str`，字面量原样（`"Q3"`） | 全字典唯一 | `ItemsDoc.items` 是**题干文本列表**，没有题号字段；题号只以"下标"隐式存在 |
| 变量名 | `var_name` | `str`，等于导入文件的列名 | 全字典唯一 | `ScaleDimension.items: list[str]`、`questionnaire_schema.json` 的 `"Q1"…"Q10"` |
| 量表 | `scale` | `str`（量表名） | 可重复（一份字典可含多量表） | `item_templates.ALL_TEMPLATES` 五套模板名；`construct_kb.CONSTRUCTS` 的构念名 |
| 维度 | `dimension` | `str` | 同一变量名只能属一个维度 | `ScaleDimension.name`；`construct_kb` 里 `dimensions: [{name, desc, item_count}]` |
| 量尺 | `scale_min` / `scale_max` | `int \| float` | — | `ScaleDimension.min_score/max_score`（默认 1/5）；`item_templates` 的 `anchors_5/anchors_7` |
| 反向题 | `reverse` | `bool`（题目级属性） | — | **两套并存**：`ItemsDoc.reverse_indices: List[int]`（实测 0 基，见 C2）与 `ScaleDimension.reverse_items: list[str]`（列名） |
| 缺失值编码 | `missing_codes: tuple[str, …]` | 字面量字符串，逐列声明 | 不得与量尺合法取值重叠 | **导入侧完全缺失**：`src/**.py` 无 `na_values`／`variable_missing` 声明（见 C4） |

非题目列另立一类，显式标 `role ∈ {demographic, metadata, timestamp}`，避免与题项混桶（见 C5）。

## 二、唯一键规则

1. **主键 `var_name`**：全字典唯一；既是导入列名也是分析引用名。
2. **副键 `item_no`**：全字典唯一；与 `var_name` 一一对应（适配器里默认同值）。
3. `var_name` 不得同时出现在题项集与非题目集（`E_ROLE_CLASH`）。
4. 同一 `var_name` 挂到两个维度即冲突（`E_MULTI_DIM`）——计分时的重复计入是静默的，字典层面先禁止。
5. 冲突清单**由 `Codebook.conflicts()` 机器生成**，不靠人抄；错误码集合：
   `E_VERSION` / `E_DUP_KEY` / `E_MULTI_DIM` / `E_ROLE_CLASH` / `E_REVERSE_FLAT` / `E_SCALE_RANGE` / `E_MISSING_AMBIGUOUS`。

## 三、冲突清单（改前实测，逐条给读数）

取证脚本：`D:\code\tmp\qoder-executor-20260925-1300-psy67\probe_d598_dictionary.py`
（只读；未打开 `data/` 任何文件；`data/literature_feed` 开工读数 **181 件／21,059,126 B**）

| # | 冲突 | 实测证据 | 严重度 |
|---|---|---|---|
| C1 | **字典无版本键**：现存最像字典的载体 `demo_projects/psychology_questionnaire_demo/questionnaire_schema.json` 顶层键只有 `title/description/dimensions/demographics/metadata/invalid_detection` | 探针 P5：`含 'version' 键 ? False` | 高 |
| C2 | **反向题两套书写**：题目解析面是 `List[int]`，计正面是 `list[str]` 列名，靠人换算。下标实测为 **0 基**（`items_loader.py:397` `reverse_indices.append(len(items) - 1)`；探针 P2 输入第 2 题标"（反向题）"→ 读出 `[1]`） | 探针 P2：`ItemsDoc.items 类型 = ['str','str']`、`reverse_indices = [1]` | 高 |
| C3 | **题号无显式字段**：`ItemsDoc` 只有题干列表，题号=列表位置；一旦上游删题，"第 3 题"的含义随之漂移 | 探针 P1 声明清点：`items: List[str]`，无 `item_no` | 中 |
| C4 | **缺失值编码在导入侧不存在**：`load_csv` 用 pandas 默认 NaN，未传 `na_values`；`load_spss` 只应用值标签、**不读** pyreadstat 的用户缺失范围 | 探针 P3：`src/**.py` 中 `na_values/missing_ranges/user_missing/-9xx` 命中 13 处，**全部落在 `experiment_templates.py`／`literature_*`／`construct_kb.py` 等无关件**，`src/data/loader.py` 0 处；`load_spss 是否读 missing 元数据: False` | 高 |
| C5 | **未知字段不被拒绝，反被静默并入人口学桶**：`classify_columns` 的 `else` 分支把不认识的列一律塞进 `demographic_columns` | 探针 P4：输入含 2 个"没人认识"的列 ⇒ `demographic_columns = ['Q2', 'totally_unknown_field_xyz']`、`未识别列（不在任何桶里）= []`、"静默归入且无告警"= `True`。同一探针还实测到 `Q2`（3 行取值 2/2/2）被判为**人口学列**、`另一列没人认识`（整数 1/2/3）被判为**题项列**——分桶判据是"唯一值个数 2–10 且落在 0–10"，与字典无关 | 高 |
| C6 | **越界反向题无人查**：`compute_dimension_scores` 对 `item not in df.columns` 直接 `continue`，反向清单里写了不存在的列时静默漏计 | 读源码 `import_cleaning.py:119-125`；探针 P5 对现存 demo 实测 `反向题越界=[]`（**现存实例恰好干净**，不能反推有校验） | 中 |
| C7 | **缺失值编码与真实作答可重叠**：字典层面允许写出 `missing_codes=("3",)` 这种落在 1–5 量尺内的编码 | 新增用例 `test_missing_code_inside_scale_range_is_ambiguous` 断言其被报为 `E_MISSING_AMBIGUOUS` | 中 |

> C7 是**字典自身**的口径风险（防止新写错），非现存数据缺陷；C1–C6 是改前既有实况。

## 四、"数据导入可依据字典拒绝未知字段"的契约与落地边界

契约（已在 `src/questionnaire/data_dictionary.py` 实现并由测试驱动）：

```
Codebook.reject_unknown_fields(df, strict=None) -> (df[仅含已声明字段的列], 未知字段清单)
  · unknown_field_policy="reject"（字典默认）⇒ 命中未知字段即抛 UnknownFieldError，
    异常文本列出未声明字段名并带字典版本号；
  · "report" 或非 strict ⇒ 返回 (裁剪后的 df, 未知清单)，交调用方决定；
  · 两条路径都只作用于**列面**：行数与单元格取值一字不动（用例断言 df.equals(before)）。
Codebook.find_missing_code_hits(df) -> {var_name: {编码: 次数}}   # 只报告，不改写
```

**未接线面（本班故意不做，交回主班裁）**：`src/ui/questionnaire_import_panel.py:_render_upload`
今天走裸 `pd.read_csv(uploaded)`，`import_cleaning.classify_columns` 的宽松分桶仍在原位。
把字典接到这两个入口会改变"哪些列进入计分"，从而可能改变**样本量与项目数**的读数——
这属统计数值口径，不在 docs 单授权内。两条出口：

- 方案 甲：新增 `strict` 开关（默认关），UI 上多一个入口 → 触"新增入口"面；
- 方案 乙：把 `classify_columns` 的 `else` 桶从"并入人口学"改为"未声明清单" → 改变既有分桶口径，
  需先重取 `tests/test_questionnaire_import_cleaning.py` 与 e2e 族的在册数。

## 五、复算命令（逐条可跑）

```
# 1) 探针（只读，仓外临时目录）
cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe \
  D:/code/tmp/qoder-executor-20260925-1300-psy67/probe_d598_dictionary.py   # rc=1 仅因 P6 子进程段，P1–P5 读数已完整输出

# 2) 字典用例
cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe \
  -m pytest tests/test_questionnaire_data_dictionary.py -q                 # 18 passed / rc=0

# 3) 门禁面（按件点名，不用宽 -k）
... -m pytest tests/test_skip_gates_are_explained_and_not_misjudged.py \
      tests/test_export_gate_global_scan.py -q                             # 1 failed / 19 passed / rc=1
      # 唯一红：test_all_download_buttons_accounted_for，offender 仍只有 src/ui/questionnaire_panel.py（在册红，红名集未扩大）

# 4) 不变量（开工＝收工）
python -c "import os;r='data/literature_feed';print(sum(1 for _,_,f in os.walk(r) for _ in f), sum(os.path.getsize(os.path.join(d,f)) for d,_,fs in os.walk(r) for f in fs))"
```

## 六、字典 v1 的变更约束（给后续班）

1. 加字段族先加"规范字段名＋类型＋唯一性"三行，再谈代码；
2. `missing_codes` 只在字典层声明，替换动作留在清洗层并写进日志；
3. 反向题**新代码一律用 `reverse: bool`**，不得再引入下标形态；
4. 升版本改 `CODEBOOK_VERSION` 与 `SUPPORTED_CODEBOOK_VERSIONS` 两处，`E_VERSION` 是兼容性的唯一闸。
