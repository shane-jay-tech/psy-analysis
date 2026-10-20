# exporters panel／summary 件 st-harness 同形冗余核对（s930-15 遗留，备用）——s1004-49

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T02:1x ｜ 性质：只核对不删，零码改动
> 矿源：`zcode-bridge/done/s930-15.result.md:29`（遗留逐字核对在册：「若后续清理，需一并核对 summary 件同形」）。
> 背景：s930-15 已抽共享基座 `tests/_feed_st_harness.py`（FeedStBase），panel 件＝`tests/test_feed_panel_charac.py:31 FakeSt`，summary 件＝`tests/test_feed_run_summary_key_contract.py:54 FakeSt`。

## 一、四形逐项与基座 diff 对照

基座四方法本体（_feed_st_harness.py:43-49,65）：markdown→`markdowns.append`、warning→`warnings.append`、divider→`dividers += 1`、`__getattr__`→`raise AssertionError(f"未预期调用 st.{name}")`；dataframe/button/columns 三分叉方法 raise NotImplementedError 强制子类覆写（s930-15 设计）。

| 形 | panel 件 | summary 件 | 与基座语义 |
|---|---|---|---|
| markdown | **保留**（:48，逐字同基座） | 未保留（继承） | 同 |
| warning | **保留**（:54，逐字同） | 未保留（继承） | 同 |
| divider | **保留**（:66，逐字同） | 未保留（继承） | 同 |
| `__getattr__` | **保留**（:98，逐字同） | **保留**（:76，逐字同） | 同 |

- panel 件另扩展 error/success/info/toast/container 六法——基座无此面，**属子类扩展非冗余**。
- 冗余面结论：panel 件冗余 **3+1 形**（markdown/warning/divider/__getattr__），summary 件冗余 **1 形**（仅 `__getattr__`）——矿源「summary 件同形」担忧实际已随 s930-15 抽基座消化大半。

## 二、rep2/3/4 空白形态差异有无结论

**summary 件不存在该差异面**：`$ grep -n "rep\|parametrize" tests/test_feed_run_summary_key_contract.py` → 0 命中（该件为键名契约测试，无 rep 参数化循环）；panel 件仅 :267 一处 parametrize（s930-15 的 rep1 收窄落点在其自身产线，非本两测试件的常设面）。⇒「rep2/3/4 空白形态差异致断言中断」问题在 summary 件**无对应物**。

## 三、两案材料（清则同笔断言翻面；本班零删）

| 案 | 动作 | 断言影响 | 建议 |
|---|---|---|---|
| 清理 | panel 件删 4 形＋summary 件删 1 形（均继承基座；约 −15 行） | **零**：四形与基座逐字同语义，`__getattr__` 报错文本亦逐字一致；同笔跑两件回归 `26 passed 持平`（s930-15 基准）即闭 | 收益小（26 例小面、可读性损益对冲），非必要不动 |
| 保留 | 维持现状（s930-15 原判「冗余无害」） | 零 | **推荐**：子类自文档化（读子类即见全貌），重复面 15 行属可接受税；若未来基座扩收集桶，子类显式覆写反而是防爆雷点 |

### 证据

- `$ grep -n "def markdown\|def warning\|def divider\|def __getattr__" tests/_feed_st_harness.py tests/test_feed_panel_charac.py tests/test_feed_run_summary_key_contract.py` → 形分布全图（见 §一表）。
- `$ sed -n 40,70p tests/_feed_st_harness.py` → 基座本体＋三分叉 NotImplementedError 设计逐字。
- `$ sed -n 54,98p tests/test_feed_run_summary_key_contract.py` → summary 件仅覆写 dataframe/button/columns/__getattr__。
- `$ grep -n "rep\|parametrize" tests/test_feed_run_summary_key_contract.py` → 0 命中。
- 零删守约：两测试件与基座文件本单零触碰。
