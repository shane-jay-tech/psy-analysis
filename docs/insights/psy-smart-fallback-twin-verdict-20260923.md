# psy `chat_with_smart_fallback` 零调用孪生出口 · 三案裁决材料

- 信箱单：`s923-51`（卷宗投产日 2026-09-23，**实际执行 2026-09-24 16:1x**，班 `qoder-executor-20260924-0955-psy28`；文件名日期沿用卷宗点名的产出路径，正文日期按实测日落笔）
- 授权位：psy **文档位**——`src/`、`tests/` 全程禁碰，本件为**只读取证 + 出稿**，零产码改动。
- 性质：🔴 **只出材料 + 推荐排序，不选案**。三案任何一案的放行都属人工裁决，执行手不代为拍板。
- 复核口径：本文所有计数均由**双轨**给出（正则 `rg` + AST/全盘字节普查），无一处"推断"；每条读数附命令原文（第七节）。

---

## 一、一句话现状

`src/llm_gateway/gateway.py:398-417` 的 `chat_with_smart_fallback` 自称「符号保留供旧调用站点不变」，但**在 git 可见历史的任何一刻、在盘上的任何一处（含点目录、含字符串反射取用）都不存在调用站点**：src/tests/app.py 三处命中全部是它自己的定义与 `__init__.py` 的两行导出 plumbing。与它撞名的 `llm_chat_with_fallback`（`:748`，多候选并发竞速、返回 `FallbackResult`）是**另一套语义**，被 10 处测试调用式直接调用（tests/ 共 20 行命中）——**"孪生"只是命名层面的相似，不是功能重复**。

## 二、现状实测

### 2.1 卷宗三条锚点复核

