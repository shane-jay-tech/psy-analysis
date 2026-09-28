# s927-52 · P3/P4 版式改值项人工拍板决策清单（承 s923-19）

生成：2026-09-29 03:4x｜执行班：`qoder-executor-20260929-0345-psy99`｜仓/HEAD：`D:\code\psy-analysis` @ `16cddbb`
性质：**只读汇编，零改值**——本档不修改任何常量、不接线、不删常量、不动生产码。所有「推荐」是**材料性排序**（按"改动可见面最小 / 可回滚性最强"排），**最终拍板留人工**，执行手不代作选择（纪律档 §五.3）。

上游锚点：`zcode-bridge/done/s923-19.result.md:92` 列出 6 个必裁项；设计稿 `docs/insights/psy-docx-style-unify-design-20260923.md`（151 行，已入库）§四 P3/P4 行。

---

## 零、开工先复核锚点：**其中 1 项已被后人闭合，2 项语义已被改写**

| s923-19 的表述 | 磁盘实况（本班实测） | 结论 |
|---|---|---|
| 「路 A/D 纸张 = `12240×15840` US Letter，与路 C 的 A4 不同」＝**最高优先缺陷** | `src/output/docx_exporter.py:393-405` `_setup_page` 现在**显式**写 `section.page_width = Cm(21)` / `page_height = Cm(29.7)`；`tests/test_exporters_docx_geometry.py:54-55` 钉 `ACTUAL_PG_W_TWIPS = 11906` / `16838` | 🔴**已闭合，不该再进清单**。闭合人＝commit `68a8822`「s924-26 空白施测卷显式钉 A4 页尺寸（走 `_setup_page` 这条路的文档此前一直继承 Letter）」，已入库非在途 |
| 「楷体只赋 `run.font.name`、**未过** `_set_east_asian_font` ⇒ 设了楷体是假象」 | `src/questionnaire/exporters.py:66-70`：`run.font.name = "楷体"` **＋** `_set_east_asian_font(run, "楷体")`，注释自标 `s924-09（P1 楷体修复）` | 🟡**前提变了**：楷体现在**真生效**。"留不留"从"留个假象"变成"留一个用户可见的中文字体改版" |
| 「两条'钉 bug 现状'断言挡路，修楷体必红」 | `tests/test_exporters_cjk_font_fallback.py:247` 已改成 `assert seen == [..., "楷体"]`、`:251` 节标「s923-19 预言的『两笔一体』改写位」；`test_exporters_docx_geometry.py:233` 已从 `not in` 翻成 `assert 'w:eastAsia="楷体"' in subtitle` | 🟡**挡路已清**（commit `5d9acb5` 两笔合笔）。⇒ 后续任何一期的回归面都比设计稿记的要小 |

**P0/P2 现状**（不属拍板项，但影响下面每一条的"改后成本"）：`tests/golden/` **不存在** ⇒ P0 基线快照未做；`src/questionnaire/exporters.py` 全文 **无一条 `docx_styles` import** ⇒ P2 未做，"路 C 完全不吃常量"这条**至今成立**（反观 `docx_exporter.py:138/140/142/143` 已吃 `S.LINE_SPACING`/`S.FIRST_LINE_INDENT_CM`/`S.SPACE_*_HEADING_PT`）。`grep -rln docx_styles src/ tests/` ＝ `src/output/docx_exporter.py`、`tests/test_fonts_and_docx_styles.py` **两枚**。

**常量表现值 = 25 个**（`python -c` 数得，与设计稿"从 25 涨到 ~31"一致）：`FONT_BODY_LATIN/BODY_CJK/HEADING_LATIN/HEADING_CJK`、`SIZE_TITLE/H1/H2/H3/BODY/CAPTION/TABLE`、`LINE_SPACING`、`SPACE_BEFORE_HEADING_PT/AFTER_HEADING_PT/AFTER_BODY_PT`、`FIRST_LINE_INDENT_CM`、`MARGIN_TOP/BOTTOM/LEFT/RIGHT_CM`、`TABLE_HEADER_FILL/BORDER_COLOR/BORDER_SIZE`、`FIG_PREFIX/TABLE_PREFIX`。表内**没有**任何一条对应下述 ①～⑦。

