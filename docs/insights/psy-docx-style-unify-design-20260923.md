# psy 两路 docx 样式统一样式源设计稿（exporters vs docx_exporter）

- 单号：s923-19 ｜ 班：`qoder-executor-20260923-0022-psy11` ｜ 出稿：2026-09-23
- 性质：**只出设计稿，不合并不改码**。`src/questionnaire/exporters.py`、`src/output/docx_exporter.py`、`src/output/docx_styles.py` 三件零改动（自证见第六节）。
- 上游：`zcode-bridge/done/s922-22-psy-docx-styles-census.result.md` 遗留问题 #3（「两路 docx 样式体系重复建设……属统一样式源的规划域工作，本单只出证据不合并」）。
- 本文所有数值均为**本班现取实测**（`.venv/Scripts/python.exe`，python-docx 1.2.0），复算命令见第六节；不抄 s922-22 的旧读数。

---

## 一、结论先行（四条，其中两条与上游口径不同）

1. **任务书的前提要收窄**：「两路都产问卷类 docx」字面成立、实质不成立。实测两路产物**是两种文档**——`exporters.export_to_docx` 出**问卷设计报告**（研究问题／构念定义／维度结构／技术参数／题库＋依据／文献锚点，样张 69 段 1 表），`docx_exporter.build_questionnaire_docx` 出**空白施测卷**（标题／指导语／锚点说明／Likert 圈选表／致谢，样张 38 段 1 表）。输入契约也不同（`Dict` vs `ItemsDoc`）。⇒ **重复的不是文档层，是版式常量层**。任何"合并成一个 builder"的方向都是错的，本稿两案都只在**样式源**这一层动。
2. **范围不止两路，是四路 docx ＋ 一处 HTML 混排**（上游与本单任务书都没数到）：
   - 路 3：`src/ui/paper_writing_ui.py:512-545` 在 UI 里**内联** `Document()`，Normal 字体写 `"SimSun"`（第四种命名法：PostScript 名），零页边距、零常量、走 `Title`/`List Number` 命名样式。
   - 路 4：`src/output/docx_exporter.py` 自身 5 个 builder（`:603` 协议 / `:850` 论文 / `:961` 问卷 / `:1068` 综述 / `:1125` 交付包）共用 `_setup_page`＋`_set_run_font`，内部已一致 ⇒ 它们是**同一套样式源的多消费方**，不是新路；但路 1/2 与它们的关系不同，见下条。
   - 混排侧：`src/ui/questionnaire_panel.py:855` 与 `app.py:2284` 各有一份内联 HTML CSS `font-family:'Microsoft YaHei'+line-height:1.8`，`src/experiment_design/script_generator.py:114/:354/:541` 三份，`src/ui/design_system.py:11` 一份 ⇒ 同一逻辑「正文/标题」在 HTML 侧还有**第 6 套**事实源（本稿只登记、不并轨）。
3. **实测新发现的最高优先缺陷：两路纸张尺寸不同**。`build_questionnaire_docx` 产物 `w:pgSz`＝**12240×15840 twips ＝ US Letter 8.5×11 英寸**（`_setup_page` `:386-392` 只设 `pgMar`、从不设 `pgSz` ⇒ 继承 python-docx 捆绑模板），而 `export_to_docx` 是 **11906×16838 ＝ A4 21.0×29.7cm**。⇒ 国内打印场景下，施测卷（要印给被试圈选的那一份）默认落在 Letter 上，A4 打印机出图会缩排／切边。**`docx_styles` 里没有页宽页高常量**，所以这条既不在常量表内、也不在任何测试钉桩内（`tests/test_exporters_docx_geometry.py` 只钉了路 1 的 A4），是彻底的看守真空。
4. **两路的差异根因不在字面量、在"写在哪一层"**：路 1 把版式写在**命名样式**（`Normal`／`Heading1..3`／`ListBullet`）上，路 2 把版式全部写成**段落/运行级直接格式**，`document.xml` 里 `pStyle` 出现 **0 次**、`outlineLvl` **0 次**。⇒ 路 2 的产物在 Word 眼里**没有文档结构**（导航窗格空白、无法生成目录、读屏软件读不出标题层级）。这条决定了「统一样式源」的正确目标是**收敛到命名样式**，而不是"让路 1 也改用直接格式"。

