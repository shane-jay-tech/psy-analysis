# s927-32 · slice 6a／片 4 搬迁顺序可行性现值与推荐执行序（只读裁决材料）

> 2026-09-30｜执行班 psy108｜位别：**只读材料单**——零码改动，`app.py` 一字未动，未 `git add`／未 commit／未跑任何测试。
> 上游：`zcode-bridge/done/s922-103-apppy-slice6a.result.md` 的三条出口（A／B／C）＋ `docs/insights/psy-apppy-split-roadmap-20260918.md` R6。
> 🔴 执行搬迁本身＝人工闸（写库面／拆片改生产码）。本班不签、不排单、不改 roadmap、不改判据本体；本文只给可批形状。
> 🔴 红线域登记：本单不涉及任何统计数值结论与医疗内容。候选块内含 `render_pii_warning` 调用位与示例数据标签（如「7维度心理量表 (N=50)」）——属隐私相邻文案位，本文一律**只登记位置、不改一字**。

## 0. 坐标系声明（先认这一节，否则全部行号都会读错）

`app.py` 此刻是他班在途 ` M`，工作树比 HEAD **净少 28 行**（`git diff --numstat` = 12/40，40−12＝28）。但**逐点位移并不统一**，因为两枚 hunk 中间还夹了一次「只增不改」的插入。现取的换算带（三条，别再沿用「整体平移 28」这句）：

| 工作树区间 | 与 HEAD 的关系 | 现证 |
|---|---|---|
| :1–136 | 同 HEAD（Δ0） | 第一枚 hunk 从 :137 起 |
| :159–171 | HEAD＝WT＋**31** | 片 4 定义行 WT :169 → HEAD :200；`with st.sidebar` 之前都属此带 |
| ≥ :175 | HEAD＝WT＋**28** | 片 4 的写点 :187→215、调用点 :835→863／:1139→1167、分支头 :738→766、uploader :772→800、`__file__` :845→873、路由 :953→981、缓存键 :1119→1147 全落此带 |

- 起因：第二枚 hunk `@@ -200,6 +169,9 @@` 往 `_autosave_current_workspace` 的 **docstring 里插了 3 行注释**（`d914-23 注：…`），所以定义行本身是 Δ31、函数尾部起 Δ28。⇒ **片 4 的行数也要声明坐标系：工作树 169–188＝20 行，HEAD 200–216＝17 行，差的正是那 3 行未入库注释**（roadmap R2 的「20 行」只对落地版成立，s922-23 的「22 行」是另一口径）。
- 好消息：本单关心的**上传段（:738 起）整体落在 Δ28 带内**，切换点不受影响。

| 坐标 | 行数 | blob／sha |
|---|---|---|
| 工作树 `app.py` | **2405** | `a2db26b`／sha256 `6522fa5ebb362103dc9d2a99146b0dae1b4eb553ea301a51e108bfcde3b0bfcd` |
| `git show HEAD:app.py` | **2433** | `5b57907` |

- **工作树 sha 与 s922-103 于 09-22 04:49 记录的 sha 逐字相同** ⇒ 自上游那单以来 `app.py` 内容零变化；s922-103 的行号**没有漂移**，可以直接复核而不是重估。
- 在途那笔（`d913a-43`／`d914-23` 启动块拆分）的**最后一枚 hunk 落在 `_autosave_current_workspace` 的 docstring 内部**（`@@ -202,0 +172,3 @@`，即新版的 :172 之后插 3 行）。配套新件 `src/ui/{startup_checks,heavy_preload}.py` 已在 `8fa9708` 入库，唯独 app.py 这一半未入库。
- ⇒ **出口 A 的第一步（动片 4）与这枚在途 hunk 逐行重叠**；出口 B 的目标块（:738 起）与它相距 550 行，**区间不相交**。这是本单最重要的一条现值，直接决定两案的先后。

## 1. 锚点逐条复核（工作树现值 ／ HEAD 现值）

