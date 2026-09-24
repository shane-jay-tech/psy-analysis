# psy 字体族栈普查与并轨裁决材料（s924-27 · 只读）

> 班名 `qoder-executor-20260925-0510-psy43` · 取数时刻 2026-09-25 05:0x · cwd `D:\code\psy-analysis`
> **本稿零代码改动**：只登记"字体族声明出现在哪些地方"，不改任何字体／docx／exporters 代码或测试（该族本波整体停派，见 §五闸列）。
> 产出面＝本文件一件；判据与前提全部现场复跑，命令原文见 §一／§二／§七 与结果件 `zcode-bridge/outbox/s924-27.result.md`。

---

## 〇、结论先行（5 条，其中 3 条是对上游口径的否证）

1. 🔴 **否证「6 套 font-family」**：`s923-19.result.md:96` 与 `psy-docx-style-unify-design-20260923.md:16` 都写成「HTML 侧 6 处内联 `font-family`」，且六处点名是 `questionnaire_panel.py:855`／`app.py:2284`／`script_generator.py:114/354/541`／`design_system.py:11`。实测被跟踪源码有 **9 处 / 7 件文件**（`rg -c` 遍历态读到 11 行，扣掉 `docs/insights/psy-docx-style-unify-design-20260923.md` 的 2 行登记文字）。**前稿漏掉 3 处**：`src/ui/renderers.py:679`（数据分析报告 HTML）、`src/ui/paper_writing_ui.py:570`（论文初稿 HTML）、`launcher.pyw:117`（桌面启动器 splash）。
2. 🔴 **行号锚点已漂**：`script_generator.py` 三处实测在 `191/431/618`（前稿写 `114/354/541`，各 **+77/+76/+77**），`design_system.py` 的 `font-family` 实测在 **`:40`**（前稿写 `:11`，`:11` 是变量定义行）；`questionnaire_panel.py:855` 与 `app.py:2284` **未漂**。⇒ 本稿行号一律现取，且每个数都附复跑命令。
3. 🔴 **"按 font-family 字面串盘"这一判据本身有盲区**：字面串只覆盖 S1–S3（CSS 文本栈）；S4 fpdf2 / S5 Plotly / S6 python-docx / S7 matplotlib **四条栈一个 `font-family` 都不写**。按渲染栈盘，psy 实际是 **7 条栈**，不是 6 套。
4. **docx 侧已有唯一常量源、但只有一个消费方**：`src/output/docx_styles.py:6-9` 四个 `FONT_*` 常量全仓**只被 `src/output/docx_exporter.py:30` import**；路 1 `src/questionnaire/exporters.py` 与路 3 `src/ui/paper_writing_ui.py:518` 绕过常量直接硬编码，导致同一逻辑字体在全仓有 **4 种命名法**（详见 §四矩阵）。
5. **并轨可行，但"跨栈单一 profile"这个提法按字面不成立**：S1–S3 是"族名字符串"，可收敛到一份 CSS 常量；S4–S7 是"运行时在文件系统里解析可用字体"，它们要收敛的是**候选优先级表**（实测该表全仓重复建设 **4 份**，见 §三 S4/S7 行）。⇒ 交主班的是**两个不同的并轨题**，不是一个（§六裁决条目 A/B）。

---

## 一、判据①读数：`rg -c "font-family"` 按文件计数（可直接对拍）

```
$ cd D:/code/psy-analysis && rg -c 'font-family' --stats
app.py:1
launcher.pyw:1
src\ui\renderers.py:1
src\ui\questionnaire_panel.py:1
src\ui\paper_writing_ui.py:1
src\ui\design_system.py:1
docs\insights\psy-docx-style-unify-design-20260923.md:2
src\experiment_design\script_generator.py:3

11 matches
11 matched lines
8 files contained matches
804 files searched
```
`rc=0`。**合计 11 行 / 8 件**，其中 `docs/insights/psy-docx-style-unify-design-20260923.md` 的 2 行是**登记文字不是渲染点** ⇒ 渲染点 **9 处 / 7 件**。

