# psy docx 两常量说谎裁决材料（`SPACE_AFTER_BODY_PT` / `TABLE_HEADER_FILL`）· s923-18 · 2026-09-23

> **性质：只读裁决材料。常量未动、测试未动、`src/` 零改动**（自证见第六节）。
> 上游出处：`zcode-bridge/done/s922-22-psy-docx-styles-census.result.md:116-117`（两条都写"交人工裁决、本单不动"）。
> 本件的作用是**把两条出口的后果量清楚**，不是重做普查——机制结论与 s922-22 一致，但所有读数**今日现场复算**。

## 〇、锚点复核（含一处独立复算的加强证据）

| 前提 | 实测（cwd `D:\code\psy-analysis`） | 判定 |
|---|---|---|
| `src/output/docx_styles.py:24 SPACE_AFTER_BODY_PT = 0` | `sed -n '24p'` 逐字相符 | ✅ 零漂移 |
| `src/output/docx_styles.py:34 TABLE_HEADER_FILL = "DDDDDD"` | `sed -n '34p'` 逐字相符 | ✅ 零漂移 |
| `tests/test_fonts_and_docx_styles.py:143/:150` 两钉桩 | 两行现读见第一节，逐字未变 | ✅ |
| 「正文段后距实际 10pt」 | **独立复算成立**（非抄上游）：本机用 `.venv` 真造一份 docx，`word/styles.xml` 的 `<w:docDefaults>` 实测为 `<w:pPrDefault><w:pPr><w:spacing w:after="200" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>` ⇒ **`after=200` 单位 1/20 磅 = 10pt**；同件 `word/document.xml` 里正文段的 pPr 只有 `<w:spacing w:line="360" w:lineRule="auto"/>`（**无 `w:after`**）⇒ 正文继承 10pt。命令与读数在第五节 E1 | ✅ 坐实 |
| 「两常量零消费方」 | `rg -n "SPACE_AFTER_BODY_PT\|TABLE_HEADER_FILL"` 全仓（含 `tests/`、`docs/`、gitignored 件）：命中 **4 行 = 2 处定义 + 2 处测试钉桩**，`src/` 内除定义文件本身**再无第三处引用** | ✅ 坐实 |
| （新查）底色是否在别处"事实上被写了" | `rg -n "w:shd\|shading" src/` → **0 命中**；三线表逻辑仅 `src/output/docx_exporter.py` 一家 | ✅ 无第二真相源 |

## 一、受影响测试清单（断言**逐字**引用，含其结构风险）

```python
# tests/test_fonts_and_docx_styles.py:139-145
def test_docx_size_and_spacing_constants_pinned():
    assert (ds.SIZE_TITLE, ds.SIZE_H1, ds.SIZE_H2, ds.SIZE_H3) == (16, 14, 13, 12)
    assert (ds.SIZE_BODY, ds.SIZE_CAPTION, ds.SIZE_TABLE) == (12, 10.5, 10.5)
    assert ds.LINE_SPACING == 1.5
    assert (ds.SPACE_BEFORE_HEADING_PT, ds.SPACE_AFTER_HEADING_PT, ds.SPACE_AFTER_BODY_PT) == (12, 6, 0)   # :143
    assert ds.FIRST_LINE_INDENT_CM == 0.74

# tests/test_fonts_and_docx_styles.py:147-153
def test_docx_apa7_margins_and_table_style_pinned():
    assert (ds.MARGIN_TOP_CM, ds.MARGIN_BOTTOM_CM) == (2.54, 2.54)
    assert (ds.MARGIN_LEFT_CM, ds.MARGIN_RIGHT_CM) == (3.18, 3.18)
    assert ds.TABLE_HEADER_FILL == "DDDDDD"                                                                 # :150
    assert ds.TABLE_BORDER_COLOR == "000000"
    assert ds.TABLE_BORDER_SIZE == 4
    assert (ds.FIG_PREFIX, ds.TABLE_PREFIX) == ("图", "表")
```

