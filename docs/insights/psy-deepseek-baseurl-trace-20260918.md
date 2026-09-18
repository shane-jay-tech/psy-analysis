# psy `DEEPSEEK_BASE_URL` 读取链取证（s918-15，只读）

生成：2026-09-19 01:2x｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
**只读，未改任何文件**（除本报告的产出文件本身）。

## 结论一句话

**`DEEPSEEK_BASE_URL` 真实生效，README.md:49 那一行应当「保留」**——它不是死变量，
读取点唯一且确在跑动路径上；9/17 那份对账报告留的「留日间确认」可以就此关闭。

## 一、`env_prefix` → 环境变量名 映射表（预设模型表全 4 行）

| `QuickModel.id` | `env_prefix` | `provider` | `label`（UI 显示名） | 实际读取的三个环境变量 |
|---|---|---|---|---|
| `gpt` | `GPT` | `openai` | GPT-5.5 | `GPT_BASE_URL` / `GPT_API_KEY` / `GPT_MODEL` |
| **`deepseek`** | **`DEEPSEEK`** | `deepseek` | DeepSeek V4 Pro | **`DEEPSEEK_BASE_URL`** / `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` |
| `kimi` | `KIMI` | `moonshot` | Kimi K2.6 | `KIMI_BASE_URL` / `KIMI_API_KEY` / `KIMI_MODEL` |
| `claude` | `CLAUDE` | `claude` | Claude Opus 4.8 | `CLAUDE_BASE_URL` / `CLAUDE_API_KEY` / `CLAUDE_MODEL` |

表定义在 `src/llm_gateway/quick_models.py:35-64`（`QUICK_MODELS`），字段语义见 :27-32。
前缀取值域就是这四个，**`DEEPSEEK` 在域内** ⇒ 任务书留的「prefix 是否含 DEEPSEEK 未逐跳核实」这一跳已补齐。

## 二、生效链逐跳（每跳附复现命令）

```
$ grep -rn "env_prefix" src --include="*.py"
src/llm_gateway/quick_models.py:31  env_prefix: str     # .env.local 前缀
src/llm_gateway/quick_models.py:40  env_prefix="GPT"
src/llm_gateway/quick_models.py:47  env_prefix="DEEPSEEK"     ← 命中
src/llm_gateway/quick_models.py:54  env_prefix="KIMI"
src/llm_gateway/quick_models.py:61  env_prefix="CLAUDE"
src/llm_gateway/quick_models.py:156 base_url = os.environ.get(f"{qm.env_prefix}_BASE_URL", "").strip()
```

1. **读取点唯一**：`grep -rn "_BASE_URL" src scripts --include=*.py` 全仓只有 `quick_models.py:156` 一处按
   `{prefix}_BASE_URL` 形式读环境（另一处 `crossref.py:28` 是同名无关常量）。
2. **三条件 AND 门**：`:160` `if not (base_url and api_key and model): return None`——
   三者缺一，整个快捷模型配置即判不可用。所以 `DEEPSEEK_BASE_URL` 不是"读了不用"，
   而是**缺它就直接拿不到 deepseek 配置**。
3. **确实被消费**：`grep -rln "quick_models" src` → `src/llm_gateway/gateway.py`、`active_config.py`、
   `src/utils/env_check.py`、`src/literature_feed/extract/headless_llm.py`（＋定义自身）——
   含运行时装配（gateway）、配置聚合（active_config）、启动自检（env_check）三条活路。
4. **已有测试直接钉着它**：`tests/test_quick_models.py:80` `monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://x")`，
   配合 `:65 test_get_config_with_full_env`（三件齐 → 返回配置）与 `:78 test_get_config_missing_key_returns_none`
   （缺一 → None）。**即"生效"这一判定不是本单新推，是既有测试已在守护的行为。**
