# SPACE_AFTER_BODY_PT 三案裁决材料（s927-51·B′ 论证复核，前后输出对照实测版）

- 班：`qoder-executor-20260928-1800-psy97`（只读路，零码改动）　cwd：`D:\code\psy-analysis`
- 日期：2026-09-28　HEAD 现取：`84d010b`（波次简报表里的 `f0f3f73` 已过期）　porcelain：开工 12 行（全为他班在途件），本班唯一新增＝本档 1 枚 `??`
- 上游：`zcode-bridge/done/s923-18.result.md` 遗留问题 1（三问之一，档内推荐 B′）→ 材料本体 `docs/insights/psy-docx-constants-dossier-20260923.md`
- 本档性质：**裁决材料＋推荐复核**。三案只出形状与代价，选案权在人工；本班未动常量、未动测试、未动生产码。
- 与前手关系：本单前一手 `qoder-executor-20260928-1745-psy96` 被 harness 运行时故障打断且从未 claim，本班从零接手，无前手半成品。

---

## 0. 结论先行（五条）

1. 🔴 **B′ 的「零版式变化」成立**，但成立条件比 s923-18 写的更具体：正文段的继承值今天实测由 `docDefaults after=200` 提供（＝10pt），`Pt(10)` 落盘也是整数 200，**两侧同格**才等价。两路产物（综述路 11 段、直驱路 8 段）各测一遍：生效段后距逐段差异 **0 处**，段间隙序列差异 **0 对**，`styles.xml` sha 不变。
2. 🔴 **B′ 可以拆成两笔，第一笔已被证为零风险**：只把常量 `0` 翻成 `10`（不接线）时，`word/document.xml` 的 sha1 与整包字节长度和现状**逐字节相同**（37062 == 37062）。原因＝该常量在 `src/` 内消费方 **0 处**（复点见 §2）。
3. **案 A（接线不改值）不是"低风险档"，是实测的版式改版**：正文段 `w:after` 显式落成 `0`，5 个正文段从 10.0pt 塌成 0.0pt，综述路 10 对段间隙里 2 对被压平、直驱路 7 对里 3 对被压平。⇒ 卷宗给案 A 的定性「唯一有实质用户可见后果的一格」**读数级成立**，本档把它的量填上了。
4. **卷宗的两条前置今天已被前人闭合，不该再计入 B′ 的成本**：①「三案共同前置＝拆 `:143` 三元组」已由 s924-24（commit `869dd75`）做完；②「正文段后距完全没有测试看守」已由 s924-25（commit `64fbea4`）补上守卫。⇒ 见 §1。
5. **B′ 的测试面成本比卷宗记的多一条**：s923-18 只记「改常量钉桩＋补一条 XML 钉桩」，但 s924-25 新增的脱钩快照 `tests/test_fonts_and_docx_styles.py:208-245` 有**两条臂**（`:233` 正文段不得出现显式 `w:after`、`:242` 缝宽须等于 10）在 B′ 下同时必红 ⇒ B′ 落地必然连带**重评整例**。本班把「现状三条全真／B′ 三条全红」两头都在沙盒里跑出来了（§4-E）。

**推荐**：维持 B′，并按「第一笔只改值（零产物变化）→ 第二笔接线＋重评快照例」分两笔走。选案仍交人工，因为 B′ 含一条**方向性后果**（§5.3）：它把正文段后距从「跟 python-docx 捆绑模板走」改判为「本仓显式锁定 10pt」。

---

## 一、锚点复核（含行号漂移与「已闭合」点名）

🔴 行号一律双报。本单四个取证对象件 `git diff --numstat HEAD` **全空**，故 **HEAD 行号＝工作树行号**；但相对 2026-09-23 的卷宗正文已整体下移，引用时以本表为准。

