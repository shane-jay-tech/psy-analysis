# autosave 节流计时语义核对与测试（d913b-49）

## 一、§七-2 原文与现实现比对

- 设计稿原文（psy-snapshot-bg-queue-20260911.md §七.2）：「后台路径的 30s 节流以『提交』计时（原以『落盘』计）；同节流窗内结果结转依赖下次 trigger 调用触发。」——即设计稿**记载并接受**了「提交计时」为方案 B 的语义（非待修正项）。
- 现实现（autosave.py:166-171）：节流基准 SESSION_LAST_SAVE_KEY 在**入队（受理）时刻**写入（:171），与「提交计时」一致。
- **结论：实现与设计稿口径一致，无待修正差异**——按本单失败处理条款（设计稿未指定其它口径时保持现行为）保持不动，只出本报告与测试。

## 二、注入时钟测试（2 条，锁定提交计时口径）

- zcode-bridge/tests/test_autosave_throttle.py：FakeClock 注入 autosave.time.time + 同步路径（关后台开关）；
  ①阈值内（+10s）第二次 trigger 返回 False、落盘时刻不刷新（节流命中）；②跨阈值（+31s）重新落盘并刷新提交时刻。
- 计时可注入性验证：time.time 经 monkeypatch 替换即可确定性测节流（进一步抽 time_source 参数属可选重构，未实施）。

## 三、回归与不变量

- psy 全量：exit 0（0 failed，2586 基线口径零退化）；
- 真实 pending=0 / inbox=45 前后一致 ✓；方案 B 线程模型零改动 ✓。