🔴 **自扫描增量（对拍必读，纪律档 §十.4／§十一.4 同款坑）**：本档落盘后，`rg -c 'font-family'` 会**多出一件** `docs/insights/psy-font-family-stacks-20260924.md`（本档正文大量引用该字面串；**其行数随本档编辑漂移，故刻意不钉桩**）⇒ 总数会大于 11 行，**这不是渲染点漂移**。对拍一律按下式排除登记件：
```
$ rg -c 'font-family' -g '!docs/insights/psy-font-family-stacks-20260924.md' --stats
11 matches / 8 files contained matches / 804 files searched      # 与上表逐位相同
$ rg -c 'font-family' -g '!docs/**' --stats                       # 只看渲染栈：9 matches / 7 files
```

出现点行号原文（判据②的"至少 6 处"，实测 9 处全列）：

```
$ rg -n 'font-family' app.py launcher.pyw src/experiment_design/script_generator.py src/ui/renderers.py src/ui/questionnaire_panel.py src/ui/paper_writing_ui.py src/ui/design_system.py
src/ui/design_system.py:40:    font-family: var(--psy-font-sans);
src/experiment_design/script_generator.py:191:    body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f0f2f6; }}
src/experiment_design/script_generator.py:431:    body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f0f2f6; }}
src/experiment_design/script_generator.py:618:    body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f0f2f6; }}
src/ui/paper_writing_ui.py:570:body {{ font-family: 'SimSun', 'Microsoft YaHei', serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 2; }}
src/ui/questionnaire_panel.py:855:body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.8; }}
launcher.pyw:117:    font-family: -apple-system, "Segoe UI", "PingFang SC",
src/ui/renderers.py:679:        "body { font-family: 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; }",
app.py:2284:body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.8; }}
```
配套锚点：`--psy-font-sans` 定义在 `src/ui/design_system.py:11`（`"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif`），全仓 `-psy-font*` 变量只有这一个，命中 2 行（`:11` 定义＋`:40` 使用）；`DESIGN_SYSTEM_CSS` 经 `app.py:70-71 render_design_system()` 注入。

---

## 二、三轨对数（正则＋字节＋AST）与差额逐条归因

纪律档 §九.3／§十.3 要求"全仓多少处"式判据双轨以上并解释差额。本班脚本：`tmp/psy43/font_stack_census.py`（`tmp/` 已 gitignore，`git check-ignore -v tmp/psy43` → `.gitignore:29:tmp/`）。

| 轨 | 手法 | 命中 | 文件 |
|---|---|---|---|
| A 正则遍历态 | `rg -c 'font-family' --stats` | 11 行 | 8 件（搜过 804 件） |
| B 字节级全仓 | `os.walk` 排除 `.git/node_modules/__pycache__/.venv/.pytest_cache/.mypy_cache`，`open(...,'rb').count(b"font-family")` | 25 处 | 21 件（搜过 **2502** 件） |
| C AST 字面量 | 只 `.py/.pyw`，`ast.walk` 取 `ast.Constant(str)` 计数 | 22 处 | 19 件 |

⚠ **取数时序**：上表三轨读数是**本档落盘之前**取的 ⇒ 复跑时 A 轨会多本档一件（已在 §一 给出排除式）、B 轨会多本档 29 处、C 轨**不变**（只走 `.py/.pyw`）。差额归因不受影响。

**差额逐条归因（B − A = 14）**：全部落在 gitignored 的 `tmp/` 历史副本与探针件里，rg 遍历态按 `.gitignore:29` 跳过 ⇒ 不是渲染点。明细：`tmp/psy5/` 6 件 ×1（他班 app.py 快照）、`tmp/psy43/font_stack_census.py` ×2（**本班探针自身，属自扫描假命中**）、`tmp/psy42/app-at-HEAD.py` ×1（**兄弟班 psy42 在途探针**，本班未碰）、`tmp/s922-18-*` 3 件 ×1（其中 `s922-18-app.py.bak` 非 `.py`，故不入 C 轨）、`tmp/s923-25/` 2 件 ×1。⇒ 扣掉 `tmp/` 后 B 轨 = 11 = A 轨，**两轨闭合**。