| 对象 | 卷宗/s923-18 写的行号 | HEAD＝工作树现读 | 漂移原因 |
|---|---|---|---|
| `src/output/docx_styles.py` 常量定义 | `:24` | `:24` `SPACE_AFTER_BODY_PT = 0` | 零漂移 |
| `src/output/docx_exporter.py` 正文助手 | `:130-136`（`_add_paragraph`）、`:154-161`（内联助手） | `:126-154`（`_add_paragraph`，接线落点在 `:141-143` 的 `level > 0` 分支）；`:161-180`（`_add_paragraph_with_inline_format`，落点 `:165-168`） | 文件在 s924-26／cedb00e 之后长过 |
| `tests/test_fonts_and_docx_styles.py` 常量钉桩 | `:143`（一钉三元组） | **`:157`**（已是独立断言，`ds.SPACE_AFTER_BODY_PT == 0`），同函数 `:145-160` | 🔴 **s924-24 已把三元组拆成三条**（`:151`/`:154`/`:157`），拆断言这一前置**已被闭合** |
| `tests/test_fonts_and_docx_styles.py` 表头底色钉桩 | `:150` | `:166` `assert ds.TABLE_HEADER_FILL == "DDDDDD"` | 同上下移 |
| 正文段后距的产物面看守 | **卷宗时不存在** | `:172-245` 整段为 s924-25 新增：`:174` 缝宽常量 `DOCX_BODY_AFTER_GAP_PT = 10.0`、`:201-205` 动态读 `docDefaults`、`:208-245` 快照例（臂一 `:233`、臂二 `:242`） | 🔴 s923-18 遗留问题 2「该族完全没有测试看守」**已被闭合** |

同一处缺陷的跨档登记（按「先 `grep -n` 数命中次数、别把一处记成两笔」口径）：
`docs/` 内提到 `SPACE_AFTER_BODY_PT` 的共 **3 档**（`psy-docx-constants-dossier-20260923.md`、`psy-docx-style-unify-design-20260923.md`、`s927-45-format-caliber-note.md`），`tests/` 内 **1 件 9 行**（`:157`、`:158`、`:174`、`:209`、`:217`、`:219`、`:235`、`:242`、`:243`，其中读常量值的只有 `:157` 与 `:242` 两处），`src/` 内 **1 行＝定义本身**（另各 1 枚命中落在 `__pycache__/*.pyc` 二进制，非消费方，计数时已剔除）。⇒ 这是**同一笔欠账的三处记法**，不是三笔；本档不新增第四笔欠账，只在 §5 给出选案形状。

---

## 二、第 0 步前置核查＋双层口径（引用 s927-45，本档只复点自己那一档）

`docs/insights/s927-45-format-caliber-note.md` §2 已定过容差上下界的**取法**（下界＝半个产物网格、上界＝在册最小相邻意图差之一半），本档不重造规则，只按同规则算**段后距这一族**的数（该档给的是 cm 族 0.000882 cm／0.13 cm，不适用于 pt 族）。

| 项 | 读数（本机 `.venv`，python-docx 实测） |
|---|---|
| 落盘属性 | `w:spacing/@w:after`，单位 **1/20 磅** |
| 产物网格 | 1/20 pt ＝ **0.05 pt** |
| 容差下界 | 半网格 ＝ **0.025 pt**（小于它就是制造恒红） |
| 本仓 `w:after` 族在册意图值 | `[4, 6, 8, 10, 12, 18, 20, 24]` pt（前 6 项取自 `docx_exporter.py` 里 `space_after = Pt(n)` 的 8 处字面量，10 是 B′ 拟值，6 取自 `SPACE_AFTER_HEADING_PT`） |
| 最小相邻意图差 | **2.0 pt**（4 与 6 之间） |
| 容差上界 | 其一半 ＝ **1.0 pt**（大于它就允许版式被改掉） |
| 无损判定 | `10 × 20 = 200 ∈ Z` ⇒ **无损**，档二可取整数 `200` 逐位 |
| 第 0 步核查 | 常量 `src/` 内消费方 **0 处** ⇒ 现状下写任何 `w:after == 常量` 的等式都是**恒假**（s927-45 §4-E 的同一条在册实例，本档独立复点命中数） |