| 锚点（s922-103／roadmap 原话） | 工作树 | HEAD | 判定 |
|---|---|---|---|
| `def _autosave_current_workspace` 定义（原 :169） | **169**，AST `end_lineno` **188**（20 行） | 200–**216**（AST，17 行） | ✅ 与 R2「169-188／20 行」逐字相符；s922-23 的 22 行是把 :189 空行＋:190 注释计入。⚠️ **行数随坐标系变**（见 §0：HEAD 版只有 17 行） |
| 调用点「:835 块内／:1139 块外」 | **835**／**1139** | 863／1167 | ✅ 两处都在 |
| `_autosave_last_error` 写（函数内，原 :187） | **187** | 215 | ✅ |
| `_autosave_last_error` 读（引导块内，原 :325） | **325** | 353 | ✅ |
| `_workspace_last_saved` 写（手动导出，原 :347） | **347** | 375 | ✅（roadmap R3 把这条也记成「读侧」，实为**写**侧） |
| 数据分析分支头 `if mode == "📈 数据分析":`（原 :738） | **738** | 766 | ✅ |
| `st.file_uploader`（原 :772，「app.py 唯一一处」） | **772**，另有 **372**（侧栏工作区导入） | 800／400 | ⚠️ **作废一条**：全文件实为 **2 处**，:372 在片 5 内 |
| `__file__` 示例数据路径（原 :845） | **845** | 873 | ✅ |
| `_analysis_cache_key`（原 :1119/:1128，「不在上传段」） | **1119／1128** | **1147／1156**（现取） | ✅ 仍不在 :738-957 内 ⇒ 完成标准③ 至今无对象。另现取：`_recipe_prefill_text` WT 1014/1023/1026 ⇄ HEAD 1042/1051/1054 |
| 片 5 引导块 `with st.sidebar:` | **199–662**（AST，464 行） | 227–690 | ⚠️ roadmap R3 记「196-663／468 行」——起点是从 :196 的注释横幅起算、终点多吞 1 枚空行；**结论不变**（:325／:347 确在块内），但引行数时需按口径标注 |
| 候选块 :738-957 | **220 行**（`ss_ref` 26、`st.rerun` 4、`st.stop` 1、uploader 1） | — | ✅ 与 roadmap「段内 26 处」同数 |

`s922-103` 的 docstring 引文「调用点对照＝app.py:1015 与 1319」**在工作树和 HEAD 上都不成立**（835/1139、863/1167）⇒ 那 3 行未入库注释自带失效锚点，别拿它当复核基准。

## 2. 三出口复核（可行性现值）

### 出口 A｜先搬片 4，再搬片 6a

锚点原话的阻塞理由是「必须先给 `_autosave_last_error`／`_workspace_last_saved` 定一个单一持有者，否则迁后该键跨文件读写」。**这条前置今日已大体自证成立，且形态早已存在**：

- `src/utils/autosave.py:49-50` **已有键名常量** `SESSION_LAST_ERROR_KEY = "_autosave_last_error"`／`SESSION_LAST_SAVED_LABEL_KEY = "_workspace_last_saved"`。
- 该模块**已是两键的主导写方**：`_autosave_last_error` 写于 :159/:163/:196/:210/:214、成功时 :208 `pop`；`_workspace_last_saved` 写于 :205。
- 「跨文件读写」不是待避免的新形态、**而是现状**：`src/ui/undergrad_wizard.py:97` 已在读 `_workspace_last_saved`；`app.py:325/326` 读的两键本就由 autosave.py 写。⇒ 锚点据此判「停手」的前提**已失效**。
- 真正尚未收口的只有两处，且各自性质不同：
  1. `app.py:187`＝第二写方，文案是**第三种**错误串（`自动保存失败，请手动导出项目快照`；autosave.py 用「自动保存准备失败…」/「自动保存写入失败…」）。**全仓无任何测试钉这枚串**（在册钉的是 autosave.py 那两条：`tests/test_autosave_acceptance_h912_06.py:92/:110`）⇒ 消掉它不破坏在册判据，但属**用户可见文案变更**，需人工拍板。
  2. `app.py:347`＝手动「导出项目快照」按钮写 `_workspace_last_saved`。语义与 autosave 不同（人工快照 vs 自动保存），**不可并入持有者**，并了就会让侧栏 :329-330 的「✅ 当前项目已自动保存」对人工导出撒谎。
- `_autosave_current_workspace` **在 app.py 之外零代码引用**（tests／scripts／.bat 全仓 grep 无命中，只docs 提它）⇒ 片 4 的改动面只有 app.py 的 1 处定义＋2 处调用点。
- 片 4 已是薄壳：:182 直接 `return trigger_autosave(st.session_state, build_workspace_snapshot, force=force)`，迁移只需把这层壳连 `try` 一起搬进 autosave.py。**注意 `from src.utils.workspace import build_workspace_snapshot` 在 `try` 内**——这层「import 失败也不炸主流程」的保护必须随迁，属行为等价点。

