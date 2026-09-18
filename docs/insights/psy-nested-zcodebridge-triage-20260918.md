# psy 仓内嵌套 zcode-bridge 目录定性（s918-17，只读）

生成：2026-09-19 01:1x｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
**本单零文件删除、零移动**，只出定性与两案建议。

## 一句话定性

`psy-analysis/zcode-bridge/` 是 **2026-09-12 夜一班执行者用相对路径调 `focus_scan.py` 留下的错误残骸**
（2 个 140 字节的 Python 报错文本），**不含任何有效产物、不含隐私数据**；
旧签核报告的「疑似 9/12 夜间任务 cwd 误指产生」**判定成立**，且本单把「疑似」升级为实证。

## 二、全树清点（`find zcode-bridge -type f | wc -l` → **2**）

| 文件 | mtime | 大小 | 内容（全文即一行） | 定性 |
|---|---|---|---|---|
| `zcode-bridge/tmp/focus/20260912-0415/E01.run.json` | 2026-09-12 04:16 | **140 B** | `D:\Program\python.exe: can't open file 'D:\\code\\psy-analysis\\zcode-bridge\\scripts\\focus_scan.py': [Errno 2] No such file or directory` | **误指残骸**：文件里存的是**解释器报错文本**，不是 focus_scan 写的 run.json |
| `zcode-bridge/tmp/focus/20260912-0415/E02.run.json` | 2026-09-12 04:16 | **140 B** | 同上，逐字节相同（140 B/同一报错） | 同上（同一班的第二单，同一次失败） |

目录树（4 层）：`zcode-bridge/` → `tmp/` → `focus/` → `20260912-0415/`，**无其他文件、无隐藏文件、无 inbox/outbox/done**。

复现：
```
cd /d/code/psy-analysis && find zcode-bridge -type f | wc -l        # 2
cd /d/code/psy-analysis && cat zcode-bridge/tmp/focus/20260912-0415/E01.run.json
```

## 三、事发机制还原（为什么会长在 psy 仓里）

`.run.json` 的内容是解释器级报错 ⇒ **`focus_scan.py` 从未被执行**，这两个文件是**外层调用**留下的：

1. 执行者当时 `cwd = D:\code\psy-analysis`（任务书里的 `cwd` 字段本就是被分析仓）；
2. 它用**相对路径**写脚本路径（`zcode-bridge/scripts/focus_scan.py`）→ 被解析成
   `D:\code\psy-analysis\zcode-bridge\scripts\focus_scan.py` → `No such file or directory`；
3. 它的**输出路径同样是相对**的（`zcode-bridge/tmp/focus/20260912-0415/E0{1,2}.jsonl`），
   stderr 被重定向进同名 `.run.json`，目录被顺手建出来 ⇒ 嵌套树就这么长在 psy 仓里。

即：**不是「cwd 误指」，是「脚本路径与输出路径都是相对路径、而 cwd 是被分析仓」**。

## 四、复发条件（现在依然在）

`zcode-bridge/scripts/focus_scan.py:91-97` 的 `write_out()` 对 `--out` **原样当路径用**，
且 `out_path.parent.mkdir(parents=True, exist_ok=True)`——不校验绝对路径、不锚定信箱根目录；
`--out` 是 `required=True` 的自由字符串（:646）。
⇒ 任何在**非 `D:\code` 工作目录**下用相对 `--out` 调它的班，都会在那个仓里静默造出 `zcode-bridge/tmp/...` 目录树。
（对照：`focus_audit.py:404` 走的是 `root / "zcode-bridge" / "tmp" / ...`，已锚定，无此问题。）

## 五、两案建议（本单不执行）

**案 A｜删除（推荐）**
残骸无信息量、非产物，且 psy 的 `.gitignore` 现无 `zcode-bridge/` 条目 ⇒ 它以 `??` 挂着，
是 `git clean -fd` 的潜在受害者，也是「psy 仓里有半个信箱」的误导源。
```
cd /d/code/psy-analysis && git clean -nnd zcode-bridge   # 先预检，确认只列这一棵
rm -rf /d/code/psy-analysis/zcode-bridge
```
（注意：psy 工作树另有他人未收口改动，**不要**在整仓范围跑 `git clean`，限定路径。）

**案 B｜迁移**
不建议：没有可迁走的正数据（280 B 全是报错文本）。若要把 9/12 那两单 E01/E02 的本意补回来，
正确做法是在 `D:\code` 用**绝对路径**重跑扫描（`--out` 给绝对路径），而不是搬这堆残骸。

**根修（属日间，交管道侧）**
1. `focus_scan.py`（及同族 runner）对 `--out` 做绝对路径校验：非绝对路径直接退出并提示，或按信箱根锚定；
2. `zcode-bridge/prompts/executor.md` 钉一条「凡调用信箱脚本，脚本路径与 `--out` 一律用绝对路径」；
3. psy 的 `.gitignore` 补一行 `zcode-bridge/`（防再次长出来时以 untracked 形态混在签核清单里）——
   与本夜班 `s918-18`（补 `tmp/`）同族，可并一次提交。

## 六、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| `find zcode-bridge -type f \| wc -l` 数字附卷 ＋ 每文件一行定性 | **2**；两行定性见第二节表格 | `cd /d/code/psy-analysis && find zcode-bridge -type f \| wc -l` |
| 零文件删除 | 本单只跑 `find/cat/stat/sed/grep`；`psy-analysis/zcode-bridge` 仍为 2 文件、mtime 未变 | `cd /d/code/psy-analysis && find zcode-bridge -type f -exec stat -c '%n %y' {} \;` |

## 遗留问题

1. 旧报告（916p-a4-003:26）用的措辞是「疑似」，本单升级为**实证**并给出机制（第三节）；签核清单入库时应把这条改掉，
   否则后人还会重查一次。
2. 第四节那条**相对路径隐患是本单真正的价值**：它不只会造脏目录，还会让扫描单**静默零产出**
   （9/12 那夜 E01/E02 实际什么都没扫出来，但 inbox/done 表面是"有产物"的形态）。
   建议与 `n918-15-pipe-anchor-gate-pattern` 并看。
3. 本单未查 9/12 当晚是哪一班/哪张任务书发起的 E01/E02（需翻 `zcode-bridge/logs/` 与当日规划文档，
   属夜间日志考古，收益低），只定性到机制层。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
