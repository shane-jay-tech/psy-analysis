# 问卷引擎 Gap 2 接线设计稿（2026-09-06 凌晨，方案文档不实施）

- 对应：questionnaire-engine-audit-20260904.md Gap 2「基础引擎接入本地质检」（最高性价比 <50 行）；C2/C4 结论：premium 链路完备、基础引擎 14 项规范中 6 项未覆盖。
- 证据基线（本稿实读）：check_item_quality 签名 item_quality.py:19-25（items, construct_name, respondent_role, item_subject_template → ItemQualityReport，含 error/warning/info 三级 issues 与 10 分制 score）；premium 调用样例 llm_engine_premium.py:1331-1336；基础引擎主链路 llm_engine.py:71-102（design_questionnaire_llm → :101 raw=_parse_and_validate → :102 return _build_design_dict）。

## 一、接线点候选与选定

| 候选 | 位置 | 优劣 |
|---|---|---|
| 候选 1 | llm_engine.py:101-102 之间——`raw = _parse_and_validate(...)` 之后、`_build_design_dict` 之前 | ★推荐。raw["items"] 就是完整条目列表（构造名在 raw["construct_name"]），此刻插入同步质检最干净；失败/超时不影响已完成的 LLM 调用；与 premium 的 Step2 本地质检位置语义对齐 |
| 候选 2 | design_questionnaire_llm_async 包装层（:632 起） | 缺点：异步包装层职责是调度与取消，塞质检混淆职责；且 UI 轮询进度口径要跟着改 |
| 候选 3 | UI 层（app.py 问卷分支）调用后补检 | 缺点：审计报告指出的"基础引擎 6 项未覆盖"问题会继续对所有调用方不可见；不收口 |

**推荐候选 1**，理由：单点收口（所有走基础引擎的调用方都受益）、raw 结构稳定（_parse_and_validate 已保证 items 非空数组 ：338-339）、与 premium 的"Step2 本地质检"语义一致。

## 二、补丁草案（伪代码 diff，≤50 行量级，不落 src）

```diff
--- a/src/questionnaire/llm_engine.py
+++ b/src/questionnaire/llm_engine.py
@@ 设计_questionnaire_llm 主链路（:95-102 附近）
+from .item_quality import check_item_quality   # 文件顶部 import 区

 raw = _parse_and_validate(response_text, research_question)
+
+# ---- v5.11 Gap2：本地质量检查（best-effort，失败不阻塞主流程）----
+try:
+    quality_report = check_item_quality(raw.get("items", []),
+                                        raw.get("construct_name", ""))
+    weak = [it for it in quality_report.issues_summary  # 以 ItemQualityReport 实际字段为准
+            if it.get("type") == "error"]
+    raw["quality_gate"] = {
+        "score": quality_report.score,
+        "errors": len(weak),
+        "warnings": <warning 计数>,
+        "items_flagged": [条目下标列表],
+    }
+    # 处理策略：errors>0 的条目降级标记（quality_flag=true），不自动重生成——
+    #   基础引擎无 critique 基建，自动重生成会翻倍 LLM 调用时长与费用；
+    #   降级标记让 UI/报告可提示"以下条目建议复核"。
+except Exception:
+    raw["quality_gate"] = {"skipped": True}   # 质检任何异常都不阻塞出卷
+
 return _build_design_dict(raw, research_question)
```

要点：①只读检查不改 raw["items"] 本体（降级标记放旁路字段 quality_gate，UI 选择性消费）；②try/except 全包——质检属 best-effort；③premium 的 report 结构（issues/score）保持同源可序列化。

**处理策略三选一**：推荐**降级标记**（重生成一次会显著拉长基础引擎时长与费用，且无 critique 确认收敛；直接放行则 Gap 2 白修）。兜底：check_item_quality 抛任何异常 → quality_gate.skipped=True，主流程照常返回。

## 三、测试设计（≥4 条）

1. `test_quality_gate_runs_on_valid_items`：合法 items → quality_gate 存在、skipped 非 True、score 为 10 分制数值。
2. `test_double_barreled_item_flagged`：构造含"并且/同时"双重装载条目 → items_flagged 命中该条、errors≥1。
3. `test_weak_reverse_item_flagged`：构造"不+原词"伪反向条目（is_reverse=true）→ 命中弱反向检测。
4. `test_quality_check_exception_never_blocks`：monkeypatch check_item_quality 抛 RuntimeError → design_questionnaire_llm 正常返回，quality_gate.skipped=True。
5. `test_premium_path_unaffected`：premium 引擎既有测试零回归（回归保护）。
6. `test_items_not_mutated_by_gate`：质检后 raw["items"] 与质检前深度相等（旁路字段语义回归保护）。

## 四、与 6 条 Gap 的关系

- 本补丁**只覆盖 Gap 2**（基础引擎缺本地质检）。
- Gap 1（社会赞许性，两引擎 prompt 缺失）：属 prompt 文本补丁，与本接线正交，建议随同一 PR 顺带（一行 system prompt 追加），但需单独评审文案。
- Gap 3（基础引擎信效度声明）、Gap 4（premium Likert 点数）、Gap 6（条目-维度语义校验）：均不在本补丁范围；其中 Gap 6 若未来实现，建议挂在同一 quality_gate 字段下扩展。
- Gap 5（反向计分机器核对）：premium 侧独立小补丁，另行排期。

## 五、实施排期建议

补丁本体 <50 行 + 测试 6 条，半个日间工作块内完成；建议与 Gap 1（prompt 一行）合并为一个 PR，评审一次过。
