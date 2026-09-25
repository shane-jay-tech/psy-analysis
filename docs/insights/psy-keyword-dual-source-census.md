# psy 关键词双源 census：`parser/keyword_dict`（检验触发词）vs `questionnaire/construct_kb.CONSTRUCT_KEYWORDS`（构念库）

> 班次 `qoder-executor-20260925-0800-psy57`（只读位）· 2026-09-25 08:3x · 单号 `s924-67` · 基线 commit `928e62e`（`git log -1` 现取，本班开工 08:19:54）
> **只读 census**：零代码改动、零写库、零 IO、**零 LLM**（所有入口 `llm_config=None` / `use_llm=False`）。
> 红线自持：本档**不判任何统计数值结论**（触发词/构念在心理测量学上是否恰当一概不评），只数规模、口径与门禁覆盖。

---

## 一、锚点复核（卷宗三锚 **0/3 漂移**）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
ls=open('src/parser/keyword_dict.py',encoding='utf-8').read().splitlines()
t=open('tests/test_keyword_dict.py',encoding='utf-8').read().splitlines()
r=open('src/questionnaire/intent_recognizer.py',encoding='utf-8').read().splitlines()
print('keyword_dict.py',6,repr(ls[5]))
print('test_keyword_dict.py',49,repr(t[48]))
print('   同件 :50',repr(t[49]))
print('intent_recognizer.py',69,repr(r[68]))
print('lines:',len(ls),len(t),len(r))
"
keyword_dict.py 6 'TEST_KEYWORDS = {'
test_keyword_dict.py 49 '    assert len(k.TEST_KEYWORDS) == 33'
   同件 :50 '    assert len(k.STOPWORDS) == 79'