---

## 二、差异矩阵（18 维度，逐项实测值）

图例：**路 C** ＝ `src/questionnaire/exporters.py:13 export_to_docx(design: Dict)`；**路 A** ＝ `src/output/docx_exporter.py:961 build_questionnaire_docx(items_doc)`；**路 D** ＝ 同模块 `:603 build_experiment_protocol_docx`（作为"路 A 家族"的第二消费方一并抽，用来暴露家族内漂移）。样张同源（合成文案，无被试数据／无统计数值／无医疗内容）。

| # | 维度 | 路 C（exporters） | 路 A（docx_exporter） | 路 D（protocol，参照） | `docx_styles` 常量现状 | 判定 |
|---|---|---|---|---|---|---|
| 1 | 纸张 `pgSz` | `11906×16838`＝A4 | **`12240×15840`＝US Letter** | 同 A（Letter） | **无此常量** | 🔴 分叉＋无常量＋无看守 |
| 2 | 页边距 `pgMar` | top/bottom 1440、left/right 1803 | 同 | 同 | `MARGIN_TOP/BOTTOM=2.54`、`LEFT/RIGHT=3.18` | 数值一致；C 是 `Cm()` 字面量、A 吃常量 |
| 3 | 页设置作用域 | `doc.sections[0]` 单节 | `for section in doc.sections` 全节 | 同 A | — | 多节文档下 C 只改首节 |
| 4 | Normal 拉丁槽 | `ascii=宋体 hAnsi=宋体` | `ascii=Times New Roman hAnsi=Times New Roman` | 同 A | `FONT_BODY_LATIN` | 🔴 C 无中英双轨：正文数字/拉丁也按宋体渲染 |
| 5 | Normal 东亚槽 | `eastAsia=宋体`（过 `_set_east_asian_font` `:238`） | `eastAsia=宋体`（`_setup_page :401`） | 同 | `FONT_BODY_CJK` | 一致（但 C 侧是硬编码） |
| 6 | Normal 字号 | `sz=24`（12pt） | `sz=24` | `sz=24` | `SIZE_BODY=12` | 一致 |
| 7 | 行距 | `Normal` 上 `w:line=432 auto`＝**1.8**（样式层），`document.xml` 内 `w:line` **0 次** | 逐段直接格式 `w:line=360`＝**1.5**（实测 6 段／路 D 80 段） | 1.5 | `LINE_SPACING=1.5` | 🔴 值不同（1.8 vs 1.5）**且落点层不同** |
| 8 | 正文段后距 | 段落**无** `w:after` ⇒ 继承 `docDefaults after=200`＝**10pt** | 同＝10pt | 同 | `SPACE_AFTER_BODY_PT=0` | 🔴 **常量说谎**，两路都不成立（s922-22 已登记，本班复证） |
| 9 | 标题载体 | `pStyle Heading2`×11、`Heading3`×6、`ListBullet`×10 | **零 pStyle、零 outlineLvl**，全直接格式 | 同 A | — | 🔴 结构性差异（目录/导航/读屏） |
| 10 | 标题字号 | `Heading1/2/3` 样式上 `sz=44/32/28`＝22/16/14pt | run 级 `sz` ∈ {21,24,26,32}，H2 走 `SIZE_H2=13`＝26 | run 级含 `sz=28`（14pt＝`SIZE_H1`） | `SIZE_H1/H2/H3=14/13/12` | 🔴 三档字号表**两路都不符合**；C 是表外 22/16/14 |
| 11 | 标题颜色 | `2C3E50`（样式层，Heading1..3 全覆盖）；`tests/test_exporters_docx_geometry.py:170` 钉着。⚠️ 该色在 HTML 侧有**隐式第二消费方**：`src/ui/questionnaire_panel.py:856` 的内联 CSS `h1{color:#2c3e50}` 与 `:857 h2{color:#2980b9}`——两处不同源，改一处即分叉 | 无（继承黑） | `888888` | **无颜色常量** | 🔴 同族三套色、其中一路无色；且 HTML 侧靠"复制粘贴同一个十六进制串"耦合 |
| 12 | run 字号集合 | {24, 32, **52**} ⇒ 52＝`Pt(26)` 封面主标题，**表外值** | {21,24,26,32} 全在表内 | {21,24,26,28,32} 全在表内 | `SIZE_TITLE=16` | C 有 1 个表外字号 |
| 13 | run 拉丁槽字体集合 | {**楷体**, **黑体**}（中文字体写进 latin 槽） | {Times New Roman} | {Times New Roman} | 无「副标题/封面」字体档 | 🔴 C 的 latin 槽被中文字体占用 |
| 14 | 「楷体」是否真生效 | **否**。`:60` 只赋 `run.font.name`、未过 `_set_east_asian_font` ⇒ 该 run `ascii=楷体` 而**无 `eastAsia`**；实测「latin 为中文而缺 eastAsia」run 数＝**1**（A/D＝0）。中文实际按 Normal 的宋体渲染 | 0 例 | 0 例 | — | 🔴 缺陷已被两处**钉成现状**：`test_exporters_cjk_font_fallback.py:217-227`（断言 `font.name=="楷体"` "看着配了"）、`test_exporters_docx_geometry.py:219`（断言 `'w:eastAsia' not in subtitle`） |
| 15 | 表格实现 | 命名表样 `LightGrid-Accent1`（Word 内置彩色全框线表）；`tcBorders` 0、`nil` 0 | 手写**三线表**：`tcBorders` 28、`w:val="nil"` 147、`sz=4` | 该样张无表 | `TABLE_BORDER_SIZE=4`、`TABLE_BORDER_COLOR=000000`、`TABLE_HEADER_FILL=DDDDDD` | 🔴 语义完全相反（彩色学术 vs 三线表）。`TABLE_HEADER_FILL` **全仓零消费方**（A 的 `w:shd fill` 集合＝空） |
| 16 | 首行/左缩进 | `firstLine=420`×11（＝0.74cm ✓）＋ `left=567`×1（＝1cm，**表外**） | `firstLine=420`×1 | `firstLine=420`×18＋`left=420`×11 | `FIRST_LINE_INDENT_CM=0.74` | 值同但来源不同；C 另有表外 1cm |
| 17 | 常量接线面 | `import docx_styles` **False**、`S.` 引用 **0**、触达 **0/25**；版式字面量 10 处（`Cm(0.74)`×5、`Cm(2.54)`×2、`Cm(3.18)`×2、`Pt(12)`×2、`Cm(21)`/`Cm(29.7)`/`Pt(60)`/`Pt(26)`/`Pt(16)`/`Cm(1)` 各 1） | `S.` 引用 **74**、触达 **23/25**；仍留同值字面量 `Pt(12)`×4、`Cm(0.74)`×2、`Pt(6)`×1 | 同 A | 全仓零消费方 2 个：`SPACE_AFTER_BODY_PT`、`TABLE_HEADER_FILL` | ⇒ 常量表**只覆盖一路**；且接线方内部仍有"常量与字面量同值并存"，改常量不跟着动 |
| 18 | 死码 | `Inches`（`:16`）、`WD_STYLE_TYPE`（`:18`）**导入后全文件 0 引用** | — | — | — | 顺手项，不属版式裁决 |