**A 的现值判定：技术可行，且比锚点估的便宜一个量级；但第一步被在途 hunk 逐行挡住（见 §0），必须等那笔落地或回退。**

### 出口 B｜片 6a 走「回调注入」，不动片 4

- 复用 s922-103 的 AST 探针重跑现值：块 :738-876／:738-948／:738-957 的自由名里，**🔴 只来自 app.py 模块级定义的名永远只有 1 个＝`_autosave_current_workspace`**（🟡 可自 import 的分别为 7／9／10 个）。⇒ 一个 `autosave` 回调参数即可闭合；把块截到 :738-834 则 🔴 归零（但会剪断 :780-840 的提交事务，属改写不是移植）。
- 裸全局（`df`／`meta`／`inspector`／`n_rows`，写于 :877-883）**真耦合仍为 0**：探针在 :738-957（220 行、37 个块内赋值名）报「✅ 真耦合 0 个」。干净性依旧依赖 app.py 后续行的读前自赋值（`inspector` :991、`n_rows` :1080、`df` :1186）——**重排即碎**的隐式约束，锚点的这条警告原样成立。
- 新增现值两条：
  - `:845` 的 `__file__` 有**现成解药**：`src/utils/app_paths.py:25 REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent`（该模块已被 autosave.py 使用）。一行替换即可消掉锚点的「第二颗雷」；`src/ui/*.py` 目前无 app_paths 消费者，属新引入 import，需人工放行。
  - **app.py 是 100% CRLF（2405 枚 `\r\n`、0 枚裸 LF），而所有已迁面板是 LF**（`deliverable_center_panel.py` 321 LF／0 CRLF、`upload_state.py` 40 LF、`autosave.py` 261 LF）。⇒ 逐字节移植必须显式管换行：新模块写 LF、app.py 侧删除要按 CRLF 行切，否则 `git diff` 会把整份 app.py 判为改动，「仅显示移动 ≥95% 相似」这条验收（蓝图 §4.4）当场失效。
- B 的验收对象口径要先修：块尾 :957 只是「智能首页」注释行，而 :949-960 是**一枚语义单元**（快捷入口路由，两个分支各带 `st.stop()`）。截在 957 会把这组路由从中间切开 ⇒ 干净边界是 **:738-948（211 行，路由全留 app.py）** 或 **:738-960（223 行，路由全进面板）**，:738-957 只是取数口径产物、不是可交付切点。
- 净减测算（完成标准④「≥150」）：B 单走 ⇒ 净减约 207–216 行 ✅；A 全走 ⇒ 片 4 的 20 行＋片 6a 的 220 行−接线 ≈ 净减 234 行 ✅。**⇒ 阈值不构成选 A 的理由，两案都能达标**；真正的差异只剩「片 4 留不留 app.py」与「回调参数是否把隐式约束固化成跨文件约定」。

**B 的现值判定：技术上今天即可执行（区间与在途 hunk 不相交），但安全网强度低于锚点假设（见 §3）。**

### 出口 C｜回改路线图与派单阈值（规划域）

- **已部分完成**：roadmap 的 R5／R6 已把「:738-957／220 行」「`_analysis_cache_key` 不在上传段」「片 4 是片 6a 硬前置」回写进去了。⇒ 出口 C 的第①②条**无需再做**，只剩第③条与「阈值重设」在等裁决。
- 本单对 R6 的修正：**「硬前置」的实质内容变了**。R6 记的阻塞理由是键拓扑；现值上键拓扑已基本自洽（出口 A 节），**真前置变成「app.py 那枚在途 hunk 落地」**。⇒ R6 建议改写为「片 4 与片 6a 不可并行（同一函数依赖），但片 4 的键面前置已由 autosave.py 承担；执行序的真实闸门是 app.py 的在途改动归属」。此为规划域改动，**本班未动 roadmap 一字**。
- 另有**第三套顺序政策**未与 roadmap 对齐：`docs/architecture/app-split-blueprint.md` §3 的 S1–S8（「从小分支到大分支」，analysis_mode＝S7 放最后，S1 就是「建 `shared_state.py` 键名常量」）与 roadmap 的 5 步依赖序**互相冲突**——蓝图 §5 已明文要求「S6/S7 前先补两分支的 AppTest 冒烟作为迁移安全网」，而这条正是本单缺的东西。⇒ 裁决题其实是**「走蓝图的 S1→S3→S7」还是「走 roadmap 的片4＋6a 并单」**，两案对「键名常量收口」与「安全网先行」的排序正好相反。**这属规划域，需人工拍板，本班不选路。**

