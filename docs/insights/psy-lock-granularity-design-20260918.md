# psy 项目锁粒度与回退策略设计稿（s918-04 / P1 余留）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读设计稿，不写码。前置阅读：psy-multiprocess-lock-design-20260912.md（方案 A 选型，本稿补粒度与回退）。

## 调用点全量（grep -rn "project_lock" src --include="*.py" 实测 4 处）

| # | 文件:行 | 角色 | 说明 |
|---|---|---|---|
| 1 | src/utils/instance_lock.py:88 | **定义** | `project_lock(lock_dir, *, stale_seconds=DEFAULT_STALE_SECONDS)`：跨进程项目互斥，非阻塞（被占抛 ProjectLockedError），同进程按 pid+depth 可重入，stale_seconds 后可接管死锁残留 |
| 2 | src/utils/project_manager.py:34 | 导入 | `from src.utils.instance_lock import ProjectLockedError, project_lock` |
| 3 | src/utils/project_manager.py:85 | **唯一消费点** | `with project_lock(PROJECTS_DIR):` —— 锁的是**整个 PROJECTS_DIR 目录**（项目级粗粒度） |
| 4 | src/ui/literature_review_panel.py:83 | 注释引用 | 说明 ProjectLockedError 提示同源、机制分层（非调用点） |

grep 计数：4 行（1 定义＋1 导入＋1 消费＋1 注释）＝表行数一致 ✓。

## 粒度方案对比（≥2 方案）

| 维度 | 方案 A：目录级（现状） | 方案 B：项目级（每项目一锁） | 方案 C：文件级（每数据文件一锁） |
|---|---|---|---|
| 锁对象 | PROJECTS_DIR 整目录 | `PROJECTS_DIR/<project>/.lock` | 每个被写文件旁 `.lock` |
| 并发收益 | 一次只允许一个实例做任何事 | 不同项目可并行（多开/并行批处理） | 同项目内不同文件可并行 |
| 实现成本 | 0（现状） | 低：lock_dir 参数改为按项目子目录，调用点 1 处改 | 高：需要文件级写路径审计，遗漏即锁失效 |
| 风险 | 长任务阻塞其它项目（现状痛点） | 项目内仍互斥（足够——单项目写入本就单线程）；跨项目共享文件（如全局配置）需额外全局锁 | 死锁面扩大（多文件锁序）；过度工程 |
| 回退 | — | 恢复目录级调用一行 | 恢复目录级，删除文件锁目录 |

**推荐：方案 B（项目级）**——与现有「跨进程单写者＋stale 接管＋同进程可重入」机制完全兼容（仅 lock_dir 收窄到项目子目录），成本最低、解决「长任务阻塞其它项目」的实际痛点；方案 C 在单用户桌面场景属过度工程。

## 获取失败回退语义建议
1. **现状语义保留**：非阻塞、被占即抛 ProjectLockedError，由 project_manager 上层转用户提示（:81 注释「不静默等待」）——正确，不改为自动等待。
2. **补充三层回退**：
   - holder pid 存活且未过 stale → 明确提示「另一实例（PID x）自 HH:MM 持有」，给「只读打开」逃生口（读操作不需要写锁）。
   - pid 不存活且过 stale_seconds → 现有自动接管（:120 附近）保留，接管动作写日志。
   - 锁文件损坏（读不出 pid）→ 过 stale 即接管（现有 `_read_lock` 异常分支已覆盖），补充接管日志计数。
3. **禁止**：自动等待重试循环（桌面单用户场景无意义）与静默降级为无锁运行。

## 遗留
- 方案 B 落地改动点：project_manager.py:85 一处（lock_dir 收窄）＋锁文件随项目目录清理；属后续批次。
- 只读打开逃生口需 UI 侧配合（只读态标志），本稿不写码。