样式文件面：`word/styles.xml` sha8 C＝`ed699d8a`、A＝D＝`710f881f`；三路 `docDefaults` **完全相同**（`sz=22`、`after=200`、`line=276`、`rFonts` 走 theme），theme `<a:ea typeface=""/>` 为**空**、靠 `<a:font script="Hans" typeface="宋体"/>` 兜底，`fontTable.xml` 只声明 `Arial/Calibri/Cambria/Courier/Symbol/Times New Roman/ＭＳ ゴシック/ＭＳ 明朝` ⇒ 实际用到的宋体/黑体/楷体/SimSun **均不在字体表声明内**（跨平台/跨 Office 版本不可靠，与 s922-22 遗留 #5 同因：常量从不触达 `docDefaults`）。

---

## 三、合并方向两案

### 案甲：单向并轨——「exporters 吃常量」（小步、低风险）

做法：`src/questionnaire/exporters.py` 顶部加 `from src.output import docx_styles as S`，把 10 处字面量换成常量引用；**不改任何数值**。

- 可无损换的（值本来就等）：`Cm(2.54)`→`MARGIN_TOP/BOTTOM_CM`、`Cm(3.18)`→`MARGIN_LEFT/RIGHT_CM`、`Pt(12)`→`SIZE_BODY`、`Cm(0.74)`→`FIRST_LINE_INDENT_CM`、`:59 Pt(16)`→`SIZE_TITLE`、`:41` 的 `size` 若取 `SIZE_H1/H2/H3` 才是"改值"（见下条）。
- **换不动、必须先有人裁决的 6 个表外值**（案甲在此卡住，这是它的天花板）：
  ① 封面主标题 `Pt(26)` vs `SIZE_TITLE=16`；② 封面段前 `Pt(60)`（常量表无"封面留白"档）；③ 行距 `1.8` vs `LINE_SPACING=1.5`；④ Heading 22/16/14pt vs `SIZE_H1/H2/H3` 14/13/12；⑤ 副标题 `楷体`（常量表无副标题字体档）；⑥ 列表左缩进 `Cm(1)`/`left=567`。
  ⇒ 案甲要么**扩表**（新增 6 个常量，把 `docx_styles` 从 25 涨到 ~31，`tests/test_fonts_and_docx_styles.py` 的常量值/数量类钉桩要同步），要么**改值**（＝用户可见版式回归，超出执行手授权，见待人工）。
