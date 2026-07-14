"""实验设计LLM引擎测试"""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from src.experiment_design.llm_engine import (
    design_experiment_llm,
    design_experiment_llm_async,
    cancel_design_request,
    CancelledLLMError,
    LLMEngineError,
    LLMResponseParseError,
)


@dataclass
class _FakeLLMResponse:
    ok: bool = True
    cancelled: bool = False
    content: str = ""
    error: str = ""


class TestDesignExperimentLLM:
    def test_design_experiment_llm_basic(self):
        fake_resp = _FakeLLMResponse(
            ok=True,
            content="""{
            "background": "Test background",
            "hypotheses": ["H1: Test hypothesis"],
            "research_questions": ["RQ1: Test question"],
            "iv_details": [],
            "dv_details": [],
            "procedure_phases": [],
            "analysis_plan": "Use t-test",
            "ethics_notes": ["Get consent"],
            "expected_results": "Significant effect"
        }""",
        )

        with patch("src.llm_gateway.gateway.llm_chat", return_value=fake_resp) as mock_chat:
            result = design_experiment_llm(
                topic="Test topic",
                api_key="sk-test",
                base_url="https://api.test.com",
                model="test-model",
            )

        assert result["llm_enhanced"] is True
        assert result["background"] == "Test background"
        assert result["hypotheses"] == ["H1: Test hypothesis"]
        assert result["analysis_plan"] == "Use t-test"

    def test_cancelled_before_call(self):
        from src.experiment_design.llm_engine import _alloc_cancel_id, cancel_flags
        cid = _alloc_cancel_id()
        cancel_flags[cid] = True
        with pytest.raises(CancelledLLMError):
            design_experiment_llm(
                topic="Test",
                api_key="sk-test",
                base_url="https://api.test.com",
                model="test-model",
                cancel_id=cid,
            )

    def test_cancel_design_request(self):
        from src.experiment_design.llm_engine import _alloc_cancel_id
        cid = _alloc_cancel_id()
        assert cancel_design_request(cid) is True
        assert cancel_design_request(99999) is False

    def test_async_returns_future_and_cancel_id(self):
        fake_resp = _FakeLLMResponse(ok=True, content='{"background":"x"}')
        with patch("src.llm_gateway.gateway.llm_chat", return_value=fake_resp):
            result = design_experiment_llm_async(
                topic="Test",
                api_key="sk-test",
                base_url="https://api.test.com",
                model="test-model",
            )
            assert "future" in result
            assert "cancel_id" in result
            assert isinstance(result["cancel_id"], int)

    def test_parse_error_on_invalid_json(self):
        fake_resp = _FakeLLMResponse(ok=True, content="not json")

        with patch("src.llm_gateway.gateway.llm_chat", return_value=fake_resp):
            with pytest.raises(LLMResponseParseError):
                design_experiment_llm(
                    topic="Test",
                    api_key="sk-test",
                    base_url="https://api.test.com",
                    model="test-model",
                )
