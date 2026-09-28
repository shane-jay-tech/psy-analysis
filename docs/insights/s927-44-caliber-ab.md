# s927-44 `export_to_docx` CJK 补齐失败面 口径 A／B —— 裁决材料（零码改动）

- 班：`qoder-executor-20260928-1510-psy92`（只读路）　cwd：`D:\code\psy-analysis`
- 日期：2026-09-28　HEAD：`74efe31`
- 上游：`zcode-bridge/done/s923-05.result.md` 遗留问题 1（口径未拍板）　落地：`zcode-bridge/done/s924-08.result.md`（status **partial**）

---

## 0. 结论先行

**口径 A 已上线（`51d8464`，s924-08 授权面），口径 B 从未拍板、且被一条守卫逐字禁在生产码里。**

卷宗说的「补齐口径未拍板」**只对一半**：A 那一半已拍并已落地（s924-08 遗留问题 3 原话「口径 B 仍未拍板」）。
本档因此只交三件实东西：**A 在生产现场到底看不看得见（实测）**、**B 落地要付哪几条代价（含一条可翻案的守卫）**、
**A/B 都治不到的那一类失败（这才是真正的缺口）**。

**本班不选案、未改生产码、未改判据。**

## 1. 磁盘现状（复核锚点）

`src/questionnaire/exporters.py`（工作树版＝HEAD 版，该件 `git status --porcelain` 为空）：

```
  16| def export_to_docx(design: Dict) -> bytes:
 ...
 248| def _set_east_asian_font(style, font_name: str) -> None:
 249|     """设置样式的东亚字体（CJK fallback）。不是关键功能，失败时静默回退（回退语义未变，
 250|      但自 s924-08 起在 debug 级别留一条记录，见下）。"""
 251|     try:
 ...
 261|     except Exception as exc:                # 口径 A：不抬级别、不改控制流，只把"悄悄失败"变可见
 262|         logger.debug("docx 字体 %s 设置失败（回退默认）: %s", font_name, exc)
 ...
 265| def _sync_complex_script_size(target) -> None:
 294|     except Exception as exc:
 295|         logger.debug("docx 复杂文种字号同步失败（回退默认）: %s", exc)
```

⇒ 现存的 debug 级补齐口是 **2 个 helper、2 条 `logger.debug`**（第二条由 s924-10 `5d9acb5` 落地，口径与 A 一致）。
生产码里 `logger.warning`／`logger.error`／`logger.exception`／`logger.critical`／`warnings.warn` 在 `exporters.py` 内**命中 0 处**（实测）。

## 2. 可见性矩阵（开发者视角 vs 使用者视角）—— 全部实测，非推断

### 2.1 装配事实（决定性）

```
$ .venv/Scripts/python.exe   # 裸进程（streamlit 未导入）
root handlers: []            root level: 30 (WARNING)

$ 导入 streamlit 1.59.1 之后
root handlers: []            root level: 30
streamlit 自己的 logger handlers: []
config logger.level 现值: info
本仓 .streamlit/config.toml: NO [logger] section  => 用 streamlit 默认

$ 关键判据：exporters 的命名空间能不能被 root handler 收到
probe(logger 'src.questionnaire.exporters') level=0(NOTSET)  handlers=[]  propagate=True
root 原 handler 数: 0        => root 本来没 handler
logging.lastResort = <_StderrHandler <stderr> (WARNING)>  level=30
```

```
$ 级别门实测
effective level of exporters logger = 30
root 挂了 handler 但 level 仍 30 时，实收到: [('WARNING', 30)]        # DEBUG 连 handler 都进不去
显式 setLevel(DEBUG) 后，实收到: [('WARNING', 30), ('DEBUG', 10)]
```

⇒ **口径 A 在生产现场不是"字小看不清"，是被级别门整条丢掉**：`logger.debug` 在 `getEffectiveLevel()==30` 下
连 handler 都到不了。**A 实际可见性＝零**，除非有人显式把该 logger 抬到 DEBUG。

### 2.2 使用者（浏览器）侧真相 —— 对 s923-05 口径 B 代价描述的**否证**

s923-05 docstring 与遗留问题 1 写：「B 真能看见却会把失败抬到 **UI 可见面**」「Streamlit 侧若已配 logging 捕获/回显，
warning 会出现在用户界面上」。**盘上不支持这个前提**：

1. Streamlit 只给**它自己的** logger 挂 `StreamHandler`（`.venv/.../streamlit/logger.py:66` `setup_formatter` 仅作用于
   `streamlit` 命名空间的 logger），本仓 `src.questionnaire.exporters` 不在其列；
2. root 无 handler、级别 30；
3. ⇒ 一条 `logger.warning` 走的是 `logging.lastResort` → **stderr（启动器控制台）**，不是浏览器；
4. 真正能进浏览器的是 `st.warning`／`st.error`——**导出分支里一条都不覆盖本失败面**：