- 顺带能修的无裁决缺陷（1 行级）：`:60` 补 `_set_east_asian_font(run, "楷体")`（维度 14）。**注意这是"两笔一体"**：修好会让 `test_exporters_cjk_font_fallback.py:227` 与 `test_exporters_docx_geometry.py:219` 两条"钉现状"断言当场变红，**要否掉这两处必须连同设计意图一起说清楚**，不能被当成"这单弄坏了测试"。
- 回归面：路 C 的产物 XML **一字节都不变**（若只做"引用替换"）⇒ `test_exporters_docx_geometry.py`(收集 6)、`test_questionnaire_export_docx.py`(收集 22)、`test_exporters_cjk_font_fallback.py`(收集 7)、`test_questionnaire_export.py`(收集 14) 全部不动。
- 优点：可在 1–2 个单内闭合、零版式风险、立刻消灭"C 完全不吃常量"这条。
- 缺点：**不解决任何一条🔴**（纸张、双轨字体、结构层级、表格语义、段后距说谎全都还在），只是把字面量搬进常量表；并且会让常量表变成"两路各自档位的堆叠处"，26pt/60pt/1.8/楷体 与 16pt/1.5/宋体黑体长期并存 ⇒ **常量表退化成第二事实源的清单**，反而更难收。

### 案乙：双向收敛——「`docx_styles` 升级为 profile，命名样式为唯一事实源」（目标态）

