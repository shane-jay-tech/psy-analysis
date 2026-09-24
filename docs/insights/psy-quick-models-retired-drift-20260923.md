# psy `quick_models` 快捷预设 vs 退役阵容漂移 · 裁决材料（s923-52）

- 任务：`zcode-bridge/inbox/s923-52.task.md`（cwd `D:\code\psy-analysis`）
- 执行班：`qoder-executor-20260924-0955-psy29`（psy **只读位**）
- 生成时间：2026-09-24T18:14+08:00
- 红线遵守：本单**零产码改动**（`git status --porcelain` 改前/改后均为同一 4 项在册在途件，见第十节）；
  **未读取、未粘贴任何密钥值**——`.env.local` 只按键名打印「有值/空」与 `len()`，base_url 只打印 netloc。
- 性质：**裁决材料＋推荐排序**。阵容清单本身不在执行手授权内，本文不拍板。

---

## 一、三句话结论

1. 卷宗说「选中即路由到退役通道」——**现状不成立**：`.env.local` 里根本没有 `DEEPSEEK_MODEL`/`KIMI_*`/`CLAUDE_*` 这些键，
   四条腿今天只有 `gpt` 一条可解析，所以退役名**当前打不出请求**；真实故障形态是「选中即全站 LLM 静默变哑」。
2. 漂移的根因**不是标签旧**，而是 **psy 的 env 键名契约与根工作区实配键名两套并行**：
   psy 读 `DEEPSEEK_MODEL`/`CLAUDE_*`，而 `.env.local` 与根 `CLAUDE.md:276` 权威清单用的是 `DEEPSEEK_FLASH_MODEL`/`ANTHROPIC_*`。
   ⇒ 只要有人按 psy README 补一行 `DEEPSEEK_MODEL=deepseek-v4-pro`，退役腿当场复活，且它会**优先**成为文献雷达的首选腿。
3. 「统一成三条腿还是两条腿」这件事**本仓两份在册文档互相打脸**（第六节），未拍板前任何顺手统一都是越界——故本文只给改动面与红数。

---

## 二、四预设现值表（`src/llm_gateway/quick_models.py:36-65`，逐字抄）

| # | id | label | env_prefix | provider | description（=UI 角色提示） | 源码行 |
|---|---|---|---|---|---|---|
| 1 | `gpt` | `GPT-5.5` | `GPT` | `openai` | 主程序员：清楚、温度强制 1.0 | 37-43 |
| 2 | `deepseek` | `DeepSeek V4 Pro` | `DEEPSEEK` | `deepseek` | 评审官：批判性强，推理类，温度默认 0.3 | 44-50 |
| 3 | `kimi` | `Kimi K2.6` | `KIMI` | `moonshot` | 调研员：长文档总结、查文献，温度强制 1.0 | 51-57 |
| 4 | `claude` | `Claude Opus 4.8` | `CLAUDE` | `claude` | 架构师 / 总指挥：综合判断、写作、规划 | 58-64 |

### 现值实测（`.venv` 解释器，真实 `.env.local`，密钥已脱敏）

```
$ cd D:\code\psy-analysis && .venv\Scripts\python.exe -c "... list_available_quick_models() / get_quick_model_config(...) / resolve_headless_model() ..."
A) UI preset availability:
    {'id': 'gpt',      'label': 'GPT-5.5',          'model': 'gpt-5.6-terra', 'available': True}
    {'id': 'deepseek', 'label': 'DeepSeek V4 Pro',  'model': '',              'available': False}
    {'id': 'kimi',     'label': 'Kimi K2.6',        'model': '',              'available': False}
    {'id': 'claude',   'label': 'Claude Opus 4.8',  'model': '',              'available': False}
B) get_quick_model_config per id（api_key 只打印长度，base_url 只打印 netloc）:
    gpt      -> {"provider":"openai","base_url":"ai.711ev.com","api_key":"<set len=51>","model":"gpt-5.6-terra","timeout":600}
    deepseek -> null
    kimi     -> null
    claude   -> null
C) headless: DEFAULT_MODEL_ID='deepseek' FALLBACK_ORDER=['deepseek','gpt','kimi','claude']
   resolved -> {"provider":"openai","base_url":"ai.711ev.com","model":"gpt-5.6-terra"}
```

