# psy 检验方法「名称／文案」多表盘点：`get_test_name_zh` vs `app_pages_text` 单一来源裁决材料

- 班次：`qoder-executor-20260925-0220-psy36`（信箱单 `s924-11`，主班 `qoder-main-drain-20260924-2341` 代提交）
- 取数现场：`D:\code\psy-analysis`，HEAD `cf3eaa4`（`git log -1 --format=%h`，2026-09-25T02:5x 现取）
- 性质：**只读盘点**。本文只出「清单 + 建议」，🔴 未删任何表项、未改任何文案、未动任何生产码／测试／配置。
- 上游卷宗：`zcode-bridge/done/s923-07.result.md:58` 待裁决三问之③ —— 「`get_test_name_zh` 删除前，`src/ui/app_pages_text.py:169-197`（zh/en 另一套硬编码检验方法文案）是否并入 i18n 单一来源」。
- 统计内容边界：文中「文案声称 vs 代码默认值」的差异**只登记字面事实**，不判定哪个统计口径正确（属统计内容裁决，超执行手授权）。

## 〇、结论先说

1. 这不是「两张表」，磁盘实况是 **10 张以检验方法 id 为键（或按方法分叉）的文案表**，共 4 个层级：短标签 / 长句说明 / 别名 / 统计量符号。`get_test_name_zh` 只是其中最短的一层。
2. 键面：`TEST_NAMES_ZH` 48 键 ∩ `i18n.TRANSLATIONS[zh]` 106 键 = **24 键**；另有 **24 键只在 settings 表里**（`get_test_name_zh` 对这 24 键**原样吐回蛇形键名**）。
3. 值面：在「≥2 张标签表同时持有」的 39 个键里，**22 键存在字面漂移**（含全角/半角括号、加不加空格、加不加括注、`层次`vs`分层` 四种形态）。
4. 并轨三方案的最小牵动面实测为 **A=4 生产件+1 测试件／B=2~3 生产件+1 测试件／C=1 新测试件+0 生产件**；三条路都要撞 `tests/test_i18n.py:112` 的 `len(TRANSLATIONS["zh"]) == 106` 精确计数钉桩，A/B 还要动他班在途的 `app.py`。
5. 建议见第六节：先 C（加断言＋豁免清单钉现状），措辞裁决另开人工闸；不建议本波做 A/B。

## 一、表清单（10 张，锚点用唯一文本，行号是本次快照）

现取命令（AST 轨，行号无关；**已复验**，读数见「键数」列）：

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import ast as A
for f,name in [('config/settings.py','TEST_NAMES_ZH'),('src/utils/i18n.py','TRANSLATIONS')]:
    t=A.parse(open(f,encoding='utf-8').read())
    for n in t.body:
        tgt=n.targets if isinstance(n,A.Assign) else [getattr(n,'target',None)]
        if any(getattr(x,'id','')==name for x in tgt):
            v=n.value
            print(name, [(k.value,len(dd.keys)) for k,dd in zip(v.keys,v.values)
                         if isinstance(k,A.Constant) and isinstance(dd,A.Dict)]
                  if name=='TRANSLATIONS' else len(v.keys))
"      # 读数：TEST_NAMES_ZH 48 / TRANSLATIONS [('zh', 106), ('en', 106)]

PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import ast as A
t=A.parse(open('src/ui/app_pages_text.py',encoding='utf-8').read())
fn=next(x for x in A.walk(t) if isinstance(x,A.FunctionDef) and x.name=='_generate_method_description')
for i in A.walk(fn):
    if isinstance(i,A.If) and isinstance(i.test,A.Compare) and getattr(i.test.comparators[0],'value',None)=='en':
        for tag,body in (('en',i.body),('zh',i.orelse)):
            for s2 in body:
                if isinstance(s2,A.Assign) and getattr(s2.targets[0],'id','')=='descriptions':
                    print('desc_'+tag, len(s2.value.keys))
