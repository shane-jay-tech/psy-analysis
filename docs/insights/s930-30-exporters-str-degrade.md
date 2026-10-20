# exporters str 出口显式降级选项材料

> 产出单：s930-30（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-55 遗留（str 出口未处置——两支 `bytes(str)` 抛 TypeError；latin-1 降级属行为裁决面未动）。
> **零改动**。

## 一、现状与关键实测

- 两 PDF 出口（exporters.py:483/:619）＝`return bytes(pdf.output())`——`pdf.output()` 返回 **str** 时 `bytes(str)` 无编码参数 ⇒ **TypeError**（矿源「清理后仍是」复核成立）；
- **本班实测（s930-12 证据）**：fpdf2 **2.8.7** 的 `output()` 返回 **bytearray**——str 分支在现版**死码化**（永不触发）；TypeError 只在未来 fpdf 行为回退/换库时浮现＝**潜伏炸点**而非现行 bug；
- 先例形状（矿源点名两处）：`if isinstance(raw, str): return raw.encode("latin-1")`——defense_qa.py:1018、env_check.py:205。

## 二、选项对比

| 选项 | 行为 | 利 | 弊 |
|---|---|---|---|
| **A latin-1 降级**（先例同款，两支各 +2 行） | str ⇒ latin-1 编码返回 | 防潜伏炸点；与仓内两先例同款（一致性） | latin-1 对 fpdf 老版核心字体输出语义正确（Latin-1 是 fpdf 核心字体的原生编码），但**仅对纯 ASCII/Latin 内容无损**——CJK 内容在老版 fpdf 本就需 UTF-8 输出模式（返 bytearray），str 分支触达时内容必为拉丁系 ⇒ 无损前提自洽 |
| B 维持现状（str ⇒ TypeError 冒泡） | 潜伏炸点保留 | 「让版本回退立刻炸出来」——冒泡哲学 | 炸点在导出路径（用户拿不到文件）；与仓内先例不一致 |
| C 删除兼容面＋断言钉 | `assert not isinstance(raw, str)`（显式钉「2.8.7 永不返 str」） | 把「死码化」事实显性化；回退时 AssertionError 带信息 | 断言钉也是行为选择（与 B 等价的显式版） |

## 三、建议（不签口径）

1. **A 与 C 等价可辩**——差别只在「回退时静默兼容（A）还是当场红（C）」；本仓当前哲学偏显式（A′ 拒答、AST 哨兵族），**C（断言钉）更贴仓风格**且实现最小；
2. 若裁 A：latin-1 需在注释注明「fpdf 核心字体时代语义，UTF-8 输出模式（现版）不走此分支」——防后人误当通用降级；
3. 两支（:483/:619）同笔（勿单支改，重演「第二次洗一遍」）。
