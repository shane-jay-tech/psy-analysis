# 文献面板抛 ProjectLockedError 契约材料（2026-09-12 夜间执行班，任务 p911r-34，零实现）

> 执行：GLM-5.3-Flash 夜间执行班 sweep-20260911-2300。**本单只出契约材料，未写实现；未 commit/push。**
> ⚠️ **前提张力（必须先读）**：`src/ui/literature_review_panel.py:86-90` 的 dab0 注释已明确分层决策——「bool 返回契约保留——SessionLock 为 streamlit 会话咨询锁，**异常路径（ProjectLockedError）属跨进程 project_lock 职责**，两者提示同源、机制分层」。本任务要求的「改抛 ProjectLockedError」与该分层决策存在冲突，材料如实呈现两面，拍板优先。

## 一、调用点表（3 处）

| # | 调用点（文件:行号） | 当前行为 | 改抛 ProjectLockedError 后行为 |
|---|---|---|---|
| 1 | `src/ui/literature_review_panel.py:76` `_check_lock_or_warn`（helper 本体） | 查 `SessionLock`（会话咨询锁）：被他人占用 → `st.warning(locked_user_prompt(...))` + 返回 False；空闲 → `lock.acquire(TTL 30s)` + 返回 True | 改为：被占用 → `raise ProjectLockedError(lock_path=?, holder_pid=?, holder_since=?)`；注意 ProjectLockedError 构造参数是**跨进程锁语义**（lock_path/pid），会话咨询锁并无 pid/lock_path——需再造参数或换异常类（见拍板 1） |
| 2 | `:456` 保存笔记（`_LR_NOTES_LOCK`） | `if _check_lock_or_warn(...): create_note(...)`——bool False 时静默跳过（警告已由 helper 显示） | 需 try/except ProjectLockedError → `st.error(...)` 后跳过；漏包则异常沿 Streamlit 冒泡为整页报错 |
| 3 | `:500` 一键自动填充（`_LR_MATRIX_LOCK`） | 同上 bool 契约 | 同上，需逐点包 except |

（关联调用面：`app.py:956`、`app.py:2644` 引 `render_literature_review` 入口；`tests/test_concurrency.py:123,132,139` 直接 import `_check_lock_or_warn` 并按 **bool 契约**断言——契约变更会连带测试改写。）

## 二、改动契约

1. **异常语义**：ProjectLockedError（`src/utils/instance_lock.py:31`）构造签名为 `(lock_path, holder_pid, holder_since)`——跨进程文件锁语义。会话咨询锁（SessionLock，TTL 30s、holder 为 tab_id）没有 pid/lock_path，直接复用需伪造参数（语义失真）。**建议**：若坚持异常路线，新增 `LiteratureLockedError(RuntimeError)` 子类（带 resource/holder），而非复用 ProjectLockedError。
2. **调用方响应契约**：每个写操作调用点包 `try/except LiteratureLockedError as e: st.error(locked_user_prompt(...))`（提示文案仍走 locked_user_prompt 同源）；读操作不加锁不受影响。
3. **影响面**：helper 1 处 + 写调用点 2 处 + test_concurrency.py 3 处断言 + test_design_system.py:59（源码文本扫描，若断言含 bool 契约字样需同步）。
4. **回滚方式**：单文件 git revert（helper 恢复 bool 契约 + 两调用点恢复 if 判断）；无数据写入、无 schema，回滚零残留。

## 三、需拍板（≥2）

1. **分层原则 vs 异常一致性**：dab0 已刻意分层（会话锁=bool 咨询，跨进程锁=异常）。改抛 ProjectLockedError 会把跨进程异常语义套在会话锁上（且构造参数失真）。拍板：维持 dab0 分层（推荐，本任务改道为「仅文档化」）？还是坚持异常化并新增 LiteratureLockedError？
2. **异常化范围**：仅 3 处调用点（helper+2 写点）还是连同 test_concurrency 契约重写一起做？后者工作量约 2-3 倍。
3. **提示通道**：异常被 except 后走 `st.error`（红）还是保持 `st.warning`（琥珀）？影响用户感知级别。

## 四、零实现声明

本单未改任何生产代码/测试；`git status --short` 无生产代码变更；未 commit/push。

## 五、用例草案扩容至 6 条（0912-0420-03 补充，原 2 条基础上）

3. **grade='F' 拒绝**：quality_grade='F' 行即使 review_status='reviewed' 也不命中（F 门独立生效）；
4. **source_reference 空串拒绝**：来源引用为空 → 不命中（引用完整性判据）；
5. **frozen_at 非空拒绝**：冻结行不命中（冻结闸优先于 review_status）；
6. **material/principles 缺失降级**：分析题特有字段缺失时门禁不崩，行不命中并留诊断列——TrustedXxxSql 只产谓词，降级由调用方 SELECT 计数断言。
