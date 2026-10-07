# 块级依赖闭包精确化（s1007-29，AST 作用域分析）

- 日期：2026-10-08 ｜ 上游：s1004-07 遗留 1（「随搬移启动时的实施单做」）
- 性质：**分析单零改码**——搬移（降栈）未启动（app.py 分支现值 :1570-2425＝856 行，较矿源 760 行 +96 行在册期自然演进；窗界 :1570 elif 问卷／:2330 elif 论文），「搬移面 diff」不适用，本档交付精确闭包供搬移启动时直接取用

## ①AST 作用域分析结果（阶段 1 三接线块）

| 块 | 现值位 | 行数 | reads（精确闭包） | writes | session_state/workspace 闭包 | 判定 |
|---|---|---|---|---|---|---|
| upload_items | :1592-1599 | 8 | `_q_sub_class`／`render_items_upload_panel`／`st` | ∅ | **无** | 纯转发实锤 |
| import_clean | :1596-1599 | 4 | `_q_sub_class`／`render_questionnaire_import_panel`／`st`（`st.session_state` 显式实参） | ∅ | **无**（仅实参传入） | 纯转发实锤 |
| settings_sidebar | :1603-1605 | 3 | `render_settings_sidebar_panel`／`st`（同上） | ∅ | **无**（仅实参传入） | 纯转发实锤 |

- 三块 imports 各自就地延迟（items_upload_panel:1593／questionnaire_import_panel:1597／settings_sidebar_panel:1603），搬移时随块走即可。
- **保守全闭包（s1004-07 口径）≈26 名**（session_state 20 键＋df/meta/inspector/file_name/analysis_history＋分支局部）；阶段 1 精确闭包＝**每块 ≤3 名且零写**——搬移阶段 1 可按块独立执行，无需整体闭包随行，机械搬移结论由「推测」升「AST 实证」。

## ②分析脚本（搬移启动时重跑用； app.py 行号以当时 grep 分支窗为准）

```python
import ast
src = open('app.py', encoding='utf-8').read(); tree = ast.parse(src)
branch = None
for n in ast.walk(tree):
    if isinstance(n, ast.If) and isinstance(n.test, ast.Compare):
        c = n.test
        if isinstance(c.left, ast.Name) and c.left.id == 'mode' and any(
                isinstance(x, ast.Constant) and '问卷设计' in str(x.value) for x in c.comparators):
            branch = n
for n in ast.walk(branch):
    if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and isinstance(
            n.test.left, ast.Name) and n.test.left.id == '_q_sub_class':
        reads, writes = set(), set()
        for x in ast.walk(n):
            if isinstance(x, ast.Name):
                (writes if isinstance(x.ctx, ast.Store) else reads).add(x.id)
        print(n.test.comparators[0].value, n.lineno, n.end_lineno,
              sorted(reads), sorted(writes))
```

## ③搬移面 diff

不适用（降栈启动属行为单另裁，矿源原口径；本档即启动时实施单的输入件）。

## 复现

```
$ grep -n 'elif mode' app.py        # 窗界 :1570 问卷／:2330 论文
$ python ②脚本                       # 三块 reads/writes 现取
```
