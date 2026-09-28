# s928-01 · SPACE_AFTER_BODY_PT 案 B′ 接线实施（两笔落地记录）

- 班：`qoder-executor-20260929-0415-psy101`（写位路），2026-09-29，盘面 HEAD 实测 `73ed50f`。
- 卷宗：`zcode-bridge/inbox/s928-01.task.md`（首行逐字「SPACE_AFTER_BODY_PT 案 B′ 接线实施单（s927-51 拍板 B′，
  用户 2026-09-28 授权）」；台账 242① 同记「51 裁 B′ 并投实施单 s928-01（两笔拆分，任一笔红即停）」）。
- 拍板依据：`zcode-bridge/outbox/s927-51.result.md`（**实施前已读全文**）＋
  `docs/insights/s927-51-space-after-body.md` §一／§三（接线落点与测试面口径）。
- 结果：**两笔均落地、均实测过绿**，零 git 写操作；交付物留工作树待主班合提。

## 1 改了什么（四处生产码 ＋ 一枚测试件）

| 笔 | 文件 | 位置 | 改动 |
|---|---|---|---|
| 第一笔 | `src/output/docx_styles.py` | `:24` → 现 `:31` | `SPACE_AFTER_BODY_PT = 0` → `= 10`（裸数，与同族 `SPACE_AFTER_HEADING_PT` 同形状）＋ 8 行出处注记 |
| 第一笔 | `tests/test_fonts_and_docx_styles.py` | `:157` → 现 `:159` | 常量钉桩期望值 `0` → `10`（与常量**同批**，卷宗口径） |
| 第一笔 | `tests/test_fonts_and_docx_styles.py` | `:174`／`:208-245` → 现 `:184`／`:218-272` | 脱钩快照整例重评（口径见 §3） |
| 第二笔 | `src/output/docx_exporter.py` | `:141-147`、`:165-173` | 两处正文分支各加 `pf.space_after = Pt(S.SPACE_AFTER_BODY_PT)`（即 s927-51 §一 点名的唯一锚点：`_add_paragraph` 的 `level > 0` 补 `else` 分支、`_add_paragraph_with_inline_format` 补一行） |
| 第二笔 | `tests/test_fonts_and_docx_styles.py` | 臂一 | 「正文段**无**显式 `w:after`」翻正为「正文段显式 `w:after == "200"`（字面量）」 |

接线后该常量的消费方由 **0 处 → 2 处**（`grep -rn SPACE_AFTER_BODY_PT --include=*.py src/`）：

```
src/output/docx_exporter.py:147:        pf.space_after = Pt(S.SPACE_AFTER_BODY_PT)
src/output/docx_exporter.py:173:    pf.space_after = Pt(S.SPACE_AFTER_BODY_PT)
src/output/docx_styles.py:31:SPACE_AFTER_BODY_PT = 10
```

### 🔴 点名：提示词说的「改值为 `Pt(10)`」按字面执行会全线翻红

主班提示词写「第一笔改值为 `Pt(10)` 时 :157 必红」。**卷宗正文**写的是「常量值改 10（`Pt(10)`）」，
括号是**档位说明**而非字面码。实测否证字面写法：

```
$ .venv/Scripts/python.exe -c "
from src.output import docx_styles as ds
print(hasattr(ds,'Pt'), [l for l in open('src/output/docx_styles.py',encoding='utf-8').read().splitlines() if l.startswith(('import','from'))])
from docx.shared import Pt; print(Pt(10), Pt(Pt(10)), Pt(Pt(10)).pt)"
False ['from __future__ import annotations']        ← 本文件不 import docx ⇒ 写 Pt(10) 当场 NameError
127000 1612900000 127000.0                          ← 即便能 import，Pt(Pt(10))＝127000pt（双重换算）
```
⇒ 落**裸数 10**，`Pt()` 换算只在消费方做（与 `SPACE_AFTER_HEADING_PT = 6` → `Pt(S.SPACE_AFTER_HEADING_PT)`
的同族惯例一致）。钉桩随之写 `== 10`（若真写成 `Pt(10)`，`Pt(10) == 10` 也为假 ⇒ 必红）。

## 2 两笔的分笔读数（各笔独立过绿）