"      # 读数：desc_en 12 / desc_zh 12
```

| # | 表 | 锚点（文件:行，HEAD `cf3eaa4` 快照） | 键数 | 装的是什么 |
|---|---|---|---|---|
| T1 | `config/settings.py::TEST_NAMES_ZH` | `config/settings.py:11-65` | 48 | 中文短标签 |
| T2 | `src/utils/i18n.py::TRANSLATIONS["zh"]` | `src/utils/i18n.py:14-129` | 106（其中 24 个是方法键） | 中文短标签＋符号 |
| T3 | `src/utils/i18n.py::TRANSLATIONS["en"]` | `src/utils/i18n.py:130-245` | 106（同上 24） | 英文短标签 |
| T4 | `app_pages_text._generate_method_description` 的 `descriptions`（en 分支） | `src/ui/app_pages_text.py:168-192` | 12 | 英文长句方法说明 |
| T5 | 同上的 `descriptions`（zh 分支，`else`） | `src/ui/app_pages_text.py:195-208` | 12 | 中文长句方法说明 |
| T6 | `undergrad_wizard` 的 `method_templates` | `src/ui/undergrad_wizard.py:3324-3338` | 13 | 「方法描述模板」下拉标签 |
| T7 | `quick_entries._render_reliability_form` 的 `method_labels` | `src/ui/quick_entries.py:311-320` | 8 | 信度族标签 |
| T8 | `quick_entries._render_validity_form` 的 `method_labels` | `src/ui/quick_entries.py:428-435` | 6 | 效度族标签 |
| T9 | `interpretation._interpret_validity` 的 `title_map` | `src/output/interpretation.py:457-464` | 6 | 效度族结果标题 |
| T10 | `template_center_panel._translate_method` 的 `mapping` | `src/ui/template_center_panel.py:284-288` | 3 | 模板中心标签 |

配套（非 dict，因此**任何「按 dict 普查」的轨都会漏它**）：

| # | 位置 | 键数/条数 | 说明 |
|---|---|---|---|
| T11 | `src/analysis/method_recommender.py` 的 `primary_method_zh=` 与 `primary_zh=` | 13 个构造点 = 9 条 keyword 字面量 + 4 条三元（含 8 个字面量）⇒ **17 条硬编码中文名** | 双轨读数见第五节 |
| T12 | `undergrad_wizard` 的 `alias_map` | `src/ui/undergrad_wizard.py:3647-3660`，12 键 | 搜索别名，非展示名，但键集与 T6 重叠 |

## 二、键差（完成标准①：键数与交集数，每个数配复跑命令）

### 2.1 双读数（正则轨 = 缩进＋键形状；AST 轨 = 字面 dict）

| 表 | 正则轨 | AST 轨 | 差额 |
|---|---|---|---|
| T1 `TEST_NAMES_ZH` | 48 | 48 | 0 |
| T2 `TRANSLATIONS[zh]` | 106 | 106 | 0 |
| T3 `TRANSLATIONS[en]` | 106 | 106 | 0 |
| T4 `desc_en` | 12 | 12 | 0 |
| T5 `desc_zh` | 12 | 12 | 0 |

正则轨复跑（`sed` 区间是本次快照，行号会漂；改锚看第一节表的「锚点」列文本）：

```
sed -n '11,65p'   config/settings.py        | rg -c '^\s{4}"[a-z][a-z0-9_]*"\s*:'   # 48
sed -n '14,129p'  src/utils/i18n.py         | rg -c '^\s{8}"[a-z][a-z0-9_]*"\s*:'   # 106
sed -n '130,245p' src/utils/i18n.py         | rg -c '^\s{8}"[a-z][a-z0-9_]*"\s*:'   # 106
sed -n '168,192p' src/ui/app_pages_text.py  | rg -c '^\s{12}"[a-z][a-z0-9_]*"\s*:'  # 12
sed -n '195,208p' src/ui/app_pages_text.py  | rg -c '^\s{12}"[a-z][a-z0-9_]*"\s*:'  # 12
```

AST 轨复跑：见第一节的同型命令（`desc_en 12`／`desc_zh 12` 那条即 T4/T5 的 AST 读数），期望 `TEST_NAMES_ZH 48`、`TRANSLATIONS [('zh', 106), ('en', 106)]`。

### 2.2 交集与独有

| 判据 | 读数 | 复跑命令 |
|---|---|---|
| T1 ∩ T2(zh) | **24** | 见下方 `R2` |
| T1 − T2（只在 settings，i18n 查不到） | **24** | 同 `R2` |
| T2 − T1（i18n 独有，含 `chi_square`/`reliability` 等 82 键） | 82 | 同 `R2` |
| T4 键集 vs T5 键集 | **完全相同**（`only_en=[]`、`only_zh=[]`） | 见 `R3` |
| (T4 ∪ T5) ∩ T1 | **12**（文案表 12 键全在标签表里） | 见 `R3+` |
| T1 − (T4 ∪ T5)（有名字、无方法说明，走兜底句） | **36** | 见 `R3+` |
| T6 − T1（模板表有、标签表没有） | **1**：`chi_square` | 见 `R4` |
| T12 − T1 | **1**：`chi_square`（同上） | 见 `R4` |
| T2 里 `chi_square` 的值 | zh/en 均为 `"χ²"`（符号，不是名字） | 见 `R5` |
| T2 里 `reliability` | zh `"信度分析"`／en `"Reliability Analysis"`，**T1 无此键** | 见 `R5` |

```
# R2：T1/T2 键交并差（已复验）→ T1 48 T2zh 106 交 24 T1独有 24 T2独有 82
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import ast as A
t1=A.parse(open('config/settings.py',encoding='utf-8').read()); ti=A.parse(open('src/utils/i18n.py',encoding='utf-8').read())
N={k.value for n in t1.body if isinstance(n,A.Assign) and getattr(n.targets[0],'id','')=='TEST_NAMES_ZH' for k in n.value.keys}
for n in ti.body:
    if getattr(getattr(n,'target',None),'id','')=='TRANSLATIONS':
        Z={k.value for k in n.value.values[0].keys}
