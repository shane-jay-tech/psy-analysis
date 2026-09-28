"""Word 文档样式常量 — APA7 + 中文期刊通用排版。"""

from __future__ import annotations

# 字体（python-docx 用 docx.oxml 设置 east-asia 字体）
FONT_BODY_LATIN = "Times New Roman"
FONT_BODY_CJK = "宋体"
FONT_HEADING_LATIN = "Times New Roman"
FONT_HEADING_CJK = "黑体"

# 字号（pt）
SIZE_TITLE = 16
SIZE_H1 = 14
SIZE_H2 = 13
SIZE_H3 = 12
SIZE_BODY = 12
SIZE_CAPTION = 10.5
SIZE_TABLE = 10.5

# 行距 / 段距
LINE_SPACING = 1.5
SPACE_BEFORE_HEADING_PT = 12
SPACE_AFTER_HEADING_PT = 6
# s928-01 案 B′（s927-51 拍板，用户 2026-09-28 授权）：0 → 10。
# 改前两值：常量 0、消费方 0 处 ⇒ 正文段生效值一直由捆绑模板的
# `docDefaults after=200`（twips＝10pt）继承而来，常量本身从未生效。
# 本行把「正文段后距」由“跟随模板 docDefaults”改判为“本仓显式锁定 10pt”——
# 今天与模板同格（零版式变化），模板若变更即分叉（风险已并入 s923-18 在册条目，台账 241ⓒ）。
# 单位仍是 pt 裸数（与 SPACE_AFTER_HEADING_PT 同族形状）；`Pt()` 换算只在消费方做，
# 本文件不 import docx，写 `Pt(10)` 会 NameError。
SPACE_AFTER_BODY_PT = 10
FIRST_LINE_INDENT_CM = 0.74  # 中文论文首行缩进 2 字符

# 页边距 (cm) — APA7 标准
MARGIN_TOP_CM = 2.54
MARGIN_BOTTOM_CM = 2.54
MARGIN_LEFT_CM = 3.18
MARGIN_RIGHT_CM = 3.18

# 表格样式
TABLE_HEADER_FILL = "DDDDDD"
TABLE_BORDER_COLOR = "000000"
TABLE_BORDER_SIZE = 4  # eighths of a point

# 图标题前缀
FIG_PREFIX = "图"
TABLE_PREFIX = "表"
