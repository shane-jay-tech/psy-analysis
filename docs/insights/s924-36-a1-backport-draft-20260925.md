# s924-36 落码草案 — app.py 计时面回流（案 A1，六 hunk patch 已生成）

> **状态：草案（未落 app.py）**。前置失败＝`app.py` 在途脏（` M`，52 行 diff，归属 d913a-43 的 startup 拆分，mtime 09-22 04:29，未收口）——任务书明令「否则只出落码草案并 partial」。**本档与 `tmp/s924-36-a1-backport.patch` 即全部交付物；app.py 未被本班触碰。**

## 一、草案内容（对现行 app.py :1646-1671 计时面，panel 已测口径回流）

6 hunk，patch 全文在 `tmp/s924-36-a1-backport.patch`（43 行，已在 tmp 副本上实改并过 `ast.parse`）：

1. **计时计算块**（:1646-1652）：`started_at = pending.get("started_at") or _t.time()` → `started_at = pending.get("started_at")`（去假 0 兜底）＋单一 `_now` ＋ `compute_pending_elapsed`/`pending_clock_anomaly`/`elapsed_txt` 三名（对齐 panel :201-205）。
2. **三名导入**：在 pending 分支内**懒导入** `from src.ui.questionnaire_panel import CLOCK_ANOMALY_WARNING_TEXT, compute_pending_elapsed, pending_clock_anomaly`——设计时点 design_engine 等重依赖必已入 `sys.modules`（问卷已在生成），无 D1 冷启动影响；不碰 panel 文件本体、不造第三副本。
3. **premium 标题行**：`（已 {elapsed}s）` → `（已 {elapsed_txt}）`（缺失态显「—」不再假 0）。
4. **premium 时钟异常警示**：`st.progress` 之前插 `if clock_anomaly: st.warning(CLOCK_ANOMALY_WARNING_TEXT)`（s922-139 补位）。
5. **premium 超时门**：`if elapsed > 90` → `if elapsed is not None and elapsed > 90`（负秒/缺失不再静默失效）。
6. **普通梯前置两支**：`elif elapsed < 30` 之前插 `elif elapsed is None: st.info("…缺少 started_at，耗时未知…")` 与 `elif clock_anomaly: st.warning(CLOCK_ANOMALY_WARNING_TEXT)`（对齐 panel :229/:231）。

草案自证：`grep -cE "pending_clock_anomaly|compute_pending_elapsed" tmp/app-backport-draft.py` → **3**（应用后 app.py 即满足完成标准①的 ≥2）；基线 `pytest tests -q -k "premium or pending"` → **100 passed**（5433 deselected）。

## 二、应用后的配套用例（app 侧新增，草案）

复用 `tests/test_questionnaire_panel_logic.py` 断言口径，新增 `tests/test_app_pending_clock_backport.py` 三例：

```python
import ast, pathlib

APP = pathlib.Path(__file__).resolve().parents[1] / "app.py"

def _app_src():
    return APP.read_text(encoding="utf-8")

def test_app_wires_panel_clock_helpers():
    src = _app_src()
    assert "compute_pending_elapsed" in src and "pending_clock_anomaly" in src
    assert 'started_at = pending.get("started_at") or _t.time()' not in src, "假 0 兜底必须已移除"

def test_app_premium_uses_elapsed_txt_and_anomaly_warning():
    src = _app_src()
    assert "高质量模式生成中（已 {elapsed_txt}）" in src
    assert "if elapsed is not None and elapsed > 90" in src

def test_app_normal_ladder_has_missing_and_anomaly_branches():
    src = _app_src()
    assert "缺少 started_at，耗时未知" in src
    assert src.count("CLOCK_ANOMALY_WARNING_TEXT") >= 3  # 导入 + premium + 普通梯
```

（结构级断言沿用 k920-56 B 组口径；行为级验收按 s923-22 门＝`test_e2e_ui.py:83` 的 AppTest，待真落时跑。）

## 三、落码步骤（app.py 让位后执行）

1. `git -C psy-analysis status --porcelain -- app.py` 为空（让位确认，d913a-43 收口后）。
2. `git apply tmp/s924-36-a1-backport.patch`（对 HEAD 态；若 d913a-43 落地改了行号，patch 的 hunk 锚文本仍逐字可配，冲突概率低）。
3. 落 `tests/test_app_pending_clock_backport.py`（上文）。
4. 验收：`rg -n "pending_clock_anomaly|compute_pending_elapsed" app.py` ≥2；`pytest tests -q -k "premium or pending"` 0 failed；`test_e2e_ui.py` AppTest 一跑。

## 四、前提与依据

- app.py 在途 diff 归属：d913a-43（startup_checks 拆分，`git diff` hunk 全在 :137-202，与问卷分支零交集——s923-22 同判）。
- panel 已测面：`tests/test_questionnaire_panel_logic.py` 567 行（compute_pending_elapsed 边界例 s921-07 系列、anomaly 判据 s922-02 系列全绿）。
- A1 清单出处：`docs/insights/psy-qpanel-parallel-impl-census-20260923.md` §五案 A 与 §三 D3；`zcode-bridge/done/s923-22.result.md`。
