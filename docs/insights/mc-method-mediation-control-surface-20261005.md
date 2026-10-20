# mc_method 与 _run_mediation 默认配置控制面缺位设计稿（ae49 遗留 3＋4d99 E2）——s1004-37

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T10:3x ｜ 性质：**只设计不落码**，不改任何默认值语义
> 矿源：`zcode-bridge/done/20260925-154313-ae49.result.md`（mc_method/missing_strategy 无控制面）＋`20260925-154316-4d99.result.md`（_run_mediation 硬编码默认，E2）——两处逐字核对在册。
> 姊妹稿：`docs/insights/s927-23-missing-strategy-design.md`（missing_strategy 暴露设计，本稿并族对齐，见 §四对照段）。
> 探针：`zcode-bridge/tmp/s1004-37/probe_setattr.py`（合成数据 seed=3，看列标签非统计结论）。

## 一、三面不可达实证（命令＋输出内联）

**① mc_method 声明缺口（TypeError 硬证）**：`$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-37/probe_setattr.py` →
```
默认链(未声明字段) 列标签 = ['p (未校正)', 'p (Holm-Bonferroni)']
声明态构造 = TypeError: AnalysisPlan.__init__() got an unexpected keyword argument 'mc_method' ⇒ 字段未声明，关键字注入不可达
setattr 注入后 列标签 = ['p (Bonferroni)'] ⇒ 消费侧在位，声明即通
```
- 声明面：`grep -n "mc_method\|missing_strategy" src/parser/intent_resolver.py` → **0 命中**（AnalysisPlan 未声明，ae49 成立）。
- 消费面在位：`runner.py:734-736`「# 支持通过 plan 传入 mc_method」＋`mc_method = getattr(plan, "mc_method", "holm") or "holm"` ⇒ **只差声明即通**（setattr 演示实证）。
- 附注：默认链 dunn 表同时含「p (未校正)」与「p (Holm-Bonferroni)」两列（:386-389 method_names 面），与 s1004-38 的 fail-open 材料同源。

**② missing_strategy 同族**：消费面 `runner.py:886`（getattr）＋`:927`（handle_missing strategy=）在位；声明面同样 0 命中——**设计权属 s927-23**（案 B 披露-only 先行／案 A 三道闸），本稿不重复设计。

**③ mediation 配置不可达**：`runner.py:844` `result = advanced.mediation_analysis(df, x, m_arg, y)` **四实参直调**（4d99 时点 ：845，行号微漂）；签名 `advanced.py:116-124` 七参：`n_bootstrap: int = 5000, seed: int = 42, progress_callback=None` ⇒ **n_boot/seed 生产路径不可达**，与 4d99 E2「SEED_RECORDED=False、无透传通道」互证。

## 二、设计稿：plan 增字段＋UI 可选层两级

### 2.1 plan 增 3 字段（默认值=现网默认，零语义变化）

| 字段 | 类型/默认 | 消费点 | 状态 |
|---|---|---|---|
| `mc_method: str = "holm"` | 四名白名单 | runner:735 **已就位** | 声明即通（实证①） |
| `mediation_n_boot: int = 5000` | 上限闸（建议 ≤20000 需确认） | runner:844 改透传 | +1 行 |
| `mediation_seed: Optional[int] = None` | None=维持现行为（不改默认语义） | runner:844 改透传（None→42 现值） | +1 行；设值时 seed 进产物/血缘＝4d99 E2「seed 可追溯」修复面 |

不增 `missing_strategy`（s927-23 所有）。runner 侧合计 ≈2 行（:844 一处调用改七参）。

### 2.2 UI 可选层两级（借 s927-23 形态学）

- **L1 披露-only（先行，对齐 s927-23 案 B）**：「📋 分析计划」expander 只读徽标：`多重比较校正：holm（runner 缺省）`／`中介 Bootstrap：5000 次、种子未设（每次重跑会变）`——零行为变化，先让默认可见。
- **L2 可选层（对齐 s927-23 案 A 三道闸形态）**：
  - `mc_method` selectbox＝四名白名单（holm/bonferroni/fdr/none）；**`none` 需确认框**（未校正多重比较＝高风险闸，借 s927-23「drop_column 命中 DV 禁止提交」同型）；
  - `mediation_n_boot` 数字输入（>20000 需确认框）；
  - `mediation_seed` 输入框后置（先徽标披露，输入权随 L2 批次）。
- **联动闸**：mc_method 白名单的强制力依赖 **s1004-38 案①**（_apply_mc_correction 未知名抛错）先行——否则 UI 白名单外的代码路径仍 fail-open，两单构成族内前后置。

### 2.3 field_lineage 衔接（借 s927-23 别名先例）

- `mc_method`/`mediation_n_boot`/`mediation_seed` → 挂 **S10_plan_parameter** 族（沿用 s927-23 的 `plan_missing_strategy → S10` 别名方案，规避 EXACT_FIELD_SPEC 同名撞位）；`mediation_seed` 设值后另进 **S26_model_spec** 族（复现性语义，与 is_fallback 同域——s1004-56 已核 field_lineage.py:472 消费面在世）。

## 三、与 s927-23 对照段（无冲突声明）

| 面 | s927-23 | 本稿 | 冲突 |
|---|---|---|---|
| missing_strategy | 全生命周期设计权（案 B 披露/案 A 三道闸/B1-B5 落地清单/EXACT_FIELD_SPEC 别名） | **不设计**，仅引其 :886 消费点为同族证据 | 无 |
| mc_method／mediation_n_boot／mediation_seed | 未涉及 | 本稿新增三字段＋L1/L2 暴露 | 无（字段集不相交） |
| 形态学 | 三道闸／披露-only／S10 别名 | 全盘借用其形态 | 对齐即复用 |
| 落地顺序 | B1-B5 先行不受影响 | 本稿字段走同族后置批 | 无 |

## 四、留主班三问

1. `mediation_seed` 设值后是否进产物（4d99 E2 修复面）——涉及复现性语义，建议进（S26 族）；
2. L2 暴露时点：与 s927-23 案 A 同批一齐开闸，还是披露-only 先行、开闸另批；
3. `progress_callback` 是否接 UI 进度条（功能增强，可后置，不阻塞本稿）。

### 证据存根

- `$ grep -n "mc_method\|missing_strategy" src/parser/intent_resolver.py` → 0 命中。
- `$ sed -n 734,736p src/analysis/runner.py` → 消费点逐字；`$ sed -n 886p`＋`$ sed -n 927p` → missing 消费面。
- `$ sed -n 116,136p src/analysis/advanced.py` → 七参签名逐字；`$ sed -n 844p src/analysis/runner.py` → 四实参直调逐字。
- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-37/probe_setattr.py` → 三行实证（§一①）。
- `$ grep -n "missing_strategy\|控制面" D:/code/zcode-bridge/done/s927-23.result.md` → 案 A/B 框架逐字。
- 零码改动守约：仓内仅本档；默认值语义零触碰。