做法：
1. `docx_styles.py` 从"25 个散常量"升级为**按文档角色的 profile 表**：`PROFILE_REPORT`（设计报告）/`PROFILE_FORM`（施测卷）/`PROFILE_THESIS`（论文）/`PROFILE_PROTOCOL`（协议）。每个 profile 携带**成对的字体名**（`cjk_localized` 走 `w:eastAsia`、`latin_postscript` 走 `w:ascii/hAnsi`）＋ 五档字号 ＋ 行距 ＋ 段距 ＋ **页宽页高** ＋ 表格语义（三线表 / 无表）＋ 强调色。字体命名直接复用 `src/visualization/fonts.py:41-57` 已有的「文件→PostScript 名」映射（那里已有 `KaiTi`/`SimSun`/`SimHei`），从而**同时**满足 docx 的 localized 名与 matplotlib 的 PostScript 名，消灭维度 13/14 与"同一字体两种命名法"。
2. 新增 `apply_profile(doc, profile)`：**显式改写 `docDefaults`**（当前三路 `docDefaults` 全停在模板值 `sz=22/after=200/line=276`，这是 `SPACE_AFTER_BODY_PT` 说谎的根）＋ 写 `Normal`／`Heading1..3`／`ListBullet`／`ListNumber` 名片段 ＋ 写 `pgSz`/`pgMar` 到**每一节**。
3. **标题一律走 `pStyle`**（吸收路 C 的做法、废掉路 A 的直接格式）⇒ 一次性补回目录／导航窗格／`outlineLvl`／读屏结构。
4. **表格一律三线表**（吸收路 A 的 `_apply_three_line_borders`，废掉路 C 的 `LightGrid-Accent1`）；`TABLE_HEADER_FILL` 要么接线要么删（现在零消费方）。
5. 两路 builder 只保留"填内容"的职责；`exporters.export_to_docx` 改为 `apply_profile(doc, PROFILE_REPORT)` ＋ 内容，`build_questionnaire_docx` 改为 `apply_profile(doc, PROFILE_FORM)` ＋ 内容；路 3（`paper_writing_ui.py:512` 内联）改为调用 `docx_exporter` 的既有 builder，不再自建 `Document()`。
- 优点：**唯一能同时关掉 5 条🔴的方案**，并且关掉"改常量不跟着变"（维度 17 后半）和"docDefaults 隐式基线"（s922-22 遗留 #5）。
- 代价与风险：
  - **每一项都是用户可见版式变更**：路 A 的 Letter→A4（施测卷要重印）、路 A 获得命名样式（styles.xml 必变）、路 C 的 26pt/1.8/楷体若并入 profile 需明确保留还是弃用、路 C 的彩色表→三线表。⇒ 必须先出**版式基线对照**（同一份样张改前/改后 PDF 目检）并**人工放行**，不能由执行手判断。
  - 改动面：2 个 exporter ＋ 1 个常量模块 ＋ 1 个新 `apply_profile` ＋ 4 处 UI 调用面 ＋ 至少 5 个测试件；`test_exporters_docx_geometry.py` 是**twips 快照钉桩**（`11906/16838/1440/1803` ＋ `sz=52` ＋ `'w:eastAsia' not in subtitle`），版式一改必红，且它自带「只钉现状，不改版式」的声明 ⇒ 它的红**是设计变更的合法产物**，要连同本稿一并交裁决，不得自行放宽。
  - 行尾陷阱：`src/output/docx_exporter.py` 是**纯 CRLF**（1247 对）、`src/questionnaire/exporters.py` 是**纯 LF**（572/0）。批量编辑若整体重写行尾，会把"一行改动"放大成整文件 diff ⇒ 案乙的任何一步都要**先量行尾、后改、再复量**。
  - 统计口径：本稿不涉及任何被试/统计数值，profile 里也不得放统计结论类文案。

### 两案取舍建议

**不是二选一，是先后**：案甲的"引用替换＋缺陷修复"子集（不含 6 个表外值的裁决）作为 **P1/P2 的低风险前段**，案乙作 **P3/P4 的目标态**。理由：案乙的所有决策项都需要人工拍板，而"路 C 不吃常量"这件事不必等拍板就能改善；反过来若直接跳到案乙，会把"改一行看 diff"的可控改动混进一次版式改版，验收面（5 个测试件 ＋ 全局账本门）一次全开，不可归因。

---

## 四、分期迁移清单（每期都可独立闭合、独立回滚）

