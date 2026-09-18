# psy 测试基线数字复核（917-34）

**结论：collect 2701（known_issues 记载 2644，漂移 +57＝9/17 夜新增测试）；一次通过跑（排除 e2e/playwright/online）passed 2588 / skipped 35 / failed 0——与基线表述 2585 对照漂移 +3（新增用例），零失败。KNOWN_ISSUES.md:38 的 2644 记载实测时点 2026-09-17（当晚夜班新增 +57 后即 2701），订正文本已给（改数字＋实测日期），文档修订留日间（KNOWN_ISSUES 归日间域）。**

## 一、collect 与 passed（命令与数字同段）

```
$ .venv/Scripts/python.exe -m pytest --collect-only -q
  → 2701 tests collected
$ .venv/Scripts/python.exe -m pytest -q -x --ignore=tests/e2e -k "not playwright and not e2e"
  → 2588 passed, 35 skipped, 79 deselected, 0 failed（04:0x，4m02s）
```

## 二、与 2644/2585 对照（漂移量）

| 项 | 基线表述 | 本班实测 | 漂移 |
|---|---|---|---|
| collect | 2644 | 2701 | **+57**（9/17 夜新增测试） |
| passed | 2585 | 2588 | **+3**（新增用例净增） |
| skipped/failed | — | skipped 35／failed **0** | 零失败 |

（collect 2701 vs passed 2588 差＝e2e/playwright 排除 79 deselected＋skipped 35 等，口径自洽。）

## 三、订正文本（KNOWN_ISSUES.md:38，待日间放行）

```diff
- v5.11 当前 2644 个离线收集项（复现：… --collect-only -q -m "not online"，2026-09-17）
+ v5.11 当前 2701 个离线收集项（复现：… --collect-only -q -m "not online"，2026-09-18）
```

## 四、验收情况

- ✅ collect 与 passed 两数附命令（2701／2588 同段）；✅ 漂移量明确（+57／+3）；✅ 订正文本给 file:line（KNOWN_ISSUES.md:38）标待日间；✅ 未装依赖、未改测试代码、零联网零 e2e；不 push。

## 遗留问题

KNOWN_ISSUES.md:38 数字订正待日间放行（1 行）。
