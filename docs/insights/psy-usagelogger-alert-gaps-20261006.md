# usage_logger 告警面余留三缺口裁决材料（s1002-33，2026-10-06，只读）

- 承 s920-07 遗留 1＋s924-66 遗留 2/3。三缺口复现取证实跑（脚本化，证据节）。

## 缺口 1：`_ALERTED` 无清理入口（usage_logger.py:40）

- **现值**：模块级 `set`，`_alert_once`/`_warn_once` 双通道共用；全文件无 reset/clear 入口（`any("reset" in dir)` False）。进程级终身一次——长驻 Streamlit 进程里「日志目录坏了」这类告警第一天响过就永久哑。
- **案 A：`reset_alerts()` 显式入口**（推荐）。改动面＝+3 行（`def reset_alerts(): _ALERTED.clear()`）＋tests 1 例。红名单：无（纯增量）；消费方=夜间维护窗/maintenance_night 每轮开头调一次。
- **案 B：按小时自动重开**。改动面＝`_ALERTED` 换 `dict[kind, hour_stamp]`，两处 `in`/`add` 改 4 行＋常量。红名单：`test_usage_logger` 族按「进程级一次」钉的用例会红（需同批改）；语义变「每小时最多一次」，排障时同小时内的重复失败仍被吞。
- 建议 A（显式、语义零变、调用权在维护窗）。

## 缺口 2：写侧告警永久去重（:123/:149 `write_failed:<文件名>`）

- **现值**：kind 带文件名 ⇒ 同天同文件只响第一次；无计数档位（`any("count" in dir)` False）。日志按天轮转给天数维度兜底，但**同天内的持续写失败**只在第一次响——当天后续 N 次丢失不可见。
- **案 A：每 N 次重报＋累计计数**。`_ALERTED` 并行加 `_ALERT_COUNTS: Counter`，`_warn_once` 命中去重时递增，`count % 50 == 0` 时重报一条「已累计 N 次」。改动面＝+8 行；红名单：无既有例钉「二次必吞」（s924-66 只钉第一次），风险低。
- **案 B：维持现状＋文档声明**（当天可靠性由天轮转兜）。零改动。
- 建议 A（50 次阈值拍脑袋可调；给运维「同天持续失败」的量级感）。

## 缺口 3：`export_feedback_package` 的 `except ImportError: pass`（:255）

- **现值**：吞 `src.utils.environment_diagnosis` 缺席——环境诊断 JSON 缺席不告警、不落任何标记，反馈包静默少一节。
- **案 A：降级说明写进反馈包**。except 体改 `(output_dir / "environment_diagnosis.json").write_text(json.dumps({"status": "skipped", "reason": "environment_diagnosis 模块缺席"}, …))`——下游/人工打开包即知「缺而非漏采」。改动面＝+5 行；红名单：无钉「文件不存在」的既有例（消费面 0 读取点，s930-23 已查）。
- **案 B：加 logger.debug**（与 s1002-21 普查建议一致）。一行级；但 debug 级默认不可见，排障帮助有限。
- 建议 A＋B 并用（A 面向反馈包消费者、B 面向本机日志）。

## 三案改动面汇总

| 缺口 | 推荐案 | 生产码 | 测试 | 红名单 |
|---|---|---|---|---|
| 1 reset 入口 | A | +3 行 | +1 例 | 无 |
| 2 写侧重报 | A | +8 行 | +1 例 | 无（第一次响不被改） |
| 3 诊断缺席 | A+B | +6 行 | +1 例 | 无（消费面 0 读取点） |
