# paper_bundle 四格可达性 AppTest 走查材料

> 产出单：s930-44（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-39 遗留（「paper_bundle 生产零写者 ⇒ 规则 8-11 四格常态不可达」需 AppTest 真点判）。
> 零生产码改动；AppTest 沙盒执行（合成 bundle 只入内存，data/ 零写入）。

## 一、零写者复核与路由机制

- **零写者复核成立**：`session_state["paper_bundle"] =` 形态全仓 **0 处**（grep 实证）；读点 8 处（deliverable_center_panel:56-58、export_gate:29/:72/:90、session_reset:41、app.py:2368 交付包预检、docx/zip exporters 消费）。bundle 的**合法产生面**＝`research_deliverable.py:21`（dataclass 字段，无 session 写入路径）。
- **路由机制（走查前置发现）**：app.py 的 mode 驱动＝侧栏 radio「按阶段进入」**key=`app_mode`**（:293-298）——`session_state["mode"]` 直赋**无效**（s930-43 的失败根因）；正确走查姿势＝`session_state["app_mode"]=<模式名>`＋`onboarding_completed=True`（绕 :192 guard 的 st.stop）。

## 二、四格可达性走查表（合成 bundle 预置，AppTest 实测）

| 格（规则 8-11） | mode | AppTest 实测 | 可达性结论 |
|---|---|---|---|
| 8 写论文 | 📝 论文写作 | **3 元素**（Tab「✍️ 写作」「1️⃣ 研究信息」＋研究信息表单族 12+ widgets） | **可达**——但渲染的是研究信息**输入面**；bundle 在此格不是前提（写作自产内容），「零写者」不阻断本格 |
| 9 一致性 | 📝 论文写作（同页内部节） | 同上一帧（写作 tab 面内） | **可达但受 bundle 缺失限制**：一致性检查类按钮需要 bundle/正文存在才有效——零写者 ⇒ 该格内的 bundle 消费动作**常态空转** |
| 10 导出 | 📦 交付包导出 | **8 元素**（数据治理声明 Expander＋三 Tab「内容清单/导出前检查/导出」）——**合成 bundle 预置后整格正常渲染** | **可达（条件性）**：预置 bundle ⇒ 面渲染正常；零写者常态 ⇒ 面内容为空态（export_gate :29 `session_state.get(PAPER_BUNDLE_KEY)` 得 None ⇒ 门禁判不可导） |
| 11 最终审阅 | 📦 交付包导出（导出前检查 Tab） | 同帧内 | **可达（条件性）**——同上，空态 |

**总结论**：四格「页面级」全部可达（AppTest 可正常渲染，无 crash）——矿源预设的「常态不可达」在**页面级不成立**；真正不可达的是「**bundle 消费动作级**」（导出/一致性检查因零写者而空转）。「零写者 ⇒ 四格废」的说法需降级为「四格可用但 bundle 依赖动作空转」。

## 三、接线最小面选项（不落码）

1. **最小接线**：paper_writing_ui 的「生成论文」动作末尾加一行 `session_state[PAPER_BUNDLE_KEY] = build_bundle(...)`（workflow_service 已有 bundle 组装面，research_deliverable.py:21 字段在位）——一处写入解锁四格全部 bundle 消费动作；
2. **替代接线**：写作 tab 完成/保存钩子里接——语义更贴「写完才有 bundle」，触发点选择属产品域；
3. **不接线维持现状**：四格空态可用（内容清单页正常渲染空态），bundle 面整体闲置——若「论文写作」格本季不用，零成本。