## 3. 安全网现值（决定验收命令怎么写）

- 上传段唯一在册回归面＝`tests/test_upload_state.py`（3 例）＋`tests/test_e2e_qimport_upload.py`（9 例）＝**12 例**，与 s922-103 的「12 passed」逐字同数（静态点数，本班未跑）。
- ⚠️ **`tests/test_e2e_rendering.py` 不能当验收判据**：它对上传组件的断言包在 `if len(at.file_uploader) > 0:` 里（:37/:58/:80），注释自述「隐私声明窗口期不会出现，所以 0 个 file_uploader 也是正常状态」⇒ **上传器消失它照样绿**。锚点若把它算作安全网是乐观的。
- 唯一的硬断言在 `tests/test_e2e_ui.py`：:72 `assert len(at.file_uploader) >= 1`、:83/:84/:85 断 `file_name`／`df.shape`／`_workspace_last_saved`。⇒ 它是**片 4 与片 6a 共同的现行判据**，比锚点以为的更关键。
- ⚠️ 该件带 d913b-47 顺序依赖夹具（:57-68 autouse，把 `BACKGROUND_AUTOSAVE_ENABLED` 打 False），自述根因是「`_workspace_last_saved` 仅在 drain 到后台完成结果时写入，结果槽是 `autosave_bg` 模块级全局 ⇒ 子集单独跑无人入队 → KeyError」。⇒ **验收命令必须同时跑「定向子集」与「整件全跑」**，只跑子集会掩盖后台路径问题。
- 🔴 新建 AppTest 件必须**同笔**登记 `tests/conftest.py` 的 `_APP_TEST_FILES`（:20-31，10 枚名单）：不在名单里的 AppTest 文件**零隔离**，会直接读写用户真实 `~/.psy_analysis` 项目／偏好／日志（该 fixture 的白名单是逐档名匹配的）。⇒ 这是「改测试件＋改 conftest 必须同笔入库」的硬耦合，拆开交＝HEAD 上留一枚会写真实数据面的测试。
- 在册红（别当新回归、也别顺手修）：`test_lr_rerun_apptest.py` 不带 `LITERATURE_FEED_DATA_ROOT` 时 8 errors（机理在 `src/literature_feed/__init__.py:10-18` 包导入期复制 `DB_PATH`）；`test_export_gate_global_scan.py::test_all_download_buttons_accounted_for`（待人工台账 #81）；`test_backup_user_data.py` 未归因红。全量基线现值＝**5509 passed／3 failed／29 skipped／27 xfailed**（`s927-71`，HEAD `b05371a` 口径，引前先复跑）。
- 🔴 `docs/insights/` 无索引件（现点：192 枚 `.md`，无 index／README／哨兵）⇒ 本班不提索引登记行；若主班另有味台账档，建议行＝`docs/insights/s927-32-slice-order.md｜s927-32｜片4／片6a 顺序可行性现值＋R0–R5 推荐序｜零码改动`。

## 4. 推荐执行序（R0→R5，给主班可批形状；本班一条都不执行）

> 每步都带「现证／避让线」「最小改动面」「验收命令」「回滚成本」。**任一步的前置不成立 ⇒ 整单挂起，不要在别人的在途件上叠改**（w85 §A1）。

**R0（前置闸门，非搬迁）——确认 app.py 的在途 hunk 归属并落地。**
判据：`git status --porcelain` 里 app.py 不再出现，且 `git diff --numstat` 为空。
```
cd D:/code/psy-analysis
git status --porcelain -- app.py                      # 期望：空
git diff --numstat -- app.py                          # 期望：空
wc -l app.py                                          # 落地后应为 2405（工作树版）或 2433（回退版）——两者坐标系不同，后续行号必须按新值重取
```
回滚成本：零。**这一步不做，R1 的改动面与别人重叠，归属必然混杂。**