| 期 | 内容 | 需要裁决？ | 触碰文件 | 回归面（会被弄红的） | 建议单粒度 |
|---|---|---|---|---|---|
| **P0** | 只读盘点收口：把本稿的 18 维矩阵落成**机器可读基线快照**（`word/document.xml`＋`word/styles.xml` 的属性直方图，落 `tests/golden/`），作为后续任何版式改动的 diff 底座 | 否 | 新增 `tests/` 1 件 | 无（纯新增） | 1 单 |
| **P1** | 无裁决缺陷修复：①`:60` 楷体补 `_set_east_asian_font`；②删 `Inches`/`WD_STYLE_TYPE` 死导入；③`_setup_page` 与 `export_to_docx` 的节作用域统一为"全节"（A 已是全节、C 只首节，把 C 补齐，不改任何数值） | 否（②③纯现状收敛） | `src/questionnaire/exporters.py`、`src/output/docx_exporter.py` | 🔴①会让 `test_exporters_cjk_font_fallback.py:227` 与 `test_exporters_docx_geometry.py:219` 变红——**"钉 bug 现状"型红**，必须连断言一起改写并在 claims note 记归属；③无红（C 单节样张不变） | 1 单 |
| **P2** | 案甲的安全子集：路 C 的 6 处等值字面量换成常量引用（页边距/正文字号/首行缩进/副标题 16pt），**产物 XML 逐字节不变**，用 P0 的快照自证 | 否 | `src/questionnaire/exporters.py` | 无（前提：只换等值项）。`test_fonts_and_docx_styles.py` 只钉常量值、不钉引用方，不动 | 1 单 |
| **P3** | 常量表扩表（案甲天花板）：新增 6 个表外档（`SIZE_REPORT_TITLE=26`、`COVER_SPACE_BEFORE_PT=60`、`LINE_SPACING_REPORT=1.8`、`FONT_SUBTITLE_CJK=楷体`、`INDENT_LIST_CM=1`、`COLOR_HEADING_ACCENT=2C3E50`）＋ **`PAGE_WIDTH_CM=21`/`PAGE_HEIGHT_CM=29.7`**（这条是"补常量、不改值"，A 路何时用它属 P4） | 是（哪些是真本意）| `src/output/docx_styles.py` | `test_fonts_and_docx_styles.py`（收集 20，含常量值三元组钉桩与常量集合类断言）需同步扩 | 1 单 |
| **P4** | 案乙主体：`apply_profile` ＋ 命名样式 ＋ 三线表统一 ＋ A 路 `pgSz` 落 A4 ＋ 路 3 内联 `Document()` 归位 | **是，逐项**（A4/Letter 属用户可见改版） | `docx_styles.py`、`docx_exporter.py`、`exporters.py`、`paper_writing_ui.py`、`questionnaire_panel.py`/`items_upload_panel.py` 调用面 | `test_exporters_docx_geometry.py`(6)、`test_questionnaire_export_docx.py`(13)、`test_questionnaire_export.py`(14)、`test_exporters_cjk_font_fallback.py`(7)、`test_deliverable_docx_export.py`、`test_docx_export.py` ＋ **跨面全局账本门** `pytest tests -q -k "download_buttons or export_gate"` | 拆 2–3 单（按 profile 分），且 `app.py` 在途属他班、**本域任何一步都不得顺手碰 `app.py:2253/2284`** |

**跨期不变量**（每步都要复算）：`data/benchmark_history/` 逐文件 sha256_8 四值不变；`data/literature_feed/` 三件侧车（db/`-wal`/`-shm`）size+mtime 逐位不动（本班实测该库**当前有别的进程在写**：`feed.sqlite` mtime 12:15:30、`locks/feed_fetch.lock` 里躺着**两条**僵尸锁 `pid=130036@03:55:07Z` 与 `pid=135684@04:15:30Z`，两个 pid 均已不在进程表 ⇒ P4 若需跑 `AppTest`，**必须**先按纪律档 §廿一 整套 `copy2` 进沙盒再用 `LITERATURE_FEED_DATA_ROOT` 指过去）。

**P4 的验收补丁（必须写进将来工单的完成标准）**：改前/改后各产一份样张，按本稿第二节 18 维逐项列「改前实测值 → 改后实测值 → 期望」三列，**任何一列对不上即视为未闭合**；只比"能打开"不算验收。

