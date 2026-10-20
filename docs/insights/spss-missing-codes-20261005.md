# SPSS 用户缺失范围（missing_codes）归一判据单（d598 遗留 C4）——s1004-28

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T18:1x ｜ 性质：判据材料，不动 load_spss 生产语义
> 矿源：`zcode-bridge/done/20260925-120655-d598.result.md` 遗留 C4（逐字核对在册：「load_spss 不读 pyreadstat 的用户缺失范围…用户缺失值读入后的原样形态」）。
> 实证件：`zcode-bridge/tmp/s1004-28/probe_sav.py`（pyreadstat 1.3.5 写造最小 .sav，合成数据）。

## 一、实证反转：默认读入已归一（矿源前提在现依赖下不成立）

最小 .sav（x 列含 99，写侧 `missing_ranges={"x": [99]}`＋值标签含 99→「不清楚」）双口径读入：

```
① 现值读入 x = [1.0, 2.0, nan, 4.0]  |  user_missing=True x = [1.0, 2.0, 99.0, 4.0]
② 经 load_spss 值标签替换后 x = ['不同意', '中立', nan, '同意'] | dtype = object
③ 现值(99保留标签路径): n_total=4 missing_pct=25.0% missing_cols=['x']
```

- **pyreadstat 1.3.5 的 `user_missing` 语义与字面相反**：默认（False）＝**应用**用户缺失定义置 NaN；True＝保留原值。`load_spss`（loader.py:100 未传该参）走默认 ⇒ **用户缺失已在读入层天然归一**——d598「99 原样进来」在现依赖版本下不成立，C4 的「归一 NaN」由依赖层天然完成。
- ③ 下游互证：默认路径 missing_pct=25%（99 已计缺失）；user_missing=True 保留 99 时反而 0%——参数一旦被未来误改，下游键立即反向，建议 docstring 钉死。

## 二、值标签交互（load_spss:103-107 的次生形态）

默认读入后 99 已 NaN ⇒ 值标签 replace **不会**把 99 变「不清楚」字符串（该标签成死配置）；但整列因其余值替换成字符串转 object dtype——数值分析走 to_numeric coerce 的既有链，无新增风险。**若切换 user_missing=True 才会产出「不清楚」字符串列**＝语义雷区，写进判据。

## 三、真缺口收敛：字典与内嵌定义不一致场景

实证仅覆盖「.sav 内嵌了缺失定义」。**内嵌定义缺失时**（SPSS 外部声明的 missing_codes，如字典要求 99/98 为缺失但 .sav 没嵌）⇒ 值原样进入 ⇒ d598 设想的「按字典 missing_codes 归一」在此场景才需要：

| 场景 | 现行为 | 判据建议 |
|---|---|---|
| .sav 内嵌缺失定义 | 依赖层已置 NaN ✅ | 无需动作；docstring 钉死 user_missing 默认语义 |
| 内嵌未覆盖、字典 missing_codes 声明 | 值原样进入（99 被当合法值） | 归一开关：`load_spss(file_path, missing_codes: Optional[dict] = None)`——None=现行为（默认关）；传入时对数值列 `mask(isin(codes) | between(ranges))` 置 NaN，**仅在内嵌定义未覆盖的列生效**（用 `meta.missing_ranges` 判覆盖） |
| user_missing=True 误用 | 99 保留＋标签字符串化 | 反模式注记入 docstring |

## 四、影响面与开关方案（不定案）

- 归一前后下游对照（内嵌场景已天然归一，无需对照）；**字典补归一场景**（上表行 2）：n_total 不变、missing_pct 上升、x 列均值/SD 排除 99——影响方向与 SPSS 惯例一致；
- 开关默认关＝零行为变化；开启属统计口径变更（c36e 同款「会动读数」警示适用），须主班拍板后另单；
- 与字典域衔接：missing_codes 声明冲突已有 `Codebook.conflicts() → E_MISSING_AMBIGUOUS` 拦截（c47f E2 表六在册），开关实现须复用该判据防双源打架。

### 证据存根

- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-28/probe_sav.py` → ①②③ 全部输出（写侧 API 试错三连：missing_values 不存在→tuple 形拒收→**[99] 单值列表形成功**，已留痕）。
- `$ sed -n 96,116p src/data/loader.py` → load_spss 现值（:100 未传 user_missing）逐字。
- `$ python -c "import pyreadstat; print(pyreadstat.__version__)"` → 1.3.5。
- 禁令守约：load_spss 零触碰，归一未实施。