print('T1',len(N),'T2zh',len(Z),'交',len(N&Z),'T1独有',len(N-Z),'T2独有',len(Z-N)); print(sorted(N-Z))"

# R3：文案表 en/zh 键集（区间快照 168-208）→ 各 12 行、两份键集逐字相同
sed -n '168,192p' src/ui/app_pages_text.py | rg -c '^\s{12}"[a-z][a-z0-9_]*"\s*:'      # 12
sed -n '195,208p' src/ui/app_pages_text.py | rg -c '^\s{12}"[a-z][a-z0-9_]*"\s*:'      # 12
# ⚠ 不加 sed 区间直接扫整份文件会读 28 行：多出的 4 行是 `app_pages_text.py:124-127`
#    的 params dict（值是变量不是字符串），正则轨吃不下这个区别 ⇒ AST 轨读 12/12。

# R3+：文案表 12 键是否全在标签表里 → 交 12 / 有名字无说明 36 / desc 独有 []
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import ast as A
t1=A.parse(open('config/settings.py',encoding='utf-8').read())
N={k.value for n in t1.body if isinstance(n,A.Assign) and getattr(n.targets[0],'id','')=='TEST_NAMES_ZH' for k in n.value.keys}
ap=A.parse(open('src/ui/app_pages_text.py',encoding='utf-8').read())
fn=next(x for x in A.walk(ap) if isinstance(x,A.FunctionDef) and x.name=='_generate_method_description')
D=set()
for n in A.walk(fn):
    if isinstance(n,A.Assign) and getattr(n.targets[0],'id','')=='descriptions' and isinstance(n.value,A.Dict):
        D|={k.value for k in n.value.keys if isinstance(k,A.Constant)}
print('交',len(D&N),'有名字无说明',len(N-D),'desc 独有',sorted(D-N))"

# R4：模板表 13 键、`chi_square` 在末行 → 13 / 命中 1 行
sed -n '3324,3338p' src/ui/undergrad_wizard.py | rg -c '"[a-z_]+":'
sed -n '3324,3338p' src/ui/undergrad_wizard.py | rg -n 'chi_square'

