# 问卷设计引擎质量审查（psy-C2，2026-09-04）

- 范围：src/questionnaire/llm_engine.py（820 行，基础引擎）与 llm_engine_premium.py（1640 行，高级引擎）
- 方法：静态代码审读 + prompt 模板与校验代码交叉定位（附文件:行号）；.academic_cache 仅作结构统计不引内容；零代码改动
- 生成样例证据：tests/fixtures 的合成样例为本报告质量证据来源；缓存正文未读（隐私）

## 一、规范覆盖矩阵（规范条目 × 两引擎：硬校验 / prompt 建议 / 未覆盖）

| # | 心理测量学规范 | 基础引擎 llm_engine | 高级引擎 llm_engine_premium |
|---|---|---|---|
| 1 | 条目数量范围（每维度 3-8 题） | prompt 建议（:150） | prompt 建议 + skeleton 结构解析（:647 _validate_skeleton 查维度结构，题量数值仅建议） |
| 2 | 反向题比例 20%-30% | prompt 建议（:149） | prompt 建议 + **本地硬检测**（item_quality 弱反向检查） |
| 3 | 反向题质量（真反向 vs 伪反向/镜像题） | 未覆盖 | **prompt 详例**（:56-72 正误对照）+ **硬检测**（item_quality 弱反向） |
| 4 | 双重装载（一题两问） | 未覆盖 | **硬检测**（item_quality.py:84,246 _check_double_barreled，v3.7 含"又…又…"结构 :266） |
| 5 | 双重否定 | 未覆盖 | **硬检测**（item_quality.py:281 _check_negation，区分正向/反向语境） |
| 6 | 未定义专业术语/抽象表述 | 未覆盖 | **硬检测**（item_quality.py:296 _check_vague_words、:379 _check_abstractness） |
| 7 | 条目语义重复 | 未覆盖 | **硬检测**（item_quality.py:313 _check_redundancy 字符重叠相似度） |
| 8 | 条目与维度单义对应 | **硬校验**：JSON 必填字段+dimensions 非空（:336） | **硬校验**：_parse_json 缺字段即抛（:300-336）+ LLM critique（:1167） |
| 9 | 社会赞许性控制提示 | **未覆盖** | **未覆盖** |
| 10 | 指导语规范（目的/保密/填写/评分） | prompt 建议（:161）+ 输出 schema 字段（:204） | prompt 建议（metadata 阶段 :478） |
| 11 | Likert 点数约定 | prompt 建议（:147-148 人格 5 点/宽泛 7 点）+ 计分说明生成（:466） | 未明确约定（仅 metadata 提及计分） |
| 12 | 量表总分与维度分使用说明 | prompt 建议（:205 计分规则/总分范围） | prompt 建议（:494 心理测量学评估方案） |
| 13 | 信效度局限声明 | **未覆盖** | prompt 建议（:494） |
| 14 | 极端词/绝对化表述 | 未覆盖 | **硬检测**（item_quality.py:415 _check_extreme_words） |

（"硬检测"= 本地确定性代码检查，不依赖 LLM 自觉；"prompt 建议"= 仅存在于提示词文本。）

## 二、证据行号索引

- 基础引擎规范文本：llm_engine.py:149（反向比例）、:150（每维度 3-8 题）、:161（指导语）、:147-148（Likert 点数）、:204-205（指导语/计分 schema 字段）、:336（dimensions 非空硬校验）、:466-468（反向计分说明）。
- 高级引擎：llm_engine_premium.py:56-72（真/伪反向对照）、:626-647（_parse_json/_validate_skeleton 硬解析）、:1167（_run_llm_critique 质评环）、:1390（弱项重生成 _regen_one）、:478-494（metadata：指导语/计分/心理测量学评估/参考文献）。
- 本地质检：item_quality.py:19（check_item_quality 入口）、:84（双重陈述）、:246/:266（含"又…又…"）、:281（否定）、:296（模糊词）、:313/:332（冗余相似度）、:379（抽象度）、:399（过拟合）、:415（极端词）。

## 三、Gap 清单（按对生成质量的影响排序）

1. **【两引擎缺失】社会赞许性控制**（矩阵 #9）：无任何 prompt 提示或检测。影响：生成的条目可能诱导中性行为表述，降低构念效度。建议补丁：在两引擎 system prompt 增加一条"避免明显的社会期望表述（如'我应该''大家都知道'），必要时配反向情境题"；可在 item_quality 增加应然词（应该/必须/总是）频次告警。
2. **【基础引擎】本地质检整套缺失**（矩阵 #4/5/6/7/14）：基础引擎生成的条目不经过 item_quality.py。建议补丁：design_questionnaire_llm 返回前统一调用 check_item_quality，不合格条目走一次重生成（premium 已有 _regen_one 可复用）。
3. **【基础引擎】信效度局限声明缺失**（矩阵 #13）：导出的问卷无任何"本量表信效度待验证"声明。建议补丁：报告生成器（report_generator.py）固定追加局限声明段。
4. **【高级引擎】Likert 点数未约定**（矩阵 #11）：多阶段 prompt 均未约束点数一致性，跨维度可能混用 5/7 点。建议补丁：_items_system_prompt 增加全局点数字段，_validate_skeleton 校验全卷一致。
5. **【两引擎】反向题计分规则无硬校验**（矩阵 #12 关联）：计分为 prompt 文本，无"反向题数与计分声明一致"的机器核对。建议补丁：metadata 解析后断言 instructions/scoring 中反向题数 == 实际 is_reverse 条数。
6. **【两引擎】条目-维度单义对应的深度校验缺失**（矩阵 #8）：结构合法但"条目内容是否真属该维度"无语义校验（premium 的 LLM critique 部分覆盖，基础引擎完全依赖 LLM 自觉）。建议补丁：复用 construct_kb 的向量/关键词相似度做条目-维度归属的本地粗校验。

## 四、合成样例质检观察（tests/fixtures）

fixtures 中合成问卷经 item_quality 检查的既有断言覆盖双重装载与弱反向两厂（证明 #3/#4 的硬检测路径有效）；未覆盖社会赞许性与点数一致性（与 Gap 1/4 对应）。

## 五、结论

两引擎呈"premium 质检完备、base 裸奔"的分层：硬校验集中在 premium 的 item_quality 链路，基础引擎 14 项规范中 6 项未覆盖。**最高性价比补丁**是把 item_quality.check_item_quality 接入基础引擎返回路径（Gap 2，预计 <50 行改动），其次补社会赞许性 prompt（Gap 1，纯文本）。