---

## 一、逐项清单（13 项待拍板 ＋ 2 项登记类）

图例：**[开]**＝两候选都合法、必须有人选；**[登]**＝不改任何用户可见值、纯登记；影响面「会红」＝改这个候选后**必须连断言一起改写**的测试件。

### ① 封面主标题字号　**[开]｜P3＋P4**
- 现值：`src/questionnaire/exporters.py:57` `run.font.size = Pt(26)`（路 C 独有；常量表 `docx_styles.py:12` `SIZE_TITLE = 16` 路 A 用）
- 候选 A：**认 26pt 为本意** → P3 新增 `SIZE_REPORT_TITLE = 26`，两路并存两档标题
- 候选 B：**收敛到 16pt** → 改 `exporters.py:57`，与 `SIZE_TITLE` 对齐，常量表不涨
- 影响面：会红 `tests/test_exporters_docx_geometry.py:224`（`assert '<w:sz w:val="52"/>' in cover`，52 半磅＝26pt）、`test_questionnaire_export_docx.py`（收集 22）；候选 B 另含**用户可见改版**（封面字变小）
- 材料性推荐：**A**（扩表）。B 是唯一"缩小用户已有观感"的选项，且 26pt 在设计稿维度 15 里被记为路 C 一路的一致值（`{24,32,52}`），不像笔误。

### ② 封面段前留白　**[开]｜P3**
- 现值：`exporters.py:55` `title_para.paragraph_format.space_before = Pt(60)`；常量表**无"封面留白"档**
- 候选 A：新增 `COVER_SPACE_BEFORE_PT = 60`（承认封面是独立角色）
- 候选 B：不新增，把 60 视为"封面特例"永久留在字面量里（= 承认常量表覆盖不到封面）
- 影响面：候选 A 需同步 `tests/test_fonts_and_docx_styles.py`（收集 21，含常量值/数量类钉桩）；两者都**不改任何产物字节**
- 材料性推荐：**A**，但优先级低于 ①③⑧——这是"表变全"而非"版式变"。

### ③ 行距 1.8 vs 1.5　**[开]｜P3＋P4（真分叉项）**
- 现值：路 C `exporters.py:38` `style.paragraph_format.line_spacing = 1.8`（写在 `Normal` **样式层**，`document.xml` 内 `w:line` 0 次）；路 A/D 逐段 `w:line = 360`＝1.5，取自 `docx_styles.py:21` `LINE_SPACING = 1.5`
- 候选 A：**1.8 为报告本意** → 新增 `LINE_SPACING_REPORT = 1.8`，与 `LINE_SPACING=1.5` 并存（按文档角色分档，正是设计稿案乙 profile 的雏形）
- 候选 B：**全线收敛 1.5** → 改 `exporters.py:38`，与设计常量统一
- 影响面：会红 `test_exporters_docx_geometry.py`（`:161` 注释明确"行距 1.8 写 432"，Normal 样式快照）＋ `test_fonts_and_docx_styles.py`；**A/D 两路产物 XML 的落点层也不同**（样式层 vs 段落层），任一路"统一"都不是改一个数就完事
- 材料性推荐：**A**。理由：B 会让**每一份既有设计报告**的行距肉眼可见地变密，且 1.8 是"样式层一次生效"、1.5 是"逐段生效"——两路结构语义相反，硬凑一个数会把 diff 面撑到不可归因。

