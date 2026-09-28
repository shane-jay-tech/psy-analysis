# s927-31 · 问卷设计重复建设并单裁决材料

> 生成：2026-09-29T06:0x，班 `qoder-executor-20260929-0600-psy105`，cwd `D:\code\psy-analysis`。
> 位别：**只读／材料位**。**零码改动**——两实现一字未动，`app.py` 只读不碰（未归因在途件 12/40）。
> 上游：`zcode-bridge/done/s922-102-apppy-slice7a.result.md` 遗留 1（「重复建设待并单」）。
> **本档数字全部 2026-09-29 现取**；锚点里的「838 行」已漂（见 §1）。
> ⚠ 本档是**材料＋两案＋清单**，不含裁决。拍板权在主班／人工。

---

## 1. 重复现状核对（完成标准 ①）

| 项 | 锚点（s922-102，2026-09-22） | **2026-09-29 现值** | 漂移 |
|---|---|---|---|
| `src/ui/questionnaire_panel.py` | 838 行 | **881 行** | +43（s924-37/38 文案常量化，`3bb4eb0`） |
| ├ 其中 `render_questionnaire_page()` | — | **:74–:881（808 行）** | 文件里唯一的大渲染函数 |
| `app.py` | 2405 行（片 7a 后） | 工作树 **2405 行**／HEAD **2433 行** | 在途 −40/+12 |
| └ 问卷设计分支 | :1556–:2365（810 行） | **:1556–:2313（758 行）** | 分支终点由下一条顶层 `elif mode == "📝 论文写作"`（:2314）界定 |
| 面板生产调用方 | 全仓零 | **仍全仓零** | 未变 |

**零生产调用方（现取，这是裁决的根事实）**：

```
$ grep -rn "render_questionnaire_page" --include=*.py . | grep -v "^./tmp/\|node_modules"
./src/ui/questionnaire_panel.py:74:def render_questionnaire_page():        ← 定义
./tests/test_questionnaire_panel_charac.py:83,189,273,342                  ← 测试
./tests/test_questionnaire_panel_logic.py:81,176,178,180,404,498,514       ← 测试
（无任何 src/ 或 app.py 命中）
$ grep -rn "questionnaire_panel" src/ --include=*.py | grep -v "^src/ui/questionnaire_panel.py"
（零命中——除文件自己，仓内没有任何生产模块 import 它）
$ grep -rn "questionnaire" src/ui/navigation.py src/ui/__init__.py
（零命中）
```

⇒ 两份实现是**真平行**：`app.py` 里的 `elif mode == "📋 问卷设计":` 是**唯一活路径**；
`src/ui/questionnaire_panel.py` 是**只有测试在喂的孤儿**（808 行生产零调用码，被 2 个测试件真跑）。

**重复度（现跑 difflib，探针 `tmp/qoder-executor-20260929-0600-psy105/dup_probe.py`）**：

```
app.py   分支体 :1557-2313  原始 757 行  归一后 709  去注释 664
panel    函数体   :75-881   原始 807 行  归一后 756  去注释 712
difflib 相似度 ratio = 0.9419
最长公共块累计 646 行 ＝ 占 app 侧 97.3% ／占 panel 侧 90.7%
逐行去重集合交集 527 行；只在 panel 55 行；只在 app 16 行
```

⇒ 两实现 **app 侧内容的 97.3% 已逐行存在于 panel**。这不是"部分重复"，是**同一页的两份拷贝，各自往前长了一小截**。

## 2. 关键发现：漂移是**双向**的（锚点只说了单向）

锚点原话「两实现已漂移（panel 侧用 `classify_questionnaire_sub_mode()`，app.py 侧用 `_q_sub_mode.startswith("📤")`）」——
**成立但不完整**。现取符号对照：

