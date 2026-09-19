# 文献面板锁异常语义核验＋`LiteratureLockedError` 方案（s918-52，只读）

生成：2026-09-19 11:5x｜执行：Qoder 会话（班次 `qoder-rev-20260919-1020`，倒序尾部续班）
**不改码、不改 BACKLOG**，只出核验＋接口草案。
边界：本单只管**文献面板的会话锁异常类型**这一件事（与 `s918-04` 的分工按任务书划开）。

## 结论一句

**异常化路线事实上已被放弃，但没人写下"放弃"二字**——
`grep -r LiteratureLockedError src/` 自 9/11 至今**恒为 0 命中**，
而被当作替代方案的"文案同源化"（`locked_user_prompt` 共享 formatter）**早已 done**
（BACKLOG `B-090`：9/11 08:45 晨报回收，dab0 done）。
⇒ 建议日间把 B-090 补一句「异常化路线不采纳，维持 dab0 分层」，
否则这份 9/11 材料会一直挂着"待拍板"，下一班又照它重评一遍。

## 一、签名对比表（两套锁机制为什么不能共用异常）

| 维度 | `SessionLock`（会话咨询锁） | `ProjectLockedError`（跨进程文件锁） |
|---|---|---|
| 定义处 | `src/utils/concurrency.py:51` | `src/utils/instance_lock.py:31`（`class ProjectLockedError(RuntimeError)`） |
| 抛出点 | **不抛**——`is_locked()`/`acquire()` 返回 bool | `instance_lock.py:129` 与 `:131` 两处 `raise ProjectLockedError(str(lock_path), holder_pid or -1, holder_since)` |
| 构造签名 | 无异常类 | `(lock_path: str, holder_pid: int, holder_since: str = "")` |
| holder 语义 | **tab_id**（同一浏览器会话内的多标签页） | **pid**（跨进程） |
| 生命周期 | TTL **30 秒**自动过期（`_check_lock_or_warn` 里 `lock.acquire(..., ttl=30)`） | 文件锁 + TTL（另一套；陈旧锁见 `s918-55`） |
| 面向用户的提示 | `st.warning(locked_user_prompt(resource, holder))` | 异常消息为英文 `project workspace is locked by another instance (pid=…, since=…)` |
| 消费方式 | **bool 短路**（`if _check_lock_or_warn(...): 才写`） | 调用方需 `try/except` |

⇒ 9/11 材料 §二第 1 点的判断到今天仍成立：把 `ProjectLockedError` 套在会话锁上必须**伪造 `lock_path`/`holder_pid`**，
语义失真。真要异常化，只能新增子类（下面第三节给接口）。

## 二、现状消费点清单（全部是 bool 契约，无一处 try/except）

| # | 位置 | 形态 | 失败时行为 |
|---|---|---|---|
| 1 | `src/ui/literature_review_panel.py:76-88` `_check_lock_or_warn(resource) -> bool` | 查 `SessionLock.is_locked(resource, by_others=True)` → 命中则 `st.warning(locked_user_prompt(...))` 并返回 **False**；否则 `ensure_tab_id` 后 `acquire(ttl=30)` 返回其 bool | 只 warn，不抛、不中断渲染 |
| 2 | `:456` 保存笔记（`_LR_NOTES_LOCK`） | `if _check_lock_or_warn(_LR_NOTES_LOCK): create_note(...)` ＋ `lr_state["notes"]=...` ＋ `st.rerun()` | bool False ⇒ **静默不写**（用户只在有冲突时被 warn；acquire 失败也是静默） |
| 3 | `:500` 一键自动填充（`_LR_MATRIX_LOCK`） | 同上 bool 契约 | 同上 |
| — | `:81-83` 的 dab0 注释（原 9/11 材料记作 `:86-90`） | 明文写死分层理由：「SessionLock 为 streamlit 会话咨询锁，异常路径（`ProjectLockedError`）属跨进程 `project_lock` 职责，两者**提示同源、机制分层**」 | — |

⚠️ **锚点漂移两处**（都是文件在上滑，说明这期间该面板又改过）：
`_check_lock_or_warn` 现起于 **:76**（与任务书一致 ✓），但 dab0 注释从 9/11 记录的 `:86-90` 移到 **:81-83**；
9/11 材料那句「建议新增 `LiteratureLockedError`」实际在 **:18**（任务书写作 `:5`，`:5` 是"前提张力"那行）。
本单一律按磁盘实况引用。