⇒ 双层口径落法：**档一** `产物 after_pt == pytest.approx(10, abs=0.025)`（无损档允许逐位，但必须写明无损理由）；**档二** 钉整数与属性名 `<w:spacing ... w:after="200" ...>`，且**不得**用 `Pt(10)` 派生当档二（§4-B 禁则）。现状侧的档二不是 200 而是「正文段无 `w:after`、继承 200」，所以 s924-25 才把期望式写成"缝宽"——这层语义在 B′ 前后**必须整例重评**，不能只把 `10.0` 改成 `0.0` 了事（改完它就退化成 §4-B 禁的"两侧同过一个换算函数"的恒真式）。

---

## 三、三案终表（每格都是实测读数，非推断）

| | 案 A（接线，值仍 0） | 案 B（删常量） | **案 B′（改 10 ＋ 接线）** |
|---|---|---|---|
| **改哪几处** | `docx_exporter.py` 两处（`:141-143` 加 `else` 分支、`:165-168` 加一行） | `docx_styles.py:24` 删 1 行 ＋ 测试件 2 处读点（`:157`、`:242`）＋ `:174` 注释与 `:209-221` docstring 提法 | `docx_styles.py:24`（0→10）＋ `docx_exporter.py` 同案 A 两处 ＋ 测试件 `:157` 期望值 ＋ **整例重评 `:208-245`** |
| **测试面（实测）** | `:157` **保持绿**（值没动）；`:242` 绿（缝宽仍 10）；🔴 `:233` **必红**（正文段开始出现显式 `w:after`）⇒ 与 s923-18 说的「`:143` 保持绿、要新增钉桩」不同，今天它**会弄红在册例** | 🔴 `:157` 与 `:242` 抛 **`AttributeError`（测试报错，不是可读的红）**；`:233` 不读常量 ⇒ **仍绿**；s924-24 拆过之后**不再牵连另两格常量**（卷宗原话今天只剩一半成立） | 🔴 三条全红：`:157`（值改）、`:233`（接线）、`:242`（缝宽 10→0）——沙盒反例件 6 passed 已把这三条逐一实证 |
| **产物面（实测）** | 综述路：`document.xml` 4367→4427 B，`w:after` 命中 4→9；🔴 **5 个正文段 after 200→0（10.0pt→0.0pt）**；段间隙 2/10 对被压平。直驱路：5 段同降，3/7 对被压平 | **产物零变化**（继承链不含本仓代码，删一个没人读的名字而已）⇒ `document.xml`/`styles.xml` 与现状逐字节同 | 综述路：`document.xml` 4367→4437 B，`w:after` 命中 4→9；**生效 after 逐段差异 0 处、段间隙差异 0 对、`styles.xml` sha 不变**；仅 5 段的取值**来源**由 `docDefaults` 变 `direct`（等价换轨） |
| **用户可见** | 🔴 正文段与段之间从 10pt 塌成 0pt，只剩 1.5 倍行距 ⇒ 行数增加、观感整块化，属版式改版，历史稿与截图基线全部对不上 | 无 | **无**（两路实测等价） |
| **风险方向** | 风险最大且不可归因（产物观感回归）；且「同类段落两种间距」的隐患仍在：不走两枚助手的支路（列表项 `:246`、问卷题头 `:1043`/`:1049`、致谢 `:1074` 等）继续吃继承 200，接线支路变 0 ⇒ **同一种正文两种间距** | 意图彻底变隐式：下一个读码者只看到 `docx_styles.py` 里不再提段后距，真要改得去解 zip；失败形态是 2 处 `AttributeError`（脏红） | 风险最小，但**不是零**：①必须连 `:208-245` 整例一起重评（否则当场两臂红）；②显式化只覆盖走助手的正文段，未覆盖支路仍靠继承（数值同为 10pt 不产生视觉缝，但"全显式"没做到，见 §5.2）；③把模板依赖转成本仓锁定（§5.3） |
| **回滚成本** | 高（要重出全部受影响稿件的版式基线） | 低（一次删＋两处测试改动，产物不变） | 低（两笔可分，第一笔 sha 级零变化，第二笔红即回退） |

---

## 四、前后输出对照（读数原文）

七份产物全部由**生产码真跑**生成：现状（S0/D0）、只改值（S1）、B′（S2/DB）、案 A（RA/DA）。B′ 的接线不在盘上改码，而是在内存里把 `docx_exporter.py` 源码按锚点插两行后 `exec` 成独立模块（锚点唯一性用 `assert src.count(anchor) == 1` 守住，防"接线落点已漂"）。