```
符号                                  app.py  panel   判定
------------------------------------------------------------------------
design_questionnaire_llm_async           2      2     同（LLM 异步核心两侧都在）
design_questionnaire                    11     11     同
generate_design_report / _summary        2 / 1  2 / 1  同
cancel_design_request                    4      2     ⚠ 计数差但**非缺陷**：
        app.py 的 4 处＝:1560(分支内 import) /:1682(分支内调用) /:236,:240(**分支外**，autosave 区)
        panel 的 2 处＝:12(import) /:256(调用) ⇒ 分支内取消链路**等价**
render_settings_sidebar_panel            2      0     ★ panel **缺**片 7a 的侧栏外提
compute_pending_elapsed                  0      3     ★ app.py **缺** s922-02 计时防漂硬
pending_clock_anomaly                    0      3     ★ 同上
classify_questionnaire_sub_mode          0      2     ★ app.py **缺**子模式分类器
_q_sub_mode.startswith                   2      0     ★ panel 已弃字面判断
st.download_button / st.stop()           3 / 3   3 / 3  同（导出三件套两边各一份）
export_gate / check_before_export        0      0     ★ **panel 零门禁接线**（见 §4）
key-level session_state 读写（分支/函数体内）  6  6     同形（并单不新增会话耦合）
```

**结论：哪一侧都不是另一侧的超集。** 于是"并单删残留"不是删一刀就完事——

- **panel 领先 app.py 的两件事**：① 子工作流用 `classify_questionnaire_sub_mode()` 集中分类（app.py 仍 `startswith("📤"/"📊")` 字面判）；
  ② pending 计时有 `compute_pending_elapsed`／`pending_clock_anomaly` 护栏（app.py 直接 `int(_t.time()-started_at)`，
  缺 `started_at` 时会崩/误报；panel 侧多了 `elapsed is None → "—"` 与 `CLOCK_ANOMALY_WARNING_TEXT` 降级分支）。
- **app.py 领先 panel 的一件事**：片 7a 已把侧栏混装块（语言切换／LLM 状态／记忆管理／使用指南）外提成
  `render_settings_sidebar_panel(st.session_state)`（app.py :1586-1587，**2 行**），
  而 panel 仍内联那份**迁移前**的旧块（`src/ui/questionnaire_panel.py:97-151`，**56 行 `with st.sidebar:`**）。
  ⇒ 这 56 行正是 s922-102 从 app.py 搬走的同一块内容的**第二副本**。

**section 对应表**（两侧结构一一对得上，便于逐段并）：

| 段 | app.py | panel | 备注 |
|---|---|---|---|
| 分支／函数头 | :1556 | :74 | |
| `st.title("📋 问卷设计工具")` | :1566 | :76 | 同文 |
| 子工作流 radio | :1569–:1584 | :79–:95 | panel 在此调 `classify_...`，app.py 用 `startswith` |
| 侧栏 | :1585–:1587（2 行接线） | :96–:151（56 行内联） | **★ app 领先** |
| 快速模板 | :1589–:1603 | :152–:166 | |
| 主区域 | :1604–:1641 | :167–:204 | |
| 取消进行中设计 | :1642–:1799 | :205–:373 | **★ panel 有计时护栏** |
| 问卷设计执行 | :1800–:1875 | :374–:449 | |
| 设计结果展示（含导出） | :1876–:2313 | :450–:881 | 两侧各 3 枚 `download_button` |

## 3. 两案材料（完成标准 ②）

### 案 A：并单删残留（以 panel 为目标页，`app.py` 分支塌成路由）

做法：把 app.py 领先的**那 2 行侧栏接线**补进 panel（替掉 panel 的 :96-151 旧内联块），
再把 `app.py:1556` 分支体换成 title＋一行 `render_questionnaire_page()`。

- **收益（现算）**：`app.py` 从 2405 → **约 1655 行**（删 758 行分支体、留 ≈8 行路由）＝**净减约 750 行**，
  是全仓最大的一笔 app.py 减行（比片 7a 的 52 行大 14 倍）；
  同时消灭第二副本的 56 行侧栏 ＝ 全仓 `settings_sidebar_panel` 内容副本数 **2 → 1**。
