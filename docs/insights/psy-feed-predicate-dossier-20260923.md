# psy 文献雷达「徽章 vs 一键批准」双谓词不一致裁决材料（s923-24，只读）

> 班次 `qoder-executor-20260923-0022-psy12`｜生成 2026-09-23 13:21｜cwd `D:\code\psy-analysis`
> **本档不改任何生产码**：`git status --porcelain src/literature_feed/` 为空（见文末「零改动自证」）。
> 上游：`zcode-bridge/done/s922-107-feed-batchapprove-pins.result.md`（登记了缺陷、判"修法属行为改动，未动"）。
> 本档只回答一个问题：**要统一的话，往哪个方向统一，各付出什么。**
> 全部读数可在 `tmp/s923-24/predicate_repro.py` 一次复算（约 1 秒、零网络、不启动 app）。

---

## 〇、结论先说

| | 案 A：两处判定**都取原值** | 案 B：两处判定**都取 round 后** |
|---|---|---|
| 批准集 | **变化 0 条**（批量本来就取原值） | **只增不减**，新增 = `(0.795,0.800)` 带 ∩ 前 20 切片；现役库 **0 条** |
| 语义 | 显示向真值收敛（徽章变严） | 门禁向显示收敛（**实际批掉置信 < 0.8 的条目**） |
| 与 `:190` help 文案「批准置信度 >= 0.8」 | 一致 | **矛盾**（须同时改文案） |
| 在册测试 | **预计 0 红**（徽章文案全仓零断言） | **≥1 红**（`test_feed_batch_approve_frozen_pins.py:179`） |
| 附带风险 | 无 | `round` 在二进制下不是十进制四舍五入 ⇒ 会把方向性误差带进**写库**面 |
| 工时 | **15–25 分钟** | **40–60 分钟**（含文案与用例翻正） |

⇒ 材料倾向 **案 A**，且**与 s922-07 的 R1/R2 冻结项解耦成独立小单**（§六）。

---

## 一、缺陷的准确形状（生产事实，逐字引用）

```
src/literature_feed/ui/feed_panel.py
:177  pending = store.list_candidates(status="pending", limit=20)
:182  high_conf = [c for c in pending if (c.get("confidence") or 0) >= 0.8]      # ← 批量批准：原值
:190      help="批准置信度 >= 0.8 的全部候选"
:221  st.caption(f"共 {total_pending} 条待审 · 显示前 20 · 高置信(>=0.8): {len(high_conf)} 条")
:227      conf = round(c.get("confidence") or 0, 2)                              # ← 卡片：先舍入
:249          if conf >= 0.8:   st.success("高置信", icon="✅")
:250          elif conf >= 0.5: st.info("中置信", icon="ℹ️")
:253          else:             st.warning("低置信", icon="⚠️")
```

- **锚点复核：三处全部逐字命中、零行号漂移**（任务书给的 :182/:227/:249 与磁盘一致）。
- `0.8` 在整个 `src/literature_feed/` 只出现在 :182/:190/:221/:249；`budget_tracker.py:81 warn_ratio=0.8` 是预算比例、**与置信度无关**
  ⇒ **双谓词是本页面局部问题，没有第三处要同步**。复算：`rg -n "0\.8" src/literature_feed/ --glob '*.py'`

---

## 二、三读数 × 两谓词行为表（任务书点名交付物）

内联复算（可直接粘贴）：

```
python -c "print([(x, round(x,2), round(x,2)>=0.8, x>=0.8) for x in (0.795,0.799,0.801)])"
```

| 读数 | `round(x,2)` | 徽章 `:249`（用 round 后） | 一键批准 `:182`（用原值） | 一致？ | 用户实际看到 |
|---|---|---|---|---|---|
| **0.795** | **0.8** | 高置信 ✅ | **False** | ❌ **分歧** | 绿标「高置信」；点⚡**不会**批它；按钮计数 `(N)` 也不含它 |
| **0.799** | **0.8** | 高置信 ✅ | **False** | ❌ **分歧** | 同上 |
| **0.801** | 0.8 | 高置信 ✅ | True | ✅ 一致 | 亮标且被批 |

⚠️ **对上游描述的一处收窄**：0.801 **不在分歧面里**，它是带上方的**阴性对照**。
把三读数并列容易让人以为"三处都错"，实际只有两个落在带里。

---

## 三、分歧不是两个点，而是一个连续带；且**单向**

内联复算：

```
python -c "N=60000; xs=[0.40+(1.00-0.40)*i/(N-1) for i in range(N)]; b=[x for x in xs if (round(x,2)>=0.8)!=(x>=0.8)]; print(len(b), min(b), max(b), max(b)-min(b))"
python -c "N=60000; xs=[0.40+(1.00-0.40)*i/(N-1) for i in range(N)]; print('反向分歧条数', sum(1 for x in xs if x>=0.8 and round(x,2)<0.8))"
```

