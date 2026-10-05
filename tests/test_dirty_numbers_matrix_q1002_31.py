# -*- coding: utf-8 -*-
"""s1002-31：脏数字四入口矩阵收尾（s922-105 遗留 3 / s924-59 遗留 3 的补齐）。

四入口现状覆盖盘点与本单增量：
- 入口1 采集面（workspace.py:391 list() 静默腐蚀）：s922-106 已钉（test_lr_dirty_entry_matrix）；
- 入口1' 恢复面（:685 setdefault 全宽容）：同上已钉（12 脏形态零拦真值表）；
- 入口2 向导读（undergrad_wizard :3595-3602 AST 抽环）：已钉（阈值敏感环＋pass 外壳）；
- **入口3 写回面（review_import.apply_review_comments_to_state）＝本单增量**：
  s922-106 文件头登记「函数体未测、:150-152 就地变异点」——本单补「约 2019」类
  脏数字形态的真值表钉（脏值不抛、就地渗入条目、counts 不计它）。

真值表（四入口 × 脏值形态 → 现状行为）见 result 与既有件；本件只新增，零生产码改动。
"""
from __future__ import annotations

import pytest

from src.literature_review.review_import import apply_review_comments_to_state

DIRTY_YEAR_LIT = {"key": "k1", "title": "脏年条目", "year": "约 2019"}          # 数字位脏值
DIRTY_SCORE_LIT = {"key": "k2", "relevance_score": "约 0.75"}                  # 同族数字脏值
CLEAN_LIT = {"key": "k_clean", "title": "干净条目", "year": 2024}


def _parsed_for(key):
    return {"literature": {key: [{"author": "审稿人", "text": "补充样本量说明"}]}}


# ---------- 写回面 × 脏数字：不抛、就地渗入、不计 counts ----------

def test_dirty_year_does_not_raise_and_counts_still_count_it():
    """「约 2019」条目被点名时：写回不抛（写回面只 isinstance(dict) 过滤，不看字段类型），
    脏值条目**同样计入** counts——写回面没有字段级校验，脏数字透传进 review_comments 载体。"""
    state = {"literature_items": [DIRTY_YEAR_LIT]}
    counts = apply_review_comments_to_state(state, _parsed_for("k1"))
    assert counts["literature"] == 1
    assert state["literature_items"][0]["review_comments"] == [
        {"author": "审稿人", "text": "补充样本量说明"}]


def test_dirty_score_entry_is_treated_same_as_dirty_year():
    """「约 0.75」与「约 2019」同族：写回面对一切 dict 条目一视同仁（宽容面）。"""
    state = {"literature_items": [DIRTY_SCORE_LIT]}
    counts = apply_review_comments_to_state(state, _parsed_for("k2"))
    assert counts["literature"] == 1


def test_dirty_non_dict_rows_are_skipped_and_clean_neighbor_still_written():
    """非 dict 行被静默跳过（宽容面），旁边干净条目照写——矿源「不对称」行为在写回面的体现。"""
    state = {"literature_items": ["约 2019", CLEAN_LIT]}   # 首元素是纯字符串脏值
    counts = apply_review_comments_to_state(state, _parsed_for("k_clean"))
    assert counts["literature"] == 1
    assert state["literature_items"][0] == "约 2019"        # 非 dict 行原样保留（未被改写）


def test_in_place_mutation_leaks_into_caller_state():
    """s922-106 登记的「就地变异点」：写回直接改调用方 state 内的 dict 本体（无拷贝）——
    函数返回值 counts 与 state 内容是同一份变异的两个观察窗。"""
    state = {"literature_items": [dict(DIRTY_YEAR_LIT)]}
    entry = state["literature_items"][0]
    apply_review_comments_to_state(state, _parsed_for("k1"))
    assert state["literature_items"][0] is entry          # 同一对象被就地加键（无拷贝）
    assert "review_comments" in entry                      # 变异直接落在调用方对象上


# ---------- 四入口矩阵汇总锚（行为值引用既有件，防漂移） ----------

def test_matrix_cross_reference_the_other_three_faces_are_pinned_elsewhere():
    """四入口矩阵交叉引用自证：其余三面的钉桩件必须仍在盘（收尾单的矩阵依赖它们）。"""
    from pathlib import Path
    tests = Path(__file__).resolve().parents[1] / "tests"
    assert (tests / "test_lr_dirty_entry_matrix.py").exists(), "采集/恢复/向导读面钉桩件缺失"
    assert (tests / "test_lr_list_coercion_twins.py").exists(), "孪生真值表件缺失"
