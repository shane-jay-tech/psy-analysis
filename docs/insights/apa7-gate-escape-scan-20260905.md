# APA7 门禁漏网案例全库扫描（合成边界输入，2026-09-05 夜 1020）

> 范围：`src/output/formatter.py` 效应量全局门禁（`check_effect_size_required`:181，唯一调用方 `build_apa7_report`:239）＋ `src/paper_writer/literature_library.py::format_citation_apa7`:625（undergrad_wizard 引用路径）。
> 方法：23 组合成边界输入（A 侧 9 组 + B 侧 14 组）经 .venv 实跑真代码，零 LLM、零联网、src 与 tests 零改动。
> 结论先行：**门禁 A 的射程只覆盖效应量一条路，引用侧完全在门禁外**；引用侧 14 组边界输入 6 组必修级畸形。对 C3 决策点 4（「top10 缺口方法配专属 formatter 分支」）的证据建议：**不要分支，要收敛**——wizard 的 tuple 路径应改走 `LiteratureEntry.format_reference`（昨夜已修全 >20 作者/publisher/中文口径），单一事实源。

## 一、门禁能力边界（白名单式清单）

`check_effect_size_required` 检查什么：
- 结果对象属性白名单（11 项）：effect_size / eta_squared / partial_eta_squared / cohens_d / hedges_g / cramers_v / omega_squared / r_squared / adj_r_squared / kappa；
- output 顶层字段（3 项）：effect_size / eta_squared / cohens_d（**仅当 result 非 None 才可达**，见漏网 A9）；
- 唯一豁免：`test_type == "descriptive"`。

不检查什么（= 射程外）：
- 值的合法性与数值性（NaN、字符串均放行）；
- 信度/一致性类方法（cronbach_alpha 等被当推断统计拦下，属过度严格而非漏网）；
- **引用/参考文献格式完全不经此门禁**（build_apa7_report 只在正文报告入口调用；wizard 引用走另一条路）。

## 二、A 侧漏网实例（效应量门禁）

| # | 输入 | 实际 | 期望 | 归属 | 分级 |
|---|---|---|---|---|---|
| A3 | `effect_size=float("nan")` | 门禁放行；报告行将输出 `效应量 = nan` | NaN 应拦截并提示重新计算 | formatter 门禁缺口（无值校验） | **必修** |
| A4 | `effect_size="N/A"` | 门禁放行（非 None 非 ""） | 非数值应拦截 | formatter 门禁缺口（无类型校验） | 建议 |
| A9 | `result=None` 且 `output["effect_size"]=0.4` | 直接拦截「未找到分析结果对象」 | 文档承诺的顶层字段路径生效放行 | formatter 门禁缺口（死代码分支：顶层字段循环在 result=None 时不可达） | 建议 |
| A6 静态 | kappa-only 结果 | 门禁放行；`build_apa7_report` 的 es_parts 收集清单（9 项）不含 kappa → 报告行退化「效应量已计算（见上方输出）」 | 两清单一致 | formatter 门禁缺口（gate 白名单 11 项 vs 报告收集 9 项不同步） | 建议 |
| A7 | `cronbach_alpha` 无效应量字段 | 拦截 | 信度类 α 本身即指标，应入豁免清单 | 门禁豁免清单过窄（过度严格方向） | 建议 |

正确行为佐证（非漏网）：A1 descriptive 豁免 ✓、A2 无结果拦截 ✓、A5 零值放行 ✓。

## 三、B 侧漏网实例（format_citation_apa7，14 类边界）

| # | 输入类 | 实际输出（节选） | 期望（APA7） | 归属 | 分级 |
|---|---|---|---|---|---|
| B1 | 无作者 | `' (2020). Title…'`（空缺+前导空格） | 标题上移作者位 | apa7 函数缺口 | **必修** |
| B2 | None 作者 | `'None (2020)…'` | 前置校验拒绝 | apa7 函数缺口 | **必修** |
| B3 | 无年份 | `'Smith, J. (). …'` | `(n.d.)` | apa7 函数缺口 | **必修** |
| B4 | None 年份 | `'(None)'` | `(n.d.)` | apa7 函数缺口 | **必修** |
| B5 | 标题为空 | `'. . *J*.'` 双句点 | 前置校验拒绝 | apa7 函数缺口 | **必修** |
| B8 | 书籍（来源空） | `'Book Title. **.'`（裸斜体标记、无出版社） | 书籍格式含出版社 | apa7 函数缺口（tuple schema 无 publisher/类型区分） | **必修** |
| B9 | 网页来源 | URL 被斜体、无检索日期 | 站点名不斜体、URL 裸排 | apa7 函数缺口 | 建议 |
| B11 | 21 作者字符串 | 全量罗列 21 人 | 前 19 + … + 末位（昨夜 00ff 只修了 manager 侧 `format_reference`，库侧 tuple 路径未同步） | apa7 函数缺口（与 manager 侧不对齐） | **必修** |
| B6 | 标题句尾问号 | `'ok?.'` 双标点 | 吸收句点 | apa7 函数缺口（小） | 建议 |
| B7 | 标题含星号 | 破坏下游 markdown 斜体 | 转义 | apa7 函数缺口（小） | 建议 |
| B10 | 中文条目 | 英文逗号句点 `温忠麟, 叶宝娟 (2014).` | 中文标点（与 manager 侧口径对齐） | apa7 函数缺口（小） | 建议 |
| B12 | 作者尾随逗号 | `', (2020)'` 双逗号 | 清洗 | 上游数据问题（配套前置清洗） | 建议 |
| B13 | 字段含换行 | 引用行内裸换行 | 清洗 | 上游数据问题（配套前置清洗） | 建议 |
| B14 | 字段首尾空格 | `'  Padded  .'` | strip | 上游数据问题（配套前置清洗） | 建议 |

## 四、对「专属 formatter 分支」决策的证据建议

1. **不建议按方法建分支**：B 侧全部漏网集中在一条 625 行的朴素 tuple 函数上，而 manager 侧 `LiteratureEntry.format_reference` 已具备正确口径（>20 省略、书籍 publisher、中文格式）。分支会复制两份需同步维护的规则——本次 B11 正是「同规则两处实现只修了一处」的现行案例。
2. **建议收敛**：undergrad_wizard:3684/3696 改从 tuple 组装 LiteratureEntry（或直接调用 format_reference 逻辑），废弃 format_citation_apa7 的独立拼串；tuple 入口保留薄壳做前置清洗（B12–B14 类上游脏数据在此统一 strip/校验，B1/B2/B3/B5 缺字段直接拒绝并报因）。
3. **门禁 A 补三件事**：NaN/非数值校验（A3/A4）；顶层字段死分支修复或删除文档承诺（A9）；gate 白名单与报告收集清单同步（A6 静态）；信度类豁免清单扩充（A7）属口径决策，建议日间拍板。

## 五、复现方式

扫描脚本为一次性合成探测（%TEMP% 已弃），23 组输入全部记录于上表（输入→实际→期望三要素齐），按表可秒级复现：`.venv/Scripts/python.exe` 导入两函数后逐行代入即可。
