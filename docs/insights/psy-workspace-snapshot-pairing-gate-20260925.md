# psy workspace 快照「四键成对性」门禁设计稿（含 restore 缺键实测）

> 班次 `qoder-executor-20260925-0800-psy57`（只读位）· 2026-09-25 08:0x · 单号 `s924-62`
> 基线：`src/utils/workspace.py` / `src/ui/project_panel.py` / `src/ui/template_center_panel.py` / `app.py` 均取 **commit `928e62e`** 之上的工作树；
> 其中 `app.py` 是他班在途件（`12/40`），本档所有 app.py 行号**取自该 commit 的 blob**（`git show 928e62e:app.py`，2,433 行），不取工作树读数，以免被他班推号。
> **零代码改动 / 零写库 / 零生产目录写**（只读自证见 §七）。
> 与 `s923-38`（`docs/insights/psy-snapshot-key-sizing-20260923.md`，**体量** 26 键实测）互补不撞：本档只管**成对性**。

---

## 一、锚点复核（卷宗三锚 ＋ 本档新增锚）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
for p in ['src/utils/workspace.py','tests/test_workspace_restore_pairing_pins.py']:
    ls=open(p,encoding='utf-8').read().splitlines(); print('===',p,'lines',len(ls))
    for n in (238,240,15):
        if len(ls)>=n: print(p,n,repr(ls[n-1]))
"
```

| 卷宗锚 | 磁盘实况 | 判定 |
|---|---|---|
| `src/utils/workspace.py:238` `for k in ["meta", "inspector", "file_name", "analysis_history"]:` | 逐字一致 | ✅ 零漂移 |
| `src/utils/workspace.py:240` `if v is not None:` | 逐字一致（`:241` 为 `ws[k] = v`） | ✅ 零漂移 |
| `tests/test_workspace_restore_pairing_pins.py:15` `- 写侧对照 :238-241 build_workspace_snapshot：四键各自 if v is not None 才落盘 ⇒ 快照本身也不成对` | 逐字一致 | ✅ 零漂移 |

**卷宗三锚 0/3 漂移**（与同波次其它单出现 `+27/+30` 漂移的形态不同）；两个源件 mtime 都是 09-22（`workspace.py 30,998 B / 09-22 05:29`、`pins 14,747 B / 09-22 05:27`），本波未入库。

恢复侧与调用侧锚（本档自证，全部实读）：

| 现场 | 行号 | 实况 |
|---|---|---|
| 恢复侧 df 分支 | `workspace.py:594-601` | `df_b64` 存在且**能解码**才写 `df`；`except Exception: pass` |
| 恢复侧四键分支 | `workspace.py:606-611` | `for k in [四键 +5 键]: if k in loaded:` 逐键独立、与 df **零耦合** |
| 恢复入口三个调用点 | `project_panel.py:62 / :83 / :97` | **三处全部包在 `try/except Exception: pass` 里**（实测见 §五方案 B 的硬约束） |
| 切换项目的清空 | `project_panel.py:54` | `st.session_state.clear()` ⇒ 种子键被抹掉 |
| 会话补种 | `app.py`(blob `928e62e`):90-118 | `_defaults` 含 `df/meta/inspector/file_name = None`、`analysis_history = []`；`:116-118 if key not in st.session_state` |
| 补种与恢复的先后 | `app.py`(blob):116-118 → `:193 ensure_active_project_on_first_visit()` | 先补种后恢复 |

---

## 二、restore 缺键实测（12 例，逐字读数）

复跑命令（产物落 `tmp/qoder-executor-20260925-0800-psy57/`，`PSY_ANALYSIS_HOME` 指沙盒，`app_paths.py:18` 实测支持该环境变量）：

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 PYTHONPATH=. \
  .venv/Scripts/python.exe tmp/qoder-executor-20260925-0800-psy57/probe62.py
rc=0
```

### 2.1 结论矩阵