- **代价／风险（每条都可复算）**：
  1. **必须先把 `classify_questionnaire_sub_mode` 与计时护栏反向确认在 panel 侧行为等价**（panel 已是较新一侧，风险主要在侧栏那 2 行替换）。
  2. **★ 撞台账 #81 在册红（硬前置，非可选）**：并单后 `questionnaire_panel.py` 从"零生产调用方的孤儿"
     变成**活的导出路径**，而它 `export_gate` 引用数实测 **0**（app.py 是 2）。
     现状红（本班现跑复现，未消）：
     ```
     $ .venv/… pytest -p no:randomly tests/test_export_gate_global_scan.py -q
     FAILED …::TestExportGateGlobalScan::test_all_download_buttons_accounted_for
       AssertionError: …未被门禁覆盖或加入白名单: ['src/ui/questionnaire_panel.py']
     1 failed, 10 passed in 3.72s
     ```
     此刻它只是"死码没登记"；并单后它会变成"**生产的问卷报告 Word/PDF/HTML 三个导出口没有任何隐私门禁**"。
     ⇒ **案 A 在 #81 消红之前不可执行**（消红要么接门禁、要么做隐私分类豁免，两者都超出执行手授权）。
  3. **撞 `app.py` 未归因在途件**（12/40，d913a-43 拆分半成品）——本班核过**行区间不重叠**（见 §5），
     但文件是同一枚，同文件双改必然归属混杂 ⇒ 须等那 12/40 落地并归因。
  4. 需要**全量重跑**背书（改 750 行生产 UI 码）。
- **可复用的既有范式**：片 8/10 已经给出"并单后的验收形状"，直接照抄即可（`tests/test_app_split_slice8_10.py`）：
  ```
  :67  assert len(body) <= 6, "分支体超过『仅 title/路由』上限 6 行"
  :68  assert any("<panel_module>" in ln for ln in body), "未接线到新面板"
  :69  assert not any(re.match(r"^\s+(if|elif) mode == ", ln) for ln in body)
  ```
  ⚠ 但该件的 `:151 assert "download_button" not in text`（迁入件不得带 download_button 换桶）**问卷页过不了**
  ——panel 有 3 枚按钮。⇒ 问卷并单**不能原样套片 8 模板**，导出桶问题必须先解（同 2.）。

### 案 B：双轨维持（现状不动，加一条防漂哨兵）

做法：承认两份并存，但把"零生产调用方"这件事**显式登记＋钉住**，避免第三副本出现。

- **收益**：零生产码风险、不撞 #81、不撞 app.py 在途件；执行手当天可做完。
- **代价**：750 行平行 UI 码长期双份；每次改问卷页要改两处（漏改即静默漂）；
  孤儿面板**已经被两个测试件当真跑**（`test_questionnaire_panel_logic.py:514` 直接 `module.render_questionnaire_page()`）
  ⇒ 测试在守一份**不跑在生产上的实现**，这是"看着绿其实没人用"的形态。
- 哨兵形状建议：断言「`render_questionnaire_page` 的生产调用方数 == 0」，一旦有人接线就红、逼他并单；
  或反向断言「两实现归一后 diff 行数 == 当前实测 71 行（55＋16）」，一旦第三处漂移就红。**两者都要新写测试件，超出本班只读位授权。**

### 材料级倾向（不是裁决）

若 #81 能先行消红（接门禁或明确豁免分类），**案 A 的净收益远大于案 B**（−750 行、副本 2→1、
且把 app.py 缺的两个护栏带进生产）。
但案 A 有**两道不由本班控制的外部前置**（#81 消红、app.py 在途归因落地），
故**在主班排单上，案 A 是"案 B 之后的一枚单"，不是本波的单**。

