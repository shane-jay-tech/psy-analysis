# app.py 内联 vs panel 问卷分支对拍 v4 路径——差异表与三归类（s930-43/44 遗留）——s1004-20

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T18:4x ｜ 性质：AppTest 只读取证，零生产码零落盘（沙盒脚本 zcode-bridge/tmp/s1004-20/）
> 矿源：s930-43（v4 三步计划）＋s930-44（app_mode 驱动姿势已验证）两遗留逐字在案。

## 一、v4 前置探明（grep 证据）

- **mode 真实键**：app.py:293-298 `st.radio("按阶段进入", PAGE_MODES, key="app_mode")`——`session_state["mode"]` 直赋无效（s930-44 定谳沿用）；驱动值＝`"📋 问卷设计"`（navigation.py:13 PAGE_MODES 成员）；默认值＝`"📈 数据分析"`（app.py:292 兜底）。**s930-43 的 v4（mode 键驱动）确认未走完**（其 result 停在探明步）。
- **panel 入口**：questionnaire_panel.py:74 `render_questionnaire_page()`；app 内联分支＝app.py:1556 `elif mode == "📋 问卷设计"`（:1564 调 classify_questionnaire_sub_mode 子工作流）。
- **帧 B 预置需求**（实测迭代三枚）：`language="zh"`（panel:104 首个触点）、`questionnaire_design=None`（panel:202 引用）、`onboarding_completed=True`——AppTest 的 session_state 无 `.update()` 方法（AttributeError 实测），逐键赋值。

## 二、双帧 widget 序列对拍表（递归展平，label 截 60 字）

帧 A（app.py 内联，app_mode 驱动，exceptions=[]）20 行 vs 帧 B（panel 直渲染，exceptions=[]，预置三键后）15 行：

| # | widget（type | label） | 帧 A | 帧 B | 归类 |
|---|---|---|---|---|
| 1 | Markdown ×2（空）＋Block[Warning＋Expander「🔧 查看环境检查详情与修复建议」] | 有 | **无** | **C 在途笔噪声**＝app 级环境自检前置件（a81291f 面板外的全局段），非问卷分支产物 |
| 2 | Title＋Caption | 有 | 有 | 等价渲染 |
| 3 | Radio「选择工作流」 | 有 | 有 | 等价渲染 |
| 4 | Markdown＋Block[Column×4]（三入口卡） | 有 | 有 | 等价渲染 |
| 5 | Block[Column×2] | 有 | 有 | 等价渲染 |
| 6 | Divider＋Caption | 有 | 有 | 等价渲染 |

`diff`（剔除帧 A 环境检查前置 5 行后）＝**0 行差**——问卷主体区逐行一致。

## 三、三归类结论

1. **等价渲染**（#2-#6，主体区 100%）：v4 路径下 app 内联与 panel 直渲染的问卷面 widget 树**逐行一致**——「运行期等价」证据成立（渲染层）。
2. **真实行为差**：无（本轮零 exception 零结构差）。
3. **在途笔噪声**（#1）：环境检查 Expander 属 app.py 全局前置（:286 邻域），与问卷分支无关；对拍时按行号剔除即可。

## 四、结论与残留

- **运行期等价（渲染层）定谳**：a81291f「内联副本改调 panel 分类函数」消双份后，两分支渲染面无分叉；app_mode 驱动姿势（s930-44 前置）在本单 v4 全程复用成功。
- **残留**：①对拍深度＝首屏静态 widget 树；交互态（子工作流切换/按钮点击后的动态分支）未逐态对拍——若主班需要可按同姿势加 at.radio.set_value 后续帧；②帧 B 需预置三 session 键＝panel 直渲染的**独立可用性缺口**（直接 from_string 裸跑会 KeyError）——已在 §一留痕，是否给 panel 加缺省初始化属改码另单。

### 证据存根

- `$ grep -n "app_mode\|PAGE_MODES" app.py src/ui/navigation.py` → :293-298 键名＋:13 页名。
- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-20/frame_app_full.py` → 帧 A 20 行（exceptions: []）。
- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-20/frame_pair2.py` → 帧 B 15 行（exceptions: []，三键预置后）。
- `$ diff <(tail -n +7 frameA.txt) <(tail -n +2 frameB.txt)` → 无输出（主体区逐行一致）。
- 零落盘声明：沙盒脚本与两帧输出仅 zcode-bridge/tmp/s1004-20/；data/ 零触碰。
