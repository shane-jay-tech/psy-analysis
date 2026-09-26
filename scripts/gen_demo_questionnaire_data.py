# -*- coding: utf-8 -*-
"""生成 demo 问卷数据（可复现，seed 固定）。r5 B4 甲案：让"焦虑与自尊负相关"真的成立。

背景：改前 `data.csv` 与它自己的叙事打架——WALKTHROUGH.md:69 与 literature_seed 的 wang2023
都写"焦虑与自尊负相关"，而真算 **r=+0.986**（两种计分口径都为正）；且无效样本的 id 与
WALKTHROUGH 写的"剔除 id=5,12,28"也对不上（实测是 14/30）。用户 2026-09-27 选**甲案**：
重造数据，不动期望卡的叙事方向。

设计（全部可复算）：
- 潜变量 A（焦虑）与 E（自尊）目标相关 r≈-0.65；每个分量表 5 题，观测 = 3 + 1.0*因子 + N(0,0.5)，
  截到 1–5 整数；**反向题取 6-x**（这样"按 schema 反向计分后"才与量表同向）。
- gender 对 A 加中等效应（组内先去均值再加 ±0.45，避免被一次随机抽样抹平）。
- 时长：id 5/12/28 短于 60 秒（与 WALKTHROUGH 的"剔除 id=5,12,28"一致），其余 150–300 秒。
- 30 行、15 女 15 男。

用法：
  python scripts/gen_demo_questionnaire_data.py                       # 只打印前 6 行（dry）
  python scripts/gen_demo_questionnaire_data.py demo_projects/psychology_questionnaire_demo/data.csv
"""
import sys

import numpy as np
import pandas as pd

SEED = 20260927
N = 30
INVALID_IDS = (5, 12, 28)
GRADES = ["大一", "大二", "大三", "大四"]
GENDER_SHIFT = 0.45


def build_frame(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    r_lat = -0.65
    a = rng.normal(0, 1, N)

    gender = np.array(["女", "男"] * (N // 2))
    female = gender == "女"
    # 组内去均值后再加性别位移 ⇒ 组间差恒为 2*GENDER_SHIFT，不被一次抽样抹平
    a_centered = a.copy()
    a_centered[female] -= a[female].mean()
    a_centered[~female] -= a[~female].mean()
    a_obs = a_centered + np.where(female, GENDER_SHIFT, -GENDER_SHIFT)
    e = r_lat * a_centered + np.sqrt(1 - r_lat ** 2) * rng.normal(0, 1, N)

    grade = np.array([GRADES[i % 4] for i in range(N)])

    def items(factor, k=5, loading=1.0, err=0.5):
        return [np.clip(np.rint(3.0 + loading * factor + rng.normal(0, err, N)), 1, 5).astype(int)
                for _ in range(k)]

    anx = items(a_obs)      # Q1,Q2,Q4,Q5 正向 ＋ Q3 反向
    est = items(e)          # Q6,Q7,Q10 正向 ＋ Q8,Q9 反向
    data = {"id": np.arange(1, N + 1), "gender": gender, "grade": grade}
    q = {"Q1": anx[0], "Q2": anx[1], "Q4": anx[2], "Q5": anx[3], "Q3": 6 - anx[4],
         "Q6": est[0], "Q7": est[1], "Q10": est[2], "Q8": 6 - est[3], "Q9": 6 - est[4]}
    for i in range(1, 11):
        data[f"Q{i}"] = q[f"Q{i}"]
    dur = rng.integers(150, 301, N)
    for i in INVALID_IDS:
        dur[i - 1] = int(rng.integers(25, 56))
    data["duration_seconds"] = dur
    cols = ["id", "gender", "grade"] + [f"Q{i}" for i in range(1, 11)] + ["duration_seconds"]
    return pd.DataFrame(data)[cols]


if __name__ == "__main__":
    frame = build_frame()
    if len(sys.argv) > 1:
        frame.to_csv(sys.argv[1], index=False, encoding="utf-8", lineterminator="\n")
        print("written:", sys.argv[1], len(frame), "rows")
    else:
        print(frame.head(6).to_string(index=False))
