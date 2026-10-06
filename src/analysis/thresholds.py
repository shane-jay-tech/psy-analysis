# -*- coding: utf-8 -*-
"""thresholds — 心理测量阈值常量单源（s1006-01 落地，设计稿 psy-thresholds-module-design-20261006）。

**数值照抄现值零改动**：本模块全部数字与消费方原判据逐位相等（登记表见设计稿 §一）。
意义＝判据与文案同源：改阈值时指南自动跟，防「代码判据 0.70 / 文案 0.80」漂移。

消费方：
  - src/analysis/reliability.py（分半/ω 判据，s1006-01 迁移步 2）
  - src/questionnaire/psychometrics.py（指南文案插值，迁移步 3）

域外参照（**不入本模块**）：undergrad_wizard.py 向导阈值 >= 0.4（文献相关性，非心理测量判据）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdSet:
    """单一统计量的「档位线 + 方向 + 展示名」。direction: ge=越大越好 / le=越小越好。"""

    good: float            # 「良好」档
    acceptable: float      # 「可接受」档
    direction: str         # "ge" | "le"
    label: str             # 展示名


# ---- 拟合与效度（psychometrics 文案面 + 判据） -------------------------------
CFA = ThresholdSet(good=0.95, acceptable=0.90, direction="ge", label="CFI")
TLI = ThresholdSet(good=0.95, acceptable=0.90, direction="ge", label="TLI")
RMSEA = ThresholdSet(good=0.05, acceptable=0.08, direction="le", label="RMSEA")
SRMR = ThresholdSet(good=0.08, acceptable=0.08, direction="le", label="SRMR")
SCVI = ThresholdSet(good=0.90, acceptable=0.90, direction="ge", label="S-CVI/Ave")
ICVI = ThresholdSet(good=0.78, acceptable=0.78, direction="ge", label="I-CVI")
CVI = ThresholdSet(good=0.80, acceptable=0.80, direction="ge", label="CVI")
KMO = ThresholdSet(good=0.80, acceptable=0.80, direction="ge", label="KMO")
LOADING = ThresholdSet(good=0.40, acceptable=0.40, direction="ge", label="因子载荷")
CROSS_LOADING = 0.30        # 交叉载荷 <0.30（单值）
AVE = ThresholdSet(good=0.50, acceptable=0.50, direction="ge", label="AVE")
CR = ThresholdSet(good=0.70, acceptable=0.70, direction="ge", label="CR")
ICC = ThresholdSet(good=0.70, acceptable=0.70, direction="ge", label="ICC")
SPLIT_HALF = ThresholdSet(good=0.70, acceptable=0.70, direction="ge", label="分半信度")
OMEGA = ThresholdSet(good=0.70, acceptable=0.60, direction="ge", label="McDonald's ω")
CITC = ThresholdSet(good=0.30, acceptable=0.30, direction="le", label="CITC")
ALPHA_ITEM_CORR = (0.15, 0.50)   # α 说明：平均题间相关理想带
