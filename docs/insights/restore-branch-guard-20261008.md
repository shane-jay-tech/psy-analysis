# 恢复流程两分支无兜底——补齐裁决材料（s1007-22，零改码）

- 日期：2026-10-08 ｜ 上游：s1007-03 隐患②（口径表 #4/#5）｜ 性质：只读材料零改码

## ①两分支现值钉桩（src/utils/workspace.py，恢复流程计数段）

| # | 分支 | 现值（逐字） | 炸点 |
|---|---|---|---|
| #4 plan | :679-681 | `if plan_data is not None: st.session_state.plan = _deserialize_plan(plan_data); restored += 1` | `_deserialize_plan` 对垃圾串抛异常 → **整轮恢复崩**（后续 9 分支全不执行） |
| #5 analysis_output | :685-688 | `if ao_data is not None: st.session_state.analysis_output = _deserialize_analysis_output(ao_data); restored += 1` | 同上 |

对照（其余 11 分支兜底形态摘录）：#1 解码异常→pass 0 计／#3 非 dict 不计／#7 from_serializable 异常→pass／#10 异常→pass／#12 from_dict 异常→pass——**兜底族统一形态＝try/except 后跳过该键、计数不计、恢复继续**。

## ②补兜底两案影响面

### 案 A：try 包裹（对齐 11 分支先例）
```python
    if plan_data is not None:
        try:
            st.session_state.plan = _deserialize_plan(plan_data)
            restored += 1
        except Exception:
            logger.warning("workspace 恢复: plan 反序列化失败，跳过该键")
```
- 波及：2 分支 ×4 行；analysis_output 同型。
- 语义变化：垃圾数据从「整轮崩」变「该键丢弃＋告警」——**恢复成功率上升，且与「宁可不给数据」（s927-28 案 a）精神一致**。
- 测试面：新增 2 支（垃圾串载荷 → 恢复不崩、restored 不计、告警在册）；既有恢复流程测试零红（正常载荷路径不变）。

### 案 B：前置校验（deserialize 前查结构）
- 波及：需知 _deserialize_plan/_deserialize_analysis_output 的合法输入形态并手写校验——**形态知识重复实现**，且防不住未预期垃圾（校验漏项=仍崩）。
- 结论：天然弱于案 A，仅当主班要求「零异常吞」风格时才考虑。

## ③裁决表

| 维度 | 案 A try 包裹（建议） | 案 B 前置校验 |
|---|---|---|
| 对齐先例 | ✅ 与其余 11 分支同形 | ❌ 独立形态 |
| 防护完备 | 任何异常类型 | 仅已预见形态 |
| 语义变化 | 崩→跳过＋告警（恢复韧性↑） | 部分防御 |
| 成本 | ≈8 行＋2 测试 | 校验逻辑重写 |
| 建议 | **采 A** | 备选 |

## 复现

```
$ sed -n '679,688p' src/utils/workspace.py        # 两分支现值
$ sed -n '700,712p' src/utils/workspace.py        # 邻支兜底形态对照（#7 try/pass）
```
