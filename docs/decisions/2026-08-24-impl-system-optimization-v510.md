# v5.10 系统级优化实施与评审归档

## 原始需求

> 我想让你对本系统进行优化，优化这个系统的方方面面，使其更好用；以这个描述，固化300字左右的目标进行实现

用户随后确认“按推荐执行”：保留当前未提交改动作为基线；完成一轮有限、可验收的系统级优化；采用新手友好默认流程与专家进阶能力并存的体验。

固化目标见仓库根目录 `SYSTEM_OPTIMIZATION_PLAN.md`。

## 难度与路由

- 评分：7/12，L3 较难。
- 分项：影响面 2、风险领域 1、歧义度 1、新颖度 1、不可逆性 0、长程影响 2。
- 理由：改动横跨主导航、研究状态、项目持久化、外部输入、HTML 导出和统计执行入口，错误可能造成跨研究数据污染或错误统计结果；Git 可回滚，因此不可逆性为 0。
- 预设验收权重：正确性 40%、数据安全 25%、用户体验 15%、可维护性 10%、性能 10%。
- 健康检查：gpt、deepseek、flash、dashscope、dsbackup、kimi、claude、codex 通道均返回 OK。

## 模型与审计产出

### 主执行与仲裁

- ChatGPT/Codex（当前主会话）：制定固化目标、审计代码、实施、测试、仲裁与交付。
- 思考档：L3 深审；未调用联网资料，因为任务只依赖本地代码与测试证据。

### UX 审计代理（verbatim 摘要）

> 1 experimental design route missing (wizard sets `🧪 实验设计`, app no route)
> 2 clear session leaves old paper/cards/evidence/export flags
> 3 onboarding permanently forced completed
> 4 multiple nav facts
> 5 next_step_engine unused
> 6 exports split
> 7 autosave invisible/silent, project UI hidden
> 8 version and terminology drift.
> Recommended top fixes: route, centralized reset, onboarding, next-step, version.

仲裁：1、2、3、4、5、7、8 接受并实施；6 部分接受，统一了关键下载安全与交付文案，完整出口收敛进入路线图。

### 可靠性与架构审计代理

两名 Codex 审计代理均未产出正文，原始失败信息：

> You've hit your usage limit. Upgrade to Pro, visit Codex usage settings to purchase more credits or try again at Aug 28th, 2026 11:08 AM.

处理：不伪造其意见；由主会话补做本地可靠性/架构检查，并使用 DeepSeek 独立评审作为交付门。

### DeepSeek V4 Pro 独立评审（首轮原始 finding 摘要）

首轮结论：`do-not-ship`。主要意见原文要点：

> 1 unsafe HTML/XSS research_parse and construct filename
> 2 workspace import reapplies every rerun
> 3 same-name upload ignored
> 4 failed upload destroys current dataset
> 5 autosave throttle not project-aware
> 6 autosave imported but not called in app
> 7 template creation only legacy state
> 8 direct recipe execution blindly picks columns
> 9 reset leaves widget states
> 10 large upload getvalue/double read/column UI ineffective
> 11 homework export df.copy OOM
> 12 atomic persistence not concurrency safe/index corruption
> 13 user prefs non-atomic
> 14 app monolith/cancel NameError
> 15 hollow tests

仲裁：1–10、13、14 中可局部验证项、15 均接受并修复或补测；11 记录为大数据导出路线图；12 接受原子写与单进程锁，跨进程锁和损坏索引恢复保留为明确残余风险；app 单文件拆分属于后续架构工作。

### DeepSeek V4 Pro 独立复审（verbatim）

> Verdict: ship-with-fixes — template-center project isolation and HTML export escaping must be fixed before this increment ships; the remaining objections are fix-now or clearly-scoped hardening.
>
> Security vulnerabilities — The claimed HTML-escaping fix covers only `research_parse`, but the questionnaire HTML export still interpolates `full_report` raw into an HTML document. Escape every dynamic fragment before composing HTML and replace unsafe error boxes.
>
> Design flaws — `template_center_panel._create_project()` copies the template into a temporary directory and sets a template id, but never creates a real project-manager project or active project. Data can be autosaved into the previous active project. Create and activate a real project and save its initial workspace.
>
> Performance — Workspace import identity recomputes the full hash on every rerun. Short-circuit on cheap identity before reading and hashing bytes.
>
> Edge cases — DataFrame hash memo uses object id, so in-place mutation can return stale cached statistical results. Recompute or version the content hash.
>
> Maintainability — Several blanket exceptions are silent; log and surface non-fatal status.
>
> Smaller nits — corrupted project index may orphan workspace files; restored output without plan can raise; duplicate model labels can select wrong id; prefs sync should hold the lock across read-modify-write.

仲裁与处理：

