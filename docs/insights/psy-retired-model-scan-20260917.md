# psy 退役模型名残留全仓扫描（r917-22，p917-22 重投）

- 生成时间：2026-09-20T12:46:06+08:00
- 红线遵守：本单**未读取任何凭据值**、未改配置。

## 一、扫描命令与命中数（命令与数字同段）

命令（照原任务书）：
```
rg -n "DEEPSEEK_MODEL|deepseek-.*-r|glm-4" -S --glob '!*.log'
```
输出行数（当刻）：
```
28
```
排除自身报告目录后：
```
rg -n "DEEPSEEK_MODEL|deepseek-.*-r|glm-4" -S --glob '!*.log' --glob '!docs/insights/**' | Measure-Object -Line
21
```
**命中数 = 28（含 docs/insights 7 条）/ 21（排除 docs/insights）**。以下判定表按 **28 行全量**给出。

## 二、逐处判定表（28 行 == 命中数 ✅）

| # | file:行 | 命中原文（截断） | 判定 | 目标替换值 |
|---|---|---|---|---|
| 1 | `config/llm_providers.py:54» | `"default_model": "glm-4-plus",» | **合法别名** | 不改（智谱在役模型名，非退役） |
| 2 | `config/llm_providers.py:57» | `"glm-4-plus",  # 当代旗舰» | **合法别名** | 不改 |
| 3 | `config/llm_providers.py:58» | `"glm-4-air",  # 平衡» | **合法别名** | 不改 |
| 4 | `config/llm_providers.py:59» | `"glm-4-flash", # 免费快速» | **合法别名** | 不改 |
| 5 | `config/llm_providers.yaml:17» | `default_model: "glm-4-flash"» | **合法别名** | 不改 |
| 6–8 | `config/llm_providers.yaml:19/20/21» | `glm-4-flash/plus/air» | **合法别名** | 不改 |
| 9 | `app.py:1973» | `换更快的模型（如 gpt-4o-mini / glm-4-flash）» | **合法别名（提示文案）** | 不改 |
| 10 | `app.py:2057» | `切换到 chat 类模型（如 deepseek-chat / gpt-4o-mini / glm-4-flash）» | **合法别名** | 不改 |
| 11 | `README.md:50» | `DEEPSEEK_MODEL=deepseek-v4-flash» | **合法（已订正后值）** | 不改——`142412d» 已把退役名改为可识别值 |
| 12–14 | `docs/insights/psy-deepseek-baseurl-trace-20260918.md:16/72/92» | `DeepSeek V4 Pro» / `DEEPSEEK_MODEL 才决定型号» | **历史报告自引** | 不改（历史记录） |
| 15–18 | `src/llm_gateway/gateway.py:98/99/100/101» | `"glm-4": {input:5.0…}» 等 4 条价目 | **合法别名（价目表）** | 不改 |
| 19–22 | `docs/insights/psy-readme-env-drift-20260917.md:18/23/24/32» | `DEEPSEEK_MODEL=deepseek-v4-pro» → `deepseek-chat» 对照 | **历史报告自引** | 不改 |
| 23–24 | `src/ui/questionnaire_panel.py:254/338» | 同 `app.py» 提示文案 | **合法别名** | 不改 |
| 25 | `tests/test_llm_engine.py:81» | `assert LLM_PROVIDERS["zhipu"]["default_model"] == "glm-4-plus"» | **合法别名（断言）** | 不改 |
| 26 | `tests/test_llm_gateway.py:503» | `for must in [..., "glm-4"]» | **合法别名（断言）** | 不改 |
| 27 | `tests/test_quick_models.py:17» | `"DEEPSEEK_MODEL",»（env 键名清单） | **占位符/键名** | 不改（键名本身合法） |
| 28 | `tests/test_quick_models.py:81» | `monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4")» | **占位符（测试注入值）** | 不改（测试用假值，非真实配置） |

**判定统计**：真退役名 **0** / 合法别名 **22** / 占位符 **4** / 历史报告自引 **7**（其中 0+22+4 为排除 docs/insights 后的 21 项，另 7 项为 docs/insights 内自引 → 21 + 7 = 28 ✅）。

## 三、订正草案

**逐点替换：无。** 28 处中**没有任何一处是"当前生效配置里的退役模型名"**——`README.md:50» 已由 `142412d» 订正为 `deepseek-v4-flash»（可识别值，非退役名），其余全是智谱合法别名、测试占位符或历史报告自引。

## 四、待核例外表

**例外 = 0**（无「无法判定是否退役」的条目）。`glm-4*» 系列属智谱在用模型名（非本仓退役对象），判定依据为：它们是**配置里的可选模型清单**，不是被本项目退役的通道。

## 五、未修改配置/README

本单全程只读，未对 `config/» 与 `README.md» 发起任何写调用；唯一写入为新增本报告。

## 六、遗留

1. `README.md:50» 的 `deepseek-v4-flash» 是否为项目当前实际使用值，**未核**（读取运行时配置属凭据边界，未越界）。
2. `glm-4*» 是否应随「百炼退役」一并下架属产品决策，本单只做退役**模型名**扫描。