# R5：i18n 里非标签表的方法键 → 54/170 是 `chi_square`，83/199 是 `reliability`
rg -n '^\s{8}"(chi_square|reliability)":' src/utils/i18n.py
```
⚠ `rg` 的模式里**不要放非 ASCII 字面**（如直接锚 `"χ²"`）：本机 Git Bash 传参会把它转成 GBK 字节，
`rg` 端表现为 **rc=1 的假零命中**（本次实测）⇒ 只锚 ASCII 键名，中文值用 python 直读。

**i18n 未命中即原样回蛇形键**（24 键清单，运行轨实测，非推断）：
`ai_item_review, ancova, ave, binary_logistic, cohens_kappa, composite_reliability, criterion_validity, cronbach_alpha, cvi, discriminant_fl, discriminant_htmt, fleiss_kappa, hlm, icc, known_groups_validity, manova, mcdonald_omega, mixed_anova, multinomial_logistic, ordinal_logistic, point_biserial, sem, split_half, test_retest`

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.')
from src.utils.i18n import get_test_name_zh
from config.settings import TEST_NAMES_ZH
m=[k for k in sorted(TEST_NAMES_ZH) if get_test_name_zh(k,'zh')==k]
print(len(m), m)"        # 读数：24 + 上面那份清单
```
（该命令会打 14 条 `missing ScriptRunContext` WARNING，是 `t()` 裸模式回落 `DEFAULT_LANG` 的正常噪声，不是失败。）

## 三、值漂移实例（完成标准②：≥3 处，逐字引用双侧）

### 3.1 T1 `settings.TEST_NAMES_ZH` vs T2 `i18n.TRANSLATIONS["zh"]` —— 5 处（同一函数族，谁赢取决于走哪个入口）

| 键 | settings（逐字） | i18n zh（逐字） | 行号 |
|---|---|---|---|
| `hierarchical_regression` | `"层次回归"` | `"分层回归"` | `config/settings.py:38` / `src/utils/i18n.py:77` |
| `pearson_corr` | `"Pearson相关"` | `"Pearson相关分析"` | `:19` / `:70` |
| `spearman_corr` | `"Spearman相关"` | `"Spearman相关分析"` | `:20` / `:71` |
| `efa` | `"探索性因素分析（EFA）"` | `"探索性因素分析"` | `:34` / `:81` |
| `cfa` | `"验证性因素分析（CFA）"` | `"验证性因素分析"` | `:35` / `:82` |

复跑：`rg -n '"(hierarchical_regression|pearson_corr|spearman_corr|efa|cfa)":' config/settings.py src/utils/i18n.py`（同一行号区间内 zh 在前 en 在后，i18n 会出两条，取 8 空格缩进那条）。

裁决相关性：**i18n 侧的措辞是被测试钉死的**——`tests/test_i18n.py:59` 钉 `("pearson_corr", "Pearson相关分析", "Pearson Correlation")`、`:64` 钉 `("hierarchical_regression", "分层回归", "Hierarchical Regression")`。⇒ 并轨时若采 settings 写法，这两条钉桩当场红。

### 3.2 跨标签表漂移（22 键，摘要＋三条逐字）

「≥2 张标签表同时持有」共 **39** 键，其中 **22** 键值不一致。复跑（已复验，输出 `multi 39 drift 22`）：

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import ast as A, json
def dicts(f, names):
    t=A.parse(open(f,encoding='utf-8').read()); out={}
    for n in A.walk(t):
        if isinstance(n,A.Assign) and any(getattr(x,'id','') in names for x in n.targets):
            key=next(getattr(x,'id') for x in n.targets if getattr(x,'id','') in names)
            if isinstance(n.value,A.Dict):
                out.setdefault(key,{}).update({k.value:v.value for k,v in zip(n.value.keys,n.value.values)
                                               if isinstance(k,A.Constant) and isinstance(v,A.Constant)})
    return out