**R1（片 4 搬迁，20 行）——把壳函数移进既有持有者，不新建文件。**
改动面：`src/utils/autosave.py`（新增一个 `autosave_current_workspace(session_state, *, force=False)`，函数体逐字取自 app.py:180-188，含 `try` 内的 `build_workspace_snapshot` import）；`app.py` 删 :169-188、:835 与 :1139 两处调用换成 `autosave_current_workspace(st.session_state, force=True)`、:165 的 import 追加该名字。
待裁决的一处：`app.py:187` 的第三种错误文案——① 逐字随迁（行为零变化，但把三串并存的债搬进模块）／② 归一到「自动保存准备失败，请手动导出项目快照」（用户可见文案变更，**需人工签字**，在册测试不钉它）。
**`app.py:347` 不动**（人工快照语义，并入即造假）。
```
cd D:/code/psy-analysis
git diff --numstat -- app.py src/utils/autosave.py            # 申报逐枚可复算；期望 app.py 约 −20/＋3、autosave.py 约 ＋12/−0
wc -l app.py                                                  # 期望 2405−19＝2386（R0 后按实际基准重算）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import io;L=io.open('app.py',encoding='utf-8').read().splitlines();print([i+1 for i,l in enumerate(L) if '_autosave_current_workspace' in l])"   # 期望：[]（app.py 内零残留）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_autosave.py tests/test_autosave_acceptance_h912_06.py tests/test_autosave_bg.py tests/test_autosave_throttle.py tests/test_app_defaults_keys_snapshot.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_e2e_ui.py -q                              # 整件全跑（含 d913b-47 夹具那条路径）
```
回滚成本：单文件级 revert 即可，无数据面写。

**R2（安全网先行，蓝图 §5 的要求）——给上传段补静态结构钉＋把新 AppTest 件登记进白名单。**
新建 `tests/test_app_split_slice6a.py`（照 `tests/test_app_split_slice8_10.py` 的形状：`marker not in app_text` ＋ `marker in panel_text` ＋ 分支体行数上限 ＋ CRLF 感知取行）；**同笔**把该件档名加入 `tests/conftest.py` 的 `_APP_TEST_FILES`。
🔴 「同笔」是硬约束：拆开交＝HEAD 上留一枚零隔离的 AppTest 件，会写真实 `~/.psy_analysis`。
```
cd D:/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import io,re;s=io.open('tests/conftest.py',encoding='utf-8').read();print('test_app_split_slice6a.py' in s)"     # 期望 True（生效反证）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_app_split_slice6a.py tests/test_app_split_slice8_10.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q --collect-only 2>&1 | tail -3                                                                   # 只看收集面，不执行
```
回滚成本：删新件＋撤一行名单（两件同笔，一起 revert）。

**R3（片 6a 主体，按 R0 后的新行号重取切点）——走「无回调」的纯搬迁，边界取 :948 或 :960 二选一。**
新建 `src/ui/analysis_upload_panel.py`（**LF 行尾**，与其余面板一致）；app.py 分支体收成 title＋一行调用；面板签名 `render_analysis_upload_panel(session_state, *, autosave)` ——R1 已落地时 `autosave` 可不传（面板自己 `from src.utils.autosave import autosave_current_workspace`），但**建议仍保留关键字参数**，因为 R2 的静态钉要能断言「面板里没有只来自 app.py 的自由名」。
必改的一条：`__file__` → `from src.utils.app_paths import REPOSITORY_ROOT`，`_demo_dir = str(REPOSITORY_ROOT / "tests" / "fixtures")`（原 :845）。
不得提升的：分支内的 lazy import（蓝图 §5 标注 740ms 冷启动依赖它）。
```
cd D:/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/psy5/probe6a_free.py 738 948        # 期望：🔴 段为空（迁移前若 🔴 仍有名 ⇒ 未闭合，停手）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import io;b=io.open('src/ui/analysis_upload_panel.py','rb').read();print('CRLF',b.count(b'\r\n'),'LF',b.count(b'\n')-b.count(b'\r\n'))"   # 期望 CRLF 0
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import io;b=io.open('app.py','rb').read();print('CRLF',b.count(b'\r\n'),'bareLF',b.count(b'\n')-b.count(b'\r\n'))"                      # 期望 bareLF 0（app.py 不得被整文件换行污染）
git diff --stat --find-renames                                                                          # 期望 app.py 只有删＋接线，无「全文件重写」
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_upload_state.py tests/test_e2e_qimport_upload.py tests/test_app_split_slice6a.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_e2e_ui.py -q
```
回滚成本：新模块＋app.py 一处接线，可整体 revert；**零数据面写**（AppTest 已被 R2 的白名单隔离）。

**R4（收尾对拍，全量一次）——由主班在收班统一取，子班不跑。**
```
cd D:/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q     # 期望与 s927-71 基线 5509/3/29/27 对齐；红名集比对而非计数比对
```
🔴 判据口径（承 s927-71 主班硬结论）：**分母等价不代表红名集等价**——要比 node-id 名集，不能只比 passed 数。在册 3 枚红（`test_export_gate_global_scan`、`test_backup_user_data`、`test_lr_rerun_apptest`）若原样出现属已知，**不算新回归、不顺手修**。

