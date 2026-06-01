"""测试题目质量检查模块"""
from src.questionnaire.item_quality import check_item_quality, ItemQualityReport


def test_item_quality_all_good():
    """质量检查 — 全部通过"""
    items = [
        {"index": 1, "dimension": "认知焦虑", "text": "我经常担心会发生不好的事情", "reverse": False},
        {"index": 2, "dimension": "认知焦虑", "text": "我难以集中注意力在眼前的事情上", "reverse": False},
        {"index": 3, "dimension": "情感焦虑", "text": "我感到紧张不安", "reverse": False},
        {"index": 4, "dimension": "情感焦虑", "text": "我感到容易烦躁", "reverse": False},
        {"index": 5, "dimension": "生理焦虑", "text": "我的心跳比平时快", "reverse": True},
        {"index": 6, "dimension": "生理焦虑", "text": "我睡觉时不容易醒来", "reverse": True},
    ]
    report = check_item_quality(items)
    assert isinstance(report, ItemQualityReport)
    assert report.total_items == 6
    assert report.passed >= 4


def test_item_quality_with_issues():
    """质量检查 — 发现问题"""
    items = [
        {"index": 1, "dimension": "认知", "text": "短", "reverse": False},  # 太短
        {"index": 2, "dimension": "认知", "text": "我觉得学习压力大和人际关系也很困扰我的睡眠质量让我经常失眠", "reverse": False},  # 太长+双筒
        {"index": 3, "dimension": "情感", "text": "我经常担心会发生不好的事情", "reverse": False},
        {"index": 4, "dimension": "情感", "text": "我常常担心会发生不好的事", "reverse": False},  # 冗余
    ]
    report = check_item_quality(items)
    assert report.errors >= 1
    assert report.warnings >= 1


def test_double_barreled_detection():
    """检测双向陈述"""
    items = [
        {"index": 1, "dimension": "焦虑", "text": "我感到紧张和焦虑", "reverse": False},  # 同义并列OK
        {"index": 2, "dimension": "焦虑", "text": "我觉得学习压力大和家庭关系不好", "reverse": False},  # 双筒
    ]
    report = check_item_quality(items)
    # 第二题应该被标记
    item2 = [s for s in report.item_scores if s["index"] == 2][0]
    has_double = any(i["check"] == "双向陈述检查" for i in item2["issues"])
    assert has_double


def test_redundancy_detection():
    """检测冗余题目"""
    items = [
        {"index": 1, "dimension": "焦虑", "text": "我经常感到紧张不安", "reverse": False},
        {"index": 2, "dimension": "焦虑", "text": "我经常感觉到紧张不安", "reverse": False},  # 高度相似
        {"index": 3, "dimension": "焦虑", "text": "我的睡眠质量不好完全无关的话题", "reverse": False},  # 不同
    ]
    report = check_item_quality(items)
    # 第2题应被标记为冗余
    item2 = [s for s in report.item_scores if s["index"] == 2][0]
    has_redundancy = any("冗余" in i["check"] for i in item2["issues"])
    assert has_redundancy


# ==========================================================================
# v3.7.10: 当代测量学规则的本地启发式检查
# ==========================================================================

class TestAbstractnessCheck:
    """v3.7.10: 抽象度检查——题目仅含构念词无行为/情境锚定。"""

    def test_pure_abstract_short_item_flagged(self):
        from src.questionnaire.item_quality import _check_abstractness
        msg = _check_abstractness("我感到焦虑")
        assert "抽象" in msg

    def test_anchored_item_passes(self):
        from src.questionnaire.item_quality import _check_abstractness
        # 含时间锚定
        assert _check_abstractness("过去一周我经常担心难以入睡") == ""
        # 含情境锚定
        assert _check_abstractness("在不熟悉的环境中我会感到紧张") == ""

    def test_long_item_passes_even_without_anchor(self):
        # 长题目即便没明显锚定也不视为过于抽象（避免误报）
        from src.questionnaire.item_quality import _check_abstractness
        assert _check_abstractness("我觉得这个世界对我来说有时候是不公平的而且很难理解") == ""


class TestOverfittingCheck:
    """v3.7.10: 过拟合检查——情境过窄。"""

    def test_two_narrow_nouns_flagged(self):
        from src.questionnaire.item_quality import _check_overfitting
        msg = _check_overfitting("在地铁上手机没电时我会感到不安")
        assert "过窄" in msg or "情境" in msg

    def test_general_situation_passes(self):
        from src.questionnaire.item_quality import _check_overfitting
        assert _check_overfitting("在不熟悉的环境中我会感到紧张") == ""

    def test_single_narrow_noun_in_short_item_warns(self):
        from src.questionnaire.item_quality import _check_overfitting
        msg = _check_overfitting("地铁上我容易紧张")
        # 短题 + 单个罕见词 → 警告
        assert msg != ""