intent_recognizer.py 69 '    基于 jieba 分词 + 构念关键词库的快速匹配。'
lines: 289 102 552
```
第二词源的真实表位在 `src/questionnaire/construct_kb.py:1105 CONSTRUCT_KEYWORDS = {`（同件 `:13 CONSTRUCTS = {`、`:1163 DOMAIN_KEYWORDS = {`，模块 1,199 行 ⇒ `tests/test_construct_kb_census.py:4` 自述的"模块 1199 行数据"**0 漂移**）。

⚠ **本班新踩工具坑（错法读数）**：`rg -n -e 'KeywordIntentStrategy' -e 'IntentRecognizer(' ...` →
`rg: regex parse error: ... error: unclosed group`，**该命令一条结果都不出**；若不查 rc（当时接了 `| head`，rc 被 head 吃掉）就会读成"仓内没人构造这个类"。
正解：含字面括号的式子用 `-F`（固定串）轨。改跑 `-F` 后同一会话立即命中 17 处。

---

## 二、两源规模 census（复跑：`PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe tmp/qoder-executor-20260925-0800-psy57/probe67.py`，rc=0）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 PYTHONPATH=. \
  .venv/Scripts/python.exe tmp/qoder-executor-20260925-0800-psy57/probe67.py
```

### 2.1 源 A：`src/parser/keyword_dict.py`（289 行，3 张顶层表）

| 量 | 实测 | 在册门禁 |
|---|---|---|
| `TEST_KEYWORDS` 组数 | **33** | `test_keyword_dict.py:49` 精确等值 ✅ |
| 触发词总数 / 去重后 | **277 / 273** | ❌ **无任何测试数这个数**（只钉组数 33 与键序） |
| 组内重复触发词 | **0 组**（`{}`） | — |
| 跨组共享触发词 | **4 词各属 2 组**：`交互效应`{two_way_anova, moderation}、`分层回归`{multiple_regression, hierarchical_regression}、`控制变量`{ancova, partial_corr}、`重复测量`{paired_ttest, repeated_anova} | ❌ 未钉 |
| 每组触发词规模 | min 4 / max 19 | ❌ 未钉 |
| `requires` 为空的组 | **1/33**：`descriptive` | `:58-60` 只钉"两字段齐＋triggers 非空"，不钉 requires 非空 |
| `STOPWORDS` | **79** | `test_keyword_dict.py:50` 精确等值 ✅ |
| `VARIABLE_ROLE_KEYWORDS` | `{dependent:12, independent:5, grouping:4}`（键序钉在 `:51`） | 键序 ✅、规模 ❌ |
| **触发词 ∩ 停用词** | **1 词：`比较`**（它**只**是 `independent_ttest` 的触发词） | ❌ 未钉 ⇒ 见 §四 D1 |
| 触发词能否被自家 `tokenize()` 原样取回 | **166 / 273 不能**（61%） | ❌ 未测过 |

`A_triggers_not_self_tokenizing` 样本（逐字，实为"精确 +1 分支基本不可达"的清单）：
`block回归→[block,回归]`、`bootstrap中介→[bootstrap,中介]`、`logistic回归→[logistic,回归]`、`mann-whitney→[mann,-,whitney]`、`mixed anova→[mixed,anova]`、`split-half→[split,-,half]`、`welch方差分析→[welch,方差分析]`、`α信度→[信度]`、`χ²→[]`。

### 2.2 源 B：`construct_kb.py::CONSTRUCT_KEYWORDS`（Layer 1 词源）

| 量 | 实测 | 在册门禁 |
|---|---|---|
| 组数（构念数） | **51** | ❌ **`len(CONSTRUCT_KEYWORDS)` 在 tests 面零命中**（见 §三命令） |
| 关键词总数 / 去重后 | **242 / 228** | ❌ 无 |
| 组内重复 | 0 | — |
| 跨构念重复词 | **14 词**（`紧张`、`社交焦虑`、`考试焦虑`、`幸福感`、`倦怠`、`倦怠感`、`工作倦怠`、`职业倦怠`、`耗竭`、`敬业度`、`工作投入`、`归属感`、`助人行为`、`情绪理解`） | ❌ 无 |
| 每组规模 | min 3 / max 7 | ❌ 无 |
| 键集 vs `CONSTRUCTS` 键集 | **严格 1:1**（`B_keys_not_in_CONSTRUCTS=[]`、`CONSTRUCTS_without_keyword_entry=[]`）⇒ "51 构念派生口径"实测成立 | `CONSTRUCTS` 侧有精确 census（`:26 len==51`、DIM_TOTAL 155、ITEM_COUNT_TOTAL 732、SCALE_TOTAL 98、REFERENCE_TOTAL 80），**关键词表侧零** |
| `EXTENDED_CONSTRUCTS` | **0 条**（`construct_kb_extended.py` 仅 7 行，空占位有专钉件 `test_construct_kb_extended_placeholder.py`）⇒ 现网 B 源是纯静态 51，无"自主学习追加" | ✅ 占位形状钉住 |
| `DOMAIN_KEYWORDS` | 7 组 / 115 词 | 只有 **`test_questionnaire_design.py:97 assert len(DOMAIN_KEYWORDS) >= 5`（单边下限，非总数门禁）** |
| 含空格的英文关键词 | **6 个、覆盖 5 个构念**（员工敬业度／伦理型领导／领导-成员交换／工作旺盛感／离职意愿）；ASCII 关键词共 15 | ❌ 未钉，且它是 §四 D6 的暴露面 |

### 2.3 两源重叠

`A 触发词 ∩ B 关键词 = ∅`（逐字实测 `A_intersect_B_words=[]`）⇒ 两词库**零词汇交集**：不会互相覆盖，但也**没有任何一条同步机制**（改名/加词互不可见）。

---

## 三、完成标准②：`intent_recognizer` 侧 census 缺口 —— **结论明确：缺口成立**

```
$ cd /d/code/psy-analysis && rg --no-heading -n -F -e 'len(CONSTRUCT_KEYWORDS)' -e 'len(k.CONSTRUCT' tests > tmp/qoder-executor-20260925-0800-psy57/gate_gap.txt 2>&1; echo "rc=$?"; wc -c < tmp/qoder-executor-20260925-0800-psy57/gate_gap.txt
rc=1
0
```
⇒ **全 `tests/` 面无人断言 `CONSTRUCT_KEYWORDS` 的规模**（`rc=1` ＋ 产物 0 字节，两轨同点）。
该表在测试里只以**成员/包含**形态被引用（全部逐字命中）：

```
$ cd /d/code/psy-analysis && rg --no-heading -n -F -e 'CONSTRUCT_KEYWORDS' -e 'DOMAIN_KEYWORDS' tests
tests\test_demo_datasets_hr.py:266:    assert "工作满意度" in CONSTRUCT_KEYWORDS
tests\test_demo_datasets_hr.py:267:    assert "离职意愿" in CONSTRUCT_KEYWORDS
tests\test_demo_datasets_hr.py:268:    org_kws = DOMAIN_KEYWORDS["组织行为"]
tests\test_io_construct_keyword_index.py:38:        assert name in CONSTRUCT_KEYWORDS, (...)   # 5 条 HR 构念逐点名
tests\test_questionnaire_design.py:97:        assert len(DOMAIN_KEYWORDS) >= 5
（全式实测 **21 行**、分布 3 份件：`test_io_construct_keyword_index.py` 14／`test_demo_datasets_hr.py` 4／`test_questionnaire_design.py` 3；上列 5 行为代表，**其余 16 行同为成员式/包含式断言或 docstring 引用，无一条等值总数断言**）
```
⇒ 该式实测：`len(CONSTRUCT_KEYWORDS)` 零命中（上面 rc=1）；`CONSTRUCT_KEYWORDS|DOMAIN_KEYWORDS` 21 行命中**全部是成员式/包含式断言或 docstring 引用，无一条等值总数**。
⇒ **B 侧的"总数门禁"不存在；存在的是 51 构念（`CONSTRUCTS`）的精确普查门禁 ＋ 5 条 HR 新增构念的点名锚。** 对照 A 侧有 `33`/`79` 两个 exact 数 —— 这就是"双源两口径"：**A 侧按表钉总数，B 侧按构念集钉形状、关键词表本身裸奔。**

基线（按件点名，未用宽 `-k`）：
```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m pytest \
  tests/test_keyword_dict.py tests/test_construct_kb_census.py tests/test_io_construct_keyword_index.py tests/test_intent_recognizer.py -q
rc=0
42 passed in 1.15s
```

---

## 四、同一句「焦虑 问卷 差异」两侧各命中什么（逐字，含本班自纠）

### ⚠ 4.0 错法读数 vs 正解读数（先记账，免得后人再踩）

| 口径 | `words` 实参 | B 侧 Layer 1 命中 |
|---|---|---|
| **错法（本班第一版探针）**：直接 `jieba.lcut(SENT)` | `['焦虑', ' ', '问卷', ' ', '差异']` | **7 个构念**：焦虑 0.95、**员工敬业度 0.37**、考试焦虑 0.24、**领导-成员交换 0.21**、**伦理型领导 0.19**、**离职意愿 0.19**、**工作旺盛感 0.18** |
| **正解（生产口径）**：`design_engine.py:83-84` 与 `intent_recognizer.py:303-305` 都是 `[w.strip() for w in jieba.cut(q) if len(w.strip())>=2]` | `['焦虑','问卷','差异']` | **2 个构念**：焦虑 0.95、考试焦虑 0.24（`layers_used=['keyword']`） |

**机理（逐字定位，不是猜）**：`intent_recognizer.py:101` 的 `elif any(kw in w or w in kw for w in words)` 里 **`w in kw` 是反向包含** —— 空格 token `" "` 是全部**含空格英文关键词**的子串：
```
员工敬业度 -> [('work engagement',' ',1.75), ('employee engagement',' ',1.95)]
离职意愿   -> [('turnover intention',' ',1.9)]   伦理型领导 -> [('ethical leadership',' ',1.9)]
工作旺盛感 -> [('thriving at work',' ',1.8)]      领导-成员交换 -> [('leader-member exchange',' ',2.1)]
```
极端验证：只喂一个空格词 `s.recognize(SENT, [' '])` ⇒ 命中 `['焦虑','员工敬业度','领导-成员交换','伦理型领导','离职意愿','工作旺盛感']`。
⇒ **现网不受影响**（三个生产入口都做了 `len>=2` 过滤），但这是一条**契约风险**：谁哪天直接把 `jieba.lcut` 的结果喂 `KeywordIntentStrategy` / `chain.recognize(q, words=…)`（`words` 参数是公开的，`:300`），就会得到 5 个纯空格造成的假构念，且置信度最高到 **0.37**——已超过 `design_engine.py:211` 链结果的 0.3 采纳线。**这是 census 里唯一"数值敏感"的条目，本班只报工程口径，不据此改任何阈值。**

### 4.1 正解读数（逐字入档，生产口径）

| 侧 | 入口 | 读数 |
|---|---|---|
| A（分词） | `src.parser.tokenizer.tokenize(SENT)` | `['焦虑','问卷','差异']`（与 B 生产口径 **同集合**） |
| A（打分） | `src.parser.intent_resolver._score_test_types(tokens, {})` | top：`independent_ttest score=1.9 matched=['差异']`；次：`one_way_anova 0.3`、`manova 0.3`；**33 组里 30 组 0 分** |
| A（兼容入口，同表第二实现） | `src.questionnaire.intent_recognizer.recognize_intent(df, SENT, col_info, use_llm=False)` | `best_match='independent_ttest'`、`confidence=0.67`、`matched_keywords=['差异']`、`is_ambiguous=False`；候选 top5 分数：`independent_ttest 2.0`、`descriptive 1.0`、`one_way_anova 1.0`、`pearson_corr 1.0`、`spearman_corr 1.0`（后四个 `matched_keywords` 为空 ⇒ 纯列类型加分层） |
| A（端到端） | `src.parser.intent_resolver.resolve(df, SENT, col_info=col_info)` | **抛 `TypeError: string indices must be integers, not 'str'`**（本班传的是 `{列名: 类型}` 形状；该入口对 `col_info` 的实际期望形状未在本单 census 范围内坐实 ⇒ 记为"待复核"，不当结论用） |
| B（Layer 1） | `KeywordIntentStrategy(CONSTRUCTS, CONSTRUCT_KEYWORDS, {}).recognize(SENT, ['焦虑','问卷','差异'])` | `[('焦虑', 0.95, 'gold_standard', '匹配得分 9.7'), ('考试焦虑', 0.24, 'gold_standard', '匹配得分 2.4')]` |
| B（Layer 2） | `TFIDFIntentStrategy(...).recognize(SENT, words)` | `[('焦虑', 0.309, 'tfidf')]` |
| B（整链） | `create_default_chain(constructs, keywords, extended={}, llm_config=None).recognize(SENT)` | `top=焦虑 0.95`、`n_candidates=2`、`is_ambiguous=False`、`layers_used=['keyword']`（**TF-IDF 层未执行**：`:321-322` keyword 层达阈即 `break`） |
| B（`design_engine` 兜底） | `_match_construct(words, SENT, use_chain=False)` | `construct=焦虑`、`{'exact': True, 'reason': '…匹配到已有构念知识库（内置知识库）。'}` |
| B（`design_engine` 走链） | `_match_construct(words, SENT, use_chain=True)` | `construct=焦虑`、`{'exact': True, 'confidence': 0.95, 'source': 'gold_standard', 'reason': '…匹配得分 9.7（关键词匹配引擎）（内置知识库）。'}` |
| 变体（无空格句 `焦虑问卷差异`） | 同上 A/B | A tokens/score 不变（`1.9`）；**B Layer1 命中仍 2 个**（`['焦虑','考试焦虑']`）⇒ 空格与否在生产口径下不影响 B |

**同一例句的双源结论对照**：A 侧答"**做什么检验**"（`independent_ttest`），B 侧答"**是什么构念**"（`焦虑`）——两源**输出面正交、零词交集、零同步**，本单卷宗的"重叠"担忧实测为**无重叠**（这正是问题：加词时没人知道要同步两处）。

### 4.2 口径差的真实位置（不是空格，是停用词）

第三句实测（同一句、两口径 token 集）：
```
q='比较两组学生的社交焦虑差异 3 分'
A 口径 tokens = ['两组','学生','社交','焦虑','差异']
B 生产 words  = ['比较','两组','学生','社交','焦虑','差异']
集合差 A-B = []   B-A = ['比较']
```
⇒ **两侧真正不一致的是「停用词面」**：`比较` 被 A 侧 `tokenizer.py:50 if w in STOPWORDS` 滤掉，B 侧无停用词表、原样保留。

---

## 五、census 抓出的 6 条工程事实（可裁决项，不含数值判断）

| # | 事实 | 实测 | 影响面 |
|---|---|---|---|
| **D1** | **A 源有一枚被自家停用词吃掉的触发词**：`比较` 只属于 `independent_ttest`，但同在 `STOPWORDS(79)` | `比较两组学生的差异`：实际 `independent_ttest 2.9 matched=['差异','两组']`；假设"比较"未被滤：`3.9 matched=['比较','差异','两组']`，**且候选集多出 `one_sample_ttest`（0.3）** | 精确 +1 分支对该词**永久不可达**；不是理论问题，是已发生的分值与候选集差异 |
| **D2** | A 源 61%（166/273）触发词无法被自家 `tokenize()` 原样还原（英文/符号/多字组合） | §二清单 | `_score_test_types:58` 的 `if trigger in tokens` 精确分支对这些词形同虚设，全靠 0.5/0.3 两条降级路 |
| **D3** | **同一张 A 表有两套打分实现且权重不同** | `intent_resolver._score_test_types:57-73`：精确 **1**／部分 **0.5**／模糊 **0.3**（`ratio>0.8`，含 `t in trigger` 反向）；`intent_recognizer.recognize_intent:473-485`：精确 **2.0**／部分 **1.0**／模糊 **0.5**（`ratio>0.75`，**无反向包含**）⇒ 同句同词读回 **1.9 vs 2.0** | 且 `recognize_intent` **在 src/ 与 app.py 零消费者**（实测 `rg -F 'recognize_intent'` 只命中自身定义 ＋ `tests/test_intent_recognizer.py` 两条）⇒ 它是**无人调用的平行实现**，改 A 表时极易只改一边 |
| **D4** | **B 源 Layer 1 也是两套逐字重复实现** | `intent_recognizer.py:94-104` 与 `design_engine.py:241-250` 权重完全相同（`3+0.5len / 2+0.1len / 1+0.05len`），差异只在链版有 `max_possible=10`／`<0.15` 丢弃／`source` 标签，`design_engine` 版另有第二轮"偏好更长构念名"（`:252-255`）⇒ 类 docstring `:71` 自称"继承 …核心逻辑"，实况是**复制** | 兜底路径与链路径可给出不同结论（`use_chain=True/False` 两条实测本例句一致，但阈值面 `:211 confidence>=0.3` 与 `:222 >=0.5` 只在走链时生效） |
| **D5** | 两源零词交集、零同步机制 | `A ∩ B = []`；`B` 的键集与 `CONSTRUCTS` 严格 1:1（双向差集为空） | 加构念词不影响检验触发，反之亦然；但也意味着"用户新词"要在两处各写一遍 |
| **D6** | 反向包含匹配（`w in kw`）＋ ASCII/含空格关键词 ＝ 空格 token 可凭空造出 0.37 置信度构念 | §四 4.0 逐字（现网三入口已 `len>=2` 过滤 ⇒ **当前不发作**） | 属"公开参数缺校验"的契约风险，不是已实现的缺陷；**列此仅供裁"要不要在 `KeywordIntentStrategy.recognize` 入口自过滤"，本班未改** |

---

## 六、落档口径建议（两案＋推荐）

### 案 甲：给 B 源上"和 A 源同款"的精确总数门禁

新增（或扩进 `tests/test_construct_kb_census.py`，同文件同纪律"只数形状不评内容"）：
`len(CONSTRUCT_KEYWORDS) == 51`、`总数 == 242`、`去重 == 228`、`跨构念重复 == 上述 14 词集合`、`每组 ∈ [3,7]`、`键集与 CONSTRUCTS 严格 1:1（双向差集为空）`。
- 优点：与 A 侧 `33/79` 对称，加词必红，红名即可归因；`test_construct_kb_census.py` 已是"精确计数门禁"的在册范式（`:26/:41-45/:52-58`）。
- 代价：**每次新增构念词都要改两处测试数**（该件 docstring `:9` 已自认"新增/删改构念会让这些数字变红，这是刻意的门禁"）；B 侧有 `EXTENDED_CONSTRUCTS` 这个未来会长的口子（现 0 条），把 51 钉死会连带钉住扩展位。

### 案 乙：不钉绝对数，钉"**派生口径**"

B 源是 `CONSTRUCTS` 的派生物 ⇒ 只钉**不变量**：①键集 1:1（双向差集为空）；②每组关键词数 ∈ [3,7] 且非空、无组内重复；③跨构念重复词集合必须等于白名单（等于当前 14 词，加词需显式登记）；④ASCII 词必须含空格者才被 `len>=2` 口径保护（钉 D6 的暴露面数量：5 构念/6 词）。
- 优点：新增构念时 51→52 不用改数字，只改白名单；`EXTENDED_CONSTRUCTS` 从 0 变 N 时仍成立。
- 代价：不钉总数 ⇒ "总数被误删一半"这类红要靠不变量间接暴露。

### 推荐（分层，与 A 侧对称性兼顾）

1. **先修 D1**（这是 census 里唯一的现网行为差异）：把 `比较` 从 `STOPWORDS` 移除，或在 `tokenizer.py` 对 `TEST_KEYWORDS` 触发词做豁免（`if w in STOPWORDS and w not in _TRIGGER_SET`）。**二者都会改现网分值**（实测 2.9→3.9、候选集变化）⇒ 属**改判据口径**，按纪律档 §五.4/§十一.3 **本班不自行落地**，交主班进待人工台账裁。
2. **B 源采案 乙 的不变量门禁 ＋ 一条绝对数"下限哨"**（`len==51` 与 `CONSTRUCTS` 同源，写成 `assert len(CONSTRUCT_KEYWORDS) == len(CONSTRUCTS)` 而非硬编码 51 ⇒ 加构念时零维护成本，删词时仍红）。A 源侧顺手补 `277/273` 与 4 枚跨组共享词的白名单（当前完全裸奔）。
3. **消 D3/D4 的平行实现**：`recognize_intent`（零生产消费者）与 `design_engine._match_construct` 的兜底复制体，各列为"收敛到单一 scorer"的候选；**本档只登记，不动码**。
4. **D6 只登记不改**：改不改 `recognize` 入口自过滤，涉及阈值语义（0.37 与 `:211` 的 0.3 采纳线），按红线属"统计/阈值数值结论"边界 ⇒ **只出只读报告**，处置交主班。

---

## 七、完成标准对照 ＋ 只读自证

| # | 标准 | 实测 |
|---|---|---|
| ① | 两源实测规模表（33/79 与构念库实测数**内联复跑命令**） | §二（A：33 组／277 触发词／273 去重／79 停用词／角色 12-5-4；B：51 组／242 词／228 去重／域 7 组 115 词／EXTENDED 0），复跑命令内联在 §二 与 §一 |
| ② | `intent_recognizer` 侧 census 缺口有无，**结论明确＋附 rg 证据** | §三：`rg -F 'len(CONSTRUCT_KEYWORDS)' tests` → **rc=1、0 字节** ⇒ **缺口成立**；同时给出该表在 tests 面的全部真实引用（成员式）与 `DOMAIN_KEYWORDS` 仅有 `>=5` 单边下限 |
| ③ | 同一例句双源命中输出逐字入档 | §四 4.1（含 §五 D1/D3 的同句不同分），并附 4.0 自纠（错法 7 命中 vs 正解 2 命中） |
| ④ | 零代码改动 | 见下 |

```
$ cd /d/code/psy-analysis && git diff --numstat -- src/parser/keyword_dict.py src/parser/tokenizer.py src/parser/intent_resolver.py src/questionnaire/intent_recognizer.py src/questionnaire/design_engine.py src/questionnaire/construct_kb.py src/questionnaire/construct_kb_extended.py tests/test_keyword_dict.py tests/test_construct_kb_census.py tests/test_io_construct_keyword_index.py tests/test_intent_recognizer.py
（无输出 rc=0）
```
- 本班唯一入库产物＝本档（`docs/insights/psy-keyword-dual-source-census.md`）；探针与输出落 `tmp/qoder-executor-20260925-0800-psy57/{probe67.py,probe67_out.json,probe67.log,gate67.log,gate_gap.txt,kb_kw_in_tests.txt}`（gitignored）。
- 全程 `llm_config=None` / `use_llm=False` ⇒ **零 LLM 调用、零网络**；未启动 app、未跑全量套件、`data/literature_feed` 未打开；未触碰任何在册在途脏件（docx/字体族/exporters 族、`app.py`）。
