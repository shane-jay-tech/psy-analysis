# AI 题目预审增加"分维度评分"模式（v4.2）

- **日期**：2026-05-23
- **范围**：`ai_content_review` + 上传题目面板的 UI
- **协作模式**：单架构师直写（well-bounded scope）
- **关联**：[v4.1 上传工作流](2026-05-23-impl-questionnaire-upload.md)

## 起因

v4.1 落地后用户问：构念名 / 构念定义是不是只能填**最顶层那一个**？
如果他往下拆维度并融合了别的理论、还创新了一些维度怎么办？

确认现状：是的，旧版只能传一个 `construct_name + construct_definition`，
4 位 AI persona 把全部题目都对齐到这一个定义打分。这会让：
1. 子维度题目用顶层定义判断，粒度粗
2. **创新/融合维度**的题目反而被判低分——因为超出经典定义边界

## 决策

后端加可选 `dimensions` 参数，UI 加 checkbox 启用"分维度评分"。

### 后端 `ai_content_review`

新签名（向后兼容）：

```python
ai_content_review(
    items, construct_name, construct_definition,
    *,
    dimensions: Optional[List[Dict]] = None,
    ...
)
```

`dimensions` 每条 dict：

```python
{
    "name": str,            # 维度名
    "definition": str,      # 维度定义
    "item_indices": List[int],  # 0-based 题号
    "note": str,            # 可选（如"本研究创新"）
}
```

校验：维度必须有 name + definition；题号不能越界、不能重复归属、不能重名。

启用维度模式时 prompt 改写：
- 顶部列出**所有维度结构 + 各自定义**
- 每道题前缀 `[维度名]`
- 评分依据从"对总构念"切到"对所属维度"
- 显式提示："若维度是融合多理论或本研究创新提出，按维度定义本身判断契合度，
  不要因超出经典构念边界扣分"

### 输出新增

`AIItemReviewResult` 多两个字段：
- `dimensions`：原 payload 回传
- `dimension_summary`：DataFrame，每维度一行（题数 / 维度均分 / 标记题数 / 定义 / 备注）

`items_table` 在维度模式下多一个"维度"列。Markdown 报告多一节"维度级摘要"。

### UI（`items_upload_panel.py`）

第 3 步 AI 预审板块加 checkbox：「📐 分维度评分」。

启用后展示一个 `st.data_editor`：

| 维度名 | 维度定义 | 题号（1-based，逗号分隔） | 备注（如：本研究创新） |
| --- | --- | --- | --- |

- 1-based 输入更符合用户直觉，进 backend 前转 0-based
- 中英文逗号都接受
- 部分归属允许：未归属题目按"未分配"处理并提示

按钮触发前会做和后端一致的预校验，避免提交后才报错。

## 测试

`tests/test_ai_content_review.py` 新增 8 个测试：

1. prompt 注入维度结构 + 题目前缀 + 创新提示语
2. dimension_summary 聚合（题数、均分、标记题数）正确
3. 重复归属 → ValueError
4. 越界 → ValueError
5. 缺 name → ValueError
6. 重名 → ValueError
7. 不传 dimensions → 旧形状（无"维度"列、无 summary）
8. 部分归属 → "未分配"标签

文件级：`13 passed`（5 旧 + 8 新）。
全量回归：**1208 passed / 4 skipped**（baseline 1200，0 新失败）。

## 风险

- 增加了 prompt 长度。维度多 / 题目多时单次调用 token 上升，但仍远低于上下文窗口。
- 维度模式仍是"AI 模拟"——多 persona 同模型评分相关接近 1.0，
  即使加了维度也**不**变成正式 CVI。UI 已在两层（顶部 warning + 报告 disclaimer）标注。
- 部分归属是**允许**的（不是 error），用户可能误以为"全归属"是必填。
  通过 `st.info` 显示"x/n 已归属"提示。
