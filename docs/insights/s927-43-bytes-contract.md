# s927-43 exporters bytes/bytearray 契约归一 —— 裁决材料（零码改动）

- 班：`qoder-executor-20260928-1510-psy92`（只读路）　cwd：`D:\code\psy-analysis`
- 日期：2026-09-28　HEAD 现值：`74efe31`　`git status --porcelain` 12 行（全为他班在途件，本班未碰）
- 卷宗：`zcode-bridge/inbox/s927-43.task.md`　上游遗留：`zcode-bridge/done/s923-04.result.md` 遗留问题 1

---

## 0. 结论先行（最重要的一条）

**本案的核心裁决已经被人做过了，且做对了。**

`s923-04` 留下的「`-> bytes` 契约 vs 正向实返 `bytearray`（`exporters.py:435`）」这条，
已由入库提交 **`51d8464`（2026-09-25 11:14:13 +0800，`fix(psy): exporters 三单收口落地（PDF 容器归一／删弃用实参／CJK 静默失败补 debug 观测）`）**
按 **口径 A（归一，`bytes()` 包一层）** 落地，并且 **同笔** 把 s923-04 那条「必红的第 3 例」断言反向钉成 `bytes`
——正是 s923-04 遗留问题 1 自己预告的「两笔一体，别只摘用例」。本班核实它没有分叉、没有留半截。

⇒ 本档的用处因此从「裁 A 还是裁 B」收窄为：**登记 A 已闭合、给「若翻案到 B」的影响面、并交出一处 A 落地时留下的残留（死支）**。

## 1. 差异复核（磁盘现值 vs 卷宗锚点）

### 1.1 锚点行号已漂移（按磁盘实况修正并留痕）

卷宗／s923-04 的锚点写 `exporters.py:435`。**现值该处不是返回语句**：

- `:435` 现为 `    if rev_items:`（`export_to_pdf` 正文的「反向题」分支，不是 return）。逐字复验：

```
 433|
 434|    rev_items = [it for it in design["items"] if it["reverse"]]
 435|    if rev_items:
 436|        write("需反向计分的题目：", size=11, bold=True)
 437|        write_multi(", ".join(f"Q{it['index']}" for it in rev_items), size=11)
```
  ⚠ 注：该段经 GBK 控制台回显时中文为乱码，故改由 Read 工具直读源文件取原文（未二次转写）。
- `return bytes(pdf.output())` 现在 **`:483`**。
- `build_questionnaire_pdf` 的归一尾现在 **`:617-620`**。

漂移原因即 `51d8464` 本身在该文件插了 14 行（logging 装配、注释、debug 口）。

否证证据（本班现跑）：

```
$ git log --oneline -12 -- src/questionnaire/exporters.py
5d9acb5 fix(psy): s924-09 ＋ s924-10 两单合笔（副标题楷体东亚映射 ／ Heading1-3 的 w:szCs 跟随 w:sz）
51d8464 fix(psy): exporters 三单收口落地（PDF 容器归一／删弃用实参／CJK 静默失败补 debug 观测）
ec45485 chore: 初始化版本库 + .gitignore，清理 __pycache__

$ git blame -L 481,483 --date=short -- src/questionnaire/exporters.py
51d84647 (psy-analysis 2026-09-25 481)     # fpdf2 2.8.x 的 output() 返 bytearray，与本函数 `-> bytes` 声明不符；
51d84647 (psy-analysis 2026-09-25 482)     # 与同件 build_questionnaire_pdf 尾部的归一写法对齐（s924-06），让两个 PDF 出口容器类型一致。
51d84647 (psy-analysis 2026-09-25 483)     return bytes(pdf.output())
```

### 1.2 归一确已入库（`git show` 生产码侧）

```
$ git show --numstat --format='' 51d8464
14	6	src/questionnaire/exporters.py
48	17	tests/test_exporters_cjk_font_fallback.py
152	0	tests/test_exporters_cjk_font_fallback_observability.py
12	10	tests/test_questionnaire_export_pdf_positive.py

$ git show 51d8464 -- src/questionnaire/exporters.py   （尾部 hunk 逐字）
@@ -432,7 +438,9 @@ def export_to_pdf(design: Dict) -> bytes:
-    return pdf.output()
+    # fpdf2 2.8.x 的 output() 返 bytearray，与本函数 `-> bytes` 声明不符；
+    # 与同件 build_questionnaire_pdf 尾部的归一写法对齐（s924-06），让两个 PDF 出口容器类型一致。
+    return bytes(pdf.output())
```