- HTML 导出与错误框：接受。新增统一安全转换，先转义全部用户/模型文本，再转换系统控制的标题；动态错误改用安全组件；增加恶意标签行为测试。
- 模板项目隔离：接受。模板创建改为真实 UUID 项目，集中重置研究状态、设为 active 并立即写入含数据的初始工作区；增加项目隔离与持久化测试。
- 重复哈希：接受。先用 name/size/file_id 判断，变化时才读取并计算 SHA-256。
- 错误统计缓存：接受。每次用户真正触发分析时重算 DataFrame 内容哈希，不再用对象 id 证明数据不变。
- 推荐方案盲选列：接受首轮意见。改为只预填方法并要求用户确认真实列名，再进入统一解析与防呆检查。
- plan 未绑定、prefs 竞态：接受并修复。
- 静默异常：部分处理；自动保存本身已有可见错误状态，仍有若干非关键兼容路径只写 debug，列入可维护性路线图。
- 损坏索引恢复、跨进程文件锁：不在本轮扩张。当前为单 Streamlit 进程使用模型，原子替换与 RLock 已覆盖验收范围；风险明确保留。

最终复核回执：`ship`。评审确认模板已使用真实项目并立即持久化、HTML 导出已统一经过安全转换；其余均为非阻断加固项。复核后又采纳“切换模板前保存旧项目”和“失败前不清空 session”的意见，并新增两条故障路径测试。

## 实施摘要

- 统一导航并接通实验设计；向导跳转使用 rerun 前状态队列。
- 集中式研究状态重置，取消旧 AI 请求并延迟清理 widget key。
- 恢复真正的一次性新手引导和主动重开入口；接入下一步建议。
- 上传使用文件身份，失败时保留当前有效数据；大文件显式确认列后加载。
- 工作区/偏好/项目采用原子写；自动保存项目感知并可见。
- 模板创建进入真实独立项目；推荐分析不再自动猜测变量。
- 外部文本 HTML 转义，下载使用安全控件与净化文件名。
- Kaleido 自动发现本机 Chrome/Playwright Chromium并提供可操作降级提示。
- 版本统一为 v5.10.0，更新系统报告、已知问题、升级报告与回归测试。

## 验证证据

- `python scripts/release_gate.py --mode full`：完整门禁通过（最终修复后再次执行）。
- 定向回归：导航、模板项目隔离、HTML 转义、上传、安全重置、自动保存、偏好与推荐方案测试均通过。
- 性能 smoke：0 FAIL、0 WARN；7 条关键路径均低于预算，核心冷启动约 3.1–3.3 秒。
- 测试收集：2544 个离线项目；最终数值同步写入 `docs/SYSTEM_REPORT.md` 与 `UPGRADE_REPORT_V5.10.md`。
- 未创建 commit，等待用户确认。

## 残余风险与路线图

1. RLock 只保护单进程；若未来同时运行多个应用实例，需要 OS 文件锁或事务型存储。
2. 大工作区快照仍需同步序列化完整 DataFrame，首次自动保存或导出可能卡顿。
3. `app.py` 仍是大型编排文件，若干非关键兼容路径吞掉异常，后续应拆分并统一日志/状态反馈。
4. 浏览器 Playwright Python 包未安装，真实 Chromium E2E 在当前环境明确跳过。
5. 草稿、作业包与正式交付仍有多个出口，需进一步统一入口语义。

## 结构化元数据

```yaml
task_type: impl
difficulty_score: 7
difficulty_level: L3
models:
  - ChatGPT/Codex 主会话: implementation_and_arbitration
  - UX audit agent: completed
  - DeepSeek V4 Pro independent reviewer: initial_and_followup_review
  - reliability audit agent: failed_usage_limit
  - architecture audit agent: failed_usage_limit
critical: 2
major: 8
minor: 5
accepted: 13
partial: 2
overrides: 0
tests_passed: true
residual_risks: 5
rework: true
automatic_escalation: false
commit_created: false
secrets_redacted: true
```

## 完成度复审补遗

持续目标审计发现初版门禁只覆盖了已实现子集，因此重新按固化目标逐项核验并补齐：

- 新增隔离存储的真实 AppTest 上传→分析黄金流和无障碍契约。
- 归档、作业包与正式交付共用隐私脱敏/硬门禁。
- 损坏项目索引改为先隔离备份，再从 workspace 文件自动重建。
- 持久化路径集中配置，支持测试子进程重定向且保持默认历史路径。
- 发布门禁增加统计证据、隐私诚信、兼容恢复、UI 黄金流和严格性能预算。
- 修复并发 AI fallback 在测试退出后写关闭日志流的竞态。

复审证据见 `docs/SYSTEM_OPTIMIZATION_COMPLETION_AUDIT.md`。当前残余风险收敛为浏览器
Playwright 环境跳过、多实例文件锁、大快照同步序列化、编排层拆分与交付入口进一步收敛。

最终独立复审先因本科向导正式下载仍可绕过门禁、普通文本单元格中的手机号未脱敏而给出
`DO_NOT_SHIP`。修复后，四个正式下载在门禁失败时不创建按钮并清除已生成字节；归档与作业包
按共享模式扫描全部文本单元格，新增归档回读和真实按钮行为测试。独立复审最终改判 `SHIP`。