## 4. 并单操作清单（完成标准 ③；含测试面）

> ⚠ 全部写成"**若授权则动哪几行**"。本班**一行未动**。行号＝2026-09-29 工作树现值，
> 动手前**必须重取**（`app.py` 一旦那 12/40 落地即整体位移）。

**前置闸（不通过则不许开工）**

- [G1] 台账 **#81 已消红**：`src/ui/questionnaire_panel.py` 进入 `GATED_EXPORTS` 或经人工隐私分类进 `WHITELIST_EXPORTS`。
  复算：`.venv/… pytest tests/test_export_gate_global_scan.py -q` → 期望 `11 passed`（当前 1 failed, 10 passed）。
- [G2] `app.py` 的 12/40 在途改动**已归因并入库**，工作树对 `app.py` 干净。复算：`git status --porcelain -- app.py` → 空。
- [G3] 解释器口径已钉（见姊妹档 `s927-27-interp-caliber.md`），全量重跑用 `.venv` ＋ `-m "not (e2e or playwright)"`。

**步骤（案 A 形态，逐步给复算命令）**

- [S1] 备份两侧现状到 `tmp/<班名>/`（`app.py` 快照 ＋ panel 快照 ＋ sha），供行为对拍回滚。
- [S2] **panel 侧只改一段**：`src/ui/questionnaire_panel.py:96-151`（56 行内联侧栏）→ 换成 app.py 的 2 行等价接线
  （`from src.ui.settings_sidebar_panel import render_settings_sidebar_panel` ＋ `render_settings_sidebar_panel(st.session_state)`）。
  ⚠ **不得给 panel 新增顶层函数**——`tests/test_questionnaire_panel_charac.py:273` 钉的是顶层函数名列表**精确相等**：
  `== ["classify_questionnaire_sub_mode", "compute_pending_elapsed", "pending_clock_anomaly", "render_questionnaire_page"]`
  ⇒ 追加任何函数当场红（本班现读该行仍在）。
- [S3] panel 侧删侧栏后核对会话键无悬挂：`language`／`q_request_input` 等读写是否仍闭合
  （s922-102 验收 3 的反向检查同型）。
- [S4] **app.py 侧塌分支**：`:1556` 分支体（`:1557-2313`）→ title ＋ 一行 `render_questionnaire_page()` 接线，控制在 **≤6 行**（对齐片 8 范式）。
- [S5] 行为对拍：`at = AppTest.from_file("app.py")` 跑问卷设计页一帧，比改前／改后的 widget 创建序列
  （`tests/test_app_split_slice8_10.py:157 TestRenderSequence` 已有"渲染顺序不得变"范式可抄）。
- [S6] 全量定向族合跑（清单见下表），最后跑一次钉好的全量口径。

**测试面（逐件标：改后会怎样／要不要同笔）**

