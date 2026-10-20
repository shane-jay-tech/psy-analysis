# 锁域告警 bark 化裁决材料（s930-09 遗留：_alert_once 只进 logging）——s1004-24

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T18:2x ｜ 性质：方案材料不落码（现契约内不改）
> 矿源：`zcode-bridge/done/s930-09.result.md` 遗留逐字：「_alert_once 的告警只进 logging——若主班要 bark 化告警属另一面」。

## 一、告警面清单（rg 行号＋现契约行为）

**面 1｜lock_manager.py `_alert_once`（:89-94）**——`logging.warning("[lock-alert] …")`，同实例同 kind 去重。三个触发点：

| kind | 行号 | 触发 | 用户可见性缺口 |
|---|---|---|---|
| `held_by_other` | :128-131 | is_locked 快速探测撞非阻塞锁 | 仅进日志；「另一个进程在干活」用户不知情 |
| `stale_lock` | :166-171 | 锁 mtime 超 TTL（s930-09 秒级文案在此） | 僵尸锁 12 天无人知（s1004-36 同款场景佐证） |
| `owner_write_failed` | :273-277 | 持有者信息写盘失败（OSError/ValueError） | 可观测性丢失不吱声于日志外 |

**面 2｜usage_logger.py `_alert_once`（:55-60）＋`_warn_once`（:63-69）**——同一命名空间前缀（:28 注释「运维侧一条 grep 收齐」）。触发：`mkdir_failed`（:86，日志目录不可用）。**该面 bark 化悖论**：目录坏＝本地 I/O 故障，bark 走网络＋requests 反而依赖更外层环境，且「每次埋点都撞」的去重语境下 bark 会打真机通知——建议**不纳**。

## 二、bark 通道姿势（grep 取证）

- **仓内（psy-analysis）**：`$ grep -rln "bark" src/` → **0 命中**＝零通道现成；
- **工作区可复用先例**：`D:/code/my-quant-system-v8/bark_sender/push.py:9` `send_bark(title, body, tokens=None)`（ggsuper API `sendMsg3_New.php`，:19；secrets.json 的 BARK_TOKENS，v8.7 无 token 返回 False 不静默）＋`training-reminder/push_training.py:236`（三态留痕版）。
- 接线形态建议：psy 侧不引依赖，新 `src/utils/bark_notify.py` 薄壳（读环境变量 `PSY_BARK_TOKEN`，无 token＝no-op 返回 False——与「无 LLM Key 降级」同族姿态，见 KNOWN_ISSUES 环境边界表「无 LLM API Key」行）。

## 三、bark 化前后行为对照（per 告警面）

| 面 | 现契约 | bark 化后 | 判定 |
|---|---|---|---|
| lock `stale_lock` | logging.warning（运维 grep 可见） | ＋bark「僵尸锁 X 分钟」 | **推荐**：僵尸锁正是 12 天无人知的真实事故形态（s1004-36 实证） |
| lock `held_by_other` | logging.warning | ＋bark | **不推荐**：正常并发即触发，bark 会通知疲劳 |
| lock `owner_write_failed` | logging.warning | ＋bark | 可选（低频、真异常） |
| usage_logger `mkdir_failed` | logging.warning | 建议不纳 | 网络通道悖论＋高频去重语境 |
| lock TTL 回收停摆（s1004-36 关联） | 无告警（daily_runner 双腿全灭） | bark 化的最大受益场景，但属 feed 调度面非本单 | 关联建议单 |

## 四、方案材料（不定案）

| 项 | 建议 |
|---|---|
| 触发接线 | `_alert_once` 内 logging 后追加 `bark_notify.try_send(f"[lock-alert] {kind}", message)`——**不改变去重语义**（bark 跟随既有 once 闸）；requests 失败吞掉再留 logging（告警通道自身不得炸主流程） |
| 降噪 | 仅 `stale_lock`＋`owner_write_failed` 两 kind 白名单 |
| 测试 | token 环境变量缺省 ⇒ no-op（monkeypatch 断言 requests.post 零调用）；白名单外 kind 零调用 |
| 红线 | token 属凭据域：只读环境变量/本地 secrets，禁止硬编码（t1004-06 探针同款纪律） |

### 证据存根

- `$ grep -rn "_alert_once" src/ --include="*.py"` → lock_manager :89/:128/:166/:273＋usage_logger :55/:86。
- `$ grep -rln "bark" src/ --include="*.py"` → 0；`$ grep -rln "def send_bark" D:/code --include="*.py"` → my-quant-system-v8/bark_sender/push.py＋training-reminder/push_training.py（通道先例）。
- `$ sed -n 89,94p / :120,131p / :160,171p / :268,278p src/literature_feed/scheduler/lock_manager.py` → 三触发面逐字。
- 禁令守约：现契约零改动。