5. **运行期实测探针**（只判存在、不打印任何值，避免泄露凭据）：
   `cd /d/code/psy-analysis && .venv/Scripts/python.exe -X utf8 -c "from src.llm_gateway.quick_models import QUICK_MODELS, load_env_local; import os; load_env_local(); print([(q.id, bool(os.environ.get(q.env_prefix+'_BASE_URL'))) for q in QUICK_MODELS])"`
   → 实测 `[('gpt', True), ('deepseek', True), ('kimi', False), ('claude', False)]`。
   **`deepseek` 的 BASE_URL 确实已配置且被读到**；两个 False 正是 9/13 已退役的 kimi / claude 通道，与阵容口径自洽。

## 三、锚点复核

| 锚点 | 结果 |
|---|---|
| `README.md:49` 原文 `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1` | **逐字命中** ✓ |
| `quick_models.py:156` 存在 `{qm.env_prefix}_BASE_URL` 动态拼接 | **命中** ✓（同读 `_API_KEY`:157、`_MODEL`:158） |
| `docs/insights/psy-readme-env-drift-20260917.md:17` 把它记为「保留＋理由（留日间确认）」 | 命中，本单**关闭这个未决**：确认保留 |

## 四、顺带发现（不属本单范围，供日间）

1. **psy 仓根本没有 `.env.example`**：`ls .env.example` → `No such file or directory`
   （本单一度把它写成"示例文件里没列这三个变量"，已按实测更正为"文件不存在"）。
   ⇒ README 教用户设 `DEEPSEEK_BASE_URL` 等变量，却**没有任何模板文件**支撑；
   新环境照 README 手配，一旦漏掉 `BASE_URL`（或 `KEY`/`MODEL` 任一），按 §二 2 的 AND 门
   该模型会**静默变为"无配置"**，而不是提示"缺哪一项"。
2. **预设表的 `label`/`description` 与现行阵容脱节**：表内写 `DeepSeek V4 Pro`「评审官」、`Kimi K2.6`「调研员」、
   `Claude Opus 4.8`「架构师/总指挥」，而根工作区 2026-09-13 定稿（`CLAUDE.md`）已把
   **v4-pro 退役、kimi 退役（中转 403）**，claude 经复测恢复为「L4/L5 第二独立评审」，
   总指挥＋第一执行手是 **V4 Flash**。⇒ psy 的 UI 下拉与角色描述会让用户按旧阵容选模型。
   本单**不改**（属产品口径变更，需日间拍板），只登记。
3. 因此 README 该行"保留"的边界条件是：**它仍是 `deepseek` provider 的接线**，
   与"用的是 v4-pro 还是 flash"无关——`DEEPSEEK_MODEL` 才决定型号，`BASE_URL` 只决定端点。

## 五、建议处置

- README.md:49 → **保留**（依据：第二节 1-4）。
- 若要顺手改善可观测性：把 `:160` 的 AND 门改成**缺哪个报哪个**（一行 `logger.warning`），
  用户就不会在"配了 KEY 忘了 BASE_URL"时拿到一个无提示的"模型不可用"。属行为变更，本单未动。

## 六、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 报告含 prefix→env 名映射表 ≥4 行 ＋ 结论一句 | 第一节 4 行全表＋开头结论一句 | 见本文 §一 |
| `grep -rn "env_prefix" src --include="*.py"` 附卷 | 全文附于 §二（7 行输出） | `cd /d/code/psy-analysis && grep -rn "env_prefix" src --include="*.py"` |
| 零改动（自加门） | 除本报告自身外无文件变动 | `cd /d/code/psy-analysis && git status --porcelain docs/insights/psy-deepseek-baseurl-trace-20260918.md` → `??` |

## 遗留问题

1. 第四节 1（psy 无 `.env.example` 模板文件）与 2（预设表阵容过期）都值得单开任务，本单只取证不处置。
2. 本单的"生效"分两层证据：代码路径（§二 1-4）＋运行期是否配齐（§二 5 的布尔探针，实测 `deepseek=True`）。
   探针**只判存在、未读取任何凭据值**；`DEEPSEEK_MODEL` 具体指向哪个型号本单未查（属凭据内容，不越界）。
3. 未核 `README.md` 其余环境行是否也各有对应前缀（只做了本单点名的 `DEEPSEEK_BASE_URL`）；
   同族的 README 全面对账在 `psy-readme-env-drift-20260917.md` 已做过一轮，本单补的是它留的那个未决。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
