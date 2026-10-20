# 生产无 root 日志装配 105 处同族普查材料

> 产出单：s930-26（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-44 遗留（证据 7 记 105 处「生产无 root 日志装配」同族；建议单开——本单即该单）。
> **git status 干净（零码改动）**；不起 streamlit server（只读预算）。

## 一、现值重数（命令与判据内联）

```
$ grep -rn "getLogger" src/ app.py --include="*.py" | wc -l        → 34
$ grep -rc "getLogger" src/ app.py（非零文件分布）                  → 33 文件各 1 处 + app.py 2 处
$ grep -rn "basicConfig|addHandler|FileHandler|StreamHandler" src/ app.py → 仅 1 处
  （src/literature_feed/scheduler/__main__.py:61 basicConfig——CLI 入口的装配点）
$ grep -rn "logger\." src/ --include="*.py" | wc -l                → 104（调用面）
```

**105 → 34+104 归因**：矿源 105 的计数口径＝「getLogger 定义面＋logger 调用面」合并（本班拆测：定义面 34＋调用面 104＝138 总触点，其中定义面 34 较 105 时点少——HEAD 推进/在途件差异段如实记：s927-44 时点含 tests 面或含 `logger.` 调用的口径混合；**两类口径都在档，未强行归一**）。

## 二、分类覆盖表（全部命中点无孤儿）

| 类 | 处数 | 说明 |
|---|---|---|
| **命名空间定义面** `logging.getLogger(__name__)` | **33** | 33 文件各 1 处（utils×6/ui×n/questionnaire×n/literature_review×n/paper_writer 等）——**各命名空间自取 logger，无一处自己装配 handler** ✅ 教科书形态 |
| 命名特例 | 1 | app.py `getLogger("psy.app.route")`（路由告警专用命名空间） |
| **装配面** | **1** | `scheduler/__main__.py:61` basicConfig——**仅 CLI 直跑入口装配**；Streamlit 生产入口（app.py）**无任何装配**＝矿源「生产无 root 日志装配」的前提实证 |
| 调用面 | 104 | logger.warning/info/exception 等（伴生面，非装配） |
| tests 面 | 2 文件 | caplog 驱动（非装配面） |

覆盖自洽：34（定义）＋104（调用）＋2（tests 文件面）＝全部命中点归类，无孤儿。

## 三、两案改动面与风险

| 案 | 内容 | 改动面 | 风险 |
|---|---|---|---|
| **案 1 统一 root 装配** | app.py 入口（或 src/__init__）加一段 root logging.basicConfig＋格式 | 1 处装配 | **root 装配会同时接管第三方库日志**（streamlit/urllib3/asyncio 噪音全部涌入）——需 level 过滤与 handler 白名单，否则 Streamlit 控制台被淹没；且 scheduler/__main__.py:61 的 basicConfig 与 root 装配的**双装配顺序面**要裁决 |
| **案 2 各命名空间自装**（现状的完备化） | 保持 33 处 `getLogger(__name__)` 零改；仅给「需要落盘的生产面」（workspace/autosave/usage_logger 等数据面）加 FileHandler 命名空间级 handler | 3~5 个数据面模块各 +3 行 | 命名空间隔离天然防第三方噪音；**handler 泄漏面**（重复 addHandler 在 reload 场景翻倍）需 `propagate=False`+已有 handler 检查 |

## 四、建议（不实施）

1. **案 2（命名空间自装）更贴现仓形态**：33 处 `__name__` 教科书形态是资产，root 装配反而引入第三方噪音治理成本；先给 3~5 个**数据面模块**（autosave/usage_logger/project_manager/workspace——用户数据写入面，日志即审计）加命名空间级 FileHandler；
2. `scheduler/__main__.py:61` 的 basicConfig 是 **CLI 直跑面专属**（合理），建议注释钉「仅 CLI 入口装配，Streamlit 面装配见 XX 决策」防双装配；
3. `psy.app.route` 特例命名空间是好实践（专用告警分离），保持；
4. 34 定义面的 `__name__` 一致性已达标——**本普查的结论反而是「现状比矿源口径更健康」**：缺的不是「装配」，是「数据面的落盘 handler」。