tab={'T1':dicts('config/settings.py',{'TEST_NAMES_ZH'})['TEST_NAMES_ZH']}
ti=A.parse(open('src/utils/i18n.py',encoding='utf-8').read())
for n in ti.body:
    if getattr(getattr(n,'target',None),'id','')=='TRANSLATIONS':
        zh=n.value.values[0]; tab['T2']={k.value:v.value for k,v in zip(zh.keys,zh.values)}
for lbl,f,nm in [('T6','src/ui/undergrad_wizard.py',{'method_templates'}),('T7','src/ui/quick_entries.py',{'method_labels'}),
                 ('T9','src/output/interpretation.py',{'title_map'}),('T10','src/ui/template_center_panel.py',{'mapping'})]:
    d=dicts(f,nm); tab[lbl]=d[next(iter(d))]
keys=set().union(*[set(v) for v in tab.values()])
held=lambda k:[t for t in tab if k in tab[t]]
multi=[k for k in sorted(keys) if len(held(k))>1]
drift=[k for k in multi if len({tab[t][k] for t in held(k)})>1]
print('multi',len(multi),'drift',len(drift)); print(sorted(drift))
print(json.dumps({k:{t:tab[t][k] for t in held(k)} for k in drift},ensure_ascii=False,indent=1))"
```
（`T7` 两份 `method_labels` 同名，`dicts()` 会合并 ⇒ 信度 8 键＋效度 6 键，键不重叠，读数不受影响。）

三条最典型的逐字（含双侧行号）：

1. **`ave`——「抽量」还是「效度」，同一个键三种口径**
   - `config/settings.py:49` → `"平均方差抽取量（AVE）"`
   - `src/output/interpretation.py:459` → `"聚合效度（AVE）"`
   - `src/ui/quick_entries.py:431` → `"聚合效度 AVE（基于 CFA）"`
   复跑：`rg -n '"ave":' config/settings.py src/output/interpretation.py src/ui/quick_entries.py`
2. **`independent_ttest`——空格漂移**
   - `config/settings.py:13` / `src/utils/i18n.py:59` / `src/ui/undergrad_wizard.py:3325` → `"独立样本t检验"`
   - `src/ui/template_center_panel.py:286` → `"独立样本 t 检验"`
   - `src/ui/app_pages_text.py:196`（长句内）→ `"本研究使用独立样本 t 检验比较两组独立样本的均值差异。…"`
   复跑：`rg -n '"独立样本 ?t ?检验"' -e '独立样本t检验' config/settings.py src/utils/i18n.py src/ui/template_center_panel.py src/ui/app_pages_text.py`
3. **`cronbach_alpha`——音译名 vs 符号名**
   - `config/settings.py:25` → `"克隆巴赫α信度"`（i18n 两语**均无此键**）
   - `src/ui/quick_entries.py:312` → `"Cronbach's α（内部一致性）"`
   - `src/ui/undergrad_wizard.py:3335` → `"Cronbach's α信度分析"`
   - `src/analysis/method_recommender.py:273` → `primary_method_zh="Cronbach's α 信度分析"`
   复跑：`rg -n 'cronbach_alpha|Cronbach' config/settings.py src/ui/quick_entries.py src/ui/undergrad_wizard.py src/analysis/method_recommender.py | rg -n '"|='`

其余 19 键（同一命令的完整读数）：`cfa, chi_square, cohens_kappa, criterion_validity, cvi, discriminant_fl, discriminant_htmt, efa, fleiss_kappa, hierarchical_regression, icc, known_groups_validity, mediation, mcdonald_omega, one_way_anova, paired_ttest, pearson_corr, spearman_corr, split_half` + 下面 3 条 = 22。

### 3.3 T4/T5 文案表内部：同一个 `efa` 键，中英两侧写的是**两种不同的抽取法**

- `src/ui/app_pages_text.py:190`（en）：
  `"Exploratory Factor Analysis (EFA) was conducted using principal axis factoring with varimax rotation. "`
- `src/ui/app_pages_text.py:207`（zh）：
  `"使用探索性因素分析（主成分法 + 最大方差旋转）探索潜在因素结构。使用 KMO 和 Bartlett 检验确认数据适合性。因子保留使用 Kaiser 准则（特征值 > 1）。"`

⇒ en 说 PAF（主轴因子法）、zh 说主成分法（PCA），这是**同一函数同一次渲染里的双语互斥**，与并轨决策无关，属现状缺陷。复跑：
`rg -n '"efa":' src/ui/app_pages_text.py`

同域旁证（只登记，不判定）：`src/output/learning_card.py:783` 教用户「方法选『主轴因子法』」、`:798` 把「用主成分分析代替因子分析 — PCA不是真正的因子分析」列为常见错误；`src/analysis/factor_analysis.py:173` 亦建议「使用主轴因子法（principal axis）替代」。

### 3.4 文案声称 vs 代码默认值（3 条，只登记字面差异）

| 文案（逐字，双侧） | 代码默认（逐字） | 差额 |
|---|---|---|
| `app_pages_text.py:184-185` en `"Dunn's test with Bonferroni correction was used for post-hoc comparisons."`／`:204` zh `"事后比较使用 Dunn 检验 + Bonferroni 校正。"` | `src/analysis/nonparametric.py:174` `mc_method: str = "holm"`，`:181` 注释自述 `"holm" — Holm-Bonferroni 校正（默认，逐步下降法）`、`:182` `"bonferroni" — 传统 Bonferroni 校正` | 文案写 Bonferroni，默认参数是 `holm` |
| `:190-191` en `"Factor retention used Kaiser criterion (eigenvalue > 1)."`／`:207` zh `"因子保留使用 Kaiser 准则（特征值 > 1）"` | `src/analysis/factor_analysis.py:46` `n_factors: 因素数量（None则通过平行分析自动确定）`；`src/analysis/runner.py:760` `exploratory_factor_analysis(df, items)` 未传 `n_factors`、未传 `method`（默认 `"minres"`，`:36`） | 文案写 Kaiser，默认走平行分析；实现默认 `minres`，既非 `principal` 也非字面 `principal axis` |
| `:186-187` en `"bootstrap method (5000 resamples)"`／`:205` zh `"Bootstrap 法（5000次重抽样）"` | `src/analysis/advanced.py:121` `n_bootstrap: int = 5000`、`:135` 注释「默认5000」 | ✅ 对得上（列出以免只报坏消息） |

同理 `one_way_anova` 的「Post-hoc comparisons used Tukey HSD」与 `src/analysis/anova.py:122 post_hoc = _tukey_hsd(...)` 一致。复跑：
`rg -n 'mc_method: str =|Bonferroni 校正' src/analysis/nonparametric.py src/ui/app_pages_text.py`／
`rg -n 'n_factors|method: str =|exploratory_factor_analysis\(' src/analysis/factor_analysis.py src/analysis/runner.py`／
`rg -n 'n_bootstrap' src/analysis/advanced.py`
🔴 本班不改文案，也不判定统计口径对错；这三条只需进裁决清单。

## 四、并轨三方案的牵动面（实测，不估值）

引用位点双轨（AST 位点 = import/Name/Attribute/def/Assign；正则轨 = `rg -n -w`），扫描 556 份 `.py`：

| 符号 | AST 位点／文件 | rg 行／文件 | 生产消费方 |
|---|---|---|---|
| `TEST_NAMES_ZH` | 5／3 | 6／3 | `app.py:33`、`src/ui/quick_entries.py:152,177`（定义方 `config/settings.py:11,74` 另计） |
| `get_test_name` | 14／6 | 15／6 | `app.py:1167`、`src/analysis/runner.py:993`、`src/questionnaire/intent_recognizer.py:539`、`src/ui/undergrad_wizard.py:2972,3024,3059` |
| `get_test_name_zh` | 15／2 | 16／2 | **生产 0**（只有 `src/utils/i18n.py:269` 的 def 行）＋ `tests/test_i18n.py` 14 位点 |
| `_generate_method_description` | 4／2 | 4／3 | `src/ui/app_pages_text.py:111` 自调、`app.py:83` import |

复跑：`rg -n -w --no-heading -g '*.py' -g '!out/**' -g '!node_modules/**' -g '!tmp/**' 'TEST_NAMES_ZH|get_test_name|get_test_name_zh|_generate_method_description' .`
（`get_test_name` 与 `get_test_name_zh` 必须用 `-w`，否则 `\b` 之外仍会因子串粘连互串。）

| 方案 | 动什么 | 最小牵动件（实测） | 硬约束 |
|---|---|---|---|
| **A 迁 i18n** | 把 T1 独有的 24 键补进 T2/T3，T1 退为 alias 或删除 | 生产 4：`src/utils/i18n.py`、`config/settings.py`、`src/ui/quick_entries.py`、`app.py`；测试 1：`tests/test_i18n.py` | ① `tests/test_i18n.py:112` 的 `== 106` 必改（→130）；② 3.1 的 5 处措辞必须选一侧，选 settings 侧则 `tests/test_i18n.py:52-64` 的 parametrize 改字面；③ **`app.py` 是他班在途 ` M` 件（纪律档 §七／§九点名禁碰）**；「只补键不删表」可压到生产 1＋测试 1，但双表并存照旧 |
| **B 迁 settings** | 删 T2/T3 的 24 个方法键，名称唯一源回 T1（需另建 en 表） | 生产 2~3：`src/utils/i18n.py`、`config/settings.py`（＋新 en 表）、消费方行为不变则 0；测试 1：`tests/test_i18n.py` | ① `:112` 改 106→82；② `TestGetTestNameZh` 整类 10 个 parametrize 键里 `reliability`、`chi_square` **不在 T1**，删键后 `get_test_name("chi_square")` 从 `"χ²"` 变成蛇形键 `chi_square`（现读：`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from config.settings import get_test_name;print(repr(get_test_name('chi_square')))"` → `'χ²'`）⇒ **可见行为改动**，超执行手授权；③ 同样要碰 `app.py` 的 import 行 |
| **C 双表＋一致性断言** | 生产码 0 改，新增 1 件断言测试钉住「键集/值对齐」 | 新增 1 件（如 `tests/test_method_name_table_consistency.py`） | 断言按现状**必红**（3.1 的 5 处＋3.2 的 22 处），所以首版只能带**豁免清单**＝本文 22 键；转零豁免要先裁这 22 处措辞＝内容裁决 |