**A. 等价根因（每次 dump 都重读，不内联字面量）**

```
docDefaults pPrDefault spacing = {'after': '200', 'line': '276', 'lineRule': 'auto'}
contextualSpacing 命中 = 0 / styles.xml 14
afterAutospacing 命中 = 0
```

正文段一律 `style=Normal`、`pPr` 里**不写 `pStyle`**；`Normal` 自身无 `pPr/w:spacing`；带 `after` 的段落样式（`Header/Footer=0`、`Heading1..9=0`、`Title=300`、`BodyText=120`、`ListContinue=120`、`IntenseQuote=280`）**一个都没被这条导出链用上** ⇒ 正文的继承值确实停在 docDefaults 的 200。`document.xml` 里 `contextualSpacing` 命中 0 ⇒ Word 的"同样式免间距"不会把正文间隙吃掉。**这三条是「零版式变化」成立的前提，缺一条等价就不成立。**

**B. 只改值不接线（S0 → S1）**

```
document.xml 字节数            4367 → 4367 (Δ+0)
document.xml w:after= 命中次数 4 → 4
styles.xml sha 相同            = True
document.xml sha 相同          = True
生效 after 不同的段落数 = 0 ／段间隙差异 0 对／10
```

**C. B′ 全案（S0 → S2；D0 → DB）**

```
---- S0 → S2（综述路，11 段）----
document.xml 字节数 4367 → 4437 (Δ+70)    w:after= 命中 4 → 9    styles.xml sha 相同 = True
生效 after 不同的段落数 = 0
after 取信来源改变的段落数 = 5
   p01 <空> docDefaults → direct / p03 正文段落甲 / p04 加粗起头正文段落乙 / p09 <空> / p10 正文段落丙
段间隙（max(after,next.before)）不同的对数 = 0 ／总对数 10

---- D0 → DB（直驱全部正文支路，8 段，含表格题注 Pt(4) 支路）----
document.xml 字节数 7010 → 7080 (Δ+70)    w:after= 命中 3 → 8
生效 after 不同的段落数 = 0    取信来源改变 5 段    段间隙差异 0 对／7
⇒ 版式等价判定：等价（零版式变化）
```

逐对间隙原文（综述路 B′ 与现状 10 对全等，摘 4 行）：

```
正文段落甲　这是不含内联标记 >> 加粗起头正文段落乙　含内联标   S0=200  B′=200
• 列表项一 >> • 列表项二                                      S0=200  B′=200
一级标题样本 >> 正文段落甲　这是不含内联标记                   S0=120  B′=120
<空> >> 正文段落丙　收尾段。                                  S0=200  B′=200
```

**D. 案 A 对照组（S0 → RA；D0 → DA）**

```
---- D0 → DA ----  生效 after 不同的段落数 = 5
   p00 正文甲 首行缩进真   200 →    0 twips  (10.0pt → 0.0pt)
   p01 正文乙 首行缩进假   200 →    0 twips  (10.0pt → 0.0pt)
   p04 <空>               200 →    0 twips  (10.0pt → 0.0pt)
   p05 粗　正文丙 走内联助手 200 → 0 twips   (10.0pt → 0.0pt)
   p06 正文丁 无内联       200 →    0 twips  (10.0pt → 0.0pt)
  段间隙不同的对数 = 3／7 ⇒ 不等价（改版式）
---- S0 → RA ----  5 段 10.0pt→0.0pt，段间隙 2/10 对被压平 ⇒ 不等价（改版式）
```

**E. 测试面反例（沙盒件，6 passed）**

把在册三条断言的表达式**逐字**抄进沙盒件，在四种状态下各跑（样本失效改抛非断言异常，防 `pytest.raises(AssertionError)` 把"没找到段"吞成假绿）：