### ④ Heading 字号族　**[开]｜P3**
- 现值：路 C `exporters.py:41` `{1:(22,True),2:(16,True),3:(14,True)}` ＝ 22/16/14pt；常量表 `docx_styles.py:13-15` `SIZE_H1/H2/H3` = **14/13/12**
- 关键事实：**两路都不符合常量表**（设计稿已点名"不只 C 的 26pt 一个表外值"）。所以这不是"C 对不对"，而是"常量表本身还算不算规范"
- 候选 A：承认现实档 22/16/14，**改写** `SIZE_H1/H2/H3`（＝同时判定常量表此前是"未执行的期望"）
- 候选 B：新增 `SIZE_H1_REPORT` 等三路各档，常量表按角色分裂
- 影响面：A 必红 `test_fonts_and_docx_styles.py` 的常量值三元组钉桩；`test_exporters_docx_geometry.py:176-199` 现钉的是"sz 与 szCs 成对相等"（s924-10 已一致化），A 需同步该处期望半磅值 44/32/28
- 材料性推荐：**先 A 后 B**——先由人确认"常量表 14/13/12 是不是从未生效的旧规范"，这个事实问题一答，④⑤⑦ 三项会一起降resolution。

### ⑤ 副标题楷体留不留　**[开]｜P3（语义已因 s924-09 改写）**
- 现值：`exporters.py:66` latin 槽 `"楷体"` ＋ `:70` `_set_east_asian_font(run, "楷体")` **双槽都写**；常量表只有 `FONT_BODY_CJK="宋体"` / `FONT_HEADING_CJK="黑体"`，**无副标题字体档**
- 变化点：s923-19 时"设了楷体是假象"，**今天已不是假象**（东亚映射已补，且被 `test_exporters_docx_geometry.py:233` 钉成期望）。⇒ 选"不留"从此**是一次真实的中文字体改版**，不再是"删个装饰"
- 候选 A：留楷体 → 新增 `FONT_SUBTITLE_CJK = "楷体"`（P3），并在 P4 profile 里成对补 PostScript 名 `KaiTi`
- 候选 B：随路收敛到 `FONT_HEADING_CJK="黑体"`（＝改 `exporters.py:66/70` 两处）
- 影响面：B 必红 `test_exporters_cjk_font_fallback.py:247`（`seen` 列表末位 `"楷体"`）＋ `test_exporters_docx_geometry.py:233`；A 需扩 `test_fonts_and_docx_styles.py`
- 材料性推荐：**A（留）**。设计稿维度 13/14 的收敛正道是"字体成对命名"（`src/visualization/fonts.py:41-57` 已有 `KaiTi` 映射），不是砍字体。

### ⑥ 列表左缩进 Cm(1)　**[开]｜P3**
- 现值：`exporters.py:158` `p.paragraph_format.left_indent = Cm(1)`（落盘 567 twips，`test_exporters_docx_geometry.py:216` 记"读回 1.000125 cm"）；常量表只有 `FIRST_LINE_INDENT_CM=0.74`，**无左缩进档**
- 候选 A：新增 `INDENT_LIST_CM = 1`
- 候选 B：不扩表，永久留字面量（同 ②B）
- 影响面：仅 `test_fonts_and_docx_styles.py` 常量类断言；**两候选都不动产物字节**
- 材料性推荐：**A**，低优先。

### ⑦ 标题强调色 2C3E50　**[开]｜P3**
- 现值：`exporters.py:49` `h_style.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)`；常量表颜色只有 `TABLE_BORDER_COLOR="000000"`，**无 heading 色档**
- 候选 A：新增 `COLOR_HEADING_ACCENT = "2C3E50"`
- 候选 B：随"论文三线朴素风"收敛到黑色（＝改 `:49`，**彩色标题消失**，用户可见）
- 影响面：B 会红 `test_exporters_docx_geometry.py:207`（现钉 `w:eastAsia="黑体"` 同族样式断言）及路 C 样式快照；A 只扩 `test_fonts_and_docx_styles.py`
- 材料性推荐：**A**。设计稿对颜色的原话是"只登记归属，不判对错"，没有颜色规范来源支持 B。