**差额逐条归因（C 与 A 的源码面）**：C 轨剔除 `tmp/` 后 = 9，恰等于 A 轨的渲染点数 9；A 轨多出的 2 是 `docs/insights/*.md`（非 `.py`，C 轨不覆盖）。⇒ **每一个 `font-family` 都完整落在单个字符串常量内、一行一处、无一处在注释里或被跨行拼接切断**（若有跨行拼接，C 轨会读 0 而 A 轨读 1；实测两轨在源码面 9:9 闭合）。

**C 轨 `unparsable` 列表＝空**（`.py/.pyw` 全部 `ast.parse` 通过，无假阴来源）。
**二进制／NUL 自证**：`with_nul` 字典为空；`node_modules` 单独走一遍＝**1 文件 / 0 命中**（该目录在 `git status` 里是 `??` 未忽略态，A 轨本会进入，实测不含目标串）。
**"扫了几份文件"（纪律档 §五.6）**：A 轨 804、B 轨 2502、`node_modules` 另计 1。

**同族标识符的补盘（`font-family` 字面串扫不到的部分）**：
```
$ rg -nF 'font_family' ; $ rg -nF 'FONT_FAMILY' ; $ rg -nF 'fontFamily'
```
排除本档与登记件后：`font_family` **15 行**（`src/visualization/paper_export.py` 6 行＋`src/visualization/fonts.py` 3 行＋`tests/test_fonts_and_docx_styles.py` 5 行＋`docs/insights/psy-test-blindspot-audit-20260915.json` 1 行），`FONT_FAMILY` **7 行**（`fonts.py:61/66/67/68/69` 缓存＋`test_fonts_and_docx_styles.py:5/23` 的 monkeypatch），**`fontFamily`（JS 驼峰）全仓 0 命中**——搜过的文件数同上 B 轨 2502 件。⚠ 这两式的**原始读数含本档自命中**（同样不钉桩），复算须带 `-g '!docs/insights/psy-font-family-stacks-20260924.md'`。

---

## 三、渲染栈分类表（判据②；实测 7 条栈，S1–S3 即卷宗点名的"三栈"）