`get_quick_model_config:160` 的门槛是 `base_url and api_key and model` **三者齐全**，缺一即 `None`。

---

## 三、整链取证：`env_prefix` → `.env.local` → gateway → 实际 HTTP

```
env_prefix (quick_models.py:40/47/54/61)
  → f"{prefix}_BASE_URL" / _API_KEY / _MODEL   (quick_models.py:156-158)
  → load_env_local() 只读「首个找到的 .env.local」(quick_models.py:79-123，:122 break)
  → get_active_llm_config() 叠 temperature       (active_config.py:69-90 → _resolve_temperature:53-58)
  → gateway._resolve_llm_config()                (gateway.py:375-382，未选即空 dict)
  → gateway._backend:347-354 再查一次 get_forced_temperature（温度双写）
  → ai_tutor.chat_with_tutor:249-277
       · provider 只用于 `== "ollama"` 分支判 URL；其余一律走 OpenAI 兼容 `_openai_chat_url(base_url)`
       ⇒ **真正决定打到哪个端点的是 `base_url`，`provider="moonshot"` 这个字符串本身不路由**
```

`.env.local` 实配键名清单（13 键，只列名与「有值/空」，不列值）：

| 键名 | 状态 | 备注 |
|---|---|---|
| `DEEPSEEK_BASE_URL` / `DEEPSEEK_API_KEY` | SET / SET | 端点 `api.deepseek.com`（官方） |
| `DEEPSEEK_FLASH_MODEL` | SET（`deepseek-v4-flash`） | **psy 的预设表读不到这个键** |
| `DEEPSEEK_MODEL` | **键不存在** | psy `quick_models` 要的恰是它 |
| `GPT_BASE_URL` / `GPT_API_KEY` / `GPT_MODEL` | SET×3 | `ai.711ev.com` + `gpt-5.6-terra` ⇒ psy 唯一活腿 |
| `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | SET×3 | `ai.711ev.com` + `claude-opus-5`；**psy 要的是 `CLAUDE_*`，读不到** |
| `IMAGE_*` / `TAVILY_API_KEY` | SET | 与本单无关 |
| `KIMI_*` | **三件套全缺** | kimi 腿结构不可解析 |
| `CLAUDE_*` | **三件套全缺** | claude 腿同上 |

旁证（根工作区侧同一套键的用法）：`D:\code\scripts\health_check.py:46-47`、`llm_call.py:257`、
`night_brain.py:1068`、`oneoff/suite_v41.py:47` 全部用 `DEEPSEEK_FLASH_MODEL` / `ANTHROPIC_*`；
`D:\code\CLAUDE.md:276` 的环境变量权威清单里**没有** `DEEPSEEK_MODEL`、也没有 `KIMI_*` / `CLAUDE_*`。
⇒ psy 的 `env_prefix` 契约是**孤儿命名空间**。

---

## 四、否证的卷宗前提（3 条，命令见第十节）

| 卷宗原话 | 实测 | 判定 |
|---|---|---|
| 「侧栏四快捷预设仍含 DeepSeek V4 Pro / Kimi K2.6，**选中即路由到退役通道**」 | 选中后 `get_quick_model_config` 返回 `None` → `get_active_llm_config()` 返回 `None` → 全站 LLM「未激活」；打不出退役请求 | **否证（收窄为「选中即静默变哑」＋「补一键即复活」的潜在口子）** |
| 锚点 `quick_models.py:46/53/55` 三行 | Read 复核逐字一致 | **成立，0 漂移** |
| 历史锚点 `docs/insights/psy-deepseek-baseurl-trace-20260918.md:48` 实测 `[('deepseek', True)]` | 今日 `deepseek available=False` | **已漂移**（9/18→9/24 之间 `DEEPSEEK_MODEL` 被删/改名），引用旧读数会得出相反结论 |

补一条卷宗未提的：侧栏 `app.py:206-223` 的 selectbox **不禁用**未配置项，只是把 label 拼成
`"Kimi K2.6 ⚠️未配置"`（`app.py:207`）——用户仍可点选，点完即触发上面的「变哑」。

---

## 五、「把退役模型列为可选」的全部在册位置 ＋ 改动面

`rg -n 'env_prefix|_FORCED_TEMPERATURE' src/llm_gateway/quick_models.py` 全命中（判据点名）：
`:31 :40 :47 :54 :61 :73 :156 :157 :158 :175`

| # | 位置 | 内容 | 活/死 | 改动面 |
|---|---|---|---|---|
| 1 | `src/llm_gateway/quick_models.py:46,49` | `label="DeepSeek V4 Pro"` ＋「评审官」角色描述 | **活**（UI 直接渲染） | 2 行 |
| 2 | `quick_models.py:51-57` | kimi 整条腿（`provider="moonshot"`） | 活但不可解析 | 6 行（删）/ 2 行（只改文案） |
| 3 | `quick_models.py:58-64` | claude 腿 `env_prefix="CLAUDE"` | 活但不可解析（实配是 `ANTHROPIC_*`） | 1 行（改前缀）/ 6 行（删） |
| 4 | `quick_models.py:3-4` | 模块 docstring 列 4 组旧模型名 | 注释 | 2 行 |
| 5 | `quick_models.py:73-76` | `_FORCED_TEMPERATURE` 的 `kimi: 1.0` | 活（被 gateway 与 active_config 双读） | 1 行（联动项，见第七节） |
| 6 | `src/literature_feed/extract/headless_llm.py:25,27,28` | 注释点名 `deepseek-v4-pro`；`DEFAULT_MODEL_ID="deepseek"`；回退链含 `kimi`/`claude` | **活**（无头抽取的选腿逻辑） | 3 行 |
| 7 | `config/llm_providers.yaml:7,9,12` | `default_model: "deepseek-v4-pro"` ＋ models[0] ＋ 描述 | **死配置**：全仓零读取点（`LLM_PROVIDERS` 由 `config/llm_providers.py:_build_providers()` 硬编码，无任何 yaml 加载器；`rg "llm_providers.yaml"` 只命中历史报告） | 3 行，改之 0 生产影响、0 红 |
| 8 | `config/llm_providers.py:64-83` | `moonshot` 整块（`kimi-latest` / `kimi-k2-*`） | **半死**：唯一生产读者 `src/questionnaire/kb_search.py:238` 导入 `get_provider_config`，**该函数全仓未定义** → ImportError 被 `kb_search.py:105-118` 的 `except Exception` 吞掉 → LLM 降级搜索恒返回 `[]` | 20 行 |
| 9 | `src/questionnaire/llm_engine_premium.py:1511,1556-1557` | kimi 推理变体名单与提示文案 | 活（文案/启发式） | 3 行 |
| 10 | `src/utils/env_check.py:149` | 提示语「请配置 GPT_/DEEPSEEK_/KIMI_/CLAUDE_」 | 活（文案，且教的是孤儿键） | 1 行 |
| 11 | `src/utils/llm_timer.py:52` | docstring 示例 `model_name="deepseek-v4-pro"` | 注释 | 1 行 |
| 12 | `src/literature_feed/storage/budget_tracker.py:31` | 价目表 `"kimi-k2"` 条目 | 活（价目表，**涉数值→本单不动**） | 1 行（需人工裁决） |
| 13 | `src/utils/user_prefs.py:46` | `"_runtime_models_moonshot"` 偏好键名 | 活（存储键，改名=老用户偏好失效） | 1 行（**不宜顺手**） |
| 14 | `README.md:50` | `DEEPSEEK_MODEL=deepseek-v4-flash` | 文档（值合法、**键名与实配不符**） | 1 行 |
| 15 | `KNOWN_ISSUES.md:32` | v4.3 历史表列 4 个旧名 | 历史记录 | **不改** |

在册测试锁定点（决定「改了会红什么」）：
`tests/test_quick_models.py:45,53,91-94,100-107,120-121,138,147-151`；
`tests/test_literature_feed_headless_llm.py:32,55,56,134,183`；`tests/test_active_config.py:50,54`。
基线（`.venv`，非全量）：`tests/test_quick_models.py + test_active_config.py + test_llm_gateway_static_guard.py` → **22 passed**；
`tests/test_literature_feed_headless_llm.py` → **10 passed**；`tests/test_yaml_config.py` → 5 collected。
`tests/test_llm_engine.py`（含 `LLM_PROVIDERS` 断言）**收集 0 例**——它是脚本形态，不在套件里。
全仓 `-i` 扫描确认：无任何代码断言 label 文本（`DeepSeek V4` / `Kimi K2` / `Claude Opus 4` 只出现在 `quick_models.py:3-4,39,46,53,60`）。

---

## 六、⚠ 在册文档冲突（未拍板，禁止顺手统一）

| 文档 | 口径 | 关键行 |
|---|---|---|
| `D:\code\CLAUDE.md` | **两条腿**：官方 DeepSeek Flash ＋ 711ev 中转 GPT-5.6；claude 全系退役 | `:3`「只剩两条腿」、`:4`/`:39` claude 中转 8 模型全 503、`:53`「~~Kimi / Claude~~ ❌ 已退役」 |
| `D:\code\AGENTS.md` | **三条腿**：＋ 711ev 中转 Claude Opus 5（L4/L5 第二独立评审），并明写「别再把 claude 当退役」 | `:12`、`:13`「下午复测 11 个模型全部可用，已恢复」 |
| 今日新证据 | `D:\code\docs\decisions\2026-09-24-bridge-pending-approvals-r3.md:127`：`llm_call.py --model claude` **退出码 0**、返回正文「可用」 | 支持 AGENTS.md 一侧 |
| psy 本仓 | 无 `CLAUDE.md`/`AGENTS.md`（`ls` 已确认不存在），仅在两份历史 insights 里转述根阵容 | `docs/insights/psy-deepseek-baseurl-trace-20260918.md:66-69` |

⇒ **v4-pro 与 kimi 两侧口径一致（退役）**；**claude 是唯一分歧点**。因此 claude 腿（表中 #3）是「删」还是「接通」
取决于这份冲突怎么拍，执行手不替用户决定。本文的推荐排序把 claude 腿单列，可被裁决结果一键翻转。

---

## 七、替换候选方案（≥2 案，红数为 `.venv` 探针**实测**）

探针：`tmp/s923-52/variant_probe.py`（gitignored；仅内存替换 `QUICK_MODELS`/`_FORCED_TEMPERATURE`，
并逐字复算 `tests/test_quick_models.py` 的 7 条在册断言字面量）。复算配方见第十节。

| 方案 | 内容 | 温度表迁移 | 实测在册红数 | 红在哪 |
|---|---|---|---|---|
| **A 仅改文案** | `:46` label→`DeepSeek V4 Flash（官方）`、`:49` description 改角色；`:53/:56` kimi 标「已退役·勿选」 | **零迁移**（`_UI_DEFAULT_TEMPERATURES` 与 `_FORCED_TEMPERATURE` 不动） | **0** | — |
| **B 换读键（兜底式）** | deepseek 腿优先读 `DEEPSEEK_FLASH_MODEL`、缺则回落 `DEEPSEEK_MODEL`（`QuickModel` 加 `model_env_key` 字段 ≈3 行） | 不动；deepseek 仍走 0.3 | **0** | — |
| **B2 换读键（覆盖式）** | 同上，但 FLASH 键存在时**直接覆盖** `DEEPSEEK_MODEL` | 不动 | **1** | `test_quick_models.py::test_get_config_for_all_four`（夹具注 `DEEPSEEK_MODEL=deepseek-v4-pro` 被抢） |
| **C 删 kimi 腿＋清温度项** | 删 `:51-57`、删 `_FORCED_TEMPERATURE["kimi"]:75` | 强制温度表由 `{gpt:1.0,kimi:1.0}` → `{gpt:1.0}`；`active_config._UI_DEFAULT_TEMPERATURES` 不受影响 | **6** | `:45 ids`、`:53 provider`、`:94 kimi_timeout`、`:111 all_four`、`:121 forced_temp`、`:138 list_len4` |
| **D claude 腿接通实配** | `:61 env_prefix "CLAUDE"→"ANTHROPIC"`（分歧点，须先拍第六节） | 不动；claude 仍走 0.7 | **2** | `:111 all_four`、`:150 claude_avail`（两处夹具仍注 `CLAUDE_*`） |
| 联动项（任一方案都可能碰） | `headless_llm.py:27 DEFAULT_MODEL_ID` 若改离 `deepseek` | — | **+1** | `test_literature_feed_headless_llm.py::test_preferred_default_deepseek_hit:56` 断言 `calls[0] == "deepseek"` |

温度表迁移的完整影响面（判据点名）：
- `_FORCED_TEMPERATURE`（`quick_models.py:73-76`）被 **两处**消费：`gateway.py:347-354`（后端兜底再强制一次）与
  `active_config.py:53-58 _resolve_temperature`（API 强制优先于 UI 预设）。删 `kimi` 项对现网无行为差（kimi 腿本就不可解析），
  但会红 `test_forced_temperature_gpt_kimi:121`。
- 若 deepseek 腿从「v4-pro/0.3 评审官」改为「v4-flash/执行手」，语义冲突点不在温度（Flash 也吃 0.3）而在
  `description` 的角色标签与 `active_config.py:34 "评审官走严谨"` 注释——文案改动即可，无需动数值。
- ⚠ `budget_tracker.py:31` 的 kimi 价目是**统计/成本数值**，属红线域，本单只登记不换算。

---

## 八、推荐排序（交用户拍板）

1. **首推 B（兜底式换读键）＋ A（文案）合并**：约 5 行（`QuickModel` 加字段 1 行、`:156-158` 取键 2 行、label/description 2 处），
   实测 **0 在册红**；它同时治「UI 名不副实」和「psy 读不到 Flash 腿」两个真问题，
   且**不把任何退役名变成可达**（Flash 是在册在役腿）。
2. **次推 D**：只在第六节的 claude 分歧被拍成「claude 在阵」时才做，2 行改前缀＋2 处测试夹具，实测红 2（都是夹具值，非语义红）。
   若拍成「claude 退役」，则退化为 A 的文案处理，**不要**用 C 那种删腿做法（6 红、还把 4 条腿的不变式写坏）。
3. **不推荐 C（删 kimi 腿）**：6 条在册断言锁死「四腿」形状，删腿是**改测试契约**而不是改配置，收益只有文案。
4. **建议单独收编（与阵容无关，属清理）**：`config/llm_providers.yaml`（零读取点的死配置，内含真退役名
   `deepseek-v4-pro`）与 `config/llm_providers.py:64-83` ＋ `kb_search.py:238` 的 `get_provider_config` 断链——
   这两处 0 生产影响、0 在册红，适合并入「psy 死代码/双轨清理」专单，**别混进阵容裁决**。
5. 无论选哪案，`README.md:50` 的 `DEEPSEEK_MODEL=` 与 `env_check.py:149` 的键名提示需同步为实配键名，
   否则新装环境会照 README 配出一个 psy 读得到、根工具链读不到的半死键。

---

## 九、放行后施工单要点（本单不执行）

- 改动面预估：方案 B+A ≈ 5 行生产码 ＋ 0 行测试；方案 D 另加 2 处测试夹具。
- 必跑的定向套件（**不跑全量**，399s 口径见纪律档 §四.2）：
  `.venv\Scripts\python.exe -m pytest tests/test_quick_models.py tests/test_active_config.py tests/test_literature_feed_headless_llm.py -q`
  现值 22＋10 passed（见第五节）。
- 触及 `app.py`（侧栏文案）属他班在途件 ⇒ 施工单必须等 psy 写位空出后开工，本单只读位**一行未动**。
- 在册红 81/182/194/198/201 与本单无交集；撞红不得自行消红。

---

## 十、复算配方（命令原文，全部只读）

```
# 1) 基线在册红数（改前）
cd D:\code\psy-analysis
.venv\Scripts\python.exe -m pytest tests/test_quick_models.py tests/test_active_config.py \
    tests/test_llm_gateway_static_guard.py -q -p no:cacheprovider        # → 22 passed in 4.06s
