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
SPACE_AFTER_BODY_PT = 0
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
