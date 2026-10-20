# 非参数族效应量 CI 补齐统计层设计稿（b040 遗留，dataclass 先行）——s1004-30

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T17:5x ｜ 性质：**统计计算域只出设计稿**；dataclass 字段添加亦留裁后另单
> 矿源：`zcode-bridge/done/20260925-120700-b040.result.md` 遗留（逐字核对在册）；姊妹单 s927-61（t 族外四族区间上界兜底＝显示层）。
> 对象：`src/analysis/nonparametric.py`。

## 一、现状对账（⚠ 矿源前提已大部过时，按实况修正）

| 方法（行号） | 效应量 | effect_size_ci 现值 | 判定 |
|---|---|---|---|
| mann_whitney（:22） | r 秩双列相关（:90） | `[r_low, r_high]` 渐近 CI（:92）——Fisher z 法：z=atanh(r)、SE=1/√(N−3)、±1.96 反变换（:68-72 逐字） | **已在世** |
| wilcoxon_signed_rank（:98） | 匹配对秩双列相关（:162） | 同型渐近 CI（:164） | **已在世** |
| kruskal_wallis（:170） | η²H（:242） | 占位文案「暂无置信区间（ε²/η²H 的标准 CI 计算方法尚未确立，**建议使用 bootstrap 法**）」（:216） | **真缺口①**（码内已自荐路径） |
| friedman_test（:251） | Kendall's W（:279） | 占位文案「暂无置信区间（标准 CI 计算方法未知）」（:273） | **真缺口②** |

- `NonParamResult.effect_size_ci: Optional[str] = None` 字段**已在册**（:16）——b040「dataclass 部分无 CI 字段，需先补统计层」的前提过时：**dataclass 层零工作**，缺口收敛为 kruskal/friedman 两族的统计层。
- 字段现值三态并存：区间串（两法）／占位文案（两法）／None（默认）——建议契约注释钉三态语义（属 L1 注释级，留另单）。

## 二、各方法 CI 求法与前置（调研层，出处标注）

| 方法 | 求法 | 前置/代价 | 出处置信度 |
|---|---|---|---|
| mann_whitney / wilcoxon | 现值 Fisher z 渐近已达标；可选升级＝bootstrap（重抽 B 次重算 r） | 非必需；升级收益仅在小样本渐近失真场景 | 渐近法＝标准通法（高置信） |
| kruskal η²H | **bootstrap 百分位 CI**：联合重抽 B 次（保组结构）→ 每次算 H→η²H → 取 2.5/97.5 分位；码内 :216 已自荐 | B≥5000（仓内先例 repeated_measures_anova n_boot=5000，anova.py:312）；成本 O(B·N logN)（rank 主导） | 百分位 bootstrap＝Efron 标准法（高置信）；「解析式未确立」＝码内自注＋通说（中置信，未逐条核文献） |
| friedman Kendall's W | 同型 **bootstrap**：**按被试行重抽**（保组内配对结构，不得打散行内 rank）→ W → 百分位 CI | 配对结构保持是硬前置；n（被试数）过小时 CI 本身无意义需护住 | 同上；解析面（零假设 n(k−1)W~χ²(k−1) 反解）只是参考区间非效应量 CI，**不推荐**（码内「未知」注释维持） |

## 三、两层设计

**L1 dataclass 层（低风险，裁后另单）**：字段已在册零工作；唯一建议＝:16 墙上补三态契约注释（区间串「[lo, hi]」／占位文案「暂无…」／None）＋与 s927-61 显示层口径互引。

**L2 统计层（红线域，本稿零落码）**：
- 实施面＝nonparametric.py 两函数各加 `bootstrap_ci: bool = False, n_boot: int = 5000` 参数（默认关＝零行为变化，与仓内「参数化能力、默认不启用」先例同型）；
- 控制面衔接＝**与 s1004-37 设计并族**（mediation_n_boot/mediation_seed 同款 plan 字段＋UI 两级暴露），seed 透传进产物（4d99 E2 复现性面同治）；
- 进度面＝长循环接 progress_callback 先例（advanced.py:120 签名在册）；
- 失败面＝重抽中数值异常按 s1004-31 同款 warning 逐次留痕，不静默。

## 四、留主班三问

1. L2 两族是否立单实施（建议 friedman 优先——唯一无任何区间的族）；
2. n_boot/seed 控制面是否与 s1004-37 三字段同批走 plan/UI；
3. mann/wilcoxon 渐近 CI 是否补 bootstrap 备选（非必需，默认不做）。

### 证据存根

- `$ grep -n "class NonParamResult" -A 16 src/analysis/nonparametric.py` → :16 字段在册。
- `$ sed -n 68,79p / :90,92p / :162,164p / :216p / :242,244p / :273p,279,281p` → 四方法效应量与 CI 现值逐字。
- `$ grep -n "def mann_whitney\|def wilcoxon\|def kruskal\|def friedman" src/analysis/nonparametric.py` → 四方法行号。
- 统计层零落码声明：本单仓内仅本档。