### ⑧ 表格语义：`Light Grid Accent 1` 还是三线表　**[开]｜P4（设计稿记的"语义相反"项）**
- 现值：路 C `exporters.py:131` `doc.add_table(..., style="Light Grid Accent 1")`（命名表样、`tcBorders` 0）；路 A `docx_exporter.py:303` `_apply_three_line_borders`（`tcBorders` 28、`w:val="nil"` 147、`sz=4`）
- 候选 A：**统一三线表**（设计稿案乙第 4 步原话："吸收路 A 的 `_apply_three_line_borders`，废掉路 C 的 `LightGrid-Accent1`"）
- 候选 B：**按角色分档**——报告/设计文档用彩色命名表样，论文/施测卷用三线表（即 profile 携 `table_semantics` 字段）
- 影响面：A 改 `exporters.py:131`，必红 `test_questionnaire_export_docx.py`（收集 22）；两候选都要 `test_fonts_and_docx_styles.py` 同步
- 材料性推荐：**B**。A 是"一路吞并另一路"，而两路文档用途本就不同（彩色网格卷 vs 学术三线表），A 会把路 C 的**每一张既有表格**外观改掉。

### ⑨ 路 A 获得命名样式（`pStyle`）　**[开]｜P4**
- 现值：`docx_exporter.py:129` `p = doc.add_paragraph()` ＋ 直接格式（`:130-143` 手写 alignment/line_spacing/indent/space），**不写 `pStyle`**；路 C 走 `doc.styles["Heading N"]`＋`style="List Bullet"`
- 候选 A：路 A 改走 `pStyle`（设计稿案乙第 3 步：一次性补回目录／导航窗格／`outlineLvl`／读屏结构）
- 候选 B：维持直接格式，只做常量收敛（＝放弃目录/读屏结构收益）
- 影响面：`styles.xml` **必变**；会红 `test_docx_export.py`(13)、`test_deliverable_docx_export.py`(7) 及设计稿列的 geometry/questionnaire_export 族；A 是**功能增益**型改动（多出可导航目录），不是纯改版
- 材料性推荐：**A，但单独成单**。这是 13 项里唯一"改完用户能感到多了能力"的，值得和纯外观项分开验收。

### ⑩ 路 3 内联 `Document()` 归位　**[开]｜P4**
- 现值：`src/ui/paper_writing_ui.py:516` `doc = Document()` **在 UI 层自建文档**（设计稿记 `:512`，已漂 +4）；`docx_exporter.py` 内另有 6 处 `Document()`（`:640/890/1019/1106/1142`，均在 builder 内，合法）
- 候选 A：UI 改调 `docx_exporter` 既有 builder，删内联自建（案乙第 5 步）
- 候选 B：保留内联，仅把该路也纳入 profile
- 影响面：A 触 `paper_writing_ui.py`（P4 触碰文件清单已列）＋ 该路样张的 `docDefaults` 继承面
- 材料性推荐：**A**。现状是"第 7 个事实源"，不做完这条，①～⑨ 的任何统一都会在路 3 漏掉。

### ⑪ `SPACE_AFTER_BODY_PT = 0` 是接线还是删常量　**[开]｜P3/P4 之间**
- 现值：`docx_styles.py:24` `SPACE_AFTER_BODY_PT = 0`，**全仓消费方 0 处**（`grep -rn SPACE_AFTER_BODY_PT src/ tests/` 除定义行外无命中）；正文实际生效值由模板 `docDefaults after=200` 继承＝**10pt**
- 这条设计稿原话定性为"**常量在说谎**"，且已被 `test_fonts_and_docx_styles.py:208-220` 钉成**缝宽快照**：注释写明"期望值从 `ds.SPACE_AFTER_BODY_PT` **动态取** ⇒ 常量一改，缝宽就变，本例立刻转红，逼一次评审"，且明确"本例不主张 10pt 是对的、也不主张 0 是对的"
- 候选 A：**接线**（`apply_profile` 显式改写 `docDefaults`，案乙第 2 步）→ 0 变成真值，正文段距变紧
- 候选 B：**删常量**（承认"正文段后距"不归常量表管，让 10pt 如实来自模板）
- 影响面：A **改变所有走路 A 的文档正文间距**（10pt→0，用户可见，且是全局面）；B 只红 `test_fonts_and_docx_styles.py:208` 一条＋需删定义
- 材料性推荐：**这一项请人工单独定，别顺手绑在 ①～⑩ 里**。A 的全局面是 13 项里最大的，且"0 还是 10pt"是排版规范问题，代码里没有任何规范来源可依据。

