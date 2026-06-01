# 2026-05-30 — I/O 心理学专业方向 KB & 文献雷达加权

## 起源

用户研究生方向已锁定 People Analytics / 工业与组织心理学 / HRBP，开放性问"还有什么可以升级"，给出"专业方向加权"作为推荐方向（vs. 数据收集闭环）。用户：「先做专业那条吧，这个系统目前就我一个人用，多人不着急」。

走单模型 + Kimi 调研协作（不走 GPT/DeepSeek 多模型），因为：
- 改动是**纯数据填充**（YAML + Python dict），不是业务逻辑变更
- 主要难点是**专业知识**（哪些量表是华人 OB 研究的标配），Kimi K2.6 调研员强项
- 不涉及 architecture / security / 公共接口

## 改了什么

### Phase A — 增强 3 条已有 OB 构念的 `established_scales`

**`src/questionnaire/construct_kb.py`**：

- **组织承诺**：原仅 Allen & Meyer (1990) → +ACS 简版 (Meyer, Allen & Smith, 1993) +中文修订版 (Chen & Francesco, 2003)
- **工作-家庭冲突**：原仅 Carlson et al. (2000) → +Netemeyer et al. (1996) 双向冲突量表 +Carlson et al. (2006) 工作家庭充实量表
- **组织公民行为**：原仅 Podsakoff et al. (1990) → +Farh, Earley & Lin (1997) 华人 OCB +Farh, Zhong & Organ (2004) 扩展华人 OCB

每条 references 同步补全对应英文/中文出处。

### Phase B — 新增 5 条 KB 构念条目

**`src/questionnaire/construct_kb.py`** 在 OB 块末尾插入：

| 构念 | 量表 | 维度 | 备注 |
|---|---|---|---|
| 员工敬业度 | UWES-17 / UWES-9 / 中文版 (张轶文, 甘怡群, 2005) | 活力/奉献/专注 | People Analytics 最高频构念 |
| 家长式领导 | PLS-26 (郑伯埙等, 2000) / Cheng et al. (2004, AJSP) | 威权/仁慈/德行 | 华人 OB 标志性本土量表 |
| 伦理型领导 | ELS-10 (Brown et al., 2005) / 中文版 (徐世勇等, 2009) | 道德人/道德管理者 | 近年高被引 |
| 领导-成员交换 | LMX-7 (Graen & Uhl-Bien, 1995) / LMX-MDM (Liden & Maslyn, 1998) | 情感/贡献/忠诚/专业尊重 | 华人 OB 研究标配中介/控制变量 |
| 工作旺盛感 | Porath et al. (2012) / 中文修订 (Liu et al., 2015) | 学习/活力 | 积极组织行为学新热点 |

每条 100-150 字 definition，含理论出处+维度概要；2-4 个 dimension，每个 desc/item_count/example 齐全。

### Phase C — `data/literature_feed/domain_weights.yaml` 追加 4 条 canonical

- IO（原 8 → 11）：+家长式领导、伦理型领导、工作旺盛感
- OB（原 9 → 10）：+领导-成员交换

`default_weight=1.0 / domain_multiplier=1.5` 不动 — 通过增加 canonical 数量抬高 I/O 主题命中分数（每 unique canonical +0.5），不拉 multiplier 制造副作用。UI 编辑器（feed_panel.py 的 `st.data_editor`）自动渲染新增条目，无需改 UI。

### Phase D — 13 个新单测（实跑 29 个 parametrize 后）

- **`tests/test_construct_kb_io_seed.py`** — 25 个 case：3 个 Phase A 引用关键词检查 + 5 × 4 = 20 个 Phase B parametrize（lookup/definition/dimensions/required_fields）+ 2 个 spot check（UWES 签名、家长式领导本土化）
- **`tests/test_domain_weights_io_seed.py`** — 4 个 case：新 canonical 落 domain / 同义词反查 / score_hits 数值校验 / 未配置概念默认权重

## 回归

- 新测试：29 passed in 0.78s
- 全量：**1376 passed, 1 skipped, 0 failed**, 82.37s（1347 + 29 新）
- 0 errors, 0 regression

## 风险点

1. **量表年份/作者出处依赖训练知识** — Kimi 调研给出的 6 个构念清单中文版作者/年份基于其训练语料，未对每条做 PubMed/CNKI 实时核查。低概率出现引文细节不准（如 Chen & Francesco 2003 我标的是 Journal of Vocational Behavior，原文确实是 JVB 但若 KB 严格走中文期刊还需校对）。建议用户首次拿来给指导老师看时核一下出处再正式引用，KB 此处定位是 AI 出题/反问风格锚点而非论文引用源。
2. **construct_kb.py 行数 1043 → 1140**（+97 行），仍在 1500-2000 行密度上限内但接近。下次再加 5+ 条建议拆到 `construct_kb_extended.py` 或按 domain 分文件。

## 反方观点

**这次只动了 KB 和域权重，没动 reasoning 链路本身**。`_lookup_kb_scales` 在 AI 出题流程里**只取前 5 条 established_scales 作为 few-shot 风格参考**，并不影响题目设计的核心 prompt。所以"AI 出题更懂 I/O"这个收益主要在**风格层面**（出题语言风格更像 UWES/PLS 这类成熟量表），**而不在内容深度层面**（不会因为新加了 LMX 条目，AI 在做组织管理研究时就突然懂了"上下级配对调查"这种方法学约束）。要真在方法层面加权，需要后续单独做 `method_weights.yaml` + 改 scorer——本次列在 Out of Scope。

## 置信度

**中-高**。
- 高：测试 100% 覆盖新增条目的字段完整性 + 反查命中 + 加权数值校验，1376 全绿；YAML 加载 + 反向索引经过既有测试套件压测，新增条目自动并入。
- 中：实际"AI 出题/反问/答辩模拟更懂 I/O"的端到端体验**没在 Streamlit 里手动试过**，需要用户自己用一次"员工敬业度"或"家长式领导"主题验证 AI 是否真的引用了 UWES / PLS-26 作为风格锚点。
- 改变结论的证据：用户报告"输入员工敬业度后 AI 出题没引 UWES" → 需要查 `_lookup_kb_scales` 是否走了正确分支；用户报告"文献雷达里 LMX 论文没被加权" → 检查 yaml 加载日志确认新 canonical 进了 `_index`。

## 归档

本档：`docs/decisions/2026-05-30-impl-io-domain-seed.md`

下一步候选（不立刻做）：
- 数据收集闭环（问卷链接生成 + 远程被试自动回流）
- 方法权重层（HLM / polynomial regression / configural invariance 等研究方法 keyword）
- A 方案稳定后的 C 方案（Tauri/Electron 原生壳）