### 1.3 归一确「两笔一体」（`git show` 测试侧，用例名一起改了）

```
$ git show 51d8464 -- tests/test_questionnaire_export_pdf_positive.py
-def test_positive_branch_currently_returns_a_bytearray_not_bytes() -> None:
-    assert type(blob) is bytearray
-    assert isinstance(blob, (bytes, bytearray))
+def test_positive_branch_returns_real_bytes_matching_the_declared_contract() -> None:
+    assert type(blob) is bytes
+    assert isinstance(blob, bytes) is True
+    assert not isinstance(blob, bytearray)
```

新用例的 docstring 自己写明了沿革（`:106-107`）：「历史：s923-04 曾在同一位置钉过 `type(blob) is bytearray`」——
即**没有靠删用例来灭红**，符合本仓「删掉就再没人能证明这条契约曾经漂过」的口径。

### 1.4 运行时复算：三个出口现在真的都返真 bytes

```
$ .venv/Scripts/python.exe <只读探针>
export_to_docx             type=bytes  isinstance(bytes)=True isinstance(bytearray)=False len=38583 head=b'PK\x03\x04\x14'
export_to_pdf              type=bytes  isinstance(bytes)=True isinstance(bytearray)=False len=97726 head=b'%PDF-'
raw pdf.output() type = bytearray      fpdf __version__ = 2.8.7
```

⇒ **根因仍在**（fpdf2 2.8.7 的 `output()` 裸返 `bytearray`），归一是必需的、且现在生效。
`export_to_docx` 走 `io.BytesIO.getvalue()`，本就是真 bytes，不受影响。

### 1.5 契约族全域普查（`src/` 里所有 `-> bytes` 标注，AST 扫）

**17 处真注解**（口径自证：`grep -rn -- "-> bytes"` 原始命中 **20 行**，其中 3 行是文档串／注释里的
同名文字——`delivery_package.py:3`、`defense_qa.py:4`、`exporters.py:481` 那条归一注释——扣掉得 17；
再用 AST 逐函数取 return 表达式复算，得**同一集合**，两轨一致）：

- `src/output/delivery_package.py:40` `build_delivery_package` → `buf.getvalue()` OK
- `src/output/docx_exporter.py` 6 个 builder → 全 `buf.getvalue()` OK。
  ⚠ **本班自查修正**：`build_experiment_protocol_docx` 的 return 清单里那条 `L644: getattr(design, name, default) or default`
  **不是外层函数的早退口**，而是它内部 `:643-644` 定义的**内嵌 helper `_v`** 的 return——
  Read 直读 `:639-648` 得证，外层函数返的是 `buf.getvalue()`。**不构成契约漂移，该条撤回。**
  成因：本班探针用 `ast.walk` 收 return，**会把嵌套函数的 return 记到外层函数名下**；
  这条方法学缺陷写在这里，是为了让下次复用该探针的人不再被同一个形状骗到（真要普查得改成"只取直接子树、遇嵌套函数另列"）。
- `src/output/snapshot.py:41` `create_snapshot` → `zip_bytes` OK
- `src/output/zip_exporter.py:27` `build_deliverable_zip` → `buf.getvalue()` OK
- `src/paper_writer/defense_qa.py:739` `export_defense_handbook_pdf` → `bytes(raw)` / `raw.encode('latin-1')` **已归一** OK
- `src/questionnaire/exporters.py` 3 处 → 见 1.4 OK
- `src/visualization/paper_export.py` 4 处 → `fig.to_image()` / `_render_static_image` / `buf.getvalue()`（plotly 侧容器类型未做运行时验，见遗留问题 3）

⇒ **`exporters.py` 这个「同文件两个 PDF 出口容器类型不一致」的问题已消失**；
同族其余站点没有第二例同类漂移（能确证的见 1.4／遗留 3 的边界声明）。

### 1.6 消费端影响面：无一处依赖可变容器

