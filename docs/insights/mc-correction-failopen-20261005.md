# _apply_mc_correction 未知方法名 fail-open 修法裁决材料（ae49 遗留）——s1004-38

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T10:3x ｜ 性质：口径域只出材料不落码
> 矿源：任务书引 ae49 遗留逐字：「对未知方法名 fail-open（返回未校正 p 值且与 none 同形）。修法有争议（抛错 vs 回落 holm），涉及统计结论口径 ⇒ 只出读数，不自修。」
> 探针：`zcode-bridge/tmp/s1004-38/probe_failopen.py`（机制演示，玩具 p 值，零数据结论）。

## 一、fail-open 现值与实跑取证

**支路定位**（`src/analysis/nonparametric.py:290-334`）：docstring 契约 :296 `method: "holm" | "bonferroni" | "fdr" | "none"`；分发 ：305（none 原样返回）/:311（bonferroni）/:313-319（holm）/:321-325（fdr）/**:326-327 `else: corrected = sorted_values`＝未知名静默走未校正**（排序后恢复原序 ⇒ 与 none 输出逐字同形）。

**实跑取证**（`$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-38/probe_failopen.py`，p=[0.04,0.01,0.03]）：
```
none       = [0.04, 0.01, 0.03]
holm       = [0.06, 0.03, 0.06]
typo-holm  = [0.04, 0.01, 0.03]
empty-str  = [0.04, 0.01, 0.03]
=> 未知名与 none 逐字同形? True
```
ae49 指控**复现实锤**：`holmm`（笔误）与空串均与 `none` 逐字同形——静默返回未校正 p。

**连带面**：列名兜底 `method_names.get(mc_method, f"p ({mc_method})")`（:389）在未知名下产出「p (holmm)」这类列名但值未校正——标签诚实、数值不诚实，同族问题。

## 二、合法方法名清单（rg 证据）

契约四名：`holm / bonferroni / fdr / none`（:296 docstring）。生产面来源全集：
- `nonparametric.py:174`（kruskal_wallis 参数，默认 "holm"）与 `:345`（_dunn_test 参数，默认 "holm"）
- `runner.py:735`（缺省 "holm"，44a0:44 同款读数）
- **UI/parser/app.py 零注入面**（`$ grep -rn "mc_method" src/ui/ src/parser/ app.py` → 0 命中）⇒ 未知名今日只能来自**代码级笔误**，无用户输入通路。

## 三、两案口径影响与下游断链清单

| 案 | 改法 | 口径影响 | 下游断链清单 |
|---|---|---|---|
| ① 抛错 | :326-327 else 改 `raise ValueError(f"未知校正方法 {method!r}，合法值：holm/bonferroni/fdr/none")` | **零口径变化**（现网全部调用走合法名，行为不变）；未来笔误从静默未校正变响亮失败 | **现网断链=0**：runner 硬编码默认 holm、UI 零注入、`tests/test_robustness.py:188` 恰只参数化四合法名（:173-196 逐行核对）⇒ 零测试红 |
| ② 回落 holm（＋警告条目） | else 改按 holm 校正并向 result 附 warning | **统计语义变化**：未知名从「未校正」变「holm 校正」＝fail-silent 换 fail-safe；对复现性更差（同一错名两版行为不同）且隐藏调用方 bug | 下游零断链；但「错单静默吃下」仍属 fail-open 家族，只是方向反转 |

## 四、裁决建议（留主班，未实施）

- **推荐案 ①**：零现网波及（三路证据）＋与 docstring 契约对齐＋fail-fast；若主班选更稳的「入口白名单校验」，建议 :326 与 :389 列名兜底**两处同笔收**（否则列名兜底成新的静默面）。
- 落地时必跑＝`pytest tests/test_robustness.py -q`（现基线见 4d99 ⑦；本班未动）＋非参数族定向。

### 证据存根

- `$ sed -n 290,334p src/analysis/nonparametric.py` → 分发五支逐字（含 :326-327 else）。
- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-38/probe_failopen.py` → 四行输出＋同形判定 True。
- `$ grep -rn "mc_method" src/ --include="*.py"`（除 _apply 本体）→ :174/:180/:221/:345/:351/:388 六处＋runner 默认；`$ grep -rn "mc_method" src/ui/ src/parser/ app.py` → 0。
- `$ sed -n 173,196p tests/test_robustness.py` → 参数化恰四合法名。
- 禁令守约：口径域零落码。
