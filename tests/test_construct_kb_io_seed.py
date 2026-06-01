"""I/O 心理学方向 KB 种子条目回归（2026-05-30 加）。

验证：
- Phase A: 3 条已有 OB 构念的 established_scales 已扩展（含 Netemeyer / Farh / Chen & Francesco 等关键引用）
- Phase B: 5 条新增构念可被 _lookup_kb_scales 命中，且字段完整
- Schema 一致性：新增条目必填字段在、维度结构合法
"""

from __future__ import annotations

import pytest

from src.questionnaire.construct_kb import CONSTRUCTS
from src.questionnaire.llm_engine_premium import _lookup_kb_scales


# ---------------------------------------------------------------------------
# Phase A —— 3 条已有条目扩展验证
# ---------------------------------------------------------------------------

class TestPhaseAAugmentedScales:
    def test_organizational_commitment_has_chinese_revision(self):
        c = CONSTRUCTS["组织承诺"]
        scales = c["established_scales"]
        assert len(scales) >= 2
        joined = " ".join(scales)
        assert "Chen & Francesco" in joined or "Chen" in joined, (
            "组织承诺 应录入华人本土化量表 (Chen & Francesco, 2003)"
        )
        # references 也应同步补全
        refs = " ".join(c["references"])
        assert "Chen, Z. X." in refs or "Chen" in refs

    def test_work_family_conflict_has_netemeyer(self):
        c = CONSTRUCTS["工作-家庭冲突"]
        scales = c["established_scales"]
        assert len(scales) >= 2
        joined = " ".join(scales)
        assert "Netemeyer" in joined, (
            "工作-家庭冲突 应录入 Netemeyer (1996) 双向冲突量表"
        )

    def test_ocb_has_farh_chinese_scale(self):
        c = CONSTRUCTS["组织公民行为"]
        scales = c["established_scales"]
        assert len(scales) >= 2
        joined = " ".join(scales)
        assert "Farh" in joined, (
            "组织公民行为 应录入 Farh 华人 OCB 量表"
        )


# ---------------------------------------------------------------------------
# Phase B —— 5 条新构念查表与字段完整性
# ---------------------------------------------------------------------------

NEW_CONSTRUCTS = [
    "员工敬业度",
    "家长式领导",
    "伦理型领导",
    "领导-成员交换",
    "工作旺盛感",
]


class TestPhaseBNewConstructs:
    @pytest.mark.parametrize("name", NEW_CONSTRUCTS)
    def test_lookup_returns_nonempty_scales(self, name):
        scales = _lookup_kb_scales(name)
        assert isinstance(scales, list)
        assert len(scales) >= 1, f"{name} 应有至少 1 条 established_scale"
        # _lookup_kb_scales 最多返回 5 条
        assert len(scales) <= 5

    @pytest.mark.parametrize("name", NEW_CONSTRUCTS)
    def test_definition_is_substantial(self, name):
        c = CONSTRUCTS[name]
        defn = c["definition"]
        assert len(defn) >= 50, f"{name} 的 definition 太短（{len(defn)} 字）"

    @pytest.mark.parametrize("name", NEW_CONSTRUCTS)
    def test_dimensions_present(self, name):
        c = CONSTRUCTS[name]
        dims = c["dimensions"]
        assert isinstance(dims, list) and len(dims) >= 1, (
            f"{name} 至少应有一个维度"
        )

    def test_uwes_signature_in_engagement(self):
        """员工敬业度 must reference UWES — 用户方向最高频构念。"""
        scales = _lookup_kb_scales("员工敬业度")
        joined = " ".join(scales)
        assert "UWES" in joined

    def test_paternalistic_leadership_is_chinese_localized(self):
        """家长式领导 应注明华人本土化 + 郑伯埙 / 樊景立 / Cheng 出处。"""
        c = CONSTRUCTS["家长式领导"]
        joined = " ".join(c["established_scales"]) + " " + " ".join(c["references"])
        assert any(k in joined for k in ["郑伯埙", "Cheng", "Farh"]), (
            "家长式领导应录入郑伯埙 (2000) / Cheng et al. (2004) 出处"
        )


# ---------------------------------------------------------------------------
# Schema 一致性
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    @pytest.mark.parametrize("name", NEW_CONSTRUCTS)
    def test_required_fields(self, name):
        c = CONSTRUCTS[name]
        for field in [
            "name_zh", "name_en", "domain", "definition",
            "dimensions", "typical_scale", "established_scales", "references",
        ]:
            assert field in c, f"{name} 缺字段 {field}"
            assert c[field], f"{name} 字段 {field} 为空"

        # dimensions 子项结构
        for i, dim in enumerate(c["dimensions"]):
            assert "name" in dim and dim["name"], f"{name}[dim {i}] 缺 name"
            assert "desc" in dim and dim["desc"], f"{name}[dim {i}] 缺 desc"
            assert "item_count" in dim, f"{name}[dim {i}] 缺 item_count"
            assert isinstance(dim["item_count"], int), (
                f"{name}[dim {i}] item_count 应为 int"
            )
            assert "example" in dim and dim["example"], f"{name}[dim {i}] 缺 example"

        # domain 必须是已知标签之一
        assert c["domain"] == "组织行为", (
            f"{name} domain 应为「组织行为」（与现有 I/O 条目对齐），现为「{c['domain']}」"
        )