### ⑫ `TABLE_HEADER_FILL = "DDDDDD"` 接线还是删　**[开]｜P4**
- 现值：`docx_styles.py:34` `TABLE_HEADER_FILL = "DDDDDD"`，**消费方 0 处**（同 ⑪ 双轨 grep 实测）
- 候选 A：三线表表头接 `DDDDDD` 底纹（案乙第 4 步附带的"要么接线要么删"）
- 候选 B：删常量
- 影响面：A 会让**每张三线表表头多一层底纹**（用户可见，含论文类交付物）；B 无可见变化
- 材料性推荐：**B（删）**，除非人工确认底纹是既定规范。依据：设计稿对 `DDDDDD` 的处置与 `SPACE_AFTER_BODY_PT` 同批登记，均标注"只登记归属"，无规范支持它生效。

### ⑬ 补 `PAGE_WIDTH_CM = 21` / `PAGE_HEIGHT_CM = 29.7` 常量　**[登]｜P3**
- 现值：A4 已在两路代码里硬写（`exporters.py:27-28`、`docx_exporter.py:404-405`），常量表**无页宽页高档**
- 候选 A：补常量、不改值（设计稿原话"这条是补常量、不改值"）
- 候选 B：等 P4 的 `apply_profile` 一起写
- 影响面：**零可见变化**；A4/Letter 之争**已不存在**（见 §零），所以这项不再是 s923-19 记的"路 A 的 Letter 是否要改 A4"
- 材料性推荐：**A，可并入任意一期**（唯一一条纯登记项）。

### ⑭（登记）死导入 `Inches` / `WD_STYLE_TYPE`　**[登]｜P1 未完成子项，非版式裁决**
- 现值：`exporters.py:19` 导入 `Inches`、`:21` 导入 `WD_STYLE_TYPE`，**全文各只出现 1 次＝只在 import 行**，确认仍死码；设计稿维度 18 原话"顺手项，不属版式裁决"
- 候选 A：删导入（P1 ②，纯无裁决缺陷）；候选 B：留
- 影响面：无（设计稿判"③无红"同族）；材料性推荐 **A**

---

## 二、汇总表（勾选面）

| # | 项 | 期 | 候选 A（保现值／扩表） | 候选 B（收敛／改版） | 用户可见？ | 会红的测试件 | 材料性推荐 |
|---|---|---|---|---|---|---|---|
| ① | 主标题 26pt | P3 | 扩 `SIZE_REPORT_TITLE=26` | 收敛 16pt | B 可见 | geometry:224、questionnaire_export_docx(22) | A |
| ② | 封面段前 60pt | P3 | 扩 `COVER_SPACE_BEFORE_PT` | 永久字面量 | 否 | fonts_and_docx_styles(21) | A（低优先） |
| ③ | 行距 1.8 vs 1.5 | P3/P4 | 扩 `LINE_SPACING_REPORT=1.8` | 全线 1.5 | **B 全局可见** | geometry(Normal 432)、fonts_and_docx_styles | A |
| ④ | Heading 22/16/14 | P3 | 改常量表为 22/16/14 | 按角色分裂 | 否（先定事实） | fonts_and_docx_styles、geometry:176-199 | 先答事实再选 |
| ⑤ | 副标题楷体 | P3 | 留＋扩 `FONT_SUBTITLE_CJK` | 收敛黑体 | **B 可见**（s924-09 后为真改版） | cjk_font_fallback:247、geometry:233 | A |
| ⑥ | 列表缩进 Cm(1) | P3 | 扩 `INDENT_LIST_CM=1` | 永久字面量 | 否 | fonts_and_docx_styles | A（低优先） |
| ⑦ | 强调色 2C3E50 | P3 | 扩 `COLOR_HEADING_ACCENT` | 收敛黑色 | **B 可见** | geometry:207 族 | A |
| ⑧ | 表格语义 | P4 | 全线三线表 | 按角色分档 | **A 全局可见** | questionnaire_export_docx(22) | B |
| ⑨ | 命名样式 pStyle | P4 | 路 A 走 pStyle | 维持直接格式 | A 增益（出目录） | docx_export(13)、deliverable_docx(7) | A，单开一单 |
| ⑩ | 路 3 归位 | P4 | UI 改调 builder | 保留内联 | 否 | 路 3 样张面 | A |
| ⑪ | `SPACE_AFTER_BODY_PT=0` | P3/P4 | 接线（0 生效） | 删常量 | **A 全局可见** | fonts_and_docx_styles:208（动态取，改即红） | **留人工单定** |
| ⑫ | `TABLE_HEADER_FILL` | P4 | 表头接 DDDDDD | 删常量 | A 可见 | fonts_and_docx_styles | B（删） |
| ⑬ | 页宽页高常量 | P3 | 补常量不改值 | 等 P4 | 否 | 无 | A |
| ⑭ | 死导入 | P1 | 删 | 留 | 否 | 无 | A |