| 扫描结果 | 读数 |
|---|---|
| 0.8 档分歧样本 | **500 / 60000**，区间 ≈ **(0.795007, 0.799997)**，宽度 **0.004990** |
| 反向分歧（被批但不亮高置信）样本 | **0** ⇒ **徽章集 ⊇ 批量集恒成立** |
| 0.5 档同形状带 | **500/60000，区间 ≈ (0.495002, 0.499992)**（`:250` 中置信档，任务书未点名） |

**"单向"是本案最重要的结构事实**：`round` 最多把值挪 0.005，从 ≥0.8 的位置**不可能**被挪到 <0.8。
⇒ 用户永远只会被"**多亮标签**"误导，不会被"少亮标签"坑到；
⇒ 所以案 A（收紧显示）是**纯纠错**，案 B（放宽批准）是**放宽门禁**——两者不是"两种等价风格"。

⚠️ **带下界不是一条干净的 0.795**：

```
python -c "from decimal import Decimal`nfor x in (0.795,0.785,0.815,0.845,0.855): print(x, round(x,2), format(Decimal(x),'.20f'))"
```

（上面是两行式 `-c`；单行版：`python -c "from decimal import Decimal; print([(x,round(x,2),format(Decimal(x),'.20f')) for x in (0.795,0.785,0.815,0.845,0.855)])"`）

| x | `round(x,2)` | Decimal 真值 |
|---|---|---|
| 0.795 | **0.8**（抬上去了） | 0.79500000000000003997（**略大于** 0.795） |
| 0.785 | 0.79 | 0.78500000000000003109 |
| 0.815 | **0.81** | 0.81499999999999994671（略小于 0.815 ⇒ 舍下） |
| 0.845 | **0.84** | 0.84499999999999997335 |
| 0.855 | **0.85** | 0.85499999999999998224 |

⇒ 0.795 被抬到 0.8 是**这枚 double 恰好偏大**的结果，不是"四舍五入规则"。同一个 `round` 在 0.815/0.845/0.855 上方向相反。
⇒ **案 B 若复用 `round`，等于把这种不可预测性从显示层搬进写库层**；真要走案 B，正解是 `Decimal` 或 `conf >= 0.8 - 1e-9`（那是**又一次**行为改动）。

---

## 四、带能不能被命中？——能。今天的 0 命中是数据运气

### 4.1 现役库实测（沙盒副本，`PRAGMA integrity_check` = ok）

```
python -c "import sqlite3;c=sqlite3.connect('tmp/s923-24/feed.sqlite');print(c.execute('SELECT confidence,COUNT(*) FROM llm_candidates GROUP BY 1 ORDER BY 2 DESC').fetchall())"
```

| 指标 | 读数 |
|---|---|
| 候选总数 | **122**（approved 105 / pending 17） |
| `confidence` 取值 | **`0.95`×48、`0.9`×47、`0.85`×15、`0.8`×6、`1.0`×3、`0.7`×2、`0.75`×1** ⇒ 7 个格点，全 2 位小数 |
| 非 2 位精度的行 | **0** |
| `confidence IS NULL` | **0** ⇒ `(x or 0)` 兜底面本库未触达 |
| 落在 0.8 分歧带 `(0.795,0.8)` | **0 条**（全库，不限 pending） |
| 落在 0.5 分歧带 `(0.495,0.5)` | **0 条** |
| 可见切片 | pending **17 < limit=20** ⇒ 今日未触发 `:177` 切片裁剪 |
| 徽章高置信数 / 一键批准数 | **17 / 17，差集空** ⇒ 两谓词今日给同一个集合 |

⇒ **两案的"当前批准集影响"实测都是 0 条**。这条必须写清楚，否则会把它当成现症去排紧急单。

### 4.2 但上游不设防

- `src/literature_feed/extract/extractor.py`：`conf = float(n)` / `conf_raw = float(item["n"])` —— **无 `round`、无量化、无 clamp**。
- `src/literature_feed/extract/prompts.py:28`：示例只写 `"confidence":0.85`（另一处 `0.9`），约束文案是「`n ∈ [0,1]`」——**没有小数位数要求**。
- 唯一的上游数值约束是「`conf < 0.4` 视为低置信丢弃」，与 0.8/0.5 两档无关。

⇒ LLM 只要回一个 `0.799`，带当场命中，且**这条链上没有任何一处会拦它**。
⇒ 若要估"历史命中频率"，那属统计结论域（红线），**本档不做**。

---

## 五、两案影响估计

记 `S_raw = {c : conf(c) >= 0.8}`（今日批量名单）、`S_round = {c : round(conf(c),2) >= 0.8}`（今日徽章名单）。
§三 已证 `S_raw ⊆ S_round`，差集 `D = {c : 0.795 < conf(c) < 0.800}`。

### 案 A：两处判定都取**原值**（`round` 只留给显示文案）

- 改点：`:249`/`:250` 的判据从 `conf` 改成原值（或在 `:227` 旁并存一个 `conf_raw`，判据一律用 `conf_raw`）；`:227` 的 `conf` 退化为纯显示量。
- **批准集变化：∅**。`S_raw` 的定义没动 ⇒ **一条都不会多批、一条都不会少批**。
- 显示变化：`D` 内条目从「高置信」降为「中置信」；若同时处理 0.5 档，`(0.495,0.5)` 内条目从「中置信」降为「低置信」。
- 与文案：`:190`「批准置信度 >= 0.8」、`:221`「高置信(>=0.8)」在案 A 下**自动自洽**（判据就是字面原值）。
- 测试面：`tests/test_feed_panel_charac.py`/`test_feed_batch_approve_frozen_pins.py`/`test_literature_feed_ui.py`/`test_feed_panel_trending_override.py` 合计 40 例里，
  **对「高置信/中置信/低置信」徽章文案零断言**（`rg -uu -n "高置信|中置信|低置信" tests/*.py` 的命中全部落在注释与 `APPROVE_LABEL_HINT` 按钮前缀上）
  ⇒ **预计 0 红**；`:179` 那条批量钉桩在案 A 下**保持绿**（`store.writes == [22]`、标签 `"(1)"` 都不变）。
- 建议同时补 3–5 例徽章钉桩：0.795/0.799 必须落「中置信」、0.8 必须落「高置信」，否则这次统一没有看守。
- **工时：约 15–25 分钟**（2 处判据 + 常量/纯函数抽取 + 3–5 例钉桩 + 跑上面两个测试文件）。

### 案 B：两处判定都取 **round 后**（`:182` 跟上 `:249`）

- 改点：`:182` → `[c for c in pending if round(c.get("confidence") or 0, 2) >= 0.8]`。
- **批准集变化：单调扩大**，`S_raw → S_round`，新增集 = `D ∩ 前 20 切片`；**现役库 0 条**，但结构上会把「实际置信 < 0.8」的条目纳入一键批准。
- 语义方向：**放宽门禁**。与 `:190` help「批准置信度 >= 0.8」**直接矛盾** ⇒ 必须同时改文案（例如"约 0.8"），否则修一个不一致造出一个新的。
- 测试面：**至少 1 红** —— `test_feed_batch_approve_frozen_pins.py:179`（0.799/0.795/0.8 三条夹具，现断言只批 `[22]`、标签含 `"(1)"`；案 B 下变 `[21,22,23]`、`"(3)"`）。
  该件 docstring 已自陈"翻正请改断言而不是删用例" ⇒ 这条红属**设计内翻正**，但**需要人工确认**。
- 附带风险：§三 的 `round` 方向性表 ⇒ 案 B 把不可预测的二进制舍入**引入写库判定**。
  若坚持案 B，工程正解是 `Decimal(str(conf)).quantize(...) >= Decimal("0.80")` 或 `conf >= 0.8 - 1e-9`，
  而那已经是**第三次**行为改动，应单列。
- **工时：约 40–60 分钟**（1 处判据 + 1 条用例翻正 + help/caption 文案同步 + 是否改用 Decimal 的落地），另加 §六 的合流成本。

### 共同第三案（本档不推荐，但登记）

案 C：**统一提高到"显示也只报原值到 2 位"**（即 `:227` 改成 `f"{conf_raw:.2f}"` 只是格式化、判定与文案一律原值），行为与案 A 等价、
差别只在实现是否保留 `round()` 调用。**案 A 与案 C 的选择是风格问题，对批准集与测试面同读数为 0。** 不单列。

---

## 六、排单依赖（必须一并知道，否则会把两笔改动撞在一起）

`tests/test_feed_batch_approve_frozen_pins.py` 顶部自陈：**s922-07 §3 的两段式改造未放行**——

- **R1**：一键批准缺确认帧（现在"点一次就直接写库"）；R1 落地会顺带修掉「`limit=20` 静默漏批」与「按钮文案说全部、作用域是切片」。
- **R2**：批准循环应收敛到 `review_service.bulk_review_candidates`（现在第 k 条炸 ⇒ 前 k-1 条已各自提交，半批态不可回滚）。

⇒ **双谓词统一（本档）、R1、R2 三笔改动都动 `feed_panel.py:177-197` 同一段。**
建议：

1. **案 A 排在 R1 之前单独落地**——它不碰写库集合，与 R1/R2 无断言冲突（§五 已证测试面 0 红）。
2. **不要让案 B 与 R1 并行**：两者都会改 `high_conf` 的算法与按钮计数语义，合流时同一批断言要被翻两次，必冲突。
3. 若人工选案 B，请把"文案同步改"与"是否用 Decimal"**写进同一单**，别拆——拆开了会出现"行为放宽了、文案还说 >= 0.8"的中间态。

---

## 七、零改动自证

| 判据 | 命令 | 读数 |
|---|---|---|
| `src/literature_feed/` 零改动 | `git status --porcelain src/literature_feed/` | **空** |
| 整个 `src/` 零改动 | `git diff --name-only HEAD -- src/ \| wc -l` | **0** |
| 他班在途三件未被本班改 | `git diff --numstat HEAD -- app.py pytest.ini requirements-lock.txt` | `12 40` / `1 1` / `6 6` ＝**开工前同值** |
| 文献库原件零写坏（纪律档 §廿一） | `.venv/Scripts/python.exe -X utf8 tmp/psy12/feed_guard.py verify` | **181 件 / changed 0 / ZERO-DIFF** |
| benchmark 不变量 | 逐件 sha256_8 | `3d83f7e9 / dff47515 / 092d61b0 / 909b4799`，mtime ≤ 09-16 |
| 全局账本门无新增红 | `.venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"` | **1 failed / 19 passed / 1 skipped**（＝在册红，待人工 81，本班未修未放宽） |
| feed 邻域基线 | `pytest tests/test_feed_batch_approve_frozen_pins.py tests/test_feed_panel_charac.py tests/test_literature_feed_ui.py tests/test_feed_panel_trending_override.py -q` | **8 failed / 36 passed** ⇒ 全部 8 条红是**测试隔离缺陷**，非本档、非生产码（见 §八.1） |
| 未启动应用 | 本档全程 `python -c` / 纯 sqlite3 复算，**未 import streamlit、未跑 `AppTest`** | ✅ |

沙盒法：`data/literature_feed` 整套 181 件 `copy2` 到 `tmp/psy12-feed-sandbox/`（跑 pytest 时用 `LITERATURE_FEED_DATA_ROOT` 指过去）；
库读数则用 `tmp/s923-24/feed.sqlite{,-wal,-shm}` 副本查询（允许 WAL 回放，故比 `immutable=1` 更接近现盘）。

---

## 八、本档换来 / 撞到的坑

1. 🔴 **新发现一条 psy 测试隔离缺陷（不属本单范围，未修）**：
   `tests/test_literature_feed_ui.py:13-19` 的 `feed_root` 夹具会 `setenv("LITERATURE_FEED_DATA_ROOT", tmp_path)` 后
   **把所有 `src.literature_feed*` 从 `sys.modules` 里删掉**；而 `tests/test_feed_panel_trending_override.py` 在**模块导入期**
   就绑定了 `tw_mod` 与 `_apply_trending_override`，且生产函数 `_apply_trending_override` 内部是**函数级懒导入**
   ⇒ `monkeypatch.setattr(tw_mod, "write_trending_yaml", capture)` 打在**已被驱逐的旧模块对象**上，捕获器永不被调，8 例 `IndexError: list index out of range`。
   - 复现（红）：`pytest tests/test_literature_feed_ui.py tests/test_feed_panel_trending_override.py -q` → **8 failed / 6 passed**
   - 复现（绿）：`pytest tests/test_feed_panel_trending_override.py -q` → **8 passed**
   - ⇒ 这是纪律档 §九「psy 全量**失败集合本身不稳**」的一条**具体机制**：既非负载相关，也非并发污染，而是**夹具 purge `sys.modules` × 测试件模块期绑定 × 生产懒导入**三者相乘。
     修法（改测试）属另一单，交主班登记台账。
2. **"两个谓词不一致"必须先判方向再判成本**：本案分歧单向（`S_raw ⊆ S_round`），所以两案一个是纯纠错、一个是放宽门禁，**成本不对称的主要来源是语义风险而不是 LOC**（两处改动都是 1 行级）。凡"显示 vs 判定"类不一致，先扫一遍反向分歧是否存在，能直接把决策空间砍掉一半。
3. **`round()` 不能当"业务上的两位小数"用**：0.795→0.8 与 0.815→0.81 同函数反向（§三 表）。裁决材料里若不写这条，人工很容易把案 B 读成"和显示对齐就行"。
4. **锚点计数在 psy 侧也会漂**：`s922-107` 记的 :182/:227/:249 今日**零漂移**（与 §十七 里 kaoyan 锚点大幅漂移不同），
   但 `data/literature_feed` 的 `feed.sqlite` mtime 在 12:15 被并发写手推过（§十七 已提醒）⇒ **库内读数一律现取**，本文 §四 的 122 条/17 pending 只在 13:21 那一次取值有效。