| 阶段 | 定向三件（fonts 21 ＋ review_docx 6 ＋ docx_export 13） | 产物 |
|---|---|---|
| 改前（HEAD，常量 0 未接线） | `40 passed in 4.65s` | `document.xml` sha `c82ab4ba06e1`、`styles.xml` `16c148c90ee9` |
| 第一笔后（常量 10，仍未接线） | `40 passed in 4.81s` | `document.xml` sha **`c82ab4ba06e1`（逐字节不变）**、`styles.xml` `16c148c90ee9`（不变）；`w:after` 命中仍 2 |
| 第二笔后（接线落地） | `40 passed in 4.66s` | 见 §4 两路对照（生效值不变、显式属性增加） |
| 第二笔扩面（8 件 docx 消费族） | `100 passed in 22.15s` | — |

第一笔「零产物变化」与 s927-51 结论 2（S0→S1 的 document.xml/styles.xml sha 相同）独立复现。

## 3 测试件重评口径（为何不是把 `10.0` 划成 `0.0`）

s927-51 §5 与 `docs/insights/s927-45-format-caliber-note.md` §4-B 定过两条，本单照办：

1. **不许造恒真式**：原臂二写作「产物继承值 − 常量现值 == `DOCX_BODY_AFTER_GAP_PT`」。
   B′ 之后两侧同值，若只把 `10.0` 改成 `0.0`，这一格就退化成「两侧同过一个换算函数」的空断言。
   ⇒ 改为三臂，各自独立、可单点定位：
   - **臂一（direct，档二整数字面量）**：正文段 `w:after == "200"`——字面量，不由 `Pt(常量)` 派生。
   - **臂二（等价换轨哨兵）**：`docDefaults == 200` 且 `direct == docDefaults`——
     模板一旦变更（docDefaults ≠ 200）本臂即红，正是台账 241ⓒ 记的「今天等价、未来不等价」那一条。
   - **臂三（接线因果）**：`direct / 20 == pytest.approx(ds.SPACE_AFTER_BODY_PT, abs=0.025)`
     （容差＝s927-45 §2 的半网格 0.025pt）——证明"产物那个数确实是这个常量接出来的"。
   - 前导保留 s924-25 的"探针非恒真"对照（标题段 `w:after=120` 必须在场）。
2. **第一笔态与第二笔态分开钉**：第一笔（值改、未接线）时臂一写作「正文段仍**无**显式 `w:after`」，
   用途是证明"此刻同值纯属巧合，常量仍无消费方"；第二笔落地才翻正。
   本班按此顺序执行并逐步跑绿（见 §2），工作树只保留**末态**（第二笔态）文本。

## 4 零版式变化的产物对照（真跑两路，改前组＝HEAD 版生产码）

对照组用 `git show HEAD:` 把 `docx_exporter.py`／`docx_styles.py` 取到 `tmp/s928-01/headpkg/output/`
独立成包加载（常量 0、未接线），实验组＝当前工作树；两路同一 payload 各出一份真 docx：

| 指标 | 综述路 `build_review_docx`（7 段） | 直驱路 `build_experiment_protocol_docx`（60 段） |
|---|---|---|
| **生效 after 逐段差异** | **0 处 / 7 段** | **0 处 / 60 段** |
| **段间隙差异**（Word 折叠 `max(after_i, before_{i+1})`） | **0 对 / 6 对** | **0 对 / 59 对** |
| `word/styles.xml` sha | 相同（`16c148c90ee9`） | 相同（`16c148c90ee9`） |
| 显式 `w:after` 命中（document.xml） | 3 → 7 | 21 → 53 |
| `document.xml` 长度 | 4137 → 4193（Δ+56 B） | 18328 → 18776（Δ+448 B） |
| 段落样式序列 | 相同 | 相同 |
| 改后仍吃继承的正文段 | 0 段 | **7 段**（索引 3/8/20/30/36/39/50，生效值改前改后同为 200） |

⇒ 与 s927-51 结论 1 同形（差异 0 处／0 对、styles.xml 不变）。绝对值与其 Δ+70／命中 4→9 不冲突：
两班的 markdown 样本段数不同（本班 7 段、S0 侧 11 段口径），比的是**差异计数**不是字节数。

复算入口（`tmp/` 在 `.gitignore:29` 内，不入库）：

```
$ git show HEAD:src/output/docx_exporter.py > tmp/s928-01/headpkg/output/docx_exporter.py
$ git show HEAD:src/output/docx_styles.py   > tmp/s928-01/headpkg/output/docx_styles.py
$ PYTHONPATH=".;tmp/s928-01" PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s928-01/gap_compare.py
```

## 5 显式化覆盖面（B′ 的已知未尽项，与 s927-51 遗留 4 同源）

两枚正文助手接了线，**不走助手的支路**仍靠模板继承：直驱路实测残留 **7／60 段**（s927-51 登记 10 处支路）。
数值仍为 200 ⇒ 无视觉缝，但「全显式」没做到。扩面会把改动面从 2 处变 12 处，属人工可选加项，本单未做。

