# psy `instance_lock` 时钟接缝裁决：epoch `st_mtime` 判龄 vs 墙钟内容戳

> 班次 `qoder-executor-20260925-0800-psy57`（只读位）· 2026-09-25 08:1x · 单号 `s924-63`
> 基线 commit `928e62e`（`git log -1` 现取，本班开工 08:12:17）；`src/utils/instance_lock.py` 146 行 / 5,582 B / sha8 `fe361ef1`（§八），mtime `2026-09-11 02:23:51` ⇒ **本波未被改动**。
> **只读裁决材料，不改锁语义、不改任何码。**
> 边界：本档只管**时间口径**。告警日志缺口／锁粒度／回退策略另册（`KNOWN_ISSUES.md:101` P1 行 ＋ `tests/test_instance_lock_alert_gap_pin.py` 钉桩），不在此抵账。

---

## 一、锚点复核（完成标准 ① 逐字）

```
$ cd /d/code/psy-analysis && rg -n "time\.time|datetime\.now" src/utils/instance_lock.py
117:                age = time.time() - lock_path.stat().st_mtime
132:    os.write(fd, f"{os.getpid()} {datetime.now().isoformat(timespec='seconds')}".encode("ascii"))
rc=0
```
卷宗两锚 **0/2 漂移**：`:117` 与 `:132` 逐字一致。python 轨对数同点（`total 146`，命中 2 行、行号同上）。

⚠ **本档踩到的工具坑（下传）**：`rg -E "time\.time|datetime\.now"` 在本机 **rc=2**，报
`rg: error parsing flag -E: grep config error: unknown encoding: ...` —— **rg 的 `-E` 是 encoding，不是 git grep 的扩展正则开关**；
纪律档 §十五.6 说的"`git grep` 默认 BRE 需 `-E`"不适用于 rg（rg 默认即 rust regex，交替无需开关）。
只看 stdout 会把这条 rc=2 读成"零命中"。三轨里可用的是：**rg 默认轨 ＋ python 字面计数轨**（`git grep -E` 是第三种）。

---

## 二、同一把锁上的两个时间源（实测，非推断）

探针：`tmp/qoder-executor-20260925-0800-psy57/probe63.py`（锁件全落 `tmp/.../locks/`，**未触碰 `PROJECTS_DIR`**）。

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe tmp/qoder-executor-20260925-0800-psy57/probe63.py
rc=0
```

`with project_lock(dir)` 内部一次取齐（`1_fresh_lock`）：

| 量 | 实测值 |
|---|---|
| 锁文件内容 | `161540 2026-09-25T08:14:48` |
| 内容戳（naive 本地墙钟，`:132`） | `2026-09-25T08:14:48` |
| `st_mtime`（epoch 秒，`:117` 的判龄源） | `1790295288.6429577`（`st_mtime_ns=1790295288642957800`，小数 7 位） |
| `age = time.time() - st_mtime` | `0.0090` s |
| **内容戳 − mtime（本地口径互读）** | **−0.642958 s** |
| **内容戳按 UTC 解释 − mtime 按 UTC 解释** | **+28,799.357 s（＝8 h − 0.64 s）** |
| `time.timezone` / `altzone` / `tm_isdst` | `−28800` / `−32400` / `0`；`tzname=('中国标准时间','中国夏令时')` |
| 释锁后锁文件 | 不存在（`:142 unlink` 正常） |

### 2.1 亚秒截断的**方向性**（6 次采样，逐次取锁）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "
import sys,time; from datetime import datetime; from pathlib import Path
sys.path.insert(0,'.')
from src.utils.instance_lock import project_lock
d=Path('tmp/qoder-executor-20260925-0800-psy57/loops'); d.mkdir(exist_ok=True); res=[]
for i in range(6):
    with project_lock(d) as lp:
        text=Path(lp).read_text(encoding='utf-8'); m=Path(lp).stat().st_mtime
        t=datetime.strptime(text.split(' ',1)[1],'%Y-%m-%dT%H:%M:%S')
        res.append(round((t-datetime.fromtimestamp(m)).total_seconds(),4))
    time.sleep(0.05)
print(res); print('全部落在 (-1,0] ？', all(-1.0 < x <= 0.0 for x in res))
"
[-0.8898, -0.957, -0.0099, -0.0711, -0.1247, -0.1768]
全部落在 (-1,0] ？ True
```
⇒ **两口径不是"随机不一致"，而是恒定单向**：`timespec='seconds'` 是**向下截断**，`os.write`/`os.close` 又把 mtime 推到 `datetime.now()` **之后** ⇒ 内容戳永远 ≤ mtime，偏差 ∈ (−1, 0] s。
这条同时决定：**任何拿内容戳与 mtime 互推"锁龄"的做法都会系统性偏小**，且 `st_mtime_ns` 有纳秒位，说明 FS 侧不缺精度，丢精度的是内容戳。