| 栈 | 载体 | 出现点（现取行号） | 字体族现状 | 是否写 `font-family` |
|---|---|---|---|---|
| **S1 Streamlit 全局 CSS** | `st.markdown(DESIGN_SYSTEM_CSS)` | `src/ui/design_system.py:40`；变量定义 `:11`；注入 `app.py:70-71` | `"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif` | ✅ 1 处 |
| **S2 HTML 导出（下载件）** | f-string 内联 `<style>` | `app.py:2284`、`src/ui/questionnaire_panel.py:855`、`src/ui/renderers.py:679`、`src/ui/paper_writing_ui.py:570` | 前两者**逐字相同** `'Microsoft YaHei', sans-serif`（+`line-height:1.8`、`max-width:900px`）；`renderers.py` 同族但**无 line-height**；`paper_writing_ui` 是**唯一 serif 序** `'SimSun', 'Microsoft YaHei', serif`（`line-height:2`、`max-width:800px`） | ✅ 4 处 |
| **S3 jsPsych 施测页 HTML** | 脚本模板 `<style>` | `script_generator.py:191`(`_gen_between_subjects:153`)、`:431`(`_gen_within_subjects:386`)、`:618`(`_gen_survey:594`) | 三处逐字相同 `'Microsoft YaHei', 'SimHei', sans-serif`；**第 4 生成器 `_gen_generic:708` 的 `html_content` 只有两行注释（`:721-722`）、无 `<style>` ⇒ 施测页降级路径完全不声明字体族** | ✅ 3 处（+1 处缺声明） |
| **S4 PDF / fpdf2** | `pdf.add_font`/`set_font` | 注册名统一 `"CJK"`：`exporters.py:279-281`＋`:285/:294/:350`（第二函数 `:499-501/:505/:513`）；`defense_qa.py:781-784`（4 style）＋`_set_font:789-790` 24 次调用；`env_check.py:199-200` | 实字体＝运行时解析系统 TTF。**候选表全仓 4 份互不相同**：`fonts.py:15-27`（8 文件候选＋3 pattern 通配兜底）、`defense_qa.py:705-716`（6 项，含 Noto/PingFang）、`env_check.py:232-246`（4 项，**返回 `""` 而非 None**）、`environment_diagnosis.py:107`（关键字表 `SimHei/YaHei/SimSun/FangSong/KaiTi`）。降级族＝`Helvetica`（`defense_qa.py:787`、`env_check.py:203`） | ❌ 不写 |
| **S5 Plotly / Kaleido 图** | `family=` 键 | `fonts.py:41-58 get_font_family()`（路径子串 → PostScript 名映射，兜底 `sans-serif`）；`charts.py:13-14 FONT/TITLE_FONT`；`paper_export.py:124` 取值 → `:180/:181/:188/:194/:197` 5 处 `family=font_family` | 唯一"运行时感知"的一条：`Microsoft YaHei / SimHei / SimSun / KaiTi / Microsoft JhengHei / DengXian / sans-serif` 七值 | ❌ 不写（写 `family`） |
| **S6 python-docx** | `style.font.name` ＋ `w:rFonts/@w:eastAsia` | 常量源 `docx_styles.py:6-9`；唯一 import `docx_exporter.py:30`，落点 `_set_run_font:99-116`＋`12` 处 `S.FONT_*`；**绕过常量**：`exporters.py:36/39`（宋体）、`:43/47/56/57`（黑体）、`:63`（楷体，**只设 latin 槽、无 eastAsia 映射**）、`paper_writing_ui.py:518`（`font.name="SimSun"`，零页边距零常量） | `FONT_BODY_LATIN=Times New Roman`／`FONT_BODY_CJK=宋体`／`FONT_HEADING_LATIN=Times New Roman`／`FONT_HEADING_CJK=黑体` | ❌ 不写 |
| **S7 matplotlib** | `plt.rcParams` | `src/output/apa_figures.py:18` | `["SimHei", "Microsoft YaHei", "DejaVu Sans"]`——**优先级与 S4/S5 的 `fonts.py`（雅黑优先）正好相反**；全仓 `rcParams` 字体项只有这 1 处，`font.sans-serif`／`axes.unicode_minus` 各 1 命中 | ❌ 不写（写 `font.sans-serif`） |

⇒ 卷宗要的"三栈分类表"＝S1/S2/S3（＝CSS 侧 9 处 `font-family`）；但**"6 套渲染栈"这一说法无论按哪种口径都不闭合**：按 CSS 栈只有 3 条，按全渲染栈有 7 条，按 CSS 出现点有 9 处。

---

## 四、与 docx 侧常量的对应关系（同一逻辑字体的 4 种命名法）

`docx_styles.py:6-9` 是仓内**唯一**给字体起了"角色名"的地方（`FONT_BODY_*` / `FONT_HEADING_*`）。其余六条栈各说各话：