方案 C 的钉桩范式在仓内已有两处现成先例可抄：`tests/test_i18n.py:110-113`（键对称＋精确计数）、`tests/test_reliability_bands.py:83-109`（「数量与名字同时钉死」的台账式断言，注释自述「这是台账，不是终点」）。

## 五、双轨对账与差额归因（本域实测，单轨三处会失手）

纪律档 §九.3／§十.3 要求「全仓多少处」式判据双轨对到位。本次三处单轨读数与另一轨不合：

1. **dict 普查轨（AST）漏 T11**：`method_recommender.py` 的 17 条中文名是 keyword 实参和三元表达式，**不是 dict**，AST dict 普查读数 0。正则轨 `rg -c "primary_method_zh\s*=" src/analysis/method_recommender.py` → **13**（= 9 条 keyword 字面量 + 4 条 `primary_method_zh=primary_zh` 变量转赋；另有 `rg -n "primary_zh\s*=" ` 4 行 ×2 个字面量）⇒ 差额 4 行**全部可归因**，取「13 构造点／17 条字面量」双口径，不取单个数。
2. **`_generate_method_description` 正则轨多 1 文件**：`tests/test_reliability_bands.py:88` 是 docstring 提及，AST 轨正确排除 ⇒ 生产消费方 2 文件，非 3。
3. **`get_test_name_zh` 引用数：正则 16 行 vs AST 15 位点**，差额 1 = `tests/test_i18n.py:46` 的 docstring。上游 `psy-dead-code-dossier-20260923.md:94` 记的是「15 行命中／13 处调用」——本班按磁盘实况读作 **16 行／15 位点／生产 0 调用**，"生产零调用" 命题**复验成立**。
4. ⚠ 另记一条 `rg` 假零：`(?!/[A-Za-z_])t\(...` 这类 lookbehind 在默认引擎下**报 rc=2 且 stdout 为空**，若用 `subprocess` 只取 stdout 就会读成「零命中」。正确形态：`rg -P -n "(?<![A-Za-z_])t\(\"(independent_ttest|welch_anova)\"" .` → 4 行，与 AST 轨 4 位点闭合（全在 `tests/test_i18n.py:13,17,41,42`）⇒ **生产码零处直调 `t("<方法键>")`**，方法名的生产出口只有 `get_test_name`／`get_test_name_zh`／`TEST_NAMES_ZH` 直读三条。