class TestExtremeWordsCheck:
    """v3.7.10: 极端词检查。"""

    def test_extreme_word_flagged(self):
        from src.questionnaire.item_quality import _check_extreme_words
        assert "极端" in _check_extreme_words("我总是感到焦虑")
        assert "极端" in _check_extreme_words("我从不撒谎")
        assert "极端" in _check_extreme_words("我绝对相信他")

    def test_normal_words_pass(self):
        from src.questionnaire.item_quality import _check_extreme_words
        assert _check_extreme_words("我经常感到焦虑") == ""
        assert _check_extreme_words("我有时会担心未来") == ""


class TestHypotheticalCheck:
    """v3.7.10: 假设句检查。"""

    def test_hypothetical_if_then_flagged(self):
        from src.questionnaire.item_quality import _check_hypothetical
        msg = _check_hypothetical("如果有人骂我，我会反击")
        assert "假设" in msg or "想象" in msg

    def test_assumption_form_flagged(self):
        from src.questionnaire.item_quality import _check_hypothetical
        msg = _check_hypothetical("假设遇到困难，我会主动寻求帮助")
        assert msg != ""

    def test_real_behavior_passes(self):
        from src.questionnaire.item_quality import _check_hypothetical
        assert _check_hypothetical("过去一周我经常因小事失眠") == ""


class TestDirectConstructQuestionCheck:
    """v3.7.10: 直接问构念检查。"""

    def test_construct_name_in_text_flagged(self):
        from src.questionnaire.item_quality import _check_direct_construct_question
        msg = _check_direct_construct_question("我的工作满意度高", "工作满意度")
        assert "工作满意度" in msg

    def test_no_construct_name_passes(self):
        from src.questionnaire.item_quality import _check_direct_construct_question
        assert _check_direct_construct_question("我每天上班路上会期待今天的工作", "工作满意度") == ""

    def test_empty_construct_name_skips_check(self):
        from src.questionnaire.item_quality import _check_direct_construct_question
        assert _check_direct_construct_question("我对自己满意", "") == ""


class TestSubjectConsistencyCheck:
    """v3.7.10: 题目主语与 item_subject_template 一致性。"""

    def test_self_subject_required_but_org_used(self):
        from src.questionnaire.item_quality import _check_subject_consistency
        items = [
            {"index": 1, "text": "我经常感到焦虑", "item_type": "construct"},
            {"index": 2, "text": "我们公司的标准很合理", "item_type": "construct"},
        ]
        issues = _check_subject_consistency(items, item_subject_template="我...")
        # 第 2 题违反
        assert any(iss["index"] == 2 for iss in issues)

    def test_attention_check_skipped(self):
        from src.questionnaire.item_quality import _check_subject_consistency
        items = [
            {"index": 1, "text": "请选择 3 以表明你认真作答",
             "item_type": "attention_check"},
        ]
        issues = _check_subject_consistency(items, item_subject_template="我...")
        assert issues == []

    def test_org_subject_with_self_text_flagged(self):
        from src.questionnaire.item_quality import _check_subject_consistency
        items = [
            {"index": 1, "text": "我感到匹配", "item_type": "construct"},
        ]
        issues = _check_subject_consistency(items, item_subject_template="我们公司的标准...")
        assert len(issues) == 1

    def test_no_template_skips_check(self):
        from src.questionnaire.item_quality import _check_subject_consistency
        items = [{"index": 1, "text": "我们公司很好", "item_type": "construct"}]
        # 不传 template → 跳过
        assert _check_subject_consistency(items) == []


class TestMirrorReverseCheck:
    """v3.7.10: 镜像反向题检查。"""

    def test_mirror_reverse_flagged(self):
        from src.questionnaire.item_quality import _check_mirror_reverse
        items = [
            {"index": 1, "dimension": "D1", "text": "我感到自信", "reverse": False,
             "item_type": "construct"},
            {"index": 2, "dimension": "D1", "text": "我感到不自信", "reverse": True,
             "item_type": "construct"},
        ]
        issues = _check_mirror_reverse(items)
        assert any(iss["index"] == 2 for iss in issues)

    def test_real_reverse_situation_passes(self):
        from src.questionnaire.item_quality import _check_mirror_reverse
        items = [
            {"index": 1, "dimension": "D1", "text": "我感到自信",
             "reverse": False, "item_type": "construct"},
            {"index": 2, "dimension": "D1", "text": "遇到挫折时我容易情绪崩溃连自己都吓到",
             "reverse": True, "item_type": "construct"},
        ]
        issues = _check_mirror_reverse(items)
        assert issues == []