结构风险（决定"删除"案的真实代价，普查没写的部分）：

- **`:143` 是一钉三元组**：`SPACE_AFTER_BODY_PT` 与两个**已接线且正确**的标题距常量同绑一行 ⇒ 动它必然同时把 `SPACE_BEFORE_HEADING_PT/SPACE_AFTER_HEADING_PT` 的读数拉进同一条红。拆成三行是安全前置，但**拆断言＝改测试语义**，不在执行手授权内。
- **删除常量后 `:143/:150` 不是"断言失败"而是 `AttributeError`**（`ds` 上没这个属性）⇒ 失败形态从"可读的红"退化成"测试报错"，日志里更像套件坏了。**两案的"红"不一样，别按同一验收口径写。**
- 现状基线：`PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest tests/test_fonts_and_docx_styles.py tests/test_exporters_docx_geometry.py -q` → **26 passed in 1.37s**（全绿，2026-09-23T12:1x 现取）。

## 二、四格影响表（两常量 × 两案）

|  | **案 A：接线** | **案 B：删除** |
|---|---|---|
| **`SPACE_AFTER_BODY_PT = 0`**<br>（正文段后距） | **改什么**：`docx_exporter.py:130-136` 的 `level == 0` 分支补 `pf.space_after = Pt(S.SPACE_AFTER_HEADING_PT 之外)` ⇒ 实写 `Pt(S.SPACE_AFTER_BODY_PT)`；`:154-161` 的 `_add_paragraph_with_inline_format` 同分支也要补（否则**带 `**粗体**` 的正文漏接**，出现两种正文段距）。<br>**测试**：`:143` **保持绿**（值不变），但要新增 XML 级钉桩证 `w:after="0"` 真落盘（现无任何测试覆盖正文 after ⇒ 接线本身**无验收**）。<br>**用户可见后果**：论文/问卷 Word 正文**段与段之间从 10pt 间隙塌成 0pt**，只剩 1.5 倍行距 ⇒ 全文行数增加、观感变"整块"。这是**版式回归**，影响所有已生成的历史稿与对比截图。<br>**风险**：一处漏补即产生"同类段落两种间距"的新不一致，比现状更难解释。 | **改什么**：删 `docx_styles.py:24`＋改 `:143`（去三元组里的第三项）。<br>**测试**：`test_docx_size_and_spacing_constants_pinned` 必改；`src/` 无其它引用 ⇒ 零连带红。<br>**用户可见后果**：**无**（产物里从来没有这个属性）。<br>**风险**：意图丢失——下一个读 `docx_styles.py` 的人仍可能以为"正文段距由本文件管"。需在同文件留一行"正文段距由模板 `docDefaults after=200` 决定"的注释，否则删了等于把谎言改成沉默。 |
| **`TABLE_HEADER_FILL = "DDDDDD"`**<br>（表头底色） | **改什么**：`_add_dataframe_table`（`:254-293`）表头循环里给每个 `cell._tc.get_or_add_tcPr()` 加 `<w:shd w:fill="DDDDDD">`。<br>**测试**：`:150` 绿；但 `rg "w:shd" src/` 现为 0 ⇒ **接线会新增一个全仓唯一的底色彩源**，`tests/test_exporters_docx_geometry.py` 的 XML 快照口径需扩面（它现在只钉页面/字号族）。<br>**用户可见后果**：表头变灰底。**与三线表规范正面冲突**（见第三节），且灰底在打印/黑白复印下会把表头文字压暗。<br>**风险最高**：它不是"补一个漏"，是**改一个既定规范决定**。 | **改什么**：删 `docx_styles.py:34`＋删 `:150`。<br>**测试**：`test_docx_apa7_margins_and_table_style_pinned` 必改（同左，`AttributeError` 形态）；同函数里 `TABLE_BORDER_COLOR/TABLE_BORDER_SIZE` **确实被 `_apply_three_line_borders` 消费**（`:318-320`）⇒ 只有 `TABLE_HEADER_FILL` 是孤儿，删它不影响同组其它钉桩的语义。<br>**用户可见后果**：**无**。<br>**风险**：几乎无。若将来产品要求"表头浅灰"，届时是**新的规范决定**，不该由一个残留常量代签。 |