## 三、若仍要走异常路线：新子类的最小接口（草案，不落码）

```python
# src/utils/concurrency.py（与 SessionLock 同处，避免跨包再引一层）
class LiteratureLockedError(RuntimeError):
    """会话咨询锁被同会话另一 tab 占用（与 ProjectLockedError 分层，不共用构造参数）。"""
    def __init__(self, resource: str, holder: str = "") -> None:
        self.resource = resource
        self.holder = holder
        super().__init__(locked_user_prompt(resource, holder))   # 与 warning 路径同源文案
```

消费侧最小改动（两处，保持向后兼容）：

```python
# 现状：if _check_lock_or_warn(_LR_NOTES_LOCK): create_note(...)
# 异常路线：加一个 strict 开关，默认 False，逐步迁移
def _check_lock_or_warn(resource: str, *, strict: bool = False) -> bool: ...
# strict=True 时被占用即 raise LiteratureLockedError；调用点各包一层
#   try: ...strict 调用... except LiteratureLockedError as e: st.error(str(e))
```

**接口约束（三条，缺一不建议动）**：
① 子类消息必须复用 `locked_user_prompt`（否则破坏 dab0 同源化，B-090 已 done 的成果会退化）；
② 只加 `strict` 关键字参数、**默认 False**，保持 3 个调用点的 bool 契约不变；
③ 抛异常的路径**不得再 `st.warning`**（同一冲突只能有一个提示出口，否则 warn＋error 双弹）。

## 四、建议（本单不动手）

1. **首选：维持 dab0 分层，把 9/11 材料正式结案**——在 BACKLOG `B-090` 行补「异常化不采纳」一句，
   并把本文件与 9/11 材料一并入库，避免第三班再来评。
2. 真需要异常化，只有一种场景值得：**将来要在非 UI（服务层/批量脚本）里复用这几个写操作**——
   那时 bool 静默失败会变成"数据没写而没人知道"，异常才有价值。目前 3 个消费点全在 UI 内，不构成理由。
3. 无论走哪条，先修第二节标出的**静默面**：`acquire()` 返回 False（TTL 未过期但 holder 是自己另一 tab？）
   时今天**连 warning 都不发**，用户点保存按钮毫无反应 ⇒ 这比"用 bool 还是用异常"更该先解决。

## 五、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 签名对比表＋现状消费点清单 | 第一节 8 维对比＋第二节 4 行清单（含 helper 本体与 2 个写点与注释行） | 见文中各 file:line |
| `grep -c LiteratureLockedError src/` 仍为 0 | **命中文件数 0** | `cd /d/code/psy-analysis && grep -rl LiteratureLockedError src/ --include=*.py \| wc -l` → 0 |
| 只读、零变更（自加门） | 本单只 `grep`/`sed`/`wc`，产出仅本文件；`src/ui/literature_review_panel.py` 未被写（其 git 态无新增变化） | `cd /d/code/psy-analysis && git status --porcelain src/ui/literature_review_panel.py` → 空 |

## 遗留问题

1. 第二节末条那个「acquire 失败连 warning 都没有」的静默面，建议单开一单（属实现缺陷，不是口径选择）。
2. 两个资源名已核：`_LR_NOTES_LOCK = "literature_notes"`、`_LR_MATRIX_LOCK = "literature_matrix"`
   （`literature_review_panel.py:71-72`）。全仓检索 `"literature_notes"|"literature_matrix"` 的其余两处命中
   都在 `src/utils/concurrency.py`——:52 的 docstring 举例与 :138 的示例代码，**不是真实竞争方**
   ⇒ 今天不撞名。但注意 `SessionLock` 与跨进程 `project_lock`
   **共用一个字符串命名空间**（同一进程内不同机制），将来若有人给项目锁起同名 resource 就会互相看不见。
3. 9/11 材料里的「调用点 3 处」今天仍是 3 处（helper ＋ 2 写点），**未被新增消费点稀释**——这点值得记，
   说明那条链路这一年没扩面。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
