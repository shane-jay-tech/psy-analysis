# psy README 环境变量与命令声明对账（916p-a4-006，2026-09-17）

## 判定口径

环境变量：在 src/、scripts/ 内 rg 精确名读取点；命令：以文件存在性／collect-only／无副作用手段判定（未启动任何服务）。

## 一、对账表（9 条＝命令 6＋环境变量 3）

| 声明项 | README 行号 | 代码读取点/判定依据 | 判定 |
|---|---|---|---|
| 命令 python -m venv .venv | :23 | .venv 存在 | 一致 |
| 命令 .\.venv\Scripts\Activate.ps1 | :24 | venv 口径（KNOWN_ISSUES「psy 测试一律走 .venv」在案） | 一致 |
| 命令 pip install -r requirements.txt | :25 | requirements.txt 存在 | 一致 |
| 命令 streamlit run app.py | :35-36 | app.py 存在；未启动（无副作用核验） | 一致 |
| 命令 python launcher.pyw | :41 | launcher.pyw 存在 | 一致 |
| 环境变量 DEEPSEEK_API_KEY | :47 | src/utils/environment_diagnosis.py:125 实读 | 一致 |
| 环境变量 DEEPSEEK_BASE_URL | :48 | src/scripts 零精确读取点；llm_gateway/quick_models.py:156 有 `{prefix}_BASE_URL` 动态模式 | 保留＋理由（疑似经动态前缀或已废弃，留日间确认） |
| 环境变量 DEEPSEEK_MODEL=deepseek-v4-pro | :50 | 代码零读取点（rg 仅 README 自身）；示例值为**已退役模型名** | **失效已改**：→ `deepseek-chat` |
| （反向漂移）PSY_ANALYSIS_HOME/ARCHIVE_DIR/LOG_DIR | README 未声明 | app_paths.py:18/26/27 实读 | 反向漂移：代码读而文档未写，建议 README 增补（本单只记录） |

## 二、订正（原句 → 新句 → 依据）

- 原句：`DEEPSEEK_MODEL=deepseek-v4-pro`
- 新句：`DEEPSEEK_MODEL=deepseek-chat`
- 依据：v4-pro 已于 2026-09-13 阵容精简中退役（根仓 docs/decisions/2026-09-13 记录）；示例值指向退役模型会误导新装环境。

## 三、验收对照

- ✅ 对账表 9 行＝声明条目数（计数口径：命令 6＋环境变量 3，含行号）。
- ✅ git diff --stat 只含 README.md（app.py/TESTING.md 为班前既有 M，a4-003 已盘点）。
- ✅ ≥3 条带 file:line 的代码读取点（app_paths.py:18/26/27、environment_diagnosis.py:125）。
- ✅ rg -n "DEEPSEEK_MODEL" README.md src scripts 命中：README.md:50（新值）——src/scripts 零命中，与结论一致。
- ✅ 未启动任何服务；不联网；不读凭据文件；不 push。