| 逻辑字体 | S6 docx 常量 | S6 绕过点 | S1/S2/S3 CSS 串 | S4/S5 文件系统候选 | S7 matplotlib | S4 降级 |
|---|---|---|---|---|---|---|
| 微软雅黑 | — | — | `Microsoft YaHei`、`Microsoft YaHei UI`（S1 首选，全仓独一份） | `msyh.ttc`/`msyhbd.ttc` → 返回 `Microsoft YaHei` | `Microsoft YaHei`（第 2 序） | — |
| 宋体 | `FONT_BODY_CJK="宋体"` | `exporters.py:36/39` 硬编码 `"宋体"` | `SimSun`（`paper_writing_ui.py:570`） | `simsun.ttc` → `SimSun` | — | — |
| 黑体 | `FONT_HEADING_CJK="黑体"` | `exporters.py:43/47/56/57` 硬编码 `"黑体"` | `SimHei`（S3 三处） | `simhei.ttf` → `SimHei` | `SimHei`（**第 1 序**） | — |
| 楷体 | **无常量** | `exporters.py:63` `run.font.name="楷体"`（无 `_set_east_asian_font` ⇒ 中文实际按 Normal 宋体渲染；该缺陷已被 `test_exporters_cjk_font_fallback.py:227`、`test_exporters_docx_geometry.py:219` 钉成现状） | — | `simkai.ttf` → `KaiTi` | — | — |
| SimSun（PostScript 名） | — | `paper_writing_ui.py:518`（第四种命名法，见 `psy-docx-style-unify-design-20260923.md:14`） | `SimSun` | — | — | — |
| Times New Roman | `FONT_BODY_LATIN`/`FONT_HEADING_LATIN`（两槽同值） | — | — | — | — | — |
| Helvetica | — | — | — | — | — | `defense_qa.py:787`、`env_check.py:203` |

**对应关系的三条硬结论**：
1. **CSS 侧与 docx 侧不是"同一 profile 的两个渲染分支"**：S6 的 CJK 槽写的是**中文字面名「宋体/黑体」**（Word 按 `w:eastAsia` 匹配），S2/S3 的 CSS 写的是 **PostScript/英文名 `SimSun/SimHei`**（浏览器按已安装族名匹配），S5 又拿**文件名字串**反推族名——三套名字**不能互换**，"把 docx 常量搬到 HTML"会当场出哑字体。
2. **docx 侧唯一缺常量的正是那条已知缺陷**：`楷体` 在 `docx_styles.py` 里没有槽位，所以 `exporters.py:63` 只能硬编码，也才导致它漏掉 `_set_east_asian_font`。⇒ 若要并轨，`docx_styles` 需先补 `FONT_SUBTITLE_CJK`，但**改值本身属人工裁决**（`psy-docx-style-unify-design-20260923.md` 遗留问题 1 已点名"楷体留不留"）。
3. **Latin 槽在 HTML/PDF 侧没有对应物**：`Times New Roman` 只存在于 S6，fpdf2 侧的 `Helvetica` 是内置 AFM 而非"latin 字体选择"。⇒ 单一 profile 若含 `latin` 字段，对 S1–S5/S7 六条栈语义为空。

---

## 五、统一 profile 可行性与牵动文件数

脚本 `tmp/psy43/profile_blast_radius.py`（token 集＝`font-family`/`font_family`/`FONT_FAMILY`/`fontFamily` + 14 个字体名字面量 + 6 个字体 API 名；轨 B 字节计数、轨 C AST 字面量计数，跳过 `tmp/`）：

```
$ .venv/Scripts/python.exe tmp/psy43/profile_blast_radius.py
### 生产码牵动文件（18 件）… ### 测试件牵动（7 件）… ### 合计文件 25（生产 18 / 测试 7）
### AST 轨文件数 22 / 字面量命中总数 143；正则轨文件数 25
### 差额文件: ['src/output/docx_exporter.py', 'src/visualization/charts.py', 'src/visualization/paper_export.py']
```

**双轨差额逐条归因（3 件，正则命中而 AST 字面量未命中）**：
- `src/output/docx_exporter.py`：12 处 `S.FONT_BODY_*`/`S.FONT_HEADING_*`＋`run.font.name` 是**属性/常量引用**，`黑体`×1 在 `:1092` 的**注释**里 ⇒ 均非 `ast.Constant`。
- `src/visualization/charts.py`：`get_chinese_font`×3 全是 import 与调用标识符。
- `src/visualization/paper_export.py`：`font_family`×6 是**局部变量名与 `family=` 关键字**，`get_chinese_font`×2 是标识符。
⇒ 差额全部是"标识符而非字面量"，**无假阴**；本 token 集下的真实牵动面取 **25 件（正则轨，上限口径）**，其中真含字面量者 22 件。

