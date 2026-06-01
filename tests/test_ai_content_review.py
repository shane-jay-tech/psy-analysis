"""测试 v3.8 AI 题目预审：4 persona 模拟 + 聚合 + Markdown 报告。

⚠ 关键：本模块输出非正式 CVI；测试用 mock LLM，不打真 API。
"""
import json
from unittest.mock import MagicMock

import pytest

from src.llm_gateway import LLMUnavailableError, clear_cache
from src.questionnaire.ai_content_review import (
    AIItemReviewResult,
    ai_content_review,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _ok_config():
    return {
        "provider": "openai", "base_url": "https://x",
        "api_key": "sk-test", "model": "gpt-4", "timeout": 30,
    }


def _build_persona_response(scores_per_item: list, suggestion: str = "") -> str:
    """生成单 persona 的 JSON 数组响应。

    scores_per_item: e.g. [4, 3, 4, 2, 4] —— 每题的 relevance 分数
    """
    arr = []
    for i, rel in enumerate(scores_per_item, start=1):
        arr.append({
            "item_idx": i,
            "relevance": rel,
            "suggestion": suggestion if rel < 4 else "",
        })
    return json.dumps(arr, ensure_ascii=False)


def _multi_response_mock(persona_jsons: list):
    """构造 requests mock：每次 post 调用按顺序返回一个 persona 的响应。"""
    responses = []
    for content in persona_jsons:
        resp = MagicMock(status_code=200)
        resp.json.return_value = {
            "choices": [{"message": {"content": content}}]
        }
        responses.append(resp)
    req = MagicMock()
    req.post.side_effect = responses
    return req


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_ai_content_review_happy_path():
    """4 personas 全成功 → items_table 形状正确，平均/分歧/flagged 都对"""
    clear_cache()
    n_items = 5
    persona_jsons = [
        _build_persona_response([4, 4, 4, 4, 4]),   # 临床派：全 4
        _build_persona_response([4, 3, 4, 4, 4], suggestion="表述可更具体"),  # 测量派
        _build_persona_response([4, 4, 4, 4, 4]),   # 应用派
        _build_persona_response([4, 4, 4, 4, 4]),   # 语言派
    ]
    result = ai_content_review(
        items=[f"题目{i}" for i in range(1, n_items + 1)],
        construct_name="happy_path_社交焦虑",
        construct_definition="个体在社交场合感到不自在和担忧的稳定倾向。",
        llm_config=_ok_config(),
        requests_module=_multi_response_mock(persona_jsons),
    )
    assert isinstance(result, AIItemReviewResult)
    assert result.test_type == "ai_item_review"
    assert result.n_items == n_items
    assert result.n_personas_succeeded == 4
    # 列：序号 + 题目 + 4 persona 名 + 平均 + 分歧 + 改进建议 = 9
    assert result.items_table is not None
    assert result.items_table.shape == (n_items, 9)
    # 题 2 平均 = (4+3+4+4)/4 = 3.75，分歧 = 4-3 = 1
    row2 = result.items_table.iloc[1]
    assert row2["平均"] == 3.75
    assert row2["分歧"] == 1
    # 报告 markdown 包含 disclaimer
    assert "AI 模拟" in result.summary_markdown
    assert "不是" in result.summary_markdown  # disclaimer 关键词


# ---------------------------------------------------------------------------
# 部分失败
# ---------------------------------------------------------------------------

def test_ai_content_review_partial_failure():
    """1 persona 返回非法 JSON → 其他 3 仍成功，n_personas_succeeded=3"""
    clear_cache()
    persona_jsons = [
        "not valid json at all",  # 临床派 解析失败
        _build_persona_response([4, 3, 4]),
        _build_persona_response([4, 4, 4]),
        _build_persona_response([3, 4, 4]),
    ]
    result = ai_content_review(
        items=["partial_题1", "partial_题2", "partial_题3"],
        construct_name="partial_测试构念",
        construct_definition="测试用构念定义，足够长以满足要求。",
        llm_config=_ok_config(),
        requests_module=_multi_response_mock(persona_jsons),
    )
    assert result.n_personas_succeeded == 3
    assert any("临床" in w or "JSON" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# 全部失败
# ---------------------------------------------------------------------------

def test_ai_content_review_all_fail_raises():
    """全部 persona 网络挂掉 → 抛 LLMUnavailableError"""
    clear_cache()
    bad_req = MagicMock()
    bad_req.post.side_effect = RuntimeError("network down")
    with pytest.raises(LLMUnavailableError):
        ai_content_review(
            items=["all_fail_题1", "all_fail_题2", "all_fail_题3"],
            construct_name="all_fail_构念",
            construct_definition="测试用定义。",
            llm_config=_ok_config(),
            requests_module=bad_req,
        )


# ---------------------------------------------------------------------------
# Flagged：低分 / 高分歧
# ---------------------------------------------------------------------------

def test_ai_content_review_flags_low_score():
    """1 题 4 个 persona 全 1 分 → flagged_items 含此题"""
    clear_cache()
    # 题 3 全部低分；其他题 4 分
    persona_jsons = [
        _build_persona_response([4, 4, 1, 4]),
        _build_persona_response([4, 4, 1, 4]),
        _build_persona_response([4, 4, 1, 4]),
        _build_persona_response([4, 4, 1, 4]),
    ]
    items = ["low_题1", "low_题2", "low_题3_被标记", "low_题4"]
    result = ai_content_review(
        items=items,
        construct_name="low_构念",
        construct_definition="测试用定义。",
        llm_config=_ok_config(),
        requests_module=_multi_response_mock(persona_jsons),
    )
    assert "low_题3_被标记" in result.flagged_items


def test_ai_content_review_flags_high_disagreement():
    """1 题 4 个 persona 评分 1/1/4/4 → 分歧 3，flagged"""
    clear_cache()
    persona_jsons = [
        _build_persona_response([4, 1, 4]),  # 题 2 = 1
        _build_persona_response([4, 1, 4]),  # 题 2 = 1
        _build_persona_response([4, 4, 4]),  # 题 2 = 4
        _build_persona_response([4, 4, 4]),  # 题 2 = 4
    ]
    items = ["dis_题1", "dis_题2_分歧", "dis_题3"]
    result = ai_content_review(
        items=items,
        construct_name="dis_构念",
        construct_definition="测试用定义。",
        llm_config=_ok_config(),
        requests_module=_multi_response_mock(persona_jsons),
    )
    # 题 2：avg = (1+1+4+4)/4 = 2.5（< 3）也满足；分歧 = 4-1 = 3 也满足
    assert "dis_题2_分歧" in result.flagged_items
    row = result.items_table[result.items_table["题目"] == "dis_题2_分歧"].iloc[0]
    assert row["分歧"] == 3


# ---------------------------------------------------------------------------
# v4.2 维度模式
# ---------------------------------------------------------------------------


class TestDimensionMode:
    """分维度评分：dimensions 参数 → prompt 注入 + 聚合 dimension_summary。"""

    def _capture_prompt(self, captured):
        """生成一个 mock requests，把每次 post 的 payload 抓到 captured。"""
        responses = []
        for content in [
            _build_persona_response([4, 4, 3, 4, 4, 4]),
            _build_persona_response([4, 4, 3, 4, 4, 4]),
            _build_persona_response([4, 4, 3, 4, 4, 4]),
            _build_persona_response([4, 4, 3, 4, 4, 4]),
        ]:
            resp = MagicMock(status_code=200)
            resp.json.return_value = {"choices": [{"message": {"content": content}}]}
            responses.append(resp)
        req = MagicMock()

        def _post(url, **kwargs):
            captured.append(kwargs.get("json") or {})
            return responses.pop(0)

        req.post.side_effect = _post
        return req

    def test_prompt_includes_dimension_labels(self):
        """启用维度模式 → prompt 中题目带 [维度X] 前缀，且含维度结构块。"""
        clear_cache()
        captured = []
        items = [
            "dim_题1_A", "dim_题2_A",
            "dim_题3_B",
            "dim_题4_C", "dim_题5_C", "dim_题6_C",
        ]
        dims = [
            {"name": "上级互动", "definition": "在上级面前的紧张感",
             "item_indices": [0, 1]},
            {"name": "客户回避", "definition": "陌生客户场合的回避倾向",
             "item_indices": [2]},
            {"name": "会议发言恐惧", "definition": "在会议中公开发言的恐惧",
             "item_indices": [3, 4, 5], "note": "本研究创新"},
        ]
        result = ai_content_review(
            items=items,
            construct_name="职场社交焦虑",
            construct_definition="个体在职场情境下对他人评价的稳定担忧。",
            dimensions=dims,
            llm_config=_ok_config(),
            requests_module=self._capture_prompt(captured),
        )
        # 至少抓到 1 个 prompt
        assert captured, "未捕获到任何 LLM 调用 payload"
        prompt_text = captured[0]["messages"][1]["content"]
        # 维度结构块出现
        assert "维度结构" in prompt_text
        assert "上级互动" in prompt_text
        assert "客户回避" in prompt_text
        assert "会议发言恐惧" in prompt_text
        # 题目前缀
        assert "[上级互动]" in prompt_text
        assert "[会议发言恐惧]" in prompt_text
        # 创新维度提示
        assert "创新" in prompt_text or "融合" in prompt_text
        # 结果 ok
        assert result.dimension_summary is not None
        assert len(result.dimension_summary) == 3

    def test_dimension_summary_aggregation(self):
        """dimension_summary 的均分 / 题数应正确按维度聚合。"""
        clear_cache()
        # 6 题：维度 A=[0,1]（4分），维度 B=[2,3,4,5]（前3题 4分，最后1题 1分 → 标记）
        scores = [4, 4, 4, 4, 4, 1]
        persona_jsons = [_build_persona_response(scores)] * 4
        items = [f"题{i + 1}" for i in range(6)]
        dims = [
            {"name": "A", "definition": "维度A定义", "item_indices": [0, 1]},
            {"name": "B", "definition": "维度B定义", "item_indices": [2, 3, 4, 5]},
        ]
        result = ai_content_review(
            items=items,
            construct_name="agg_构念",
            construct_definition="测试聚合。",
            dimensions=dims,
            llm_config=_ok_config(),
            requests_module=_multi_response_mock(persona_jsons),
        )
        ds = result.dimension_summary
        assert ds is not None
        row_a = ds[ds["维度"] == "A"].iloc[0]
        row_b = ds[ds["维度"] == "B"].iloc[0]
        assert row_a["题数"] == 2
        assert row_b["题数"] == 4
        # A 均分 = 4，B 均分 = (4+4+4+1)/4 = 3.25
        assert row_a["维度均分"] == 4.0
        assert row_b["维度均分"] == 3.25
        # B 维度有 1 题被标记（题6 全1分 < 3）
        assert row_b["标记题数"] == 1
        assert row_a["标记题数"] == 0
        # items_table 含"维度"列
        assert "维度" in result.items_table.columns
        assert result.items_table.iloc[0]["维度"] == "A"
        assert result.items_table.iloc[5]["维度"] == "B"

    def test_dimensions_validation_duplicate_assignment(self):
        """同一题号被两个维度归属 → ValueError"""
        clear_cache()
        with pytest.raises(ValueError, match="只能归属一个维度"):
            ai_content_review(
                items=["x", "y", "z"],
                construct_name="c",
                construct_definition="d",
                dimensions=[
                    {"name": "A", "definition": "da", "item_indices": [0, 1]},
                    {"name": "B", "definition": "db", "item_indices": [1, 2]},
                ],
                llm_config=_ok_config(),
                requests_module=_multi_response_mock([]),
            )

    def test_dimensions_validation_index_out_of_range(self):
        """题号越界 → ValueError"""
        clear_cache()
        with pytest.raises(ValueError, match="题号.*越界|越界"):
            ai_content_review(
                items=["x", "y"],
                construct_name="c",
                construct_definition="d",
                dimensions=[
                    {"name": "A", "definition": "da", "item_indices": [0, 5]},
                ],
                llm_config=_ok_config(),
                requests_module=_multi_response_mock([]),
            )

    def test_dimensions_validation_missing_name(self):
        """维度缺 name → ValueError"""
        clear_cache()
        with pytest.raises(ValueError, match="name"):
            ai_content_review(
                items=["x", "y"],
                construct_name="c",
                construct_definition="d",
                dimensions=[
                    {"definition": "no name", "item_indices": [0]},
                ],
                llm_config=_ok_config(),
                requests_module=_multi_response_mock([]),
            )

    def test_dimensions_validation_duplicate_name(self):
        """两个维度同名 → ValueError"""
        clear_cache()
        with pytest.raises(ValueError, match="重复"):
            ai_content_review(
                items=["x", "y", "z"],
                construct_name="c",
                construct_definition="d",
                dimensions=[
                    {"name": "A", "definition": "da", "item_indices": [0]},
                    {"name": "A", "definition": "另一个A", "item_indices": [1]},
                ],
                llm_config=_ok_config(),
                requests_module=_multi_response_mock([]),
            )

    def test_no_dimensions_keeps_legacy_shape(self):
        """不传 dimensions → items_table 不含"维度"列，dimension_summary 为 None。"""
        clear_cache()
        persona_jsons = [_build_persona_response([4, 4, 4])] * 4
        result = ai_content_review(
            items=["t1", "t2", "t3"],
            construct_name="legacy",
            construct_definition="测试向后兼容。",
            llm_config=_ok_config(),
            requests_module=_multi_response_mock(persona_jsons),
        )
        assert result.dimension_summary is None
        assert result.dimensions is None
        assert "维度" not in result.items_table.columns

    def test_partial_assignment_does_not_crash(self):
        """部分题目未归属维度 → 应仍能跑完，items_table 中未归属题目维度='未分配'。"""
        clear_cache()
        persona_jsons = [_build_persona_response([4, 4, 4, 4])] * 4
        result = ai_content_review(
            items=["a1", "a2", "u3", "u4"],  # u3/u4 不归属
            construct_name="partial_dim",
            construct_definition="部分归属测试。",
            dimensions=[
                {"name": "A", "definition": "da", "item_indices": [0, 1]},
            ],
            llm_config=_ok_config(),
            requests_module=_multi_response_mock(persona_jsons),
        )
        assert "维度" in result.items_table.columns
        assert result.items_table.iloc[2]["维度"] == "未分配"
        assert result.items_table.iloc[3]["维度"] == "未分配"