.venv\Scripts\python.exe -m pytest tests/test_literature_feed_headless_llm.py -q -p no:cacheprovider   # → 10 passed
.venv\Scripts\python.exe -m pytest tests/test_yaml_config.py tests/test_llm_engine.py -q --collect-only # → 5 collected（test_llm_engine 0 例）

# 2) 判据点名的行号表
rg -n 'env_prefix|_FORCED_TEMPERATURE' src/llm_gateway/quick_models.py   # → :31 :40 :47 :54 :61 :73 :156 :157 :158 :175

# 3) 整链现值（密钥脱敏：只打印 api_key 的 bool/len 与 base_url 的 netloc）
.venv\Scripts\python.exe -c "import urllib.parse,json;from src.llm_gateway.quick_models import list_available_quick_models,get_quick_model_config;from src.literature_feed.extract.headless_llm import resolve_headless_model,DEFAULT_MODEL_ID,_FALLBACK_ORDER;..."

# 4) .env.local 只取「键名 + 有值/空」，不取任何值
python -c "from pathlib import Path;...print(k, 'EMPTY' if not v.strip() else 'SET')"

# 5) 方案红数探针（内存替换，未写在册文件）
PYTHONIOENCODING=utf-8 .venv\Scripts\python.exe tmp\s923-52\variant_probe.py