**生产码 18 件**：`app.py`、`launcher.pyw`、`src/experiment_design/script_generator.py`、`src/output/apa_figures.py`、`src/output/docx_exporter.py`、`src/output/docx_styles.py`、`src/paper_writer/defense_qa.py`、`src/questionnaire/exporters.py`、`src/ui/design_system.py`、`src/ui/paper_writing_ui.py`、`src/ui/questionnaire_panel.py`、`src/ui/renderers.py`、`src/ui/undergrad_wizard.py`（`:1550` 文案承诺"宋体/黑体"）、`src/utils/env_check.py`、`src/utils/environment_diagnosis.py`、`src/visualization/charts.py`、`src/visualization/fonts.py`、`src/visualization/paper_export.py`（**共 18 件，与脚本输出的 `### 生产码牵动文件（18 件）` 逐件对应**）。
**测试 7 件**：`test_environment_diagnosis.py`、`test_exporters_cjk_font_fallback.py`、`test_exporters_cjk_font_fallback_observability.py`、`test_exporters_docx_geometry.py`、`test_fonts_and_docx_styles.py`、`test_questionnaire_export_docx.py`、`test_questionnaire_export_pdf_positive.py`。

🔴 **本波闸列（这些件不可动，故"统一 profile"在本波不可能整体落地）**：

| 件 | 状态 | 为什么是闸 |
|---|---|---|
| `app.py` | ` M` 他班在途 | 9/14–9/22 在途件，零接触 |
| `src/questionnaire/exporters.py` | ` M` 叠加工作树 | s924-06/07/08 三单叠加态，纪律档 §十一.2 停派 |
| `tests/test_exporters_cjk_font_fallback_observability.py` | `??` 在途 | 同上族 |
| `tests/test_questionnaire_export_pdf_positive.py` | ` M` 在途 | 同上族 |
| `tests/test_fonts_and_docx_styles.py` | 干净但在点名停派族 | 本班只读 |
| `src/output/docx_exporter.py` | 干净但在点名停派族 | 本班只读 |

⇒ 闸外可动面：**S1＋S2＋S3 的 6 件 CSS 侧文件（9 处字面串）＋ S4/S7 的候选表收敛（`defense_qa.py`／`env_check.py`／`environment_diagnosis.py`／`apa_figures.py` 4 件）**，合计 **10 件**，且其中 `app.py` 仍在闸内 ⇒ **本波真能动的只有 9 件**。

---

## 六、交主班的裁决条目（本班不代作选择，纪律档 §五.3）

- **A. CSS 侧（S1–S3）9 处 → 1 源**：技术难度低（纯字符串注入），但**视觉会变**——`paper_writing_ui.py:570` 现在是 `serif` 序 + `line-height:2` + `max-width:800px`，与其余 8 处的 `sans-serif` + `1.8`/无 + `900px` 不同 ⇒ 并轨＝用户可见改版，**要人工点头**。最小无风险步：只把 `app.py:2284` 与 `questionnaire_panel.py:855` 那对**逐字相同**的串合到同一常量（零视觉变化，但 `app.py` 在闸内 ⇒ 得等 `app.py` 收班窗口）。
- **B. 候选表（S4/S7）4 份 → 1 份**：`fonts.py:15-27` 是事实最完整的一份（8 候选＋通配兜底），另 3 份向它收敛；但 `env_check.py:232-246` **返回 `""` 而 `fonts.find_chinese_font()` 返回 `None`**，收敛要改调用方判定 ⇒ 触及 `src/utils/env_check.py`（闸外、可动），且 `tests/test_fonts_and_docx_styles.py` 钉了 `None` 语义（该件在停派族内）⇒ **需主班排窗**。
- **C. matplotlib（S7）优先级相反**：`apa_figures.py:18` 是 `SimHei` 优先、`fonts.py` 是雅黑优先 ⇒ 同一份 PDF 里图与文可能不同族。**这是缺陷还是本意，属"报告可读性"域，交人工**。
- **D. `script_generator.py:_gen_generic` 完全不声明字体族**（`:708-728`）：施测页降级路径的浏览器默认字体可能无 CJK ⇒ **给被试看的实验页可能出豆腐块**。若确认是缺陷，修法是在 `:721-722` 那段 `html_content` 补 `<style>`，但那是**印给被试的东西**（同 §十一 里"页尺寸 Letter"那条的风险等级）⇒ 本班只登记。
- **E. 不要复用"6 套"这个说法**：本稿给出可复算的 9 处／7 栈两个口径；历史件 `psy-docx-style-unify-design-20260923.md` 与 `s923-19.result.md` 按纪律档惯例**不回改**。

