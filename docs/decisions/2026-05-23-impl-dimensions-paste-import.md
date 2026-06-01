# 维度编辑器加"粘贴自动导入"（v4.4）

- **日期**：2026-05-23
- **范围**：新增 `src/questionnaire/dimensions_paste_parser.py`；`src/ui/items_upload_panel.py::_render_dimension_editor` 顶部加 expander
- **协作模式**：单架构师直写
- **关联**：[v4.2 维度评分](2026-05-23-impl-ai-review-dimensions.md)

## 起因

v4.2 落地后用户反馈：维度多了之后，在 `st.data_editor` 里一行行敲太累——
他平时已经用 Markdown / Excel 写好了维度清单，希望粘贴一下就自动导入到表里，看到不对的再调。

## 决策

新增独立解析模块 + UI 上方加粘贴 expander。**只解析不强校验**——所有错误降级为 warnings，让用户在表格里继续修。

### 解析模块 `dimensions_paste_parser.py`

```python
parse_dimensions_text(text: str, n_items: int)
    -> Tuple[Optional[pd.DataFrame], List[str]]
```

返回 4 列 DataFrame（与 `_render_dimension_editor` 列名严格对齐）+ warnings 列表。

#### 支持的 4 种格式（按检测优先级）

1. **Markdown 表格**
   ```
   | 维度名 | 维度定义 | 题号 | 备注 |
   | --- | --- | --- | --- |
   | 上级互动 | 在上级面前的紧张感 | 1,2 | |
   ```
   自动跳分隔行 / 表头行。

2. **Tab 分隔**（直接从 Excel/Notion 复制）

3. **段落键值**
   ```
   上级互动
   定义：在上级面前的紧张感
   题号：1, 2
   备注：本研究创新
   ```
   也认 `上级互动（在上级面前的紧张感）` 这种括号内联定义。

4. **CSV** 兜底

#### 题号字段宽容解析

- 半/全角逗号、顿号：`1,2,3` / `1，2，3` / `1、2、3`
- 范围：`1-3` / `1~3` / `1～3`（倒序也认）
- 题号前缀：`题1` / `Q1` / `第1题`（前缀剥离）
- 越界 / 重复 / 跨维度冲突 → warning 而不是 error

### UI 接入

`_render_dimension_editor` 顶部加一个折叠 expander：
- text_area + 「📥 解析并导入到下方表格」按钮
- 点击后 `parse_dimensions_text` → 写入 `session_state["_items_dim_editor_rows"]`
  → **同时 pop 掉 `items_dim_editor`**（widget 内部 state）→ `st.rerun()`
- 不 pop 的话 streamlit data_editor 会用 widget state 盖住新的默认值，导入看似无效
- 「🗑️ 清空表格回到一行」按钮：双 pop

### 与下游的衔接

解析后的 DataFrame 形状和原 data_editor 完全一致，所以：
- 下方 data_editor 直接接住，用户继续在表格里编辑
- 既有的 `_render_dimension_editor` 校验逻辑（题号越界 / 重复归属 / 缺定义）原样复用
- 解析器和 editor 内的校验**重叠**——这是有意的：解析器友好兜底，editor 严格把关

## 测试

`tests/test_dimensions_paste_parser.py` 31 个测试：

- `parse_indices_text` × 14：4 种分隔符、范围、题号前缀、去重、越界、倒序
- Markdown 表格 × 3：含/不含表头、3 列也行
- Tab 分隔 × 2：含表头自动跳过
- CSV × 1：题号字段加引号
- 段落 KV × 3：典型格式、括号内联、`1.` 编号前缀剥离
- 错误处理 × 6：重复归属（先到先得）、重名（丢后者）、空名跳过、越界 warning、空文本、垃圾文本
- DataFrame 形状 × 2：列名严格对齐、attrs 记录解析器

全量回归：**1253 passed / 4 skipped**（baseline 1222，0 新失败）。

## 风险与权衡

- 段落 KV 格式的"括号内联定义"启发式可能在题目本身名字带括号时误拆——但维度名带括号的情形很少；且用户能看到表格立即修
- 多维度模式的 used_indices 是"先到先得"——解析器和 editor 校验都是这个语义，与 v4.2 一致
- 解析器对"垃圾文本"会兜底为 1 行（first cell 当维度名），加 warning。这比直接 None 更友好，让用户至少看到结构

## 不在本期

- 解析器不支持反向：用户编辑完表格 → 反向导出文本（用户没要）
- 不解析 reverse 标记（反向题信息属于「第 2 步：编辑题目」，与维度归属正交）