# 6) 退役名残留全仓扫描（含 -i，覆盖 20260917 那次的正则盲区）
rg -n -i "v4[\s.-]?pro|kimi|k2\.6|moonshot|dashscope|opus\s*4|deepseek-reasoner|万象" \
   --glob '!node_modules' --glob '!.venv' --glob '!logs' -g '*.py' -g '*.md' -g '*.yaml' .

# 7) 零产码改动自证（改前=改后同一读数）
cd D:\code\psy-analysis && git status --porcelain
#  M app.py / M pytest.ini / M requirements-lock.txt / ?? node_modules/   ← 全部是他班在途件，本单未触碰
git check-ignore -v tmp/s923-52/variant_probe.py   # → .gitignore:29:tmp/
```

与 `psy-retired-model-scan-20260917.md` 的关系：那次命令是 `rg "DEEPSEEK_MODEL|deepseek-.*-r|glm-4"`，
正则要求字面 `-r`，**匹配不到 `deepseek-v4-pro`**（该串里没有 `-r` 子串）⇒ 它给出「真退役名 0」的结论，
但漏掉了 `config/llm_providers.yaml:7,9,12` 的三处。本文用 `-i "v4[\s.-]?pro"` 双轨补齐。

---

## 十一、遗留问题

1. **claude 在阵/退役未拍板**（第六节）——`CLAUDE.md:3/:39` 与 `AGENTS.md:12/:13` 直接冲突，且今日
   `docs/decisions/2026-09-24-bridge-pending-approvals-r3.md:127` 有 rc=0 的新证据偏向 AGENTS.md 一侧。
   ⇒ 交主班进待人工台账，**不要**由执行手统一。
2. `DEEPSEEK_MODEL` 键在 9/18→9/24 之间从有到无（历史读数 `psy-deepseek-baseurl-trace:48` 为 True，今日 False），
   谁删的、是否有意，本仓无 git 痕迹（`.env.local` 被 `.gitignore:20` 忽略）。⇒ 需人工确认。
3. `budget_tracker.py:31` 的 `kimi-k2` 价目条目属成本数值红线域，只登记未处置。
4. `user_prefs.py:46` 的 `_runtime_models_moonshot` 是持久化偏好键，改名会让老用户偏好失效，未给方案。
5. `kb_search.py:238` 导入不存在的 `get_provider_config`、且被 `except Exception` 吞掉 ⇒ LLM 降级搜索恒空。
   这是**功能静默失效**，与阵容无关，建议单开一单（本单只取证）。
6. 侧栏不禁用不可解析预设（`app.py:206-223`）这件事，即使选了方案 A 也仍在：文案加了「勿选」但照样能点。
   真正堵住需要改 `app.py`（他班在途件），本单未碰。
