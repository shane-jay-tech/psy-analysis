"""实验设计LLM引擎测试"""

import pytest
from unittest.mock import patch, MagicMock

from src.experiment_design.llm_engine import (
    design_experiment_llm,
    design_experiment_llm_async,
    cancel_design_request,
    CancelledLLMError,
    LLMEngineError,
    LLMResponseParseError,
)


class TestDesignExperimentLLM:
    def test_design_experiment_llm_basic(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "background": "Test background",
            "hypotheses": ["H1: Test hypothesis"],
            "research_questions": ["RQ1: Test question"],
            "iv_details": [],
            "dv_details": [],
            "procedure_phases": [],
            "analysis_plan": "Use t-test",
            "ethics_notes": ["Get consent"],
            "expected_results": "Significant effect"
        }"""

        with patch("src.experiment_design.llm_engine.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

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
        with patch("src.experiment_design.llm_engine.OpenAI"):
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
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json"

        with patch("src.experiment_design.llm_engine.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

            with pytest.raises(LLMResponseParseError):
                design_experiment_llm(
                    topic="Test",
                    api_key="sk-test",
                    base_url="https://api.test.com",
                    model="test-model",
                )