## 三、与三线表规范的冲突说明（专给 `TABLE_HEADER_FILL`）

本仓"三线表"的实现口径是**代码自己写明的**，不是外部解读：

- `docx_exporter.py:255` 函数 docstring：`"""三线表风格。"""`
- `docx_exporter.py:296-297`：`"""三线表：仅顶部、表头底、表尾有横线。"""`
- `docx_exporter.py:321-327` 逐边设值：`top = (i==0)`、`bottom = (i==0 or i==n_rows-1)`、`left/right/insideH/insideV = False`（写成 `w:val="nil"`）
- `docs/DELIVERY_PACKAGE_GUIDE.md:44` 对用户承诺：**「三线表样式（无竖线）」**；`docs/SYSTEM_REPORT.md:54,56,263` 三处把产物宣称为「APA 格式三线表」

三线表（GB/T 7713 系列与 APA 表格惯例共同点）只允许**顶线、栏目线、底线三条横线**，其要旨是"不用任何封闭框与**单元格填充**"——表头层次由**栏目线本身**表达，不靠底色。故：

> **接上 `TABLE_HEADER_FILL` ＝ 在产物里引入规范禁止的要素，同时让 `:297` 的 docstring 与对用户承诺的"三线表"变成新的一句谎。**
> 也就是说，这个常量若接线，不会修好"常量说谎"，而是把**一处**谎（常量与产物不符）**升级成两处**（常量接线了但与规范不符、docstring 与实际不符）。

另注：`rg "w:shd|shading" src/` 现 0 命中 ⇒ 不存在"别处已经在偷偷加底色"的第二真相源，删除案不会留下不一致现状。

## 四、建议案与理由（只出建议，处置权在人工）

1. **`TABLE_HEADER_FILL` → 建议案 B（删除）**，并在删除处留一行说明"三线表禁单元格底色，表头层次由栏目线表达"。
   理由：与规范正面冲突（第三节）、零消费方、零用户可见后果、`src/` 内除定义外 0 引用；唯一代价是改一条测试钉桩（`:150`），而那条钉桩今天钉的正是**一个不该存在的意图**。
2. **`SPACE_AFTER_BODY_PT` → 建议先做"诚实化"，不选 A 也不选 B，落 B′**：
   **保留常量但把值改成与产物一致（`10`），并在 `docx_exporter` 正文分支显式接线 `Pt(S.SPACE_AFTER_BODY_PT)`。**
   理由：
   - 案 A（接 `0`）是**唯一有实质用户可见后果**的一格，把 10pt 段间距压成 0 属版式改版，超出"消灭常量说谎"的原始目的，且现状 10pt 已被历史稿与既有截图验收过；
   - 案 B（删）把"正文段距是多少"这件事彻底变成模板隐式默认，下一个读码者只能去解 zip；
   - B′ 既让常量不再说谎、又**不改变任何产物字节语义**（显式 `after=200` 与继承 `after=200` 渲染等价），代价是要同步把 `:143` 的 `0` 改 `10` 并补一条 `w:after="200"` 的 XML 钉桩。
   - ⚠ **B′ 仍属"改版式代码 + 改测试语义"两件事**，且 `0 → 10` 是**改一个用户可见数值**——按纪律档红线口径，本单**不自行执行**，只把它作为建议递交。
3. 无论选哪格：**先把 `:143` 的三元组拆成三条独立断言**（单独一笔），否则将来任何一格的处置都会把两格无关常量的红混进同一行日志，验收期归因成本被人为放大。这条是三案共同的前置。

## 五、证据（复算命令与读数）

