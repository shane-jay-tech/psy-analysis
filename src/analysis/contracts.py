"""Versioned, backward-compatible contracts for analysis orchestration."""

from __future__ import annotations

from typing import Any, Mapping


ANALYSIS_RESULT_SCHEMA = "psy-analysis/analysis-result/v1"


class AnalysisResult(dict[str, Any]):
    """Dict-compatible analysis result with an explicit schema version.

    Existing UI and exporters can continue using ``result[\"...\"]`` and
    ``result.get(...)``.  New code can depend on ``schema_version`` and
    ``canonical_method_id`` instead of probing an unversioned dictionary.
    """

    def __init__(self, values: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        super().__init__(values or {}, **kwargs)
        self.setdefault("schema_version", ANALYSIS_RESULT_SCHEMA)

    @property
    def schema_version(self) -> str:
        return str(self["schema_version"])

    @property
    def canonical_method_id(self) -> str:
        return str(self.get("canonical_method_id") or self.get("test_type") or "")

