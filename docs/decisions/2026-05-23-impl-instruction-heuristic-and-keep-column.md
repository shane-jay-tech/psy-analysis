# 题目解析器：指导语启发式 + UI 删除列（v4.5）

- **日期**：2026-05-23
- **范围**：`src/questionnaire/items_loader.py` 段落兜底分支 + `src/ui/items_upload_panel.py` 第 2 步表格
- **协作模式**：单架构师直写
- **关联**：[v4.1 上传题目](2026-05-23-impl-questionnaire-upload.md)

## 起因

用户反馈：

> 在自动解析题目的时候会把我的一些指导语识别成题目，并且我还无法删去，更新一下

两个问题叠加：

1. **解析侧假阳**：v4.1 段落兜底（无编号、无 bullet）的指导语过滤只看了一条窄正则
   `^(指导语|说明|填写说明|请阅读|请根据|背景信息)[:：]?`，
   像「本问卷不涉及对错」「亲爱的同学」「感谢您的参与」「测验题目用于评估……（80+ 字长段）」全漏。
2. **UI 侧没出口**：第 2 步 `st.data_editor` 虽然 `num_rows="dynamic"`，
   但对 streamlit 不熟的用户不知道怎么删行——右键菜单要选中行 + 按 Delete，发现路径太隐蔽。

## 决策

两侧都改。**解析侧拓宽过滤**，**UI 侧加显式删除列**——双保险，互不依赖。

### 解析侧：`_looks_like_instruction(s)` 三路启发式

替换 `_parse_text` 段落兜底分支里那条窄正则：

```python
_INSTRUCTION_PREFIXES = (
    "指导语", "说明", "填写说明", "请阅读", "请根据", "请仔细", "请按",
    "请您", "请就", "请在", "请于", "请如实",
    "背景信息", "答题方式", "作答方式", "评分方式",
    "注意事项", "本问卷", "本调查", "本研究", "本量表",
    "为了", "欢迎", "感谢", "亲爱的", "尊敬的", "敬启者",
    "您将", "您好", "下面", "以下", "如下",
)

_INSTRUCTION_KEYWORDS = (
    "无对错", "保密", "匿名", "不涉及对错", "无标准答案",
    "您的回答", "您的答复", "您的真实", "如实作答", "如实填写",
    "回答均无对错", "结果仅用于", "用于学术研究", "答题须知",
    "保护您的隐私", "感谢您的", "请您仔细",
)

_INSTRUCTION_LONG_LEN = 40

def _looks_like_instruction(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    for p in _INSTRUCTION_PREFIXES:
        if s.startswith(p):
            return True
    if len(s) >= 80:
        return True
    if len(s) >= _INSTRUCTION_LONG_LEN:
        for kw in _INSTRUCTION_KEYWORDS:
            if kw in s:
                return True
    return False
```

三条独立路径任一命中即算指导语：

1. **强信号前缀**：30 个常见行首词，命中即过
2. **长行 + 弱信号**：≥ 40 字 且 含 17 个关键词之一
3. **超长行**：≥ 80 字一律视为指导语（典型 Likert 题干很少这么长）

**只在段落兜底分支用**——编号题、bullet 路径不参与（编号路径下指导语有结构边界，不需要启发式）。

被过滤掉的行进 `instructions` 字段（用现有的「标题后到第一题前」回填逻辑捎带）。

### UI 侧：第 2 步加 `保留` CheckboxColumn

```python
df_items = pd.DataFrame({
    "保留": [True] * parsed_doc.n_items(),
    "题号": [...],
    "题干": parsed_doc.items,
    "反向": [...],
})
```

加在最左边，默认全选。用户取消勾选 → 该行直接从最终 `items_now` 里去掉。

行迭代从 `itertuples` 改成 `iloc[i]` + `row.get("保留", True)` 过滤；底部加 caption「🗑️ 已移除 N 行」反馈。

