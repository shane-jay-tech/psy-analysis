# s922-07 材料单：「⚡ 一键批准高置信」分支两段式确认评估（只读，零代码 diff）

- 班次：qoder-executor-20260921-2206-psy · 2026-09-21T22:15
- 锚点复核：s921-11 遗留原文有效——「⚡ 一键批准高置信」与逐卡批准仍在直接写库无确认（磁盘实测 feed_panel.py:187-197 / :263-271；行号漂移留痕：s921-10 +1、本班 s922-06 又 +1，本文全部按当前磁盘实况重取）。
- 红线自查：本档只登记 UI 写库面与调用链，不判定任何候选内容的医学/统计含义，零数值改动。

## 1 调用链（自上而下）

```
render_literature_feed()                      feed_panel.py:60
 └ tab_daily → _render_daily_tab(store)       :99 → :123
    ├ pending = store.list_candidates(status="pending", limit=20)   :177  ← 只取前 20
    ├ high_conf = [c for c in pending if (c.get("confidence") or 0) >= 0.8]  :182
    ├ 「⚡ 一键批准高置信 (N)」 :187-197  点击即
    │    for c in high_conf: store.update_candidate_status(cid, status="approved", reviewer="batch_high_conf")  :192-195
    │      └ feed_store.py:551-569  UPDATE llm_candidates SET status=?, reviewer=?, reviewed_at=?, rejection_reason=NULL, target_kb_id=NULL WHERE candidate_id=?
    │        每行一个独立 transaction()（一次 commit），N 条 = N 次落盘
    └ 逐卡「✅ 批准 / ❌ 拒绝」 :263-271  同函数同性质，reviewer="manual"，单行
```

对照面（本仓自己声明的口径）：
- 批量拒绝 :199-220 —— 两段式（`_confirm_batch_reject` 武装帧 → 确认/取消），已被 s921-11 四条钉桩锁死行为。
- 危险区「重置 pending 候选」 :787-800 —— 第三种口径：checkbox 门禁 + 单条 UPDATE（一次提交）。
- 独立面板 literature_review_queue_panel.py:26 走 review_service；**review_queue_ui.py:4 明文「所有审核操作走 review_service，不可绕过」**——review_service.review_candidate(:41-83) 除 UPDATE 外还写 `candidate_review_events` 审计表（:78-81），且支持 deferred/merged/rejection_reason。feed_panel 的三条批准/拒绝路径**全部绕过该层**，批准动作在审计表零留痕。

## 2 写库面与风险量化（按可逆性排序）

1. **不可逆面**：approved 后候选退出 pending 查询面（:177 只列 pending），feed_panel 内无任何 UI 可回退；唯一现成出口是危险区反向 SQL（无此按钮）或手工 SQL。批准 N 条 = N 行 status/reviewer/reviewed_at 三字段覆写、rejection_reason/target_kb_id 清空（feed_store.py:564-568 无条件 SET）。
2. **半批态**：for 循环无 try（对照 s922-05 材料单同款「一条坏数据弃整批」形态）——第 k 条抛异常则前 k-1 条已各自 commit 不可回滚，页面整页红，剩余 N-k 条停在 pending；toast/rerun 都不执行。
3. **审计缺口**：reviewer="batch_high_conf" 写进了 llm_candidates.reviewer 列（部分可溯源），但 candidate_review_events 无行 → list_review_events 查不到批量批准历史；且逐卡再操作会覆写 reviewer，痕迹被抹。
4. **口径不一致三处（任务书点名项）**：
   a. 同 tab 同列族：拒绝批量=两段式，批准批量=直接写——风险方向相反的两者防护倒挂（拒绝至少还有确认帧）。
   b. 「一键批准高置信 (N)」与「全部拒绝」的 N 都来自 **limit=20 切片**，而 caption 明写「共 total_pending 条待审 · 显示前 20」：按钮语义是「批准/拒绝**全部**高置信」，实际只作用于前 20 条中的高置信——总数 >20 时静默漏批，与文案不一致（拒绝帧 warning 文案「确定拒绝全部 {len(pending)} 条」同样把切片说成全部）。
   c. 逐卡批准 reviewer="manual" 与批量共用同一状态字段，无 source 区分列，回滚批量只能靠 reviewer 值匹配，脆弱。

## 3 两段式方案草案（供放行后另单执行，本单不动码）

- **R1 复用既有范式**：照抄 `_confirm_batch_reject` 键名风格加 `_confirm_batch_approve`，武装帧显示「确定批准全部 N 条高置信候选？· 实际待审共 M 条」——一句同时修掉 4b 的口径问题（N=命中数，M=count_candidates 全量数）。确认/取消两键、取消只清态。钉桩直接套 s921-11 的 4 例假 st 跨帧 harness，改断言即可（status_writes 期望 approved/batch_high_conf）。
- **R2 收敛写路径**：把 :192-195 换成 review_service.bulk_review_candidates(store, ids, "approved", "batch_high_conf")（该函数已存在且带逐条 try+审计写入，直接解决风险 2/3 的一半）。注意其 :103 `except (ValueError, Exception)` 实际吞所有异常并只 logger.warning——若采纳 R2 需配「成功 x/N 条」回显，否则失败静默是第四种坑。
- **R3 回滚出口**：危险区加「撤销上次批量批准」按钮（UPDATE llm_candidates SET status='pending', reviewer=NULL, reviewed_at=NULL WHERE reviewer='batch_high_conf' AND status='approved'，单事务），checkbox 门禁同危险区现有口径。属新增写面，建议人工放行后再做。
- **不建议**给逐卡批准/拒绝加两段式（单条粒度 + 卡片就在眼前，确认疲劳反而降低复核质量），只需并入 R2 走 review_service 补审计。
- 交审顺序建议：R1（纯 UI 防护，最小）→ R2（换写路径，动 import）→ R3（新写面，单独批）。

## 4 证据附录（本单实跑命令）

```
$ sed -n '187,197p;263,271p' src/literature_feed/ui/feed_panel.py   # 直接写库两分支，见 §1
$ sed -n '551,569p' src/literature_feed/storage/feed_store.py       # UPDATE 无条件 SET 五字段
$ grep -n "不可绕过" src/literature_feed/review_queue_ui.py          # :4 审计层声明
$ grep -n "candidate_review_events" src/literature_feed/review_service.py  # :78-81 INSERT 只在走 review_service 时发生
```
生产码 diff：无（本档为唯一新增文件）。
