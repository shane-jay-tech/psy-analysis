# method_weights_io_seed 20 红独立族归因（s930-48 遗留：canonicals 空集）——s1004-22

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T18:3x ｜ 性质：归因材料不落码
> 矿源：`zcode-bridge/done/s930-48.result.md:8`（「独立族（canonicals 空集——疑似 domain/method weights 加载链断或种子面缺失…归因待派」逐字在册）。

## 一、现值复跑：红已消失

`$ .venv/Scripts/python.exe -m pytest tests/test_method_weights_io_seed.py tests/test_domain_weights_io_seed.py -q` → **29 passed rc=0**（0.48s）＝s930-48 时点的 20 红族**现值全绿**。测试件 git 史＝ec45485 后零笔（与矿源读数一致）⇒ 红不是被「修」掉的，是**环境态函数**。

## 二、根因定谳（复现实锤＋读码证据链）

**复现**：`$ LITERATURE_FEED_DATA_ROOT=$(mktemp -d) pytest 同件` →
```
method_weights.yaml 不存在，使用空词表：C:\Users\…\tmp…\method_weights.yaml
canonicals n= 0
```

证据链：
1. `paths.py:17-25`——`LITERATURE_FEED_DATA_ROOT` env 覆盖 DATA_ROOT（:25 import 期解析）；
2. `METHOD_WEIGHTS_PATH = DATA_ROOT / "method_weights.yaml"` ⇒ 沙盒 env 下指向**空临时目录**；
3. `MethodWeights.from_yaml_path` 对缺文件**静默降级空词表**（复现输出第一行原文）；
4. 测试件 `_load()`（:37-38）直接经该 PATH ⇒ 8 条种子断言全数「canonical 应包含…」红——s930-48 的 20 红即此形态。

**结论：环境型假红**——s930-48 三件口径（.venv＋`-m not(e2e,playwright)`＋`LITERATURE_FEED_DATA_ROOT` 沙盒 env）里，该 env 是 feed 族隔离用的；method/domain_weights_io_seed 两件**不属 feed 沙盒隔离目标面**（它们断言的恰是真实种子数据面），被同一 env 误伤。矿源「加载链断或种子面缺失」两猜中前者（链被 env 改道），种子面（data/literature_feed/method_weights.yaml）在册无缺。

## 三、修法两案（不落码）

| 案 | 动作 | 波及面 |
|---|---|---|
| A 测试件钉环境 | 两 io_seed 件头部加 pytestmark/skipif：`LITERATURE_FEED_DATA_ROOT` 在 env 时 `pytest.fail("本件须跑真实数据根，勿带 feed 沙盒 env")`（或 autouse fixture 清该 env） | 两测试件各 +4~6 行；语义＝这两件是「真数据面」钉桩，拒绝沙盒 |
| B 加载器去静默 | `from_yaml_path` 缺文件从「空词表+print」改 `warning`（logging）或 `allow_missing=False` 参数 | 波及生产调用方（feed 族现依赖静默降级语义者需逐个点名）；波及面大 |

**倾向 A**：矿源注记该族「非本班改动面」＝它本就不该随 feed 沙盒跑；B 动生产语义（c47f 同款「静默」议题）应另单（可并入 s1004-31 逐图可观测化同族讨论）。

## 四、给主班

- s930-48 遗留的「独立族归因待派」可随本单销案：20 红＝环境型假红（沙盒 env 误伤真数据面钉桩件），非回归非种子缺失；
- 后续全量跑若维持三件口径，建议口径注记「method/domain_weights_io_seed 2 件在沙盒 env 下预期红（A 案落地后转预期 fail-fast）」。

### 证据存根

- 现值：`$ pytest tests/test_method_weights_io_seed.py tests/test_domain_weights_io_seed.py -q` → 29 passed。
- 复现：`$ LITERATURE_FEED_DATA_ROOT=$(mktemp -d) python -c "MethodWeights.from_yaml_path(METHOD_WEIGHTS_PATH)"` → 空词表＋canonicals=0 两行。
- 链条：`$ sed -n 17,25p src/literature_feed/paths.py`（env 覆盖＋import 期解析）＋`$ sed -n 1,44p tests/test_method_weights_io_seed.py`（_load 直经 PATH）。
- 禁令守约：weights 数据面零触碰、零落码。