---

## 五、红线与刻意不做的决定

- 本稿**不动任何数值**：26pt、60pt、1.8、楷体、`LightGrid-Accent1`、`DDDDDD`、10pt 段后距，一律**只登记归属**，不判对错（判"哪个是本意"需要产品/原作者拍板）。
- 不碰 `app.py`／`pytest.ini`／`requirements-lock.txt`（他班在途）。本稿只**读** `app.py:2253/2284` 作为调用面证据（取值时刻 2026-09-23 12:2x，HEAD `92805ff`）。
- 不新增 `st.download_button`、不改导出门（`tests/test_export_gate_global_scan.py` 的三表 `WHITELIST_EXPORTS/GATED_EXPORTS/NEEDS_MIGRATION` 一字不动；`NEEDS_MIGRATION` 有 `assert len(...)==0` 的"债务登记册必须为空"语义，**不可当收容所用**——纪律档 §十五 已立此条）。在册 1 条红 `test_all_download_buttons_accounted_for`（待人工 81）与本稿无关，不修不放宽。
- HTML/PDF 侧的 6 套 font-family（本稿第二节末登记）**只登记不并轨**：它们属"报告可读性"域，与 docx 分属不同渲染栈，并轨前需要先决定"是否有单一 profile 概念跨栈"。

---

## 六、证据与复算命令

```bash
cd /d/code/psy-analysis
# 沙盒（纪律档 §廿一）：探针先把 data/literature_feed 整套 copy2 进 tmp，再用 LITERATURE_FEED_DATA_ROOT 指过去
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -X utf8 tmp/s923-19/style_diff_probe.py > tmp/s923-19/r2.txt   # rc=0，PROBE_ERRORS=0
# 探针自证：三样张均构建成功（尺寸 38570/37728/39390B），18 维直方图非空（空则 rc=5）；沙盒复制 181 件
```

关键行号（本班 `rg` 复核，**锚点零漂移**）：

```
src/questionnaire/exporters.py:13  def export_to_docx        :60  run.font.name = "楷体"      :121 style="Light Grid Accent 1"
src/output/docx_exporter.py:30     from . import docx_styles as S   :386 def _setup_page   :919 def _add_likert_table   :961 def build_questionnaire_docx
src/ui/paper_writing_ui.py:512-545（内联 Document()，:519 font.name="SimSun"）
src/ui/questionnaire_panel.py:826 下载 Word(路 C) / :838 下载 PDF(路 C) / :865 下载 HTML(内联 CSS 块 :854-862，:855 body line-height:1.8、:856 h1 #2c3e50)
src/ui/items_upload_panel.py:326-338 Word(路 A，:335 按钮) / :345-354 PDF(路 C 的 build_questionnaire_pdf，定义在 exporters.py:449，:354 按钮)   ← 同一面板相邻两枚按钮分属两套体系
```

零改动自证：

```
$ git status --porcelain            # 14 行，与开工同（app.py/pytest.ini/requirements-lock.txt 三件 M 属他班，未碰）
$ git diff --numstat -- src/questionnaire/exporters.py src/output/docx_exporter.py src/output/docx_styles.py | wc -l
0
$ ls docs/insights/psy-docx-style-unify-design-20260923.md   # 本稿，唯一新增受版件
```

新增件均在 `.gitignore:29 tmp/` 下（`git check-ignore -v tmp/x` 已验）：`tmp/s923-19/style_diff_probe.py`、`r1.txt`、`r2.txt`、`litfeed_sandbox/`。

---

## 七、本班新否证/新增的事实（供主班入台账）