```
test_S0_在册三条断言此刻全真_证明反例件不是无中生有        通过（现状 :157/:233/:242 全真）
test_S1_只把常量改10_在册钉桩条红_其余两条仍真             通过（:157 红、:242 红、:233 绿）
test_S2_B全案三条全红_这就是B的测试面成本                  通过（三条全红）
test_S2_B全案下正文段显式落盘的就是整数200_档二证据        通过（w:after="200"，docDefaults 亦 200）
test_案A_接线不改正_正文段塌成0pt_档二证据                 通过（w:after="0" ≠ 继承 200）
test_案B_删常量_两处读点变AttributeError_第三处仍绿        通过
```

---

## 五、推荐与选案时要知情的三条

1. **维持 B′，且按两笔走**：第一笔只把 `docx_styles.py:24` 的 `0` 改 `10` ＋ 同件 `:174` 注释与 `:157` 期望值、`:242` 缝宽一起改（这一笔**不接线**，产物 sha 级零变化，§4-B 已证）；第二笔再接线 ＋ 重评 `:208-245` 整例（接线一红就落在同一笔里被解释掉）。这样做的收益：把「零风险改诚实」与「需要重评守卫」两件事的归因面分开，避免一笔里同时出现版式与测试语义两类变更。
2. **B′ 的诚实化只覆盖"走两枚助手的正文段"**：`docx_exporter.py` 里直接 `doc.add_paragraph()` 的站点实测 **20 处**（含两枚助手自身各 1 处 `:129`/`:163`），其中 **8 处**在站点附近自带 `space_after` 字面量（`:267`、`:384`、`:431`、`:651`、`:840`、`:849`、`:1024`、`:1112`），剩下 **10 处**既不走助手也不设段后距——列表项 `:246`、图段 `:376`、关键词 `:448`/`:496`、副标 `:655`、提示 `:855`、问卷 `:1043`/`:1049`、`:1073` 空段、致谢 `:1074`——**B′ 后它们继续吃继承 200**。B′ 下它们与显式段的数值同为 200 ⇒ 无视觉缝，但"常量说 10、代码在某条支路其实没写 10"这件事没有全根除。若人工要"全显式"，改动面从 2 处扩到 12 处，属另一档工作量，选案时可点名。
3. 🔴 **B′ 会把"跟模板走"改判成"本仓锁定 10pt"**：现状正文段后距是 python-docx 捆绑模板的 `docDefaults` 值（本档实测 200，与 `docs/insights/psy-docx-style-unify-design-20260923.md:70` 的三路同值读数一致）；接线之后模板若换、若升、若被 `apply_profile` 改写，正文段都不再跟着变。**今天等价、未来不等价**——这正是"诚实化"想要的方向，但它是一条**决定**而不是一条修复，须人工点头。
4. 另需知情：`src/output/docx_exporter.py` 磁盘现值是**纯 CRLF**（1264 对、裸 LF 0），`src/output/docx_styles.py` 是**纯 LF**（CRLF 0、裸 LF 40），`tests/test_fonts_and_docx_styles.py` 纯 CRLF（246 对），而本仓 `core.autocrlf=true` 且**无 `.gitattributes`** ⇒ 三件跨两种行尾制式。实现 B′ 时必须"先量行尾、后改、再复量"，否则"改一行"会放大成整文件 diff（探针是在内存里按通用换行读源码 exec 的，**观察不到行尾效应**，此条按磁盘计数与既有教训给出，不冒充实测）。
5. 与案乙的关系（避免重复建设）：`psy-docx-style-unify-design-20260923.md` 的案乙第 2 步（`apply_profile` 显式改写 `docDefaults`）与本单是**同一处缺陷的另一种出口**，且落点与 B′ 重叠（都要动正文段后距的取信来源）。若人工已排案乙 P4，B′ 可被其吸收；两者按 1 笔登记，不是 2 笔欠账。

---

## 六、复算入口（唯一，沙盒，保留）

```
D:\code\tmp\qoder-executor-20260928-1800-psy97\probe_before_after.py            # sha1 5a9b3544319b84a49cf74369b75c38dc42c2d942
D:\code\tmp\qoder-executor-20260928-1800-psy97\test_bprime_counterexample.py    # sha1 445a52a676468d7341d3702c64c5975a49c3b100
D:\code\tmp\qoder-executor-20260928-1800-psy97\probe_run_final.txt               # 全部判定原文 28556 B
D:\code\tmp\qoder-executor-20260928-1800-psy97\counterexample_run.txt            # 6 passed
D:\code\tmp\qoder-executor-20260928-1800-psy97\products\                          # S0／S1／S2／D0／DA／DB／RA 七份 docx ＋ 补丁版源码
```