| 测试件 | 现值 | 并单后 | 是否必须同笔 |
|---|---|---|---|
| `tests/test_app_page_branch_pins.py` | 124 passed（合跑） | 路由链仍含 `"\U0001f4cb 问卷设计"`（:63）⇒ **只要保留 `elif mode ==` 头即不红**；若删头则红 | 保留分支头 ⇒ 不需改此件 |
| `tests/test_questionnaire_panel_charac.py` | 同上合跑绿 | `:273` 顶层函数名列表精确相等 ⇒ **禁止加函数**；侧栏替换若改了 `# 侧边栏` 注释行不影响 | **S2 若动结构必须同笔** |
| `tests/test_questionnaire_panel_logic.py` | 同上绿 | `:514` 真跑 panel render；侧栏块换外提调用后，假 `st` 录帧序列会变 ⇒ 帧断言大概率红 | **必同笔（预期翻正）** |
| `tests/test_app_split_slice8_10.py` | 绿 | `_branch_body()` 取 `elif mode == "<key>"` 缩进体；问卷分支塌成 ≤6 行后**新分支体符合其范式**；`:151 download_button not in text` 若把问卷件加进参数化则红 | 若扩展参数化 ⇒ 同笔 |
| `tests/test_export_gate_global_scan.py` | **1 failed, 10 passed**（#81 在册红） | G1 未过时并单＝把死码问题变成生产问题 | **G1 必须先单独入库** |
| `tests/test_settings_sidebar_panel.py` | 绿（s922-102 建，13 处引 app.py） | 钉 `st.header("🌐"/"💡")` **已离开 app.py、在新面板**；panel S2 后这两串仍不在 app.py ⇒ 仍绿 | 复核即可 |
| `tests/test_reliability_bands.py` | 绿 | `:114` 是 `holders == {...}` **精确字典**，含 `"questionnaire_panel.py": 2`（α 阈值计数）⇒ S2/S4 只要不移动那两行 α 文案就不红 | 不红则不同笔 |
| `tests/test_questionnaire_design.py` | 绿 | 只测 `src/questionnaire/*` 引擎，不碰 UI ⇒ 无影响 | 否 |
| `tests/test_app_routes_v6_panels.py`／`test_e2e_rendering.py`／`test_e2e_ui.py`／`test_ui.py`／`test_navigation_pagemodes_snapshot.py`／`test_script_generator_branches.py` | — | 均含"问卷设计"字面串，属**改名/删页敏感**面 ⇒ 并单后逐件复跑 | 若翻正则同笔 |
| `tests/test_app_defaults_keys_snapshot.py` | 绿（读 app.py 10 处） | 分支塌行不动 `_defaults` 播种 ⇒ 预期不红 | 否 |
| `tests/conftest.py::_APP_TEST_FILES` | — | 若并单**删除** app.py 侧某 AppTest 件 ⇒ 需同步摘登记行（未登记＝零隔离，见 s924-01） | 视 S4 形态 |

## 5. `app.py` 在途件不重叠取证（本班只读它）

本班唯一一次读 `app.py` 的 diff，只做行区间比对，**未读写任何内容**：

```
$ git diff -U0 -- app.py | grep "^@@"
@@ -139,0 +140 @@ render_privacy_gate()
@@ -141,9 +142,3 @@ render_privacy_gate()
@@ -152,0 +148 @@ if "has_auto_cleaned" not in st.session_state:
@@ -154,9 +150 @@ if "has_auto_cleaned" not in st.session_state:
@@ -164,16 +152,2 @@ if not st.session_state.startup_check_done:
@@ -181,6 +155 @@ def _preload_heavy_deps() -> None:
@@ -202,0 +172,3 @@ def _autosave_current_workspace(*, force: bool = False) -> bool:
$ git diff --numstat -- app.py
12  40  app.py
$ wc -l app.py / git show HEAD:app.py | wc -l
2405（工作树） / 2433（HEAD）      ← 2433 − 40 + 12 = 2405，逐笔闭合
```

⇒ 全部 7 个 hunk 落在 **HEAD :139–:202**（隐私门／启动自检／预加载／autosave 区），
问卷设计分支在 **:1556–:2313** ⇒ **行区间不重叠**。
**但这不构成绕法**：文件同一枚，`git add app.py` 必把那 12/40 一起吞进本笔 ⇒ 归属混杂（brief §C）。
故 [G2] 仍是硬前置，本班不自行安排提交顺序。

## 6. 复算命令（主班可原样跑）