---

## 七、零改动自证（判据③）

```
$ git status --porcelain           # 开工基线 8 项 → 收工 10 项
$ git diff --numstat -- src/questionnaire/exporters.py src/output/docx_exporter.py src/output/docx_styles.py src/ui/design_system.py tests/test_fonts_and_docx_styles.py
14	6	src/questionnaire/exporters.py     # 收工复点：与开工逐字相同（他班 s924-06/07/08 叠加态，本班未碰）
$ certutil -hashfile src/questionnaire/exporters.py SHA256   # 开工 ce17c4dd0d41…  收工同值
```
- 本班**只新建 2 件**：`docs/insights/psy-font-family-stacks-20260924.md`（本档，被跟踪目录下的新未跟踪件）＋ `tmp/psy43/` 下 3 个探针件（`.gitignore:29` 已自证忽略）。
- porcelain 里 `tests/test_i18n.py` 由"不在列"变为 ` M`、`tests/test_exporters_cjk_font_fallback_observability.py` 与 `tests/test_app_page_branch_pins.py` 在列 ⇒ 属**兄弟班 psy42（s924-20／s924-22 测试位）正常作业**（纪律档 §十二"同仓多路并发"口径），本班未碰、未定性为"第二写手"。
- 未跑全量套件（只读位，纪律档 §四.2）；本单也不需要测试数——产出是普查档。

---

## 八、复算配方

```
cd D:/code/psy-analysis
rg -c 'font-family' -g '!docs/insights/psy-font-family-stacks-20260924.md' --stats    # 判据①对拍：11 matches / 8 files（含 docs 登记件 2 行）
rg -c 'font-family' -g '!docs/**' --stats                                             # 只看渲染栈：9 matches / 7 files
rg -n 'font-family' -g '!docs/**'                                                     # 判据②行号（9 处原文）
.venv/Scripts/python.exe tmp/psy43/font_stack_census.py                              # 三轨对数（需 tmp/ 探针件在位）⚠ B 轨走全文件类型，复跑时本档会被计入（B 总量 > 25）；C 轨只走 .py/.pyw，不受本档影响
.venv/Scripts/python.exe tmp/psy43/profile_blast_radius.py                           # 牵动面 25 件（只走 .py/.pyw，不受本档影响）
rg -nF 'font_family'  -g '!docs/insights/psy-font-family-stacks-20260924.md'         # 补盘：15 行
rg -nF 'FONT_FAMILY'  -g '!docs/insights/psy-font-family-stacks-20260924.md'         # 补盘：7 行
rg -nF 'fontFamily'                                                                  # 0 命中（JS 驼峰不存在）
rg -n 'Microsoft YaHei|SimHei|SimSun|KaiTi' -g '!docs/**' -g '!tests/**'             # 命名法矩阵复核
```
⚠ 后两条依赖 `tmp/psy43/*.py`（gitignored，会被清理）；两轨总数差额若变化，按 §二归因表逐条重归，不要只取单个数。
