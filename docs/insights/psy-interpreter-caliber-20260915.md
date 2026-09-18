# psy 测试解释器口径说明（n915-79，只读起草）

> **推荐口径**：psy 仓一切测试/collect 一律用仓内虚拟环境解释器
> `.venv/Scripts/python.exe -m pytest …`（Windows）。系统 python 与 .venv 的
> 依赖集不同（Playwright 在系统口径下为 ERROR、venv 口径为 SKIP；d914 批曾出现
> 25F/13E 的系统口径假失败），口径混用会把环境差异误报为代码回归。

## 两口径数字与出处

| 口径 | 数字 | 出处 |
|---|---|---|
| .venv 全量 | **2606 passed / 60 skipped / 0 failed**（4m22s） | zcode-bridge/done/…（915-40 result，9/16 复跑）；同口径 9/14 夜为 2600/60 |
| 系统 python 全量 | 2600 passed / 60 skipped（venv 对照）；**collect-only（collect=2665）** | p914-19-bridge-collect-relocation.result.md（.venv 2665 collected 0 error） |
| collect（venv） | 2665 collected | p914-19 同报告 |

差异原因：系统解释器缺 Playwright/部分依赖 → 测试在收集/跳过判定上与 venv 不一致；venv 是 requirements-freeze 的权威镜像。

## 复跑命令

```
cd D:/code/psy-analysis && .venv/Scripts/python.exe -m pytest -q
cd D:/code/psy-analysis && .venv/Scripts/python.exe -m pytest tests --collect-only -q | tail -1
```

## 备注

- 本稿为只读起草，未写入 KNOWN_ISSUES/TESTING 文档（建议日间把上表并入 docs/TESTING.md）。
- 桥侧任务书若写 `python -m pytest`，执行班按本口径替换解释器并在 result 披露（既有先例：915-19/915-40）。