1. **纸张尺寸分叉（Letter vs A4）** — 上游 s922-22 的三路对账**没有抽 `pgSz`**（它抽了 `pgMar`），所以这条一直没人看见；且 `docx_styles` 无页宽常量、`tests/` 对 A 路页尺寸零钉桩 ⇒ **看守真空**。建议进待人工，优先级高于原"样式统一"整题。
2. **「两路都产问卷类 docx」前提收窄** — 实测是「设计报告」与「空白施测卷」两种文档；且**范围实为四路 docx（含 `paper_writing_ui.py` 内联路）＋ 一处同面板 Word/PDF 跨体系配对**。上游把本题写成"两路重复建设"，若照字面施工会漏掉路 3。
3. **路 A 的 `pStyle`/`outlineLvl` 双 0** — 上游只说"A/B 与常量一致"，未指出 A 路产物在 Word 里**没有大纲结构**；这使"统一"方向有了非美学判据（不能反向收敛到直接格式）。
4. **两条"钉 bug 现状"断言会挡住 P1 的正确修复** — `test_exporters_cjk_font_fallback.py:227` 与 `test_exporters_docx_geometry.py:219` 把"楷体无东亚映射"钉成了期望值 ⇒ 属纪律档 §十二「两笔一体」型（quant `test_bark_channels_resid_q92211.py:56` 同型），改它必须连生产码意图一起交裁决。
5. `docx_exporter.py` 纯 CRLF／`exporters.py` 纯 LF ⇒ 案乙任何一步的行尾风险都要单独自证（纪律档「行尾逐文件量」条目在本仓的具体命中）。
6. **例数口径有两种，别混**（本班 s923-20 落地时自纠）：`tests/test_questionnaire_export_docx.py` ＝ **13 个 `def test_` 函数 / 22 条 pytest 收集用例**（`--collect-only -q` 现取），上游 s922-22 说的「22 例」用的是**收集数**、并没有错；本稿第二节引用的 6/7/14 也是收集数。⇒ 后续工单**统一用收集数**，且注明口径。环境：`.venv` python-docx **1.2.0**（本班实测）。

---

## ⚠ 勘误横幅（2026-10-02 追加，s930-39；append-only，正文一字未改）

> **六处被磁盘否证（s927-52 点名，本班逐处现值复核确认）——引用本档 P3/P4 行时以下表为准**：
>
> | # | 本档原文 | 磁盘现值 | 取证 |
> |---|---|---|---|
> | 1 | P3 提议新增 `LINE_SPACING_REPORT=1.8` | `docx_styles.py` **无此常量**（grep 0 命中）——P3 尚未实施 | `grep -c LINE_SPACING_REPORT src/output/docx_styles.py` → 0 |
> | 2 | P3 提议新增 `PAGE_WIDTH_CM=21`/`PAGE_HEIGHT_CM=29.7` | 已由**另一路径落地**：`_setup_page` 直接写 `Cm(21)/Cm(29.7)`（s924-26 A4 改版），且 s930-11 已建读回钉（test_docx_page_layout_readback_s93011.py 3 passed）——「补常量」形态已被超越 | s930-11 result |
> | 3 | 「两处钉断言挡路」 | 现值钉面非挡路：七件 docx 族 **92 passed**（2026-10-02 实跑），P1 的两枚「钉 bug 现状」红是否仍在以单跑为准 | 七件定向命令在档 |
> | 4 | 「三个测试收集数 20/6/13…」 | 现值漂移：test_fonts=14 def/test_docx_export=13 def/geometry=6 def（用例数随期数增长） | `grep -c "def test" <件>` |
> | 5 | `paper_writing_ui.py:512` | 现值 **678 行文件**（:512 超界或已漂）——引行号时须重定位 | `wc -l src/ui/paper_writing_ui.py` → 678 |
> | 6 | `app.py:2284` | 现值 **2413 行文件**（app.py 经多轮收编，行号全档漂移） | `wc -l app.py` → 2413 |
>
> **1.8 两义说明**（防混淆）：`exporters.py:38` 的 `1.8`＝**docx 行距倍数**（line_spacing）；`app.py` 旧 :2284 的 `1.8`＝**CSS line-height**（Web 层）——与 s923-19「1.8 还是 1.5」行距裁决相关、**与任何统计量无关**。
> **请勿按本档 P3/P4 行号与收集数原文引用**；done/s923-19.result.md:92/94 为信箱历史件不回改（同批六处否证见该档）。