---

## 三、双口径风险清单（8 条，每条给实测/在册件出处）

| # | 风险 | 实测证据（探针 case ／ 在册件行） | 严重度判定 |
|---|---|---|---|
| **R1 时钟跳变（回拨向）** | `age` 是差分 ⇒ 墙上钟回拨 N 秒 ≡ 锁 mtime 前移 N 秒，二者对 `:117` **不可区分**。若回拨量 ≥ `stale_seconds`，**即使持有者已死也夺不掉锁**，项目被锁到"墙上钟追上"为止 | `2_clock_back_equiv`：mtime 前移 601 s、`pid_alive(999999)=False`、`age=-600.993` ⇒ 结果 **`ProjectLockedError`**（未夺锁）。本仓在册现象：纪律档 §一「本机休眠校时会让时钟双向跳」；同型判例 `tests/test_lock_manager.py:101` 已为另一把锁钉过「NTP 回拨导致 age<0：不炸，仍不陈旧」 | **高**（可用性；非正确性——不会双写） |
| **R2 touch 面** | `os.utime` 可任意改写 mtime ⇒ 判龄源完全可被外部（含测试、含脚本误操作）伪造，且**夺锁需 age 超阈值 ＋ pid 不存活**，两者都能伪造 | 在册测试件自己就在用：`tests/test_instance_lock.py:72`、`:96` 两处 `os.utime(lp,(old,old))`；`3_unparseable_content_aged`：不可解析内容 ＋ age 3600 ⇒ **`ACQUIRED（夺锁）`** | 中（设计内用法；缺的是"无防护声明"） |
| **R3 时区／夏令时** | 内容戳是 **naive 本地**（`datetime.now()` 无 tz）；判龄源是 epoch（本质 UTC 基准）⇒ 互读差 8 h；一旦按 tz-aware 消费（如 `datetime.fromisoformat` 后与 aware 值比较），naive 戳直接抛错或被隐式当 UTC | §二实测：按 UTC 解释 ⇒ **+28,799.357 s**；`tzname` 第二项『中国夏令时』在册、`altzone=-32400`（差 1 h），现测 `tm_isdst=0`；对照组：仓内**另一把锁已经是 tz-aware**——`lock_manager.py:244 datetime.now(timezone.utc).isoformat(...)` | 中（当前无害，因内容戳不参与判定；排障与未来消费会踩） |
| **R4 排障误导（内容戳唯一去处就是给人看）** | 内容戳只进 `ProjectLockedError.holder_since`（`:34-41`）与异常文本，**但 UI 侧只显示 pid**：`project_panel.py:23-25` 只取 `exc.args[1]` 拼 `pid=...` ⇒ 内容戳在 UI 上不出现、只出现在日志/裸异常文本里；而它一旦与 mtime 矛盾（例 R1/R2 的伪造态）就会把人引向错误时间窗 | `4_contradictory_pair`：内容 `2020-01-01T00:00:00` ＋ 新鲜 mtime（age 0.001 s）⇒ 异常文本仍写 `since=2020-01-01T00:00:00`，**与真实锁龄差 212,487,288 s ≈ 6.73 年**；`5_alive_pid_blocks`：age 3600 的活锁，`holder_since` 仍返回 `"2020-01-01T00:00:00"` | 中（可观测性缺陷，非语义缺陷） |
| **R5 内容不可解析 ⇒ 探活被整条跳过** | `:120` 的 `holder_pid is None or not _pid_alive(...)` 短路：解析失败即"视为可夺"，**不看任何存活证据** | `_read_lock` 边界实测（`7_read_lock_edge`）：空文件→`(None,"")`；`abc ...`→`(None,"")`（**连 since 一起丢**）；`12345`（无空格）→`(12345,"")`；`"1234  2020..."`（双空格）→since 被 `strip()` 救回；`"1234 2026-...T08:00:00+08:00"`→原样透传（**解析层零校验**） | 中（`os.open` 与 `os.write` 之间崩溃会留空锁文件，正是这一支） |
| **R6 单次读、单向依赖** | `:117` 一次调用里 `time.time()` 与 `stat()` 各一次，中间无一致性保证；跳变恰好落在两者之间即读到"错配差" | 对照：`lock_manager.py:136-137` 的 docstring 明说旧版调两次 `time.time()` 会"差出调度抖动"，s921-13 已改成"一个读数共用" | 低-中（本函数只有 1 次 `time.time()`，形态比 feed 侧旧版轻） |
| **R7 PID 复用（与 R1 同向的可用性面）** | Windows 侧 `_pid_alive` 用 `OpenProcess`+`GetExitCodeProcess==259`（`:60-74`），无法区分"持有者还活着"与"PID 被别的进程复用"⇒ 一个无关活进程占住该 PID 会让锁**永久不可夺**（age 再大也没用，因 `:120` 要求两条件同时成立） | `5_alive_pid_blocks` 实测该合取的门效果：活 pid ＋ age 3600 ⇒ 拒夺；`tests/test_instance_lock.py:90-100` 同型钉桩（用 `os.getpid()`） | 中（概率低但恢复成本＝手工删锁文件） |
| **R8 全静默** | 夺锁/拒锁/重开 0 日志：`rg -n -e 'logging\|logger\|warn\|alert' src/utils/instance_lock.py` → **rc=1、stdout 0 字节**（实测，非转述） | 已另册钉桩（`test_instance_lock_alert_gap_pin.py:17-19`），本档不重复裁 | 归属 KNOWN_ISSUES P1 |