```
$ grep -rn "\.append(\|bytearray(\|memoryview(" --include="*.py" src/ui/questionnaire_panel.py app.py \
      | grep -i "pdf\|docx\|blob\|bytes"
  （空）

$ grep -rn "data=bytearray\|data=pdf_bytes\|data=docx_bytes" --include="*.py" src app.py
src/ui/literature_review_panel.py:905:                    data=docx_bytes,
src/ui/questionnaire_panel.py:831:                        data=docx_bytes,
src/ui/questionnaire_panel.py:843:                        data=pdf_bytes,
app.py:2257:                        data=docx_bytes,
app.py:2269:                        data=pdf_bytes,
```
⚠ 取证口径留痕：首跑把第二个过滤器写成 `grep -i "pdf|docx|blob|bytes"`（竖线未转义），
在 BRE 下它是**字面量**、必然零命中——那种"空"是假证据。上面是转义后的有效式，重跑仍为零命中才是实证。

5 个出口全部**直传给 `st.download_button`**，无一处就地改写缓冲区、无一处 `isinstance(..., bytearray)` 判别。
⇒ 归一对消费端零行为影响（本来也是 `st.download_button` 都能吃下的可缓冲对象）。

## 2. 两案与各自测试影响

### 口径 A：归一（`bytes()` 包一层，让实返追上注解）—— **已落地，零待办**

- 改动面：生产码 1 行（`:483`）＋ 测试 1 例（用例名＋3 条断言），同一笔 `51d8464`。回滚成本：单点 revert 一笔。
- 运行时代价（实测 CPython 语义）：

```
bytearray->bytes is same obj: False id diff: True     # 另拷一份，97,726 字节量级
bytes->bytes is same obj : True                        # 注解已符时零拷贝，白给
```

  即：每次 PDF 导出多一次 ~97 KB 拷贝；`export_to_docx` 那类本就返 bytes 的出口**不产生拷贝**。可忽略。
- 测试影响：**已全部闭合**。定向四件现跑 `48 passed in 10.30s`（见 §4）。
- 残留：见 §3（唯一一处 A 落地时留下的形态瑕疵）。

### 口径 B：改注解（把签名改成 `-> bytearray`）—— **现在翻案＝净亏，且要动 4 枚件**

若主班想改判为 B，需要同时处理：

1. `src/questionnaire/exporters.py:303` 签名＋`:483` 去掉 `bytes()`；`export_to_docx:16` 也得跟着改成 `-> bytes` 保持族内一致或再分叉——**这正是当初要修的病**。
2. `tests/test_questionnaire_export_pdf_positive.py:103-117` 三行断言（`type is bytes`／`isinstance(bytes) is True`／`not isinstance(bytearray)`）全须反转＝**把已经钉住的契约再拆一次**。
3. `src/paper_writer/defense_qa.py:739` 已是 `bytes(raw)` 归一口径；B 会让两个 PDF 出口重新分叉。
4. 5 个消费端点（§1.6）拿到可变容器，而消费端**没有任何一处做防御拷贝** ⇒ 未来若有人把 blob 存进 `st.session_state` 又原地改，会污染已下发的字节。这是 B 独有的新增风险面，不是理论：`tests/test_experiment_design_ui_detail_branch.py:349-352` 已经在测另一条面板路时踩过这个形状，其注释原文——

```
#: 实测：CPython 里 `bytes(x)` 与 `x + b""` 都会**原样返回同一对象**（只有 bytearray 才真另拷）
#: ⇒ 变异体必须用 bytearray，否则「另拷一份」这个坏形态根本没被构造出来。
```

⇒ B 的净收益＝省一次 97 KB 拷贝；净成本＝重开分叉＋拆掉已钉断言＋引入可变容器外泄面。**不对等。**

## 3. 残留（A 落地时留下的一处形态瑕疵，可批形状）

`src/questionnaire/exporters.py:617-620`（`build_questionnaire_pdf` 尾部，`ec45485` 初版就在、非 `51d8464` 引入）：

```
617	    out = pdf.output()
618	    if isinstance(out, (bytes, bytearray)):
619	        return bytes(out)
620	    return bytes(out)  # fpdf2 新版本返回 bytearray，统一转 bytes
```

**`isinstance` 判别是死支**：两个分支返回值逐字相同（都 `bytes(out)`），条件永不影响结果。
后果不是错、是**误导**：读代码的人会以为这里做了「按类型分流」，而 `:481-483` 的 `export_to_pdf` 是无条件 `bytes()`——
**两个 PDF 出口容器类型一致（语义达成），但归一写法不一致（形态分叉）**，恰好是 `:482` 注释自称「对齐」想避免的那件事。