```bash
cd /d/code/psy-analysis
# 规模与调用方（§1）
wc -l src/ui/questionnaire_panel.py app.py; git show HEAD:app.py | wc -l
grep -rn "render_questionnaire_page" --include=*.py . | grep -v "^./tmp/\|node_modules"
grep -rn "questionnaire_panel" src/ --include=*.py | grep -v "^src/ui/questionnaire_panel.py"   # 期望：零命中
# 重复度（§1 末，探针已留 tmp，非入库件）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260929-0600-psy105/dup_probe.py
# 双向漂移符号对照（§2）
for S in render_settings_sidebar_panel compute_pending_elapsed pending_clock_anomaly \
         classify_questionnaire_sub_mode export_gate st.download_button; do
  printf "%-34s app.py=%s panel=%s\n" "$S" "$(grep -c -- "$S" app.py)" \
    "$(grep -c -- "$S" src/ui/questionnaire_panel.py)"; done
# 并单相关的现存绿／红
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -p no:randomly \
  tests/test_app_page_branch_pins.py tests/test_questionnaire_panel_charac.py \
  tests/test_questionnaire_panel_logic.py tests/test_questionnaire_design.py \
  tests/test_app_routes_v6_panels.py -q                              # 现值 124 passed, 2 warnings / 21.53s
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -p no:randomly \
  tests/test_export_gate_global_scan.py -q                           # 现值 1 failed, 10 passed（#81，勿消）
```

**局限（如实写）**：
- 行号随 `app.py` 那 12/40 落地即整体位移；`_branch_body()` 与 `test_app_page_branch_pins.py` 都**按 AST/缩进取**而非按行号断言，
  所以清单里的行号是"施工坐标"不是"断言键"。
- difflib 的 0.9419 属**归一后**（去缩进／空行／纯注释行／压空白）读数；按原始行比会更低。探针里同时给了三种口径（原始／归一／去注释）。
- 本班**未做行为等价对拍**（要执行 app.py 一帧，超出只读位）；§4-S5 只是把方法指到位。
- 主班复跑 `dup_probe.py` 属**同源脚本**，不算独立复算。

## 7. 零改动自证与安全边界

- 未改 `app.py`／`src/ui/questionnaire_panel.py`／任何 `src/`／任何 `tests/`——两文件 diff 前后不变（证据 §8）。
- 唯一产出＝本档。**未新建测试件、未改 conftest 白名单、未碰导出门禁表**。
- `data/` 全程未触碰：本单未做写实验、未跑 sqlite；但**跑了定向测试**（§6 的 124 passed 一跑会 import 面板链），
  故以**真库指纹跑前＝跑后逐位相同**承担该职责，实测读数见 §8（181 件 / 21,059,126 B）。
  ⚠ 本单**未**给这些定向跑设 `LITERATURE_FEED_DATA_ROOT`（理由：安全职责已由指纹对照承担，且 `src/literature_feed/__init__.py:10-18`
  在包导入期复制常量，setenv 对已导入的链无效——同 `s927-27-interp-caliber.md` §8 的交叉注记）。此为如实声明的口径差，非疏漏掩盖。
- 红线自查：不含统计数值结论、不判隐私分类（#81 的 A/B 出口只转述台账原文）、不下"并/不并"裁决。

## 8. 收工读数

```
$ git status --porcelain | wc -l
13          # 开工 11 → 收工 13 ＝ 基线 11 ＋ 本班两枚新增 insights 档（s927-27／s927-31），他人在途 11 项一字未动
$ git diff --numstat -- app.py src/ui/questionnaire_panel.py
12  40  app.py                          ← 与开工逐字相同（他人在途，本班未动）
（src/ui/questionnaire_panel.py 无输出＝零改动）
$ git diff --stat -- src/ui/questionnaire_panel.py
（空）
$ git check-ignore -v tmp/qoder-executor-20260929-0600-psy105/dup_probe.py
.gitignore:29:tmp/  tmp/qoder-executor-20260929-0600-psy105/dup_probe.py   ← 探针不入库
$ .venv/Scripts/python.exe -c "…data/literature_feed 文件数/字节数…"
AFTER-31 files 181 bytes 21059126        ← 与开工指纹（s927-27 证据 §6 的 BEFORE）逐位相同 ⇒ §7 的"真库零触碰"是实测非主张
```