## 六、建议（不执行，交主班裁决）

1. **先 C 后 A**：C 是唯一「生产码 0 改、且把 22 处漂移变成可机读台账」的路；A/B 都需要人工先裁第 3.1/3.2 节的措辞口径（哪个是权威名），这属内容裁决，本波不宜由执行手代签。
2. **别把「并入 i18n 单一来源」理解成两张表合一**：实况是 10~12 张表。先只把 **T1/T2 的名称层**收口（这是 `get_test_name_zh` 能否删除的前提），T4~T10 的标签/长句层另开单，否则并轨后 UI 仍会各自显示不同写法。
3. **`chi_square` 是并轨的前置阻塞键**：它在 T1 缺失、在 T6/T12 存在、在 T2 里值是 `"χ²"`，且是 `result_card` builder 的在册方法 id（`src/analysis/result_card.py:1389`）⇒ 任何「删 T2 键」的方案都会让它退化成蛇形键显示。建议裁决时单列。
4. **删除 `get_test_name_zh` 与并轨是两件事**：它生产零调用（第五节实测），删它**不会**收口 `app_pages_text.py` 的双语硬编码文案（`psy-dead-code-dossier-20260923.md:85` 早预警过）。若只为清死码而删，`tests/test_i18n.py:45-106` 那 14 处双语钉桩要一并迁指 `t()`，收益≈0；若为收口而留，就要给它接上文案层，成本＝方案 A。
5. **`tests/test_i18n.py:112` 的精确计数钉桩（`== 106`）在任何并轨下必红**，无论选哪条路，改它都得在 result/claims 里点名，别让人以为并轨方案本身失败。
6. 🔴 本文不删表项、不改文案、不改口径；第 3.3/3.4 节那类「文案 vs 实现」的字面差请另开人工闸，本班不判定哪个统计口径正确。