可批形状（**本班未做，属生产码改动**）：

- 最小改动面：删 `:618-619` 两行，`:620` 改为 `return bytes(pdf.output())` 并复用 `:481-482` 的注释措辞。约 −3/+2 行。
- 回滚成本：极低（单函数尾两行）。
- 复算读数：删后 `build_questionnaire_pdf` 的运行时类型仍是 `bytes`；`tests/test_questionnaire_export.py` 有 7 处消费 `build_questionnaire_pdf`（`:131-207`）但无容器类型断言 ⇒ **预期零红**，仍需按 §4 口径跑门禁。
- ⚠ 该清理**不影响任何产物字节**，纯形态一致性 ⇒ 优先级低，可与下次真正碰 `exporters.py` 的单合笔，不必单开一笔。

## 4. 判据读数（含全局清单型门禁单列加跑）

本仓有一族「全局清单型」门禁，单文件测试完全看不见（`tests/test_export_gate_global_scan.py` 扫全仓 `st.download_button`）。
本班虽零码改动，仍按硬口径单列加跑：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"
1 failed, 19 passed, 1 skipped, 5530 deselected in 12.11s
FAILED tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for
E   Left contains one more item: 'src/ui/questionnaire_panel.py'
tests\test_export_gate_global_scan.py:88: AssertionError
```

**唯一红＝已知在册红，且已证 clean@HEAD 同红**（不是本班所加，本班未修未放宽）：

```
$ git status --porcelain tests/test_export_gate_global_scan.py src/ui/questionnaire_panel.py \
      src/questionnaire/exporters.py tests/test_questionnaire_export_pdf_positive.py
  （空 = 四件全 clean ⇒ 工作树版 == HEAD 版）

$ git show HEAD:src/ui/questionnaire_panel.py | grep -c "st.download_button"   → 3
$ grep -c "st.download_button" src/ui/questionnaire_panel.py                   → 3
```

⇒ offender 文件与门禁件都逐字等于 HEAD，HEAD 上跑必是同一条红，无需 stash/checkout 即可归因。

定向四件（同函数的契约面）：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest \
    tests/test_questionnaire_export_pdf_positive.py tests/test_questionnaire_export_docx.py \
    tests/test_questionnaire_export.py tests/test_exporters_cjk_font_fallback.py -q
48 passed in 10.30s
```

门禁结构（为何本班两条路都不走，只登记）：`WHITELIST_EXPORTS` / `GATED_EXPORTS` / `NEEDS_MIGRATION` 三名单，
`test_no_pending_migrations` 在 `:156` 断言 `len(NEEDS_MIGRATION) == 0`
⇒ 挂 `NEEDS_MIGRATION` 会被同文件那条否证（＝绕门禁）；写进 `WHITELIST_EXPORTS` ＝替隐私分类签字。
两条都超出执行手授权，**正解是让红如实留在盘上＋进待人工**（该红已在待人工 81，见 s923-04 验收情况③）。

另：本班确认 `docs/insights/` **无清单型闭合闸**（`grep listdir|glob|iterdir` 过 tests 对 docs 命中为空），
故本档落盘不触发任何在册红。

## 5. 推荐（倾向，非裁决）

**维持口径 A（现状），不翻案。** 理由：A 已入库且断言已反向钉住、消费端零依赖可变容器、根因（fpdf2 2.8.7）仍在。
唯一值得动作的是 §3 那处死支的**形态一致性清理**，属低优先、可与下次真碰 `exporters.py` 的单合笔。

⚠ 本条是材料级倾向，**不等于放行**：`bytes()`／`bytearray` 属对外契约面，翻案与否、死支是否清理仍由主班／人工签。
本班未选案、未改生产码、未改判据。

## 6. 红线自证

零鉴权／凭据／密钥触碰；零资金与统计数值结论（本文所有数字均为**字节数、行数、测试计数**，非统计推断量）；
零医疗内容；`design` 入参全为 `minimal_design()` 的合成文案，不含被试数据；
未 `git add`／`commit`／`stash`／`checkout`／`restore`／`clean`；未装依赖；未联网；未跑全量套件。
