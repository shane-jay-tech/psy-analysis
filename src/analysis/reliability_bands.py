"""信度档位（Cronbach's α 判读阈值）单一来源（s920-05 双源收口）。

历史上两处各写一份「α ≥ 0.90 优秀」：`src/questionnaire/psychometrics.reliability_guidance`
（问卷设计指南）与 `src/output/reasoning.TEST_TEMPLATES["cronbach_alpha"]`（结果解读指南），
改阈值必漏一处（见 `done(s919-03)` 遗留 1）。本模块收口的是**阈值**，两处各自的原话不改一个字。

`text` 是渲染原文（两位小数），`threshold` 是数值口径：`str(0.90) == "0.9"`，
直接用数值渲染会把文案里的「0.90」变成「0.9」⇒ 两个字段必须成对维护。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlphaBand:
    threshold: float
    text: str
    label: str


# 「≥ 阈值」的四档（label 取 reasoning 侧的叫法；psychometrics 侧原话不同，故标签不在共享范围）
EXCELLENT = AlphaBand(0.90, "0.90", "优秀")
GOOD = AlphaBand(0.80, "0.80", "良好")
ACCEPTABLE = AlphaBand(0.70, "0.70", "可接受")
EXPLORATORY = AlphaBand(0.60, "0.60", "探索性边界")

RELIABILITY_BANDS: tuple[AlphaBand, ...] = (EXCELLENT, GOOD, ACCEPTABLE, EXPLORATORY)

# 「< 0.60」这一档：psychometrics 侧叫「需要修订」，reasoning 侧叫「不可接受」，同阈值不同话
UNACCEPTABLE = AlphaBand(0.60, "0.60", "不可接受")