| 卷宗锚点 | 实测 | 判定 |
|---|---|---|
| `gateway.py:398`「def chat_with_smart_fallback(」 | 逐字命中 | **成立** |
| `gateway.py:407`「    符号保留供旧调用站点不变。retries=2 → 总计最多 3 次尝试；」 | 逐字命中（是 docstring 正文第 3 行） | **成立，但不是 `rg 'chat_with_smart_fallback'` 的命中** |
| `__init__.py:18`「    chat_with_smart_fallback,」 | 逐字命中 | **成立** |

⚠ **否证卷宗「完成标准」里的预期命中清单**：卷宗写「预期仅 gateway.py:398/**407** 与 `__init__.py:18/41`」（4 处），实测 `rg -n 'chat_with_smart_fallback' src/ tests/ app.py` 只有 **3 处**——`:407` 那行是 docstring 的**描述文字**，行内不含符号名，正则扫不到。锚点行号本身零漂移，偏差在"预期命中数"。本件按实况收窄，不判 failed。

### 2.2 零调用面的三轨取证（互不依赖）

| 轨道 | 口径 | 读数 |
|---|---|---|
| 正则 `rg` | `rg -n 'chat_with_smart_fallback' src/ tests/ app.py` | 3 命中：`__init__.py:18`（import alias）、`__init__.py:41`（`__all__` 字符串）、`gateway.py:398`（def） |
| AST | 547 个 `.py`（排除 `tmp/` 沙盒），找 `Name`/`Attribute`/`Constant` 三种取用形态 | **Name 0 / Attribute 0 / Constant 1（即 `__all__` 那行）**；另 `FunctionDef` 1、`alias` 1。⚠ 含 `tmp/` 时文件数读数会随他班沙盒当场漂移（本班同一天内 703 → 711，只因自己往 `tmp/psy28/` 放了取证脚本）⇒ 计数一律排除 `tmp/` 并报口径 |
| 全盘字节 | 879 个文件（含 `.streamlit`/`.github` 等点目录，跳过 `.venv`/`node_modules`/`.git`/`data`/`tmp`） | 仅 4 件带字样：`src/llm_gateway/gateway.py`(1)、`src/llm_gateway/__init__.py`(2)、`docs/history/UPGRADE_REPORT_V3.9.md`(3)、`docs/insights/psy-test-blindspot-audit-20260915.json`(1) |

⇒ **"仅剩 `__init__` 双处导出"成立且可穷举**；反射式取用（`getattr(gw, "chat_with_smart_fallback")`、`from ... import *`）实测零命中，`import *` 全仓不存在（`rg` rc=1）。

### 2.3 两个"孪生"的真实语义差（读码实测，非命名推断）

| 维度 | `chat_with_smart_fallback`（`:398`） | `llm_chat_with_fallback`（`:748`） |
|---|---|---|
| 语义 | 单调用 + 固定 `retries=2` | 多候选**并发竞速**，先到先用、其余自动取消 |
| 返回 | `LLMResponse` | `FallbackResult`（含 `winner_model`/`winner_index`/`elapsed_ms`/`attempts`） |
| 必填入参 | 无（`messages` 之外全 keyword-only，默认值齐备） | `candidates: List[Dict]`，空列表抛 `ValueError`（`:785-786`） |
| 单次退化 | 本体就是 `return llm_chat(..., retries=2)`（`:411-417`，7 行） | `len(candidates)==1` 时退化走 `llm_chat`（`:789-802`），**不传 retries** |
| 尝试次数 | retries=2 ⇒ **最多 3 次**（实测 `:519 for attempt in range(max(1, retries + 1))`，非按 docstring 采信） | 由候选数与线程池决定 |
| 测试直接调用 | **0 处** | `tests/` 20 行命中（`test_llm_gateway.py` 16 + `test_golden_path_e2e.py` 4），拆为 **10 行真实调用式 + 10 行 import**（`rg` 双口径实测，见第七节） |
| `llm_chat` 默认 retries | `:464 retries: int = 1` ⇒ 默认 2 次尝试 | 同左 |

⇒ **关键推论**：二者不可互换。`chat_with_smart_fallback` 唯一不可替代的"内容"是把 `retries` 从默认 1 抬到 2；除此之外它就是 `llm_chat` 的三层参数转发壳。

### 2.4 历史与"保留决定"的可追溯性

- `git log --oneline -S 'chat_with_smart_fallback' --all` → 仅 3 笔：`ec45485`（仓库初始化）、`097a657`（chore: checkpoint existing work before coverage audit）、`ef6e9b7`（c918-10 insights 入库）。
- 逐修订 `git grep -c`：`ec45485` 的 src 侧就是 `gateway.py:1 + __init__.py:2` = **3 处，仓库第一笔就没有调用站点**；"旧调用站点"若真存在，只可能在 git 之前的工作区，**现已不可证**。
- 当初记有"保留符号"决定的两份 v4.6 决策档 `docs/decisions/2026-05-25-merge-llm-config-quickonly.md`、`docs/decisions/2026-05-26-llm-single-track-review.md`（各 2 处提及该符号）**已在 `097a657` 一并删除**（`git log --diff-filter=D` 实证），盘上 `find` 无同名件；`KNOWN_ISSUES.md:35/:36` 至今仍按 `docs/decisions/…` 旧路径指向它们 ⇒ **"保留"这一决定目前只剩二手记载**（`docs/history/UPGRADE_REPORT_V3.9.md` 三处 + 已删档的 git blob）。这条影响"删除是否算破既定决策"的判断，见第六节遗留 3。

## 三、三案影响面对比（改动面行数为沙盒实测量，非估算）

测量法：把 `gateway.py`(959 行)/`__init__.py`(54 行) `copy2` 到 `tmp/psy28/sandbox/`（已 `git check-ignore -v tmp/psy28` 自证 gitignore），按各案文本改沙盒件，再 `len(splitlines())` 差 + `ast.parse` 验语法。生产件零触碰。取证脚本留在 `tmp/psy28/`：`measure_surface.py`（本节改动面）、`ast_scan.py`（2.2 AST 轨）、`census_smart_fallback.py`（2.2 全盘字节轨），三件均可复跑。

| | 案 A：删除符号 + 清理导出 | 案 B：降级为 `llm_chat` 显式别名 | 案 C：保留符号，注明零调用现状 |
|---|---|---|---|
| 具体动作 | 删 `gateway.py:398-419`（def 块 20 行 + 其后 2 个空行，令 `:396-397` 与 `:420` 注释块保持两空行分隔）；删 `__init__.py:18` 与 `:41` | `gateway.py:398-417` 的 20 行函数体换成别名式（实测用 `functools.partial(llm_chat, retries=2)` 3 行 + 1 空行）；`__init__.py` 不动 | 只在 `gateway.py` docstring（`:407-409` 之后）追加 3 行零调用现值注；`__init__.py` 不动 |
| 改动面（实测） | `gateway.py` **−22**、`__init__.py` **−2** ⇒ 净 **−24 行 / +0 行**，2 文件；沙盒 `ast.parse` OK | `gateway.py` **−16 净**（959→943；**若按字面 `= llm_chat` 则 −17，但 retries 由 2 降 1 ⇒ 属行为变更**）；`ast.parse` 文本层 OK，**但 `gateway.py` 现无 `import functools`**（顶层 import 12 行，实测 `rg -n 'functools' src/llm_gateway/gateway.py` → rc=1 零命中），落地需 **+1 行 import ⇒ 净 −15** | `gateway.py` **+3 / −0**（959→962），`__init__.py` 0 行 |
| 测试影响 | **0 例**（该符号在 `tests/` 引用数 0，AST 轨同证）；受影响的在册基线：`tests/test_llm_gateway.py + test_llm_gateway_streams.py + test_llm_gateway_static_guard.py` 现跑 **69 passed / 4.43s**，删后仍应 69 绿 | **0 例**（同上）；但 `partial` 令 `inspect.signature`/`help()` 自省退化、keyword-only `*` 约束丢失（现签名 `messages` 后强制 kw）⇒ **静态形态变更，无测试看守** | **0 例**（纯注释） |
| 红名单（会翻红的在册用例） | **空**（实测口径：三案均无引用； psy 的"全局账本门"是导出/下载按钮清单 `test_export_gate_global_scan`，与本符号无关，本单未触碰导出/下载面 ⇒ 无需按 §八 加跑） | **空**；风险在"绿而行为变"：若别名丢掉 `retries=2`，尝试数 3→2 属**静默语义变更**且无测试可见 | **空** |
| 文档连带 | 须同批改 `KNOWN_ISSUES.md:7/:11/:16/:76`？**否**——那 4 处是 9/24 `s923-49` 已订正的报告文件指针，与本符号无关。须改的是 `docs/history/UPGRADE_REPORT_V3.9.md`？**否**（历史件不回改，9/23 口径）；`psy-test-blindspot-audit-20260915.json`？**否**（9/15 快照型取证件，回改＝篡改历史读数；它记的 `gateway.py lines: 959` 到案 A 后会变成 937，属快照正常老化） | 同案 A；另 `__init__.py` 的导出名单与 docstring 表述需保持自洽 | 无连带 |
| 消债效果 | **真消债**：符号、导入、`__all__` 三处一并归零，公开 API 面 −1 名 | 半消：名字仍在、plumbing 仍在，只把 20 行壳压成 3 行 | **不消债**：只把债的现状写进码内注释 |
| 主要回归风险 | 唯一残余风险 = **仓外消费者**（用户自己的 REPL/临时脚本 `from src.llm_gateway import chat_with_smart_fallback`）。本仓是单人本地项目、无打包发布、无 `import *`，该面不可静态穷举，只能由人工确认 | 与案 A 同样的仓外面，且**多一条**：别名若少传 `retries` 会静默降低重试；`partial` 版则丢 kw-only 约束 | 几乎为零（唯一坑：追加文案若含"已无调用点"字样，未来调用点真出现时该注释会变谎言） |

## 四、推荐排序与理由（🔴 不选案）

**推荐排序：案 A ＞ 案 C ＞ 案 B。**

1. **案 A 首位**：三案回归面实测**都是 0 例**（引用数 0 由 rg/AST 双轨坐实），既然风险相同，就只有"消不消债"这一个差别量——A 净 −24 行、公开 API 少一个假出口、`_resolve_fallback_candidates` 这类同族死符号（实测 src 侧已零命中）说明本仓确有清理先例。删除的**唯一不可静态穷举面**是仓外私人用法，恰好只有人工能回答。
2. **案 C 次位**：如果人工确认"留着是因为我自己偶尔在解释器里调它"，那 C 的 +3 行注释是**最低成本的正确做法**——它不消债但让下一班不必重新做本件这份盘点（本单实测耗时折算约 8 分钟）。C 应写成"现值注（日期＋单号＋读数 0）"而非"永不使用"，避免注释反被现实破修。
3. **案 B 末位**：它的收益（少 15~16 行壳）案 A 能给得更彻底，而它的成本案 A 和 C 都没有——**要么改语义（丢 retries=2，属统计无关但确凿的行为变更），要么引 `functools` 并接受自省与 kw-only 约束退化**。B 是"看起来折中、实际两头不讨好"的形态。
4. 三案都**不触发** psy 的导出/下载全局账本门（未触碰 `st.download_button`/隐私预检面），也**不涉**红线域（鉴权/凭据/密钥/资金/统计结论/经济平衡/医疗）——`MODEL_PRICING_CNY`、`estimate_cost_cny` 等计费符号本单一字未动。

## 五、若人工放行某案，落地要点（写给主班/下一班，本班不执行）

- 案 A：改动面就是上表 2 文件 3 处；提交前加跑 `pytest tests/test_llm_gateway.py tests/test_llm_gateway_streams.py tests/test_llm_gateway_static_guard.py -q`（基线 69 passed）。**不要**顺手改 `docs/history/UPGRADE_REPORT_V3.9.md` 与 9/15 快照 JSON。
- 案 B：必须显式决定 `retries` 归属——推荐保留 `retries=2` 语义（`functools.partial` 或保留现 def 壳），并在 `__init__.py` 的导入清单同批改齐；`import functools` 是当前缺口（实测 gateway.py `:3-16` 无 functools）。
- 案 C：只加 3 行；建议文案含"实测口径与日期"，方便下次复核直接比对。
- 三案共同：`tests/` 无需改动（引用数 0）；`app.py` 无需改动。

## 六、遗留与关联

1. **`KNOWN_ISSUES.md:18`** 的 `UPGRADE_REPORT_V3.0.md ~ V3.9.md` 仍是根目录口径（实测两件都在 `docs/history/`）——与 `s923-49` 同型，已登在该单遗留 1，本件不重复处理。
2. **`psy-test-blindspot-audit-20260915.json:786-810`** 把该符号列在 `src.llm_gateway.gateway` 的 `top_level_symbols` 里、整模块 `verdict: "covered"` ⇒ **这份 9/15 快照不构成"该符号有测试"的证据**（模块级判定，非符号级）。任何按它下结论的后续单要先看这一层。
3. 两份 v4.6 决策档已被删除但 `KNOWN_ISSUES.md:35/:36` 仍指向 `docs/decisions/…` 路径（实测 `find` 无同名件、`git log --diff-filter=D` 落在 `097a657`）——属"退役漂移"型缺陷，**已作为 `s923-52` 的关联证据**，本件只登记不改。
4. 卷宗「完成标准」的 4 处预期命中实测为 3 处（见 2.1），已按实况收窄。

## 七、证据命令原文（全部本机 `.venv` 实跑，2026-09-24 16:1x）

```
$ rg -n 'chat_with_smart_fallback' src/ tests/ app.py
src/llm_gateway\__init__.py:18:    chat_with_smart_fallback,
src/llm_gateway\__init__.py:41:    "chat_with_smart_fallback",
src/llm_gateway\gateway.py:398:def chat_with_smart_fallback(

$ rg -c 'chat_with_smart_fallback' .
.\docs\history\UPGRADE_REPORT_V3.9.md:3
.\docs\insights\psy-test-blindspot-audit-20260915.json:1
.\src\llm_gateway\__init__.py:2
.\src\llm_gateway\gateway.py:1

$ rg -n 'llm_chat_with_fallback' src/ tests/ app.py        # 逐行读数见下（三轨核对）
src/llm_gateway\__init__.py:28（import alias）/ :51（`__all__`）
src/llm_gateway\gateway.py:748（def）
tests/test_llm_gateway.py:536,538,541,543,558,563,583,598,611,626,636,650,670,686,704,715（16 行）
tests/test_golden_path_e2e.py:278,292,421,446（4 行）

$ rg -c 'llm_chat_with_fallback' src/ tests/ app.py
src/llm_gateway\__init__.py:2
src/llm_gateway\gateway.py:1
tests/test_golden_path_e2e.py:4
tests/test_llm_gateway.py:16
（⇒ tests/ 共 20 命中行；再按形态拆：`rg -n 'llm_chat_with_fallback\(' | rg -v import` = 11 行（含 gateway.py:748 的 def 行）⇒ tests/ 真实调用式 10 行；`rg -n 'import .*llm_chat_with_fallback' tests/` = 10 行）

$ D:/code/psy-analysis/.venv/Scripts/python.exe tmp/psy28/ast_scan.py   # AST 轨（排除 tmp/）
files 547 hits 3
  ('./src/llm_gateway/__init__.py', 18, 'alias')
  ('./src/llm_gateway/__init__.py', 41, 'const')
  ('./src/llm_gateway/gateway.py', 398, 'def')
by-kind {'alias': 1, 'const': 1, 'def': 1} | Name/Attribute 取用数 = 0
（含 tmp/ 时同一天两次读数 703 → 711，差异全因本班自己往 tmp/psy28/ 放脚本 ⇒ 报数一律排除 tmp）

$ rg -n 'functools' src/llm_gateway/gateway.py
（rc=1，零命中 ⇒ 案 B 若用 partial 需 +1 行 import）

$ D:/code/psy-analysis/.venv/Scripts/python.exe tmp/psy28/census_smart_fallback.py   # 全盘字节轨，含点目录
files scanned: 879
    docs/history/UPGRADE_REPORT_V3.9.md -> 3 lines
    docs/insights/psy-test-blindspot-audit-20260915.json -> 1 lines
    src/llm_gateway/__init__.py -> 2 lines
    src/llm_gateway/gateway.py -> 1 lines

$ rg -n 'from src.llm_gateway import \*|from .llm_gateway import \*' src/ tests/ app.py scripts/
（rc=1，零命中）

$ rg -n 'def llm_chat\(|retries: int = 1,|for attempt in range' src/llm_gateway/gateway.py
454:def llm_chat(
464:    retries: int = 1,
519:    for attempt in range(max(1, retries + 1)):

$ git log --oneline -S 'chat_with_smart_fallback' --all
ef6e9b7 c918-10: 31+4 份未跟踪 insights 入库（…）
097a657 chore: checkpoint existing work before coverage audit
ec45485 chore: 初始化版本库 + .gitignore，清理 __pycache__

$ git grep -c 'chat_with_smart_fallback' ec45485
ec45485:UPGRADE_REPORT_V3.9.md:3
ec45485:docs/decisions/2026-05-25-merge-llm-config-quickonly.md:2
ec45485:docs/decisions/2026-05-26-llm-single-track-review.md:2
ec45485:src/llm_gateway/__init__.py:2
ec45485:src/llm_gateway/gateway.py:1

$ git log --oneline --diff-filter=D -- docs/decisions/2026-05-25-merge-llm-config-quickonly.md
097a657 chore: checkpoint existing work before coverage audit

$ git check-ignore -v tmp/psy28
.gitignore:29:tmp/	tmp/psy28

$ # 沙盒改动面测量（生产件零触碰）
$ D:/code/psy-analysis/.venv/Scripts/python.exe tmp/psy28/measure_surface.py
orig gateway lines 959 init lines 54
A: gateway 959 -> 937 (delta -22) ; init 54 -> 52 (delta -2)
B: gateway 959 -> 943 (delta -16) ; init 0 行改动
C: gateway 959 -> 962 (delta 3) ; init 0 行改动
gateway.py 顶层 import 行数 12 ；含 functools 的行 无
案 A ast.parse OK
案 B ast.parse OK
案 C ast.parse OK
（⚠ 控制台把后四行的中文打成 cp936 乱码——显示层现象，脚本与输出文件均纯 UTF-8；functools 那条另用 ASCII 命令独证：上方 `rg -n 'functools' …` rc=1）

$ D:/code/psy-analysis/.venv/Scripts/python.exe -m pytest tests/test_llm_gateway.py tests/test_llm_gateway_streams.py tests/test_llm_gateway_static_guard.py -q
69 passed in 4.43s

$ D:/code/psy-analysis/.venv/Scripts/python.exe -c "import os; fs=[f for f in os.listdir('docs/insights') if f.endswith(('.md','.json'))]; print('files',len(fs)); print('index-like:',[f for f in fs if 'index' in f.lower() or f.startswith('000') or 'README' in f])"
files 101
index-like: []      # psy 无 insights 索引件与闭合哨兵（本单独立复算，与前两班结论一致 ⇒ 新档不补索引、不为此落 partial）
```

未跑全量套件（本波并行约束；本单是文档位，判据不点名全量数）。