跑法（cwd `D:\code\psy-analysis`，全程 `.venv` 解释器，两文件各 2 秒）：

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "D:/code/tmp/qoder-executor-20260928-1800-psy97/probe_before_after.py"
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest "D:/code/tmp/qoder-executor-20260928-1800-psy97/test_bprime_counterexample.py" -q
```

## 七、零改动自证与门禁读数

```
git rev-parse --short HEAD                                  84d010b
git status --porcelain                                      开工 12 行 → 收班 13 行（唯一增量＝本档 1 枚 ??，无新增 M）
git diff --numstat HEAD -- src/output/docx_styles.py \
    src/output/docx_exporter.py tests/test_fonts_and_docx_styles.py \
    tests/test_export_gate_global_scan.py                    四件全空
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_fonts_and_docx_styles.py tests/test_exporters_docx_geometry.py -q
                                                            27 passed in 2.04s
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"
                                                            1 failed, 19 passed, 1 skipped, 5531 deselected in 18.06s
```

唯一红＝在册红 `tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for`（`:88`，`unaccounted == ['src/ui/questionnaire_panel.py']`，纪律档 §十五／待人工 81 同源）：本班**未消红、未挂 NEEDS_MIGRATION、未写白名单**，红如实留在盘上。

`tests/test_exporters_docx_geometry.py` 的 `w:spacing` 正则（`:166`、`:222`）经复核确认属 `src/questionnaire/exporters.py`（路 C，该件 `:44-45` import 可证），与路 B 的 `document.xml` 不同源 ⇒ B′ 不撞它（现状合跑 27 passed 也旁证）。路 B 的四件导出测试（`test_review_docx_export.py`、`test_docx_export.py`、`test_deliverable_docx_export.py`、`test_experiment_docx_export.py`）里 `spacing`/`pPr` 断言计数为 **0**，字节类断言只有两条宽松下限（`len(docx_bytes) > 1000`／`> 5000`）⇒ **B′ 的回归面就是 `test_fonts_and_docx_styles.py` 一个件的三条，不外溢**。

未触碰清单（他班在途件，12 枚 porcelain 全在）：`app.py`、`pytest.ini`、`requirements-lock.txt`、`src/analysis/__init__.py`、`src/analysis/cfa.py`、`src/analysis/result_card.py`、`src/output/interpretation.py`、`tests/test_cfa_sem_golden.py` ＋ 四枚未跟踪件。本单取证不需要它们，未引用其行号，故无 HEAD／工作树双报需求；`pytest.ini` 是在途件，本班跑法按现值执行未改配置。

## 八、遗留（交人工／交主班）

1. 🔴 **选案**：A／B／B′ 三案形状与代价已量化，推荐 B′（分两笔）。B′ 含「把用户可见数值 0 改 10」的字面变更，按红线只出建议。
2. 🔴 **一条需要人工点头的决定**：§5.3「跟模板走 → 本仓锁定 10pt」。这条不在 s923-18 的原始三问里，是本次复核新查出的方向性差别。
3. **B′ 落地时的同集合提交清单**（分开提交＝HEAD 红）：`src/output/docx_styles.py` ＋ `src/output/docx_exporter.py` ＋ `tests/test_fonts_and_docx_styles.py`（`:157`、`:174`、`:208-245` 整例）＋ 本档。第二笔（接线）必然与测试件同笔，第一笔（只改值）也必然与测试件同笔——`:157`/`:242` 两读点会当场红。
4. **`TABLE_HEADER_FILL` 那一格不在本单范围**：s923-18 已建议案 B（删），且与三线表规范冲突的论证是另一族的证据，本档未复核（未跑底色彩源对照），主班若要合并按同一人工单处理即可。
5. 本班未新增红、未新增待人工条目（§5.3 这条**并进 s923-18 已挂的那一条**，不另起一笔）。