**R5（规划域，人工）**——按 §2 出口 C 改写 roadmap R6 一句，并对「蓝图 S 序 vs roadmap 片序」二选一。执行班不代改。

## 5. 我作废过的初读（本单一律现取后再判）

1. 作废「片 4 需先新建键持有者」：`src/utils/autosave.py:49-50` 已有两键常量且已是主写方。
2. 作废「迁后 `_autosave_last_error` 会跨文件读写＝新形态」：跨文件读写**已是现状**（`undergrad_wizard.py:97` 读、autosave.py 写、app.py:325 读）。
3. 作废「app.py 内 `st.file_uploader` 只有 1 处」：实为 2 处（:372 侧栏／:772 上传段）⇒ 验收命令不能写成全文件 grep 期望命中 1。
4. 作废「片 5 = 196-663／468 行」：AST 现值 199–662／464 行（口径差 3＋1，结论不受影响）。
5. 作废「:738-957 是自然切点」：它把 :949-960 的路由单元（两枚 `st.stop()`）切开；自然切点是 :948 或 :960。
6. 作废我自己的第一判断「A 的第一步被键拓扑挡住」：真闸门是**在途 hunk 与 169-188 逐行重叠**（键拓扑已自洽）。
7. 作废「出口 C 的三条待回写还没做」：①② 已由 roadmap R5 落地，只剩③与阈值重设。
8. 作废「`test_e2e_rendering.py` 属上传段安全网」：它是 `if len(file_uploader)>0` 的条件式断言，上传器消失仍绿。
9. 未采纳（按盘态存疑）锚点 docstring 里的「调用点 :1015/:1319」——两版盘态都不符，属未入库注释自带失效锚点。
10. **自否证（本班先写错再改）**：我初稿写「工作树与 HEAD 恰好整体平移 28 行，无一例外」——**错**。第二枚 hunk 在片 4 的 docstring 里插了 3 行，故 :159–171 带是 Δ31、≥:175 带才是 Δ28；连带把 HEAD 片 4 终点写成 219（实为 **216**，17 行）。已按现取改正，并把「片 4 行数」改成需声明坐标系的量。**⇒ 「净差 −28」只能用于文件末尾，不能用于逐点换算。**
11. 同批现取补正：`_analysis_cache_key` 的 HEAD 位（1147/1156）与 `_recipe_prefill_text`（WT 1014/1023/1026 ⇄ HEAD 1042/1051/1054）由推导改为现取。

## 6. 零改动自证（本班收工现取）

```
$ date                                                    2026-09-30 01:0x（本机有休眠校时史，落笔前已重取）
$ git status --porcelain | wc -l                          12（开工 11 ＋ 本班唯一新建件 ＝ 12；他人在途 11 枚一枚未动）
$ git diff --numstat -- app.py                            12  40（仍是他在班那笔，本班一字未动）
$ sha256sum app.py                                        6522fa5ebb362103dc9d2a99146b0dae1b4eb553ea301a51e108bfcde3b0bfcd
$ git status --porcelain -- docs/insights/                 ?? docs/insights/s927-32-slice-order.md（唯一新增）
$ wc -l -c docs/insights/s927-32-slice-order.md            以主班复点为准（本件刻意不自指写死行/字节数，改一行即失真；终值见 result 件）
```
未跑任何 pytest／未连库／未碰 `data/`／未 `git add`／未联网。所有实测只读：`ast.parse`＋两枚复用探针（`tmp/psy5/probe6a_free.py`、`probe6a_ast.py`，均为上游班留下的 gitignore 下只读工件，argv 驱动、只打印不写文件）。

### 取证口径一条（写位班会踩）

emoji 类锚点**不要用 shell grep 直传**：`grep -n "📈 数据分析" app.py` 在 Git Bash 下恒 **0 命中**，且加 `PYTHONIOENCODING=utf-8` 也救不回来（该变量管 Python 的 stdio，管不到 MSYS 传参）——这是**假阴性**，不是「分支已迁走」。同一条用 UTF-8 python 读到 **4 处**（:292/:305/:738/:761），只 grep 中文片段「数据分析」得 6 处。⇒ roadmap 文末那句 `grep -n '📈 数据分析\|st.file_uploader…'` 的复算命令在 Windows 上不可直接照抄，验收命令里的页名匹配一律换成 python 现取或去 emoji 的片段匹配。
