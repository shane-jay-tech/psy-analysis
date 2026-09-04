# 全仓测试覆盖率审查报告

审查日期：2026-07-14

## 结论

完整离线测试集保持全绿，并新增 111 个针对核心行为、异常路径和边界条件的测试。
总体分支覆盖率从 48% 提升到 51%。最终覆盖率运行额外导入并纳入了
`environment_diagnosis` 的生产语句；即使分母扩大，未覆盖语句仍从
16,753 条降至 15,812 条，净减少 941 条。

审查同时发现并修复了两个真实缺陷：归档标签中的 `..` 可导致归档目录越界，
以及效应量为合法数值 `0` 时被 APA 门禁误判为“未报告”。两者均已加入回归测试。

| 指标 | 基线 | 最终 |
|---|---:|---:|
| 通过测试 | 2,283 | 2,394 |
| 跳过测试 | 1 | 1 |
| 按标记排除 | 88 | 88 |
| 纳入统计的生产语句 | 34,843 | 34,934 |
| 未覆盖语句 | 16,753 | 15,812 |
| 分支覆盖率（四舍五入） | 48% | 51% |

## 本次补测重点

| 模块 | 基线 | 最终 | 新增验证重点 |
|---|---:|---:|---|
| `src/data/transforms.py` | 0% | 99% | 计算、重编码、筛选、异常值、错误输入、不可变性 |
| `src/utils/privacy_ethics.py` | 30% | 97% | PII 扫描、严重度、DataFrame 扫描、缓存发现与清理 |
| `src/utils/archive_manager.py` | 20% | 96% | 归档往返、索引去重/限长、标签、损坏索引 |
| `src/utils/usage_logger.py` | 23% | 87% | 启停、事件/错误汇总、坏日志、反馈包、清理 |
| `src/output/formatter.py` | 8% | 88% | t/ANOVA/相关/卡方格式、效应量门禁、双语报告 |
| `src/parser/tokenizer.py` | 15% | 93% | 停用词、数字、标点和中英文词元 |
| `src/parser/intent_resolver.py` | 15% | 83% | 模糊匹配、默认降级、变量回填、方法升级、追问 |
| `src/experiment_design/jspsych_data_importer.py` | 11% | 89% | v6/v7、CSV/JSONL、空试次、JSON 展平、RT 单位、宽表 |
| `src/analysis/manova.py` | 13% | 95% | MANOVA/MANCOVA、输入校验、Box's M、小样本警告 |
| `src/analysis/logistic_regression.py` | 37% | 61% | 字符分类、类别校验、伪 R²、Hosmer-Lemeshow |
| `src/utils/method_exposure.py` | 24% | 100% | 方法分级、警告、新手安全和分组一致性 |
| `src/output/interpretation.py` | 4% | 18% | 效应量阈值、相关强度、缺失/未知/描述性降级 |

## 仍需优先处理的覆盖缺口

1. **Streamlit 页面和应用编排**：`app.py` 22%，`undergrad_wizard.py` 2%，
   多个页面模块为 0%–15%。这些代码耦合会话状态和渲染副作用，应先抽离纯逻辑，
   再通过 Streamlit 测试工具或 Playwright 覆盖关键用户流程。
2. **外部网络和文献抓取**：Crossref、手工导入、期刊抓取器和文献爬虫约
   10%–17%。本次强制证明命令排除了联网测试；后续应补 HTTP 录制/固定响应测试，
   验证限流、分页、坏响应和重试。
3. **核心低覆盖引擎**：`design_engine.py` 11%、`sem.py` 10%、
   `section_writers.py` 8%、`questionnaire/exporters.py` 22%、
   `analysis/runner.py` 28%。其中输出解释层虽然由 4% 提升到 18%，各统计结果类型的
   完整解释仍是下一轮最高价值目标。
4. **大对象分派层**：`result_card.py` 49% 和 `runner.py` 28% 含大量方法路由。
   应以表驱动契约测试验证“方法 ID → 执行器 → 结果卡 → 表格/解释”的全链路一致性。

## 工具链与维护风险

- `requirements-dev.txt` 在中文 Windows 区域设置下被 pip 按 GBK 解码，直接执行
  `pip install -r requirements-dev.txt` 会失败；本次改为单独安装已声明的
  `pytest-cov`。建议将该文件改为纯 ASCII 注释或使用兼容编码。
- 当前有 Pandas 4 `select_dtypes` 弃用警告、pytest 10 类级实例 fixture 弃用警告，
  以及 SimHei 缺少上标 2 字形警告。它们不影响本次通过结果，但应在依赖升级前修复。
- 联网、LLM 基准和 Playwright 测试未纳入强制离线证明；它们属于独立的发布前验证层。

## 证明命令

```powershell
python -m pytest -m "not online and not benchmark and not e2e and not playwright" --cov=src --cov=app --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
```

最终结果：`2394 passed, 1 skipped, 88 deselected`，总覆盖率 `51%`。