**已完成、本轮无需拍板**：路 A 纸张 Letter→A4（`68a8822`）、楷体东亚映射（`5d9acb5`）、Heading `szCs` 一致化（`5d9acb5`）、两条"钉 bug 现状"断言改写（`5d9acb5`）。

---

## 三、本班对设计稿/上游的否证与漂移（照盘改，不改判据）

1. 🔴 **纸张项已从"待裁决"变成"已闭合"**：s923-19:92 与 §四 P4 行、§五.105 都把"路 A 的 Letter 是否要改 A4"列为必裁项，但 `docx_exporter.py:393-405` 已在 HEAD 里显式钉 A4。⇒ **清单里已剔除**，拍它等于拍一件已发生的事。
2. 🟡 **测试收集数 3 处漂移**（`python -m pytest --collect-only -q` 逐件实测）：`test_questionnaire_export_docx.py` 设计稿 P4 行写 **13**、正文 62 行写 22 ⇒ **实为 22**；`test_questionnaire_export.py` 写 14 ⇒ **实为 16**；`test_fonts_and_docx_styles.py` 写 20 ⇒ **实为 21**。（`geometry`=6、`cjk_font_fallback`=7 两处对得上。）派单时请以实测值为准。
3. 🟡 **行号漂移**：路 3 内联 `Document()` 设计稿记 `paper_writing_ui.py:512` ⇒ 实为 **`:516`**；楷体锚点 s923-19 记 `exporters.py:60` ⇒ 实为 **`:66`＋`:70` 两行**（因已修复而变长）。
4. 🟡 **`app.py:2253/2284` 只有一处仍对**：`:2253` 确为 `from src.questionnaire.exporters import export_to_docx` ✅；`:2284` 现是一行 CSS（`body {{ font-family: ... line-height: 1.8; }}`），**不是导出调用面**。app.py 内真实导出调用面为 `:2253-2254`（docx）与 `:2265-2266`（pdf）。`app.py` 属 §C 在途禁碰件，本班**未做任何修改**，仅作登记。
5. ⚪ `zcode-bridge/inbox/s927-52.task.md` 的横幅把设计稿原句截成「`LightGrid-Accen…`」，盘上 python-docx 的样式名实为 `"Light Grid Accent 1"`（带空格），grep 时用后者才命中。

## 四、红线自查

- 未修改任何常量、未接线、未删常量、未加白名单、未动 `src/`、`tests/`、`app.py`、`pytest.ini`；本班在 psy 的**唯一**新增件是本档。
- 未触碰统计数值/被试数据/医疗内容：本档全部为版式属性（字号、行距、字体、缩进、颜色、表样、页尺寸）。`exporters.py:38` 的 `1.8` 是**行距倍数**，与 CSS `line-height`、与任何统计量无关——已在 ③ 内注明二者非同一物。
- 所有「推荐」为材料性排序，**判定留人工／主班**；尤其 ④（常量表是否曾为规范）与 ⑪（0 还是 10pt）是事实/规范问题，执行手无权裁定。
