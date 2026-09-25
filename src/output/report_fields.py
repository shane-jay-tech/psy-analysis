"""报告字段统一口径 v1：alpha／omega／项目数／样本量／置信区间。

信箱单 `20260925-120658-c36e`。人读版口径表与现存分歧取证见
``docs/insights/psy-report-fields-unification-20260925.md``。

三条硬边界：

1. **不重算、不改写任何数值**：本模块只做"取哪个键、写成一行的哪一段"，
   α／ω／k／N／CI 的数值原样搬运（默认 ``decimals=None`` 即连显示位数都不动）。
2. **不替用户判断可接受阈值**：不引用 ``reliability_bands`` 的档位标签，
   只报数值与区间；阈值判读留在解读层由人做。
3. **不伪完整**：缺键、``None``、``NaN``、类型不符一律走 ``missing_fields`` 提示，
   绝不落成 ``-``／``?`` 这类"看起来是一格"的占位符。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

REPORT_FIELDS_VERSION = "psy-analysis/report-fields/v1"

#: 统一后的字段名（左）与现存载体里的别名（右，按普查顺序）。
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "alpha": ("alpha",),
    "omega": ("omega", "omega_value", "mcdonald_omega"),
    "n_items": ("n_items", "item_count", "n_factors_items"),
    "n_cases": ("n_cases", "n_obs", "sample_size", "total_n", "n"),
    "ci": ("ci",),
}

#: 五个必报字段；缺任何一个都要出提示，不得静默。
REQUIRED_REPORT_FIELDS: tuple[str, ...] = ("alpha", "omega", "n_items", "n_cases", "ci")

#: CI 的两个端点键（现存件里已是这对名字，故不引入新写法）。
CI_ENDPOINT_FIELDS: dict[str, tuple[str, str]] = {
    "ci": ("ci_lower", "ci_upper"),
}

_FIELD_LABELS: dict[str, str] = {
    "alpha": "α",
    "omega": "ω",
    "n_items": "项目数 k",
    "n_cases": "有效样本 N",
    "ci": "95% CI",
}


@dataclass(frozen=True)
class MissingField:
    """一个未成功取到的报告字段。"""

    field: str
    reason: str
    looked_up: tuple[str, ...] = ()

    def render(self) -> str:
        where = f"（已尝试键 {', '.join(self.looked_up)}）" if self.looked_up else ""
        return f"⚠ 缺字段：{_FIELD_LABELS.get(self.field, self.field)} {self.reason}{where}"


def _unwrap(source: Any, key: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(key)
    return getattr(source, key, None)


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not (isinstance(value, float) and math.isnan(value))


def format_value(value: Any, *, decimals: int | None) -> str:
    """数值的书写口径；``decimals=None`` 时原样输出，不做任何舍入。"""

    if decimals is None:
        return str(value)
    if isinstance(value, int):
        return str(value)
    return f"{value:.{decimals}f}"


def _build_ci(source: Any) -> tuple[bool, Any, str]:
    for ci_key, (low_key, high_key) in CI_ENDPOINT_FIELDS.items():
        low, high = _unwrap(source, low_key), _unwrap(source, high_key)
        if low is None and high is None:
            continue
        if not (_is_number(low) and _is_number(high)):
            return False, None, f"端点类型不符（{low_key}={low!r}, {high_key}={high!r}）"
        return True, (low, high), ""
    inline = _unwrap(source, "ci")
    if isinstance(inline, (tuple, list)) and len(inline) == 2 and all(_is_number(x) for x in inline):
        return True, (inline[0], inline[1]), ""
    if inline is None:
        return False, None, "未提供（既无 ci_lower/ci_upper，也无 ci 对）"
    return False, None, f"类型不符（收到 {type(inline).__name__}）"


def read_field(source: Any, field: str) -> tuple[Any, MissingField | None]:
    """按别名顺序取一个报告字段；取不到时返回 ``MissingField``，不返回占位符。"""

    aliases = FIELD_ALIASES.get(field, (field,))
    if field == "ci":
        ok, value, why = _build_ci(source)
        if ok:
            return value, None
        return None, MissingField(field, why, aliases)
    for key in aliases:
        value = _unwrap(source, key)
        if value is None:
            continue
        if not _is_number(value):
            return None, MissingField(field, f"类型不符或为 NaN（键 {key}={value!r}）", aliases)
        return value, None
    return None, MissingField(field, "未提供", aliases)


def collect_report_fields(
    source: Any,
    fields: Sequence[str] = REQUIRED_REPORT_FIELDS,
    *,
    decimals: int | None = None,
) -> tuple[dict[str, Any], list[MissingField]]:
    """一次取齐报告字段。

    返回 ``(取到的字段值, 缺字段清单)``；两者互斥覆盖所有请求字段，
    调用方只要把两段都渲染出来就不可能产出"伪完整"报告。
    """

    values: dict[str, Any] = {}
    missing: list[MissingField] = []
    for field in fields:
        value, miss = read_field(source, field)
        if miss is not None:
            missing.append(miss)
        else:
            values[field] = format_value(value, decimals=decimals) if field != "ci" \
                else f"[{format_value(value[0], decimals=decimals)}, {format_value(value[1], decimals=decimals)}]"
    return values, missing


def render_report_fields(
    source: Any,
    fields: Sequence[str] = REQUIRED_REPORT_FIELDS,
    *,
    decimals: int | None = None,
) -> list[str]:
    """渲染统一字段行；缺字段以 ``⚠ 缺字段：`` 行显式出现。"""

    values, missing = collect_report_fields(source, fields, decimals=decimals)
    lines: list[str] = []
    for field in fields:
        label = _FIELD_LABELS.get(field, field)
        if field in values:
            lines.append(f"{label} = {values[field]}")
    lines.extend(m.render() for m in missing)
    return lines


def missing_fields(
    source: Any, fields: Sequence[str] = REQUIRED_REPORT_FIELDS
) -> list[str]:
    """只要字段名清单，供门禁／自检用。"""

    return [m.field for m in collect_report_fields(source, fields)[1]]