class TestAttentionCheckQuota:
    """v3.7.10: 注意力检测题数量配额。"""

    def test_zero_attention_flags_warning(self):
        from src.questionnaire.item_quality import _check_attention_check_quota
        items = [
            {"index": i, "text": f"题{i}", "item_type": "construct"}
            for i in range(1, 11)
        ]
        warnings = _check_attention_check_quota(items)
        assert any("数量不足" in w or "≥ 1" in w for w in warnings)

    def test_in_range_passes(self):
        from src.questionnaire.item_quality import _check_attention_check_quota
        items = [
            {"index": i, "text": f"题{i}", "item_type": "construct"}
            for i in range(1, 21)
        ] + [
            {"index": 21, "text": "请选3", "item_type": "attention_check"},
            {"index": 22, "text": "请选最右", "item_type": "attention_check"},
        ]
        warnings = _check_attention_check_quota(items)
        assert warnings == []

    def test_too_many_attention_warns(self):
        from src.questionnaire.item_quality import _check_attention_check_quota
        items = [
            {"index": i, "text": f"题{i}", "item_type": "construct"}
            for i in range(1, 6)
        ] + [
            {"index": i, "text": f"检测{i}", "item_type": "attention_check"}
            for i in range(6, 12)   # 6 道注意力题 vs 5 道构念题
        ]
        warnings = _check_attention_check_quota(items)
        assert any("过多" in w for w in warnings)


class TestV3710SchemaIntegration:
    """v3.7.10: ItemQualityReport schema 扩展 + check_item_quality 新参数集成。"""

    def test_overall_warnings_field_exists(self):
        items = [
            {"index": i, "dimension": "D1", "text": f"过去一周题目{i}内容", "reverse": False,
             "item_type": "construct"}
            for i in range(1, 6)
        ]   # 无注意力检测题 → 应触发 overall_warning
        report = check_item_quality(items)
        assert hasattr(report, "overall_warnings")
        assert len(report.overall_warnings) >= 1

    def test_attention_check_excluded_from_per_item_score(self):
        """注意力检测题不计入构念题质检（避免被识别为'抽象/直问构念'）。"""
        items = [
            {"index": 1, "dimension": "D1", "text": "过去一周我经常担心未来",
             "reverse": False, "item_type": "construct"},
            {"index": 2, "dimension": "_attention_check",
             "text": "请选3", "reverse": False, "item_type": "attention_check"},
        ]
        report = check_item_quality(items)
        # total_items 仅算构念题（1 道）
        assert report.total_items == 1
        # 注意力题不在 item_scores 里
        assert all(s["index"] != 2 for s in report.item_scores)

    def test_subject_consistency_kwarg_propagates(self):
        items = [
            {"index": 1, "dimension": "D1", "text": "我们公司的标准很合理",
             "reverse": False, "item_type": "construct"},
            {"index": 2, "dimension": "D1", "text": "过去一周我经常感到焦虑",
             "reverse": False, "item_type": "construct"},
        ]
        # 模板要求自评（"我..."）
        report = check_item_quality(items, item_subject_template="我...")
        item1 = next(s for s in report.item_scores if s["index"] == 1)
        # 第 1 题应该有"主语一致性"问题
        assert any(iss["check"] == "主语一致性检查" for iss in item1["issues"])

    def test_mirror_reverse_integrated(self):
        items = [
            {"index": 1, "dimension": "D1", "text": "我感到自信", "reverse": False,
             "item_type": "construct"},
            {"index": 2, "dimension": "D1", "text": "我感到不自信", "reverse": True,
             "item_type": "construct"},
        ]
        report = check_item_quality(items)
        item2 = next(s for s in report.item_scores if s["index"] == 2)
        assert any(iss["check"] == "镜像反向题检查" for iss in item2["issues"])

    def test_backward_compat_no_kwargs(self):
        """不传新 kwargs 时仍工作（向后兼容）。"""
        items = [
            {"index": 1, "dimension": "D1", "text": "过去一周我经常感到紧张", "reverse": False},
            {"index": 2, "dimension": "D1", "text": "我难以集中注意力做事", "reverse": False},
        ]
        report = check_item_quality(items)
        assert report.total_items == 2