```
src\ui\questionnaire_panel.py  导出分支逐行读：
  828|  docx_bytes = export_to_docx(design)
  829|  st.download_button(...)
  836|  st.success("✅ Word 报告已生成，可用 Microsoft Word 或 WPS 打开编辑。")   # 无条件 success
  840|  pdf_bytes = export_to_pdf(design)  ...  848|  st.success("✅ PDF 报告已生成。")
  877|  except Exception as e:
  878|      st.error(f"❌ 导出失败：{e}")                                  # 只兜"上抛"的异常
```

   ⇒ `:878` 确实有一枚 UI 级 `st.error`，但它挂在**外层 try 的 except** 上：
   `_set_east_asian_font` 在**内层就把异常吞了**（口径 A 契约③「控制流契约未变，该函数仍然不抛」），
   失败**永远到不了 `:877`** ⇒ UI 侧对本失败面**完全无感**，且 `:836` 的绿勾在任何降级下都照弹。
   同型第二消费者 `app.py:2253-2262` 亦为无条件 `st.success`。

⇒ **修正后的 B 代价**：不是"被试在界面上看见报错"，而是"**主试/操作者的终端多两行红字，界面上照样弹绿色成功**"。
这既**减轻**了 B 的 UX 风险，也**同时削弱**了 B 的立论——因为使用者（真正拿到缺字体 docx 的人）**在 A/B 两案下都看不见**。
⚠ 该否证只针对"UI 可见"这一条措辞；「B 比 A 更可见」的大方向仍成立（stderr 优于无声）。

### 2.3 矩阵汇总

- **A（现状，debug）**：开发者＝仅在显式开 DEBUG 的诊断环境可见；使用者＝**不可见**；终端＝**不可见**（级别门丢）。
  产物＝不受影响。**零行为改动成立**。
- **B（warning）**：开发者＝裸 stderr 亦可见（`lastResort` 门限正好是 WARNING，实测 `level=30` 时 WARNING 通过）；
  使用者＝**仍不可见**（不走 `st.*`）；终端＝每次导出多 N 行（见 §3）；产物＝不受影响。
- **两案共同盲区**：见 §4。

## 3. 失败频率实测（构造一次降级统计）

分母实测：一次正常导出 `_set_east_asian_font` 被调 **6 次**（4 个调用点，`test_four_call_sites_fire_six_times_per_export` 钉着）。

正常基线（无任何失败）：

```
返回值 38583 bytes   段落数 56   DEBUG 0 条   WARNING 0 条   ERROR 0 条
```

沙盒强制全失败（拦 `w:rPr`／`w:rFonts`／`w:sz`／`w:szCs` 四类标签的 `qn`，令 2 个 helper 全抛）：

```
总记录数 = 9  产物字节 = 38554
  _set_east_asian_font     条数 = 6
  _sync_complex_script_size 条数 = 3
  其他来源               条数 = 0
  1. docx 字体 宋体 设置失败（回退默认）: sandbox w:rPr
  2. docx 复杂文种字号同步失败（回退默认）: sandbox w:sz
  3. docx 字体 黑体 设置失败（回退默认）: sandbox w:rPr
  4. docx 复杂文种字号同步失败（回退默认）: sandbox w:sz
  5. docx 字体 黑体 设置失败（回退默认）: sandbox w:rPr
  6. docx 复杂文种字号同步失败（回退默认）: sandbox w:sz
  7. docx 字体 黑体 设置失败（回退默认）: sandbox w:rPr
  8. docx 字体 黑体 设置失败（回退默认）: sandbox w:rPr
  9. docx 字体 楷体 设置失败（回退默认）: sandbox w:rPr
```

⇒ 拆分**实测非推断**：9 ＝ 6（字体）＋ 3（字号同步）＋ 0（其他）。第 9 条正是 s924-09 补上的**副标题楷体**调用点
（`test_four_call_sites_fire_six_times_per_export` 把它从 5 抬到 6 的那个），
说明"抬级别"的影响面随调用点增加而**单调增长**，B 的刷屏量不是一个常数。
⇒ **B 的刷屏量级＝每次导出最多 9 行**（若按 s923-05 建议的"首个失败 warn 一次"去重，则降到 1 行／helper＝2 行）。
⇒ 更要害的一条：**降级态与正常态的产物只差 29 字节、段落数一模一样** ⇒ 光看产物或只看"导出成功"完全分辨不出 CJK 没写上，
这正是 s923-05 证据 5「常量说谎」的定量版。

⚠ 口径声明：上表是**构造频率**（人为令 helper 必抛）而非现场发生率。真实发生率在本仓**不可测**——
它需要跑真 app 采集，而 A 的记录在生产默认根本落不了盘（§2.1），构成**循环盲**：
"看不见" ⇒ "无从统计" ⇒ "无法证伪发生率低"。这条循环是本单最该进待人工的事实，而非任何数字。

## 4. A／B 都治不到的那一类（真正的缺口，卷宗未提）