| 例 | 喂进 `restore_workspace` 的载荷 | 抛异常 | `restored` | session 里四键形态 | 属性式读 `st.session_state.<k>` |
|---|---|---|---|---|---|
| A | 四键＋`df_b64` 齐备（对照） | 无 | **5** | 四键全 present | 4× ok |
| B1 | **缺 `meta`** | **无** | 4 | 键 `meta` **根本不存在**，余三 present | `meta` → **AttributeError** |
| B2 | **缺 `inspector`** | **无** | 4 | 同上形态 | `inspector` → **AttributeError** |
| B3 | **缺 `file_name`** | **无** | 4 | 同上形态 | `file_name` → **AttributeError** |
| B4 | **缺 `analysis_history`** | **无** | 4 | 同上形态 | `analysis_history` → **AttributeError** |
| C | 键在、值为 JSON `null`（`"file_name": null`） | 无 | **5** | `file_name` present、值 `None` | ok（读回 `None`） |
| D | 同时缺 `file_name`+`inspector` | 无 | 3 | 两键都不存在 | 两 AttributeError |
| E | 只带 `df_b64` | 无 | 1 | 四键全不存在 | 4× AttributeError |
| F | `{}`（完全空） | 无 | **6** | 四键全不存在 | 4× AttributeError |
| G | 齐备但**无 `_schema`** | 无 | 11 | 四键全 present（迁移链旁路补 5 键） | 4× ok |
| H | 齐备但 `_schema="v9.9"` | **`src.utils.workspace.FutureSchemaError: 工作区文件版本（v9.9）高于当前系统版本（v3.5），请升级系统后打开此工作区。`** | — | 零键（提前抛出） | 4× AttributeError |
| I | **写侧自然产物回读**（df＋meta 有值、三键 `None`） | 无 | **2** | 只有 `meta` present；`inspector/file_name/analysis_history` **不存在** | 3× AttributeError |

### 2.2 三条实测要点（不是推断）

1. **缺键既不抛也不补默认** —— 恢复层对"四键缺一"**零留痕**：`restored` 只是从 5 减到 4，没有异常、没有 warning、没有 `_workspace_*` 标记（例 B1–B4、D、E）。唯一有异常的形态是**版本号超前**（例 H），而它恰恰会在 `project_panel.py:62/:83/:97` 的 `except Exception: pass` 里被吞掉。
2. **「缺键」与「键在值 null」是两种不同状态，恢复侧只认后者** —— `workspace.py:609` 判的是 `if k in loaded`（键存在），不是 `is not None`。例 C 里 `"file_name": null` 被当齐备、`restored` 计满 5、值落 `None`；例 B3 同字段缺键则 `restored=4` 且属性式读取 AttributeError。**⇒ 任何"成对性门禁"若只判 `is not None` 会把例 C 误判成缺键；若只判键存在则会把例 C 当齐备放过去。两者都不是想要的不变量。**
3. **`restored` 计数不能当健全性信号** —— 例 F 喂完全空的 dict 也返回 6（迁移链 `MIGRATIONS["v2.9"]/["v3.2"]/["v3.3"]/["v3.4"]` 补 `upstream_state`、`literature_review_state`、`figure_collection`、`defense_qa_mastered`、`download_history`、`undergrad_wizard_data`）。**判"这次恢复到底有没有拿到数据"目前无任何返回值可用。**

### 2.3 写侧自然产物（例 I 的来源）

```
$ ... 同 probe62.py（write_side 段）
snapshot_keys_present_of_four = ["meta"]
snapshot_keys_absent_of_four  = ["inspector", "file_name", "analysis_history"]
has_df_b64 = true ; _schema = "v3.5" ; n_keys_total = 5 ; json_text_has_null_partner = false
```

`build_workspace_snapshot` 落盘的 JSON **从不出现 `"inspector": null` 形态**（写侧 `if v is not None` 把它挡了）⇒ 例 C 的 null 形态只可能来自**手工编辑**或**别的生产者**（见 §三）。

---

## 三、写侧不成对的**三处**生产者（改动面实测）

卷宗只点名 `workspace.py:238-241` 一处；普查实为 **三处、且两种相反方向**：

| # | 现场 | 四键处理 | df 处理 | 不成对方向 |
|---|---|---|---|---|
| P1 | `workspace.py:238-241`（`build_workspace_snapshot`） | 逐键 `if v is not None` | `:232` `df is not None and hasattr(df,'to_csv')` | **有 df 无伙伴键**（例 I 即此） |
| P2 | `template_center_panel.py:230-233`（`_build_core_workspace`，非 Streamlit 调用侧的第二份孪生实现） | 逐键 `if value is not None`（与 P1 **同判据同四键**，`:234-240` 同 df 判据） | 同 P1 | 同 P1；**改 P1 不改 P2 即出现两口径** |
| P3 | `template_center_panel.py:153-168`（模板建项目时手搓 dict） | **四键无条件全写**（`:157-160`，含硬编码 `"analysis_history": []`） | `:163 if df is not None` 才写 `df_b64` | **反向：有伙伴键无 df** —— 恢复后 `inspector` 声称 N 行而 `df` 缺席 |
| P4 | `project_manager.py:216`（`create_project` 的空工作区文件） | 零键：`{"_schema":"v2.9","_version":"2.9","_saved_at":now}` | 无 | **全缺**（合法空态，**数量最大的来源**） |