caption 文案同时点出两条删除路径，让用户挑：

> 取消勾选「保留」即从问卷中删除该行；也可以右键单元格 → Delete row 或选中行后按 Delete 键。

### 双保险的逻辑

- **第一道防线（解析侧）**：常见指导语在落到 editor 之前就已经被剔除 → 默认情况下用户什么都不用做
- **第二道防线（UI 侧）**：解析漏网的（启发式总有边界），用户在表格里取消勾选即可 → 不需要回去改原文件再传

启发式必然有假阳/假阴。**靠 UI 侧的 `保留` 列兜底**比把启发式调到 100% 准确更现实。

## 测试

`tests/test_items_loader.py` 新增 `TestInstructionHeuristic` 7 个：

- `test_known_prefix_filtered_into_instructions`：「指导语：」开头被过滤进 instructions
- `test_long_text_with_keyword_filtered`：「本问卷不涉及对错……」长指导语过滤
- `test_super_long_line_filtered_even_without_keyword`：80+ 字长段（不命中前缀和关键词）独立路径生效
- `test_multiple_instruction_prefixes`：感谢/欢迎/答题方式/亲爱的 都被过滤
- `test_instruction_does_not_eat_real_short_items`：「我感到放松」等真短题干不被误杀
- `test_numbered_path_unaffected_by_heuristic`：编号题路径不动启发式
- `test_empty_after_filter_falls_through`：全是指导语 → ValueError

全量回归：**1260 passed / 4 skipped**（baseline 1253，0 新失败）。

## 风险与权衡

- 启发式是黑名单 + 长度阈值，**必有假阳**：
  - 「下面我感到紧张」（"下面"前缀）会被过滤——但这种题干极少
  - 80+ 字的极长 Likert 题干也会被吞——可能在临床量表的复合题里出现
- **靠 UI 兜底**：`保留` 列让用户在表格里看到结果再修，不需要让启发式准到 100%
- 编号题路径完全不动——避免误伤「本问卷不涉及对错（这一行在编号路径下应进 instructions）」这类正常情况

## 追加：题号自动补位 + 映射展示

用户进一步反馈：

> 解析题目错的会导致和我粘贴导入的题目题号对不上，我删了之后自动补位

**逻辑层面早就是补位的**——`items_now` 是过滤后的列表，`current_doc.items` 索引连续，下游 `_render_dimension_editor` 用 `current_doc.n_items()` 生成默认值 `1..N`。问题是 UI 没把这个事实展示出来，用户在第 2 步表格里看到的「题号」列还是原始解析序号 1..parsed_doc.n_items()，会困惑。

修复（不改逻辑，只改 UI）：

1. **「题号」列改名「原题号」**（disabled），column help 解释「解析时的原始序号；删除后下游按最终题号 1..N 连续编号」
2. **第 2 步 caption 加显式说明**：「🔢 删除后题号自动补位：剩余题目会重新连续编号 1, 2, 3...」
3. **删除发生时显示映射表**：用 expander 展示「原题号 → 最终题号 → 题干预览」对照，用户能直观看到哪行删了、剩下的题号是什么
4. **维度编辑器 caption 同步**：「这里的题号 = 第 2 步删除后自动补位的连续编号 1..N」

实现要点：
- 复用现有迭代循环，把 `mapping_rows` 一次性构建好——已删除的行也进 mapping，最终题号显示「—（已删除）」
- 不改下游接口（`current_doc.n_items()` 和 `current_doc.items` 索引一直是连续的）
- 全量回归仍 **1260 passed**（修改是纯 UI，不影响测试）

## 不在本期

- 启发式不学习用户的勾选行为（无持久化「该过滤的没过滤」反馈通道）
- 未在 `.docx` 路径下加 paragraph 级 style heuristic（用户当前都是 .md/.txt）
- 题号映射目前是只读展示——没做「按最终题号反查原行」的搜索框（必要性不强）