---

## 四、是否引入可注入 clock seam —— **裁决：引入，且照仓内既有先例的形状，不发明新形状**

仓内**已有同类接缝**，就在同仓另一把锁上（本单实测定位）：

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
s=open('src/literature_feed/scheduler/lock_manager.py',encoding='utf-8').read().splitlines()
for i in list(range(127,148))+[243]: print(i+1, s[i].rstrip())
"
128     def is_stale(self, now: Optional[float] = None) -> bool:
132             now: s921-13 加的**时钟接缝**。``None``（缺省）= 现算 ``time.time()``，
133                 行为与旧版逐字一致；传入 epoch 秒 = 用这个"现在"做判据。
134                 有了它，``>`` 与 ``>=`` 的边界可以用 ``now = mtime + ttl`` 精确断言，
145         if now is None:
146             now = time.time()
147         age = now - mtime
148         stale = age > self.ttl_seconds
244                 f"acquired_at={datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
```

⇒ **同一仓的两把锁在四个轴上全不一致**，这就是"双口径"的完整形态：

| 轴 | `instance_lock.py` | `lock_manager.py` |
|---|---|---|
| 判龄源 | `time.time() - st_mtime`（`:117`） | 同型 `now - mtime`（`:147`）✅ 一致 |
| 阈值 | `DEFAULT_STALE_SECONDS = 600.0`（`:22`） | `ttl_seconds: int = 21600`（`:54`，docstring `:47` 自述"默认 6 小时"） |
| **时钟接缝** | **无**（不可注入，测试只能 `os.utime` 造态） | **有** `now=`（s921-13） |
| **内容戳时间基** | **naive 本地**（`:132`） | **tz-aware UTC**（`:244`） |
| 夺锁可观测性 | 0 日志（R8） | `_alert_once`（`:89-94`） |

---

## 五、两案 ＋ 推荐

### 案 A：给 `project_lock` 加可注入 `now`（epoch 秒）接缝，内容戳改 tz-aware

| 面 | 内容 |
|---|---|
| 改动点 | `:88` 签名加 `now: Optional[float] = None`；`:117` 改 `age = (now if now is not None else time.time()) - lock_path.stat().st_mtime`（**保持单次读数**，照 `lock_manager.py:145-147` 形状）；`:132` 改 `datetime.now(timezone.utc).isoformat(timespec='seconds')` |
| 兼容性 | 缺省路径行为逐字不变（R1/R2 的语义不动，只是可测）；**内容戳格式变更会触红在册断言**：`tests/test_instance_lock.py:52` 是 `pid_str, since = text.split(" ")`（格式变不会炸，但若引入空格即炸）、`:54` `"T" in since`（UTC 串仍含 `T` ⇒ **该用例对 tz-aware 改造是"假绿"，不具判别力**，需顺手加严） |
| 硬约束（实测在册门禁） | `tests/test_instance_lock_alert_gap_pin.py`：`:177` 要求 `project_lock` 函数体原文必须含 `"stale_seconds: float = DEFAULT_STALE_SECONDS"`、`"age > stale_seconds"`、`"_pid_alive("`、`"os.replace("`、`:179` `".stale-"` ⇒ **改法必须保留 `age > stale_seconds` 这一逐字子串**（把 now 注入写成先算 `now_eff` 再 `age = now_eff - mtime; if age > stale_seconds` 即满足）；`:137` 还钉「调用点 `project_manager.py:85` 不得带任何 keyword」⇒ **seam 只能是带默认值的 kwarg，消费点一字不改**；`:122` 钉 src 内 `project_lock(` 的 ast.Call 恰好 1 处 |
| 风险 | 低：纯参数化；R1（回拨夺不掉）与 R3（8 h 偏移）在**缺省运行时行为**下都不消失——A 治的是"不可测/不可断言"，不是"不再跳变" |

### 案 B：判龄源改 `time.monotonic()`

| 面 | 内容 |
|---|---|
| 直接否证 | `monotonic()` 的**原点是每进程/每次 boot 各异的**（Windows QPC 自 boot，POSIX 依实现）⇒ 锁文件里存的必须是"跨进程可比的量"，epoch `st_mtime` 天然可比，monotonic 不可比。要沿用就得把 monotonic 值**写进锁内容**并改判龄为 `now_mono - content_mono` ⇒ 那不再是"锁文件 mtime"，而是**新造一套锁协议** |
| 与在册门禁正面冲突 | `test_instance_lock_alert_gap_pin.py:177` 的 `"age > stale_seconds"` 与 `:157` 的 `"lock_path = lock_dir / LOCK_FILENAME"`、`:156` 的 `"lock_dir = Path(lock_dir)"` 都是**源码原文 token 断言**；B 要把 stat 从判龄链里摘掉，token 尚在但语义已换 ⇒ 钉桩"现状已推进"会被绕过，须 `--freeze` 重钉基线（纪律档 §十一.3：**属人工闸，执行手无权自行消红**） |
| 收益 | 只治"同机同 boot 窗内的墙钟跳变"（R1 的一部分）；治不了 R2（touch 照样能伪造内容里的 mono 值），也治不了 R3 |
| 判定 | **不推荐**（性价比与风险均劣于 A） |

### 推荐：案 A ＋ 一条不改判龄的 R4 修补 ＋ 一条 R5 收严（分三步、每步独立可回滚）

1. **A 的 seam**（`now: Optional[float] = None`，缺省行为逐字不变）——先让 `>` 边界与 R1 可断言。
2. **内容戳改 tz-aware UTC**（`:132`），同时把 `ProjectLockedError` 的 `since` 字段**改成"内容戳 + 实测 age"两段并列**（例 `since=<ISO+08:00>, age=612s`），排障时不再需要人脑换算 ⇒ 直接消 R4。⚠ 这条**只改展示字符串**，`holder_since` 属性语义要保留（`project_panel.py:23` 只读 `args[1]`，不受影响）。
3. **R5 收严**：`_read_lock` 解析失败时不要顺手丢掉 `since`（`:81-82` 的 `partition` 已解析出 since，但 `int()` 抛错走 `except` 把两者一起归零）⇒ 改成"pid 解析失败但 since 可用则保留 since"。
4. **不做**的事：不改 `stale_seconds=600`（`:183-191` 已钉）、不改锁粒度（`:153-168` 已钉）、不接告警日志（属 KNOWN_ISSUES P1 另册）。

---

## 六、`test_instance_lock.py` 接线草图（**不实施**，交施工班可直接粘）

现有件基线（本班按件点名跑，未用宽 `-k`）：

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m pytest \
  tests/test_instance_lock.py tests/test_instance_lock_alert_gap_pin.py tests/test_instance_lock_oserror_branch.py -q
rc=0
26 passed in 1.00s
```

```python
# 建议追加到 tests/test_instance_lock.py（案 A 落地同批；零子进程、零真实时钟等待）
_FIXED_MTIME = 1_700_000_000.0   # 任意钉死的 epoch 秒

def test_age_boundary_is_exact_with_injected_clock(lock_dir):
    """seam 的价值：`>` 边界精确压线，不再两侧留裕量（照 tests/test_lock_manager.py:99-101 范式）。"""
    lp = lock_dir / ".psy_project.lock"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lp.write_text("999999 2020-01-01T00:00:00", encoding="utf-8")
    os.utime(lp, (_FIXED_MTIME, _FIXED_MTIME))
    with pytest.raises(ProjectLockedError):          # age == 600：`>` 判不陈旧
        with project_lock(lock_dir, now=_FIXED_MTIME + 600):
            pass
    with project_lock(lock_dir, now=_FIXED_MTIME + 600.5):   # 超半秒即夺
        assert lp.read_text(encoding="utf-8").startswith(str(os.getpid()))

def test_clock_backward_jump_does_not_panic(lock_dir):
    """R1：回拨等效态（age<0）不炸、仍判"不陈旧"——把 2_clock_back_equiv 的实测读数钉成断言。"""
    ...
    with pytest.raises(ProjectLockedError):
        with project_lock(lock_dir, now=real_mtime - 3600):
            pass

def test_content_stamp_is_tz_aware_and_matches_mtime_within_one_second(lock_dir):
    """R3＋§2.1：内容戳与 mtime 在**同一时间基**上互读，偏差必须落在 (-1, 0]。
    ⚠ 现用例 `:54 assert "T" in since` 对 UTC 化改造零判别力（本条才是有判别力的那把刀）。"""
    ...

def test_default_path_still_reads_the_real_clock(lock_dir, monkeypatch):
    """seam 缺省必须让位给真实时钟：注入 1970 ⇒ 陈旧，缺省 ⇒ 不陈旧（防"接缝吃掉默认值"）。"""
    ...
```
**施工红线（实测得自在册门禁）**：① `project_manager.py:85` 调用点**一个 kwarg 都不许加**；② `project_lock` 函数体必须保留 `age > stale_seconds` 逐字子串；③ `src/` 内 `project_lock(` 的调用数保持 1；④ 两条 subprocess 用例（`:103`、`:127`）走子进程重新 import，**in-process monkeypatch 对它们无效** ⇒ 别指望用 seam 去测它们，它们继续用 `stale_seconds=1e9`／真实竞争口径。

---

## 七、完成标准对照

| # | 标准 | 实测 |
|---|---|---|
| ① | 档内两调用点行号与 `rg -n "time\.time\|datetime\.now" src/utils/instance_lock.py` 输出一致 | 本档 §一 逐字贴该命令原文与输出（`117:`、`132:`），§二/§五引用的两处调用点行号即 `:117`（epoch）与 `:132`（墙钟），**一致** |
| ② | 风险清单含至少 3 条（跳变/touch/时区） | §三 **8 条**，其中 R1 跳变 / R2 touch / R3 时区三条均有逐字实测读数 |
| ③ | 零代码改动（`git status` 干净） | 本班唯一产物＝本 `docs/insights/` 新档；`git diff --numstat -- src/utils/instance_lock.py tests/test_instance_lock.py tests/test_instance_lock_alert_gap_pin.py tests/test_instance_lock_oserror_branch.py src/utils/project_manager.py src/literature_feed/scheduler/lock_manager.py` → **无输出 rc=0**。⚠ 字面"git status 干净"在并发仓不成立（他班在册脏件见 §八），已按逐件点名替代 |

## 八、只读自证与基线

- 开工基线（08:02:27 现取）在册脏件 7 项；本班 08:1x 复点另见兄弟班在途新增（`scripts/evaluate_socratic_benchmark.py`、`tests/test_socratic_benchmark_archive_infra.py` 等）⇒ 按纪律档 §十二 归属口径记为**同仓兄弟班正常作业**，本班未读其内容、未跑其件、不据此指控任何写手。
- `instance_lock.py` 基线指纹：146 行 / 5,582 B / **sha8 `fe361ef1`**（收工复点同值）；`tests/test_instance_lock.py` 5,120 B / `a818b96f`；`lock_manager.py` 9,664 B / `5e9cb8b7`；`tests/test_lock_manager.py` 16,549 B / `fb715963`。
- 探针锁件全在 `tmp/qoder-executor-20260925-0800-psy57/{loops,locks}/`（`.gitignore:29 tmp/`）；`PROJECTS_DIR = ~/.psy_analysis/projects` **未被本班加解锁**（探针从不以该目录为 `lock_dir`）。
- 未启动 app、未跑全量套件、未跑 feed 族、`data/literature_feed`（181 件 / 21,059,126 B）全程未打开。