> P4 不是缺陷而是**最高频路径**：每建一个新项目在首次带数据 autosave 之前，盘上就躺着这份零键快照，且它的 `_schema` 是 `"v2.9"`（会走迁移链，例 G/F 的形态）。

---

## 四、存量快照兼容性（真目录抽样，只读）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
from pathlib import Path; import json
d=Path.home()/'.psy_analysis'/'projects'
print('exists',d.exists())
for f in sorted(d.glob('*.json')):
    try: o=json.loads(f.read_text(encoding='utf-8'))
    except Exception as e: print(f.name,'PARSE',type(e).__name__); continue
    if not isinstance(o,dict): print(f.name,'顶层',type(o).__name__); continue
    print(f.name, f.stat().st_size, o.get('_schema'), {k:(k in o) for k in
      ('meta','inspector','file_name','analysis_history')})
"
```

实测读数（**扫了 2 份 `*.json`，其中 1 份不是快照**）：

| 文件 | 字节 | `_schema` | df_b64 | 四键 | null 伙伴键 |
|---|---|---|---|---|---|
| `9b2b71937e1d.json` | 1,261 | `v3.5` | 有 | **全 present** | 无 |
| `index.json` | 170 | — | — | 顶层 `list`（项目索引，非快照） | — |

**兼容性结论（含样本量声明）**：真用户目录现存量 **1/1 件、四键齐备、无 null 形态** ⇒ 三种方案的**存量迁移成本实测≈0**。⚠ 但样本只有 1 件，**该结论不支持外推到"任何用户机上的历史快照"**——尤其 `project_manager.py:216` 使"零键快照"在任何用过新建按钮的机器上都是**多数形态**（本机之所以没有，是因为那唯一的项目已存过数据）。因此三方案的兼容性评估一律按「**必须同时容纳：齐备态 / 全缺空态 / 历史 v2.9 零键态**」三态设计，不得只按齐备态设计。

---

## 五、三方案对照（改动面 / 兼容性 / 风险）

### 方案 ①：写侧缺键补哨兵（写侧收口）

| 面 | 内容 |
|---|---|
| 改动点 | P1 `workspace.py:238-241` 改为「四键一次性判：`df` 有值 ⇒ 四键必须全有（缺者写显式哨兵），`df` 无值 ⇒ 四键全不写」；**同步改 P2**（否则两口径）；给 P3 补 df 缺失分支 |
| 收敛建议 | 更稳的形态是把 P1/P2/P3 合并成**唯一 builder**（P2 已是 P1 的复制粘贴孪生，P3 是第三种写法）——本档 §三的 census 就是它的改动面清单 |
| 兼容性 | 新快照多出 `"inspector": <哨兵>` 形态 ⇒ 恢复侧 `:609 if k in loaded` 会**照写哨兵值**，若哨兵不是合法 inspector 结构，会把「键不存在」风险换成「键存在且值是哨兵」风险，下游 `inspector.get(dv,{})`（`app.py` blob `:1090/:1094`）当场 TypeError/AttributeError ⇒ **必须配恢复侧识别哨兵**，①不能单独落地 |
| 风险 | 中：哨兵选型直接决定是"少崩"还是"换个崩法"；存量 1 件不受影响 |

### 方案 ②：恢复侧拒载并明确报错

| 面 | 内容 |
|---|---|
| 改动点 | `restore_workspace` 入口（`workspace.py:576-581` 之后）加四键成对性判定，不齐则抛 |
| **硬约束（实测）** | 三个调用点 `project_panel.py:62/:83/:97` **全部** `try/except Exception: pass`。例 H 的 `FutureSchemaError` 已经证明：**这条链上任何 `Exception` 派生的"明确报错"到 UI 就是零输出**——用户既看不到版本过高，也看不到缺键。⇒ 方案② 要真"报错"，只有两条出口：(a) 让错走 `BaseException` 直系（破坏现有语义，危险）；(b) **改三个调用点**（把 `except Exception: pass` 换成捕获后 `st.sidebar.warning(...)`）。(b) 才是正解，但它把改动面从 1 文件扩到 3 文件，且 `project_panel.py` 的 `_show_locked_banner`（`:20-25`）已有可复用的横幅形状 |
| 兼容性 | **P4 会被误杀**：零键空项目（`project_manager.py:216`）走拒载 ⇒ 用户点"新建项目"后切换/首次访问直接失败，这是最高频路径。⇒ 拒载必须显式豁免「无 `df_b64` 且四键全缺 ⇒ 判为空态放行」 |
| 风险 | 高：既有 `except Exception: pass` 让"拒载"默认退化成"静默不加载"，比现状更糟（现状至少恢复 df 与齐备键） |

### 方案 ③：快照 schema 版本化（`v3.5 → v3.6` 成对性契约）

| 面 | 内容 |
|---|---|
| 改动点 | `workspace.py:394` 写侧 `_schema` 升 `v3.6`；`CURRENT_SCHEMA`（`:403`）随升；`MIGRATIONS`（`:452-503`）加 `"v3.5": [补空态标记]`；`VERSION_ORDER`（`:553-565`）加 `"v3.5"`；新增 `_pairing` 元信息键（如 `"_partners": ["meta","inspector","file_name","analysis_history"]`）供恢复侧按**版本**而非按键存在判 |
| 兼容性 | 最好：老文件按 `_schema` 走迁移链（例 G 实测：无 `_schema` 也能被 `workspace_v1` 链吸收，`restored=11` 且四键不受影响 ⇒ **迁移链旁路对四键无副作用**，这条是本档实测给的绿灯）；写侧对老项目是纯增量 |
| 风险 | 中：**版本比较用的是 `tuple(int(p) for p in schema.split('.'))`（`:521-530`）**，`v3.10` 会算成 `(3,10)` 仍大于 `(3,6)`，无字典序问题，但 `VERSION_ORDER` 漏加一项就会让该版本**静默走空迁移链**（`_build_migration_chain:567-573` 找不到 `from_schema` 时 `started` 恒 False ⇒ 返回 `[]`，而 `:542` 仍把 `_schema` 改成 CURRENT ⇒ **假迁移成功**）。⇒ ③ 必须配一条"VERSION_ORDER 与 MIGRATIONS 键集一致"的门禁测试，否则版本化本身是个新的静默口 |
| 附带实测 | `_schema` 缺失（例 G）与 `_schema="v2.9"`（P4 真实形态）都会让 `:543` 写 `_migrated_from` ⇒ `restore_workspace:584-591` 会往 session 塞 `_workspace_migration_info`；这是**现成可复用的"恢复侧留痕通道"**，方案 B′ 直接搭它即可 |

### 推荐案（①×③ 的收口顺序 ＋ 一条不拒载的 B′）

1. **先做 B′（零生产语义改动的可观测层）**：在 `restore_workspace` 里按 `loaded` 实算四键成对性偏离，写进 `st.session_state["_workspace_pairing_info"]`（形状照 `:587-591` 的 `_workspace_migration_info`），UI 侧读它出 caption。**不抛错、不改恢复结果** ⇒ 与 `except Exception: pass` 无冲突，且实测零风险（本档 12 例里除 H 外全部 no-raise 路径）。
2. **再做①的"唯一 builder"收敛**（把 P1/P2/P3 三份实现合成一份，缺键写**结构合法的**空态而非哨兵字符串：`inspector={}`、`analysis_history=[]`、`file_name=""`、`meta={}`——注意必须是"能过下游 `inspector.get(dv,{})` 的空壳"），P4 保留零键 + B′ 判为空态。
3. **③ 作为第 2 步的记账版本**：builder 收敛落地当天把 `_schema` 升 `v3.6` 并补 VERSION_ORDER/MIGRATIONS 一致性门禁，老快照靠迁移链，不拒载。
4. **门禁测试接线**：扩 `tests/test_workspace_restore_pairing_pins.py`（现 **8 passed / rc=0**，本档复跑）而非新建件——它已钉住"改前基线"，且 `:88-106 _pinned_pairing_facts` 就是现成的判据函数；新增用例钉「任何 builder 产物 ⇒ 四键全有或全无（全无时 `_empty_project` 合法）」「`"x": null` 不得出现在落盘 JSON」「VERSION_ORDER ⊇ MIGRATIONS 键集」。**设计内翻正信号**：该档 `:4-7` 明示"给恢复路径补成对断言时本档用例应主动转红，请改断言不要删用例"。

---

## 六、完成标准逐条对照

| # | 标准 | 实测 |
|---|---|---|
| ① | 含 restore 缺键实测输出（异常类型或补默认值逐字） | §二：12 例，缺键 4 例全为「不抛＋不补默认＋`restored` 5→4」；唯一异常例 H 逐字 `src.utils.workspace.FutureSchemaError: 工作区文件版本（v9.9）高于当前系统版本（v3.5），请升级系统后打开此工作区。` |
| ② | 三方案各列改动面/兼容性/风险 | §五（含实测硬约束：三调用点 `except Exception: pass`、P4 空项目误杀、VERSION_ORDER 漏项假迁移） |
| ③ | `git status --porcelain` 仅设计稿新增 | 见 §七：在册 7 件他班脏态逐字不变，本档仅加 `?? docs/insights/psy-workspace-snapshot-pairing-gate-20260925.md` |
| ④ | `workspace.py` 零改动 | 见 §七：逐件点名 numstat 为空、size/sha8 前后同值 |

---

## 七、只读自证

```
$ cd /d/code/psy-analysis && git diff --numstat -- src/utils/workspace.py src/ui/project_panel.py src/ui/template_center_panel.py src/utils/project_manager.py src/utils/autosave.py tests/test_workspace_restore_pairing_pins.py
（无输出 rc=0 ⇒ 本班点名的 6 件净改动 0）
```
⚠ **不要把 `app.py` 放进这条点名里**：`app.py` 是他班在册在途件（`git diff --numstat -- app.py` 收班时仍读 `12 40`），
用目录级或"顺手带上 app.py"的写法会把他班改动算成本班。本档对 app.py 只做过两件事：`git show 928e62e:app.py` 取 blob、
把 blob 写到 `tmp/<班名>/app_head.py` 读行号——**零写入原路径**。

sha8/mtime 逐位自证（收工复点，与开工时同值）：

| 件 | 字节 | sha8 | mtime |
|---|---|---|---|
| `src/utils/workspace.py` | 30,998 | `45c41186` | 09-22 05:29:18 |
| `src/ui/project_panel.py` | 11,594 | `b72b5432` | 09-22 01:23:54 |
| `src/ui/template_center_panel.py` | 11,465 | `b76db341` | 09-22 04:13:24 |
| `src/utils/project_manager.py` | 12,369 | `14125de1` | 09-05 23:35:38 |
| `src/utils/autosave.py` | 9,932 | `fcc259c7` | 09-22 05:54:46 |
| `tests/test_workspace_restore_pairing_pins.py` | 14,747 | `8306e4b7` | 09-22 05:27:15 |

```
$ git status --porcelain
```
本单开工前基线（09-25 08:02:27 现取，7 件全为他班在册态）：
` M app.py`｜` M pytest.ini`｜` M requirements-lock.txt`｜` M src/questionnaire/exporters.py`｜` M tests/test_questionnaire_export_pdf_positive.py`｜`?? node_modules/`｜`?? tests/test_exporters_cjk_font_fallback_observability.py`

> **窗口内基线漂移留痕（非本班改动，也不据此指控任何写手）**：本班 08:2x 复点 `git status --porcelain` 另见
> `?? docs/insights/psy-workspace-snapshot-pairing-gate-20260925.md`（= 本设计稿，本班唯一产物）与
> ` M scripts/evaluate_socratic_benchmark.py`、` M tests/test_socratic_benchmark_archive_infra.py` 两件新增脏态——
> 后两件按纪律档 §十二 归属口径记为**同仓兄弟班在途作业**，本班未读未写未跑它们的件。

- 真库不变量 `data/literature_feed` 181 件 / 21,059,126 B 未触碰（本单不需要它，全程未打开）。
- 未启动 app、未跑 `AppTest`、未跑全量套件；只点名跑了 `tests/test_workspace_restore_pairing_pins.py`（8 passed，非他班在途件）。
- 探针写盘全部落在 `tmp/qoder-executor-20260925-0800-psy57/`（`.gitignore:29 tmp/` 实测 `git check-ignore` rc=0 命中），`PSY_ANALYSIS_HOME` 指沙盒 ⇒ `~/.psy_analysis` 仅只读扫描。
