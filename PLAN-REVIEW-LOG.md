# Plan review log

## Build

- `tests/test_data_transforms.py` — covers all public data transformation operations and error paths.
- `tests/test_privacy_archive_usage.py` — covers privacy scanning, archive persistence, and anonymous usage logs.
- `tests/test_output_formatter.py` — covers APA summaries, effect-size enforcement, and report generation.
- `tests/test_parser_core.py` — covers token filtering and intent-resolution decisions.
- `tests/test_jspsych_data_importer.py` — covers jsPsych CSV/JSONL parsing, normalization, reshaping, and summaries.
- `tests/test_analysis_coverage_gaps.py` — covers MANOVA/MANCOVA and logistic-regression gaps.
- `tests/test_method_exposure.py` — covers method exposure levels and consistency.
- `tests/test_output_interpretation_helpers.py` — covers interpretation thresholds and fallbacks.
- `src/utils/archive_manager.py` — prevents dot-only/path-traversal archive tags.
- `src/output/formatter.py` — accepts a reported zero effect size as valid APA output.
- `COVERAGE_AUDIT.md` — records baseline, final coverage, residual risks, and proof command.

Proof: PASS — 2394 passed, 1 skipped, 88 deselected; branch coverage 51%.

Deviations: online, benchmark, browser E2E, and Playwright tests remain outside the mandatory offline proof as specified. Two minimal production fixes were made for defects exposed by the new regression tests.

Fix rounds used: 2 (test-fixture corrections only).
