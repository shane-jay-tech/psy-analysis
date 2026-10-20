# 运行期 skip 记录轨（-rs 反查无因 skip）设计稿（备用）——s1004-52

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T01:5x ｜ 性质：**只设计，零生产码、不入门禁不进 CI**（禁令守约）
> 矿源：`zcode-bridge/done/20260925-120710-6784.result.md:184-193`（逐字核对在册：construct_kb 空参数集样本＋「另一单的活」原文）。
> 差异点（任务书注）：池内 s930-07 钉收集差总数（node id 级）；本单=运行期 `-rs` 反查逐条 skip 记录轨。

## 一、现网 skip 全集样本（全量实测，2026-10-05）

`$ "D:/Program/python.exe" -m pytest -ra -q`（psy-analysis 全量 324 件，596.42s）
→ **17 failed, 5589 passed, 3 skipped, 27 xfailed, 13 errors**（fail/error 为现网基线，与本单无关，记录轨只看 skip 面）。

| # | 位置 | -rs 输出尾行 | 分类 |
|---|---|---|---|
| 1 | `tests/test_construct_kb_extended_placeholder.py:118` | `got empty parameter set for (construct_name)` | **pytest 生成无因**（6784 点名首样本） |
| 2 | `tests/test_socratic_quality.py:57` | `需要 --run-benchmark 才运行（默认跳过）` | 显式 reason |
| 3 | `tests/test_socratic_quality.py:156` | 同上 | 显式 reason |

## 二、解析器设计（对现网 -rs 输出实测）

**行正则**（short summary 区逐行）：
```
^SKIPPED \[(\d+)\] (.+?):(\d+): (.*)$
```
- 捕获组：count / 相对路径 / 行号 / 原因文本（原样保留，含全角标点）。
- **实测解析成功率：3/3 = 100%**（上表 3 条全命中，零漏零误；源日志 `zcode-bridge/tmp/s1004-52-ra.log:802-804`）。

**分类规则（两桶＋一白名单形态）**：
1. **生成形态白名单**：原因文本匹配 `^got empty parameter set for \(` ⇒ 分类 `generated-empty-params`（pytest 自动产出，无人类 reason）；
2. **显式 reason**：其余非空文本 ⇒ `explicit`；
3. **空 reason 文本**（理论上 `pytest.skip()` 无 message 会产生）⇒ `no-reason`（本单现网样本中 0 条）。
分类覆盖：3/3 可判定（1 generated＋2 explicit）。

## 三、记录轨与基线档

- **记录轨**：每班门禁跑 `pytest -ra -q` 后解析 short summary，产出 skip 清单 `[{path, line, reason, class, count}]`。
- **基线档**：`tests/baseline/skip-baseline.json`——键=`{path}:{line}`，值=`{class, reason_hash}`。首版基线=上表 3 条。
- **漂移语义**：只减不增。位置消失（修复/参数化补齐）⇒ 基线自动收窄（允许静默）；位置新增 ⇒ 进门禁判定。

## 四、新红门（设计，未实施）

```
gate: skip_gate
red 条件（任一）：
  ① 新增 skip 位置（基线无此 {path}:{line}）且 class ∈ {no-reason, generated-empty-params}
  ② 显式 reason skip 的新增位置（提示人工补基线，黄灯降级可选）
green 条件：skip 位置集 ⊆ 基线位置集
```
- 设计要点：**空参数集 skip 也算红**——6784 样本的本质风险正是「占位测试静默不跑」：`EXTENDED_CONSTRUCTS` 空集时 census 形状守卫（test_future_entries_match_census_schema）从未执行过，条目未来一旦加入才发现口径错。故 generated 形态按**位置**追踪：老位置放行、新位置即红。
- 与 s930-07（收集差总数、node id 级）互补：s930-07 管「少收集」，本门管「静默不跑」。

## 五、首样本三步推演（construct_kb 空参数集）

1. **记录**：`-rs` 解析 → `{path: tests/test_construct_kb_extended_placeholder.py, line: 118, reason: "got empty parameter set for (construct_name)", class: generated-empty-params, count: 1}`；
2. **基线**：写入 `skip-baseline.json` 键 `tests/test_construct_kb_extended_placeholder.py:118`；
3. **门禁**：次日全量再解析——
   - 同位置同形态 ⇒ green（占位维持现状，符合「今天恒真、明天是闸门」的登记语义）；
   - `EXTENDED_CONSTRUCTS` 补条目 ⇒ 该 skip 消失，基线收窄 ⇒ green（这是**改善**方向）；
   - 其它文件出现**新**空参数集/无因 skip ⇒ **red**，报 `新增无因 skip: {path}:{line}`，人工判读。

## 六、边界与未决（留主班）

- fail/error 面（现网 17+13）不进本轨，避免与既有门禁口径混线；
- `-rs` 与 `-ra` 等价含 skip 段，记录轨建议直接用 `-ra`（同一趟同时喂 fail 门）；
- xfail（27 条）不在本轨范围；
- 若主班拍板实施：脚本落点建议 `scripts/skip_gate.py`＋`tests/baseline/`，首版基线即 §一 表 3 条；本班未写任何脚本（零生产码守约）。