## 七、本文所有读数的现场复跑清单

```
cd /d/code/psy-analysis
git log -1 --format=%h                                   # cf3eaa4（会漂，以现读为准）
rg -n '"(hierarchical_regression|pearson_corr|spearman_corr|efa|cfa)":' config/settings.py src/utils/i18n.py
rg -n -w 'TEST_NAMES_ZH|get_test_name|get_test_name_zh|_generate_method_description' -g '*.py' -g '!tmp/**' .
rg -n '"ave":' config/settings.py src/output/interpretation.py src/ui/quick_entries.py
rg -n '"efa":' src/ui/app_pages_text.py
rg -c "primary_method_zh\s*=" src/analysis/method_recommender.py     # 13
rg -n "primary_zh\s*=" src/analysis/method_recommender.py            # 4 行 / 8 条字面量
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from src.utils.i18n import get_test_name_zh;from config.settings import TEST_NAMES_ZH;m=[k for k in sorted(TEST_NAMES_ZH) if get_test_name_zh(k,'zh')==k];print(len(m),m)"
```

探针脚本（一次性、可弃）：`tmp/s924-11/probe{,2,3,4,5}.py` ＋ `out{,2,3,4,5}.json`。`tmp/` 已 gitignore（`git check-ignore -v tmp/s924-11/probe.py` → `.gitignore:29:tmp/`），不入册。