## 6 顺手撞见的既有缺陷（未修，非本单范围）

🔴 `build_experiment_protocol_docx` 对**真实** `ExperimentDesign` 抛 `TypeError`：
`docx_exporter.py:651` 的 `_v("ethics", "")` ＝ `getattr(design, "ethics", "") or ""`，
而 `ExperimentDesign.ethics` 是 `List[str]`（`design_engine.py` 字段表）⇒ 该 list 被直接喂给
`_add_paragraph_with_inline_format` 的 `re.finditer(text)`。

```
$ PYTHONPATH=. .venv/Scripts/python.exe -c "... build_experiment_protocol_docx(真设计) ..."
File "src/output/docx_exporter.py", line 803, in build_experiment_protocol_docx
File "src/output/docx_exporter.py", line 179, in _add_paragraph_with_inline_format
TypeError: expected string or bytes-like object, got 'list'
```
- **改前改后同现**（HEAD 副本 `:796`／工作树 `:803`）⇒ 非本班引入；本班为取"直驱路"等价性读数，
  改用 `tests/test_experiment_docx_export.py:17-51` 同形的 `SimpleNamespace`（`ethics` 为 str）。
- 在册测试全用 stub ⇒ 该路对真设计稿的失败面**零覆盖**；UI 侧 `src/ui/experiment_design_ui.py:396`
  传的是真 `d`，外面套 `except Exception → st.error(f"生成失败：{e}")`（:390-400）⇒
  推断该按钮对任何引擎产出的设计稿恒显「生成失败」（未跑 Streamlit 实测，只给码证）。
- 属 s924-18 台账 215② 那一类"读侧/写侧类型口径不一致"，建议另单（改动面小：`_v("ethics")` 处 join 或
  让正文助手接受 list），本单未动。

## 7 必须同笔入库的件（主班合提口径）

**一笔四件，缺一即红**（红位逐条实测／复算）：

- 第一笔若只改常量不翻正测试件 ⇒ **两红**：`:159` 常量钉桩（复算 `ds.SPACE_AFTER_BODY_PT == 0` → `False`）
  ＋ 旧臂二缝宽式（复算 `200/20.0 - 10 == 10.0` → `False`）⇒ 与 s927-51「只改值两红一绿」同形。
- 第二笔若只接线不翻正臂一 ⇒ **实跑红**：`1 failed, 20 passed in 1.96s`，
  `test_docx_body_paragraph_after_spacing_effective_value_pinned` → `assert '200' is None`
  （原文见 result 证据节）。
- 臂二／臂三（现 `:259`／`:264`／`:269`）在接线后与 direct 读数互锁，拆开任一侧都会红。

1. `src/output/docx_styles.py`（改，＋8 −1）
2. `src/output/docx_exporter.py`（改，＋7 −0）
3. `tests/test_fonts_and_docx_styles.py`（改，＋54 −25）
4. `docs/insights/s928-01-space-after-bprime.md`（新增，`??`）

分笔形状（若主班坚持按卷宗拆两笔）：
- 笔 1 ＝ ①＋③的**第一笔态**（`:159` 期望 10；臂一写作「`body_sp.get(qn("w:after")) is None`」；
  臂二写作「`defaults_twips == int(DOCX_BODY_AFTER_EFFECTIVE_TWIPS)`」）＋④可选。
- 笔 2 ＝ ②＋③的**第二笔态**（臂一翻正为字面量 `"200"`，另加臂二的 `direct == docDefaults` 与臂三）＋④。
- ⚠ 工作树只有末态；两态文本的差异点已在 §3 写明，主班若要真拆需按 §3 手工回置臂一。
  本班实测**末态四件合提**为全绿（`40 passed` 定向、`100 passed` 扩面），故推荐合提一笔。

## 8 未碰清单

§C 的 11 枚在途件（含 `app.py`、`pytest.ini`、`src/analysis/{cfa,result_card,__init__}.py`、
`src/output/interpretation.py`、`tests/test_cfa_sem_golden.py`）**一律未碰**；
§D 在册红 `tests/test_export_gate_global_scan.py::test_all_download_buttons_accounted_for` 未跑、未消、
未挂白名单／NEEDS_MIGRATION；兄弟班 psy102 点名的 s927-56/60/62 域未碰；
同班 s927-72 的三枚交付件与本单无交集（`src/experiment_design/`、`src/analysis/post_hoc_power.py` 未再改）。
全程零 git 写操作、未跑 psy 全量套件。