s923-05 证据 3 已否证、且盘上钉成断言：`test_invalid_font_name_is_not_a_failure_at_all_and_lands_verbatim`——
**字体名根本不校验**，传 `"不存在的字体名XYZ"` 不抛、错值逐字写进 XML ⇒ **这一类压根进不了 except**，
补 debug 还是补 warning 都**不会让它变可见**。

⇒ 对使用者伤害最大的恰是这一类（文档正常打开、字体静默替成默认），
而 A/B 之争全在"进了 except 的那一类"上打转。**若主班认"补齐"是目的而非级别是目的，真正的裁决条目应是
"要不要在生产侧对字体名做白名单校验"**（s923-05 遗留问题 2 已登记，至今未拍），那属产品决定、超执行手授权。

## 5. B 案落地代价清单（可批形状，本班未做）

选 B ⇒ 必须**同时**动下面四处，**四件同集合**，分笔提交＝HEAD 红：

1. 生产码 `src/questionnaire/exporters.py:262` 与 `:295` 两条 `logger.debug(` 抬为 `logger.warning(`（2 行）。
2. **守卫反转（硬闸）**：`tests/test_exporters_cjk_font_fallback.py:172-174` 现逐字写着——
```
    for escalated in ("logger.warning(", "logger.error(", "logger.exception(", "logger.critical(",
                      "warnings.warn("):
        assert escalated not in body, f"观测被抬到用户可见面：{escalated}（属口径 B，需主班裁决）"
```
   它**就是为拦 B 而存在的闸**。选 B 必须把这段反转，且**该测试名 `..._is_debug_only_and_never_escalates` 会当场名不副实**
   （命名债交主班定，本班不擅改他班公开标识）。
3. 同文件 `:204-207` 的 `assert all(r.levelno == logging.DEBUG for r in caplog.records)` 与 `:196` `hits == 6`
   须同步改成 warning 口径；`:184`「只在 DEBUG 面留 6 条记录」的 docstring 也要改（现为**在册陈述**非注释，行号已核）。
4. `tests/test_exporters_cjk_font_fallback_observability.py`（s924-08 建的独立复钉件，1 例，名
   `test_debug_record_written_and_fallback_stays_silent_after_export`）整件按新级别重写，含函数名。
5. 另需**新拍**：要不要去重（首个失败 warn 一次）。不去重＝每次导出最多 9 行进终端。

回滚成本：低（纯日志级别，无数据、无产物变化；产物字节改前后一致，见 §3 的 38583／38554 与级别无关）。

## 6. 判据读数（零码改动下的现状全绿）

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest \
    tests/test_exporters_cjk_font_fallback.py tests/test_exporters_cjk_font_fallback_observability.py -q
8 passed in 0.42s

$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -q -k "exporters or export_docx or export_pdf"
40 passed, 1 skipped, 5510 deselected in 16.42s
```

**全局清单型门禁单列加跑**（本域硬口径，见 brief：本仓有单文件测试看不见的清单闸）：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"
1 failed, 19 passed, 1 skipped, 5530 deselected in 17.60s
FAILED tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for
E   Left contains one more item: 'src/ui/questionnaire_panel.py'
```

⇒ **19/20 绿 + 1 枚在册红**。该红＝台账 81 已知红、本班开工前即挂 HEAD：
`git status --porcelain` 对 `tests/test_export_gate_global_scan.py`／`src/ui/questionnaire_panel.py` 为**空**（两件全 clean），
且 HEAD 版与工作树版**逐字相同**、`st.download_button` 命中行同为 `[829, 841, 868]` ⇒ 同红无需 stash 即已证。
**本班未消红、未挂 `NEEDS_MIGRATION`、未写白名单**（挂 `NEEDS_MIGRATION` 被同文件 `:156` 否证＝绕门禁；
写白名单＝替隐私分类签字；两条均超授权，正解是红留在盘上＋已在待人工 81）。

## 7. 与 s924-08 遗留问题 1 的关系（别踩重做）

s924-08 落 partial 的原因是「s923-05 的 3 条钉桩怎么处置」——该题**已由主班选甲闭合**：
`51d8464` 的 numstat 里 `tests/test_exporters_cjk_font_fallback.py` 记 **48 加／17 删**，即三条桩已按可批形状改写。
现盘上该文件 7 例全绿（§6），函数名已改成 `..._records_only_at_debug` 等 debug 口径形态。
⇒ **主班若在本单重提"3 条桩怎么处置"＝重做已闭合题**；本单真正的开放项只有 §5（B 的级别）与 §4（字体名不校验）。

## 8. 红线自证

零鉴权／凭据／密钥；**零统计数值结论**（§3 的 6／9／-29 字节是**构造频率与产物字节计量**，非推断统计量，
且已声明为构造口径而非现场发生率）；零资金／经济数值；零医疗内容；design 全为合成文案，不含被试数据；
未 `git add`／`commit`／`stash`／`checkout`／`restore`／`clean`；未装依赖；未联网；未跑全量套件；
未起 `LITERATURE_FEED_DATA_ROOT`（全程沙盒，无写 `data/literature_feed/` 之虞）。