**E1 · 正文段后距实测 10pt**（`.venv/Scripts/python.exe`，python-docx 1.2.0，产物落在 gitignored 的 `tmp/s923-18/probe_spacing.docx`）

```bash
cd /d/code/psy-analysis && PYTHONUTF8=1 .venv/Scripts/python.exe - <<'PY'
import sys, zipfile, re; sys.path.insert(0,'.')
from docx import Document; from src.output import docx_exporter as E
d=Document(); E._setup_page(d)
E._add_paragraph(d,'正文样本',level=0,first_line_indent=True); E._add_paragraph(d,'标题样本',level=1)
d.save('tmp/s923-18/probe_spacing.docx')
z=zipfile.ZipFile('tmp/s923-18/probe_spacing.docx')
print(re.search(r'<w:docDefaults>.*?</w:docDefaults>', z.read('word/styles.xml').decode('utf-8'), re.S).group(0))
print(sorted(set(re.findall(r'<w:spacing[^/]*/>', z.read('word/document.xml').decode('utf-8')))))
print('body.space_after =', Document('tmp/s923-18/probe_spacing.docx').paragraphs[0].paragraph_format.space_after)
PY
```

读数（2026-09-23T12:1x）：

```
<w:pPrDefault><w:pPr><w:spacing w:after="200" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
document.xml 里出现的全部 spacing 元素（去重）：
  '<w:spacing w:line="360" w:lineRule="auto" w:before="240" w:after="120"/>'   ← 标题：240/120 twips = 12pt/6pt，与两枚已接线常量逐字相符
  '<w:spacing w:line="360" w:lineRule="auto"/>'                                  ← 正文：**没有 w:after** ⇒ 继承 docDefaults 的 200 = 10pt
body.space_after = None        ← 常量宣称的 0pt 从未落到段落上（python-docx 读回 None ＝ 未显式设值，不是"设成了 0"）
h1.space_after  = 76200 (EMU)  ← = 6pt，证 `_add_paragraph` 的 level>0 分支确实接线了
```

⇒ 同一段代码里"标题族已接线、正文族未接线"是**可对照的**，不是全局漏接；这让案 A 的落点非常窄（只差 `level == 0` 分支两行）。

**E2 · 消费方面**：`rg -n "SPACE_AFTER_BODY_PT|TABLE_HEADER_FILL"`（本机 rg 可用，纪律档 §十四）→ 恰 4 行：`src/output/docx_styles.py:24,34` ＋ `tests/test_fonts_and_docx_styles.py:143,150`。
**E3 · 底色彩源**：`rg -n "w:shd|shading" src/` → 0 命中。
**E4 · 测试基线**：`pytest tests/test_fonts_and_docx_styles.py tests/test_exporters_docx_geometry.py -q` → **26 passed in 1.37s**。
**E5 · 规范面**：`sed -n '296,327p' src/output/docx_exporter.py`（三线表逐边设值）＋ `docs/DELIVERY_PACKAGE_GUIDE.md:44`「三线表样式（无竖线）」。

## 六、零改动自证

```bash
cd /d/code/psy-analysis
git status --porcelain src/ tests/ ; git diff --numstat -- src/ tests/     # 均空输出
git status --porcelain                                                   # 只多 docs/insights/ 新报告
```

探针产物 `tmp/s923-18/probe_spacing.docx`（约 30 KB，`tmp/` 已被 `.gitignore:29` 忽略，**主班可直接删**）；
`tmp/__pycache__` 系本机解释器副产物，同样被忽略。

## 七、与本单无关但顺带撞到的事实（登记，不处置）

`s923-17` 的 i18n 运行期探针在自造 AppTest harness 下 14/14 撞到 `app.py:1417 → src/ui/renderers.py:30` 的
`'str' object has no attribute 'passed'`（在册 pytest harness 不复现、归因未坐实）。它与本单的 docx 版式无关，
但同属"导出/渲染面的产物一致性问题"，主班在排人工单时可以把两条并到一次"Word/PDF 版面级验收"里，避免两次重建夹具。
