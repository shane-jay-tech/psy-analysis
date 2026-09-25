"""分析结果 schema 校验：结果体／警告面／样本量／版本四域。

信箱单 `20260925-120713-7575`。契约口径来源：

* 版本：`src/analysis/contracts.py` 的 ``ANALYSIS_RESULT_SCHEMA``（**本模块只引用、不另立版本号**）；
* 结果体必需键：`src/analysis/runner.run_analysis` 的 docstring 与 ``output = AnalysisResult({...})`` 初始化面。

三条硬规矩：

1. **不为让现网通过而放宽口径**：必需集与判据一律照契约原样；现网结果不合，就如实报红，
   由 ``enforce_result`` 的降级面显式带出，不静默放过。
2. **不输出伪完整结果**：``result is None`` 而 ``errors`` 里没有 error 级条目 ⇒ 判 ``pseudo_complete``；
   样本量取不到 / 取到 ``NaN`` ⇒ 判 ``missing``／``nan``，绝不补 0、不补均值。
3. **不改数值**：本模块只做"读键＋判型＋贴标签"，不计算任何统计量，也不改写已有键的值。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .contracts import ANALYSIS_RESULT_SCHEMA

#: 受支持的版本集合：只有 v1；升版必须在此追加，同时保留旧条目的判读口径。
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({ANALYSIS_RESULT_SCHEMA})

#: 结果体必需键（缺任一个即 error）。``descriptive``/``reasoning``/``data_quality``
#: 在 runner 里初值为 None，属"合法空"，故只判类型不判空。
REQUIRED_RESULT_KEYS: tuple[str, ...] = (
    "schema_version",
    "test_type",
    "canonical_method_id",
    "plan",
    "result",
    "assumptions",
    "errors",
    "charts_data",
)

#: 警告面上允许出现的等级（runner 现网写的是 "warning"）。
ALLOWED_SEVERITIES: frozenset[str] = frozenset({"warning", "error", "critical", "info"})

#: 样本量的合法载体，按优先级取第一个命中的（只读键，不重算）。
SAMPLE_SIZE_CARRIERS: tuple[str, ...] = ("n", "n_cases", "n_obs", "n_valid", "sample_size")

#: 校验结论写回结果时使用的键（降级面专用；不会覆盖任何既有键）。
SCHEMA_REPORT_KEY = "schema_validation"


@dataclass(frozen=True)
class SchemaIssue:
    """一条 schema 问题。``kind`` 与完成标准逐字对应。"""

    domain: str          # result | warnings | sample_size | version
    kind: str            # missing | type | nan | unknown_version | pseudo_complete | bad_severity | empty
    message: str
    severity: str = "error"

    def render(self) -> str:
        return f"[{self.severity}] {self.domain}/{self.kind}: {self.message}"


@dataclass
class SchemaReport:
    """四域校验结论。"""

    issues: list[SchemaIssue] = field(default_factory=list)
    sample_size: int | None = None
    schema_version: str | None = None

    @property
    def errors(self) -> list[SchemaIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[SchemaIssue]:
        return [i for i in self.issues if i.severity != "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def by_domain(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for i in self.issues:
            out.setdefault(i.domain, []).append(i.kind)
        return out

    def render(self) -> str:
        head = f"schema {self.schema_version!r} 样本量={self.sample_size!r} " \
               f"errors={len(self.errors)} warnings={len(self.warnings)}"
        return "\n".join([head, *(i.render() for i in self.issues)])

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sample_size": self.sample_size,
            "ok": self.ok,
            "errors": [i.render() for i in self.errors],
            "warnings": [i.render() for i in self.warnings],
        }


def _unwrap(source: Any, key: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(key)
    return getattr(source, key, None)


def _is_nan(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _looks_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def find_sample_size(source: Any) -> tuple[int | None, SchemaIssue | None]:
    """在声明过的载体里找样本量；找不到／是 NaN／非正整数一律报问题，不猜。"""

    raw: Any = None
    tried: list[str] = []
    nested = _unwrap(source, "result")
    for holder_name, holder in (("output", source), ("result", nested)):
        if holder is None:
            continue
        for key in SAMPLE_SIZE_CARRIERS:
            name = f"{holder_name}.{key}"
            tried.append(name)
            value = _unwrap(holder, key)
            if value is not None:
                raw = value
                break
        if raw is not None:
            break
    if raw is None:
        return None, SchemaIssue("sample_size", "missing",
                                 f"样本量在已声明载体里取不到（尝试过 {', '.join(tried)}）")
    if _is_nan(raw):
        return None, SchemaIssue("sample_size", "nan", "样本量为 NaN，拒绝补 0 或补均值")
    if isinstance(raw, bool):
        return None, SchemaIssue("sample_size", "type", f"样本量类型不符：{raw!r}")
    if isinstance(raw, float):
        if not raw.is_integer():
            return None, SchemaIssue("sample_size", "type", f"样本量非整数：{raw!r}")
        raw = int(raw)
    if not isinstance(raw, int):
        return None, SchemaIssue("sample_size", "type",
                                 f"样本量类型不符：{type(raw).__name__} {raw!r}")
    if raw <= 0:
        return None, SchemaIssue("sample_size", "missing", f"样本量非正数：{raw}")
    return raw, None


def _check_version(source: Any, issues: list[SchemaIssue]) -> str | None:
    value = _unwrap(source, "schema_version")
    if _is_nan(value):
        issues.append(SchemaIssue("version", "nan", "schema_version 为 NaN"))
        return None
    if _looks_missing(value):
        issues.append(SchemaIssue("version", "missing",
                                  "缺 schema_version：结果未经 AnalysisResult 包装，无法判定契约版本"))
        return None
    if not isinstance(value, str):
        issues.append(SchemaIssue("version", "type",
                                  f"schema_version 类型应为 str，实为 {type(value).__name__}"))
        return None
    if value not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(SchemaIssue("version", "unknown_version",
                                  f"版本 {value!r} 不在受支持集合 "
                                  f"{sorted(SUPPORTED_SCHEMA_VERSIONS)} 内"))
    return value


def _check_result_body(source: Any, issues: list[SchemaIssue]) -> None:
    for key in REQUIRED_RESULT_KEYS:
        if key == "schema_version":
            continue
        if isinstance(source, Mapping) and key not in source:
            issues.append(SchemaIssue("result", "missing", f"缺必需键 {key!r}"))
    if isinstance(source, Mapping) and "test_type" in source and not isinstance(source.get("test_type"), str):
        issues.append(SchemaIssue("result", "type",
                                  f"test_type 应为 str，实为 {type(source.get('test_type')).__name__}"))
    for key in ("assumptions", "charts_data"):
        value = _unwrap(source, key)
        if value is None:
            issues.append(SchemaIssue("result", "missing", f"{key} 未提供（runner 契约里它必为 dict）"))
        elif not isinstance(value, Mapping):
            issues.append(SchemaIssue("result", "type",
                                      f"{key} 应为 dict，实为 {type(value).__name__}"))


def _check_warnings(source: Any, issues: list[SchemaIssue]) -> None:
    errors = _unwrap(source, "errors")
    if errors is None:
        return  # 缺键已由结果体报过，不重复计
    if not isinstance(errors, (list, tuple)):
        issues.append(SchemaIssue("warnings", "type",
                                  f"errors 应为 list，实为 {type(errors).__name__}"))
        return
    has_error_level = False
    for idx, entry in enumerate(errors):
        if isinstance(entry, str):
            if not entry.strip():
                issues.append(SchemaIssue("warnings", "empty", f"errors[{idx}] 是空串"))
            continue
        if isinstance(entry, Mapping):
            message = entry.get("message", entry.get("msg"))
            severity = entry.get("severity", "error")
            if severity not in ALLOWED_SEVERITIES:
                issues.append(SchemaIssue("warnings", "bad_severity",
                                          f"errors[{idx}].severity={severity!r} 不在允许集合"))
            if message is None or _is_nan(message):
                issues.append(SchemaIssue("warnings", "nan", f"errors[{idx}] 无 message"))
            elif not isinstance(message, str):
                issues.append(SchemaIssue("warnings", "type",
                                          f"errors[{idx}].message 应为 str，实为 {type(message).__name__}"))
            if severity in ("error", "critical"):
                has_error_level = True
            continue
        issues.append(SchemaIssue("warnings", "type",
                                  f"errors[{idx}] 形态既非 str 也非 dict：{type(entry).__name__}"))

    dq = _unwrap(source, "data_quality")
    if dq is not None:
        dq_warnings = _unwrap(dq, "warnings")
        if dq_warnings is None and isinstance(dq, Mapping):
            dq_warnings = dq.get("warnings")
        if dq_warnings is not None and not isinstance(dq_warnings, (list, tuple)):
            issues.append(SchemaIssue("warnings", "type",
                                      f"data_quality.warnings 应为 list，实为 {type(dq_warnings).__name__}"))
        elif isinstance(dq_warnings, (list, tuple)):
            for idx, w in enumerate(dq_warnings):
                if not isinstance(w, str):
                    issues.append(SchemaIssue("warnings", "type",
                                              f"data_quality.warnings[{idx}] 应为 str，"
                                              f"实为 {type(w).__name__}"))

    if _unwrap(source, "result") is None and not has_error_level:
        issues.append(SchemaIssue("result", "pseudo_complete",
                                  "result 为 None 但警告面没有 error 级条目 ⇒ "
                                  "对外看起来像「跑完了但没结果」，属伪完整，必须显式报错"))


def validate_result(source: Any) -> SchemaReport:
    """四域校验：结果体／警告面／样本量／版本。"""

    issues: list[SchemaIssue] = []
    if source is None or (isinstance(source, Mapping) and not source):
        return SchemaReport(issues=[SchemaIssue("result", "missing", "结果为空对象")])
    version = _check_version(source, issues)
    _check_result_body(source, issues)
    _check_warnings(source, issues)
    n, n_issue = find_sample_size(source)
    if n_issue is not None:
        issues.append(n_issue)
    return SchemaReport(issues=issues, sample_size=n, schema_version=version)


def enforce_result(source: Any, *, mode: str = "annotate") -> Any:
    """按校验结论决定"报错"还是"降级带出"。

    * ``raise``：有任何 error 即抛 ``ResultSchemaError``；
    * ``annotate``（默认）：原对象照旧返回，但把结论写进 ``schema_validation`` 键，
      并把 error 以 ``severity="error"`` 追加进 ``errors`` —— 让已经会渲染错误的下游看得见；
    * ``report``：只校验、不写回。

    三种模式都**不改动任何既有键的值**，只新增结论键与警告条目。
    """

    report = validate_result(source)
    if mode == "report":
        return report
    if mode == "raise":
        if report.errors:
            raise ResultSchemaError(report)
        return source
    if mode != "annotate":
        raise ValueError(f"未知 mode：{mode!r}（可选 raise/annotate/report）")
    if isinstance(source, Mapping):
        if report.errors or report.warnings:
            source[SCHEMA_REPORT_KEY] = report.as_dict()
        for issue in report.errors:
            source.setdefault("errors", []).append({"severity": "error", "message": issue.render()})
    return source


class ResultSchemaError(ValueError):
    """结果不合契约：把整份报告带出来，不吞。"""

    def __init__(self, report: SchemaReport) -> None:
        self.report = report
        super().__init__("分析结果不合 schema 契约：\n" + report.render())


def iter_reports(results: Iterable[Any]) -> list[SchemaReport]:
    """批量校验（交付包多结果场景）；返回逐份结论，不合并、不取交集。"""

    return [validate_result(r) for r in results]
