# error_messages.py 特征化测试（916p-a4-004，2026-09-17，只增测试）

## 验证（命令与数字同段）

```
$ .venv\Scripts\python.exe -m pytest tests/test_error_messages.py -q
12 passed in 0.65s
$ rg -c "def test_" tests/test_error_messages.py → 12（=passed 数）
$ git diff --stat -- src/ → 仅班前既有 lock_manager.py（a4-003 已盘点归属，本班零新增 src 改动）
```

## 符号清单（10 个顶层公开符号）

| # | 符号 | 行号 | 类型 |
|---|---|---|---|
| 1 | UserFriendlyError | :15 | dataclass（what/why/impact/actions/severity） |
| 2 | UserFriendlyError.to_markdown | :23 | 方法（四小节＋顺序编号） |
| 3 | UserFriendlyError.to_streamlit_dict | :34 | 方法（{type,title,detail}） |
| 4 | table_generation_failed | :44 | 模板（warning） |
| 5 | privacy_precheck_blocked | :59 | 模板（error，examples 前 3） |
| 6 | llm_unavailable | :77 | 模板（warning，4 actions） |
| 7 | pdf_unavailable | :93 | 模板（info） |
| 8 | cfa_sem_not_converged | :108 | 模板（默认 reasons 兜底） |
| 9 | next_steps_empty | :125 | 模板 |
| 10 | export_missing_dependency | :140 | 模板（missing 入文案） |
| 11 | format_error_for_streamlit | :157 | 函数（返回 str） |

## 用例 ↔ 断言面（12 用例，≥10 达标）

| # | 用例 | 口径来源 |
|---|---|---|
| 1 | 默认 severity=error＋必填字段 | :19 |
| 2 | to_markdown 四小节＋1.2.3. 编号＋行数=4+n | :23-32 |
| 3 | to_streamlit_dict 键集/type 跟随 severity/detail==to_markdown | :34-40 |
| 4 | table_generation_failed：warning＋reason 入 why＋3 actions | :44-57 |
| 5 | privacy_precheck_blocked：error＋examples 前 3 截断＋阻断在 impact | :59-75 |
| 6 | llm_unavailable：warning＋reason 入 why＋4 actions | :77-91 |
| 7 | pdf_unavailable：info＋LibreOffice 建议 | :93-106 |
| 8 | cfa_sem_not_converged：默认 reasons 兜底＋自定义 reasons | :108-123 |
| 9 | next_steps_empty：actions 非空 | :125-138 |
| 10 | export_missing_dependency：missing 入文案 | :140-155 |
| 11 | format_error_for_streamlit 返回 str | :157-160 |
| 12 | 空串/引号/emoji 特殊字符不抛异常 | 全文件容错现状 |

## 观察（不修）

模板文案质量良好（what/why/impact/actions 四段式一致）；pdf_unavailable 为唯一 info 级模板。src/ 零改动（班前 lock_manager.py M 项属 a4-003 已盘点的在途文件，与本班无关）。

## 验收对照

- ✅ passed 12 ≥10 且 =def test_ 计数（两者同段）。- ✅ git diff --stat -- src/ 的非空内容为班前既有项，本班零新增。- ✅ 新增项仅 tests/test_error_messages.py＋报告。- ✅ 未 import 私有函数；不联网；不 push。
