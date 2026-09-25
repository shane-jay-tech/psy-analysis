"""数据字典（codebook）：题号／变量名／量表／维度／量尺／反向题／缺失值编码的统一口径。

字典版本见 ``CODEBOOK_VERSION``；人读版与冲突清单取证见
``docs/insights/psy-data-dictionary-20260925.md``。

边界（本模块故意**不**做的事）：

* 不做任何统计计算，也不改写统计量 —— 字典只规定"字段怎么读写"，
  alpha／omega／项目数／样本量／效应量／置信区间的**数值**一律不经此处。
* 不改写数据值：缺失值编码只被**报告**（``find_missing_code_hits``），
  不在此静默替换成 NaN；是否替换属清洗策略，由调用方决定。
* 不接生产调用点：``reject_unknown_fields`` 目前只由测试驱动，
  导入面板仍走 ``import_cleaning.classify_columns`` 的宽松分桶。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

CODEBOOK_VERSION = "psy-analysis/codebook/v1"
SUPPORTED_CODEBOOK_VERSIONS = frozenset({CODEBOOK_VERSION})

#: 唯一键：题号与变量名在一份字典里都必须各自唯一，且不得跨维度复用变量名。
UNIQUE_KEY_FIELDS: tuple[str, ...] = ("item_no", "var_name")

#: 无版本标记的字典（如现存 demo 的 questionnaire_schema.json）落到这个哨兵值，
#: 而不是伪造一个版本号。
NO_VERSION_MARKER = "<no-version>"


class UnknownFieldError(ValueError):
    """导入数据含有字典未声明的字段。"""

    def __init__(self, unknown_fields: Sequence[str], version: str) -> None:
        self.unknown_fields = list(unknown_fields)
        self.version = version
        super().__init__(
            f"字典 {version} 未声明以下字段，已按字典拒绝导入："
            f"{', '.join(self.unknown_fields)}"
        )


@dataclass(frozen=True)
class CodebookEntry:
    """一条题目级字典项。"""

    item_no: str
    var_name: str
    scale: str = ""
    dimension: str = ""
    reverse: bool = False
    scale_min: float = 1
    scale_max: float = 5
    missing_codes: tuple[str, ...] = ()
    label: str = ""


@dataclass(frozen=True)
class NonItemField:
    """非题目列（人口学／元数据／时间戳）的字典声明。"""

    var_name: str
    role: str  # demographic | metadata | timestamp
    missing_codes: tuple[str, ...] = ()
    note: str = ""


@dataclass
class CodebookConflict:
    """冲突清单条目：字典内部自相矛盾之处，机器生成。"""

    code: str
    detail: str
    keys: tuple[str, ...] = ()


@dataclass
class Codebook:
    """版本化字典。"""

    version: str = CODEBOOK_VERSION
    title: str = ""
    entries: list[CodebookEntry] = field(default_factory=list)
    non_item_fields: list[NonItemField] = field(default_factory=list)
    #: 未在字典里声明的字段如何处理：``reject`` / ``report``。默认拒绝。
    unknown_field_policy: str = "reject"

    # ---------------- 唯一键与冲突清单 ----------------

    def conflicts(self) -> list[CodebookConflict]:
        out: list[CodebookConflict] = []
        if self.version not in SUPPORTED_CODEBOOK_VERSIONS:
            out.append(CodebookConflict(
                "E_VERSION",
                f"字典版本 {self.version!r} 不在受支持集合 "
                f"{sorted(SUPPORTED_CODEBOOK_VERSIONS)} 内",
                (self.version,),
            ))
        for key_field in UNIQUE_KEY_FIELDS:
            seen: dict[str, list[str]] = {}
            for i, e in enumerate(self.entries):
                seen.setdefault(getattr(e, key_field), []).append(f"#{i}")
            for val, where in seen.items():
                if len(where) > 1:
                    out.append(CodebookConflict(
                        "E_DUP_KEY",
                        f"唯一键 {key_field}={val!r} 出现 {len(where)} 次",
                        (val,),
                    ))
        by_dim: dict[str, list[str]] = {}
        for e in self.entries:
            by_dim.setdefault(e.var_name, []).append(e.dimension)
        for var_name, dims in by_dim.items():
            if len(set(dims)) > 1:
                out.append(CodebookConflict(
                    "E_MULTI_DIM",
                    f"变量名 {var_name!r} 同时挂在多个维度：{sorted(set(dims))}",
                    (var_name,),
                ))
        declared_item_vars = {e.var_name for e in self.entries}
        declared_other = {f.var_name for f in self.non_item_fields}
        for var_name in sorted(declared_item_vars & declared_other):
            out.append(CodebookConflict(
                "E_ROLE_CLASH",
                f"变量名 {var_name!r} 既声明为题项又声明为非题目列",
                (var_name,),
            ))
        for e in self.entries:
            if e.reverse and e.scale_min == e.scale_max:
                out.append(CodebookConflict(
                    "E_REVERSE_FLAT",
                    f"反向题 {e.var_name!r} 的量尺上下限相同（{e.scale_min}），"
                    "反向计分无意义",
                    (e.var_name,),
                ))
            if e.scale_max < e.scale_min:
                out.append(CodebookConflict(
                    "E_SCALE_RANGE",
                    f"{e.var_name!r} 量尺上下限倒置：[{e.scale_min}, {e.scale_max}]",
                    (e.var_name,),
                ))
            legal = _legal_value_strings(e.scale_min, e.scale_max)
            for code in e.missing_codes:
                if code in legal:
                    out.append(CodebookConflict(
                        "E_MISSING_AMBIGUOUS",
                        f"{e.var_name!r} 的缺失值编码 {code!r} 落在量尺合法取值内，"
                        "无法与真实作答区分",
                        (e.var_name, code),
                    ))
        return out

    # ---------------- 字段清单 ----------------

    def known_fields(self) -> set[str]:
        return ({e.var_name for e in self.entries}
                | {f.var_name for f in self.non_item_fields})

    def find_unknown_fields(self, columns: Iterable[str]) -> list[str]:
        known = self.known_fields()
        return [c for c in columns if c not in known]

    def reject_unknown_fields(
        self, df: pd.DataFrame, *, strict: bool | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """按字典拒绝未知字段。

        ``strict`` 缺省时跟随 ``unknown_field_policy``（默认 ``reject`` ⇒ 抛错）。
        返回 ``(仅含已声明字段的 DataFrame, 未知字段清单)``；不改动任何单元格取值。
        """
        unknown = self.find_unknown_fields(list(df.columns))
        do_strict = self.unknown_field_policy == "reject" if strict is None else bool(strict)
        if do_strict and unknown:
            raise UnknownFieldError(unknown, self.version)
        keep = [c for c in df.columns if c not in unknown]
        return df[keep], unknown

    def find_missing_code_hits(
        self, df: pd.DataFrame
    ) -> dict[str, dict[str, int]]:
        """报告落在字典声明的缺失值编码上的取值次数（只读，不改数据）。"""

        table: dict[str, dict[str, int]] = {}
        codes_by_field: dict[str, tuple[str, ...]] = {
            e.var_name: e.missing_codes for e in self.entries
        }
        codes_by_field.update({f.var_name: f.missing_codes for f in self.non_item_fields})
        for var_name, codes in codes_by_field.items():
            if not codes or var_name not in df.columns:
                continue
            col = df[var_name].astype("string")
            hits = {c: int((col == c).sum()) for c in codes}
            hits = {c: n for c, n in hits.items() if n}
            if hits:
                table[var_name] = hits
        return table


def _legal_value_strings(low: float, high: float) -> set[str]:
    """量尺合法取值的字面写法（整数量尺才穷举，非整数返回空集不误判）。"""

    if int(low) != low or int(high) != high:
        return set()
    return {str(v) for v in range(int(low), int(high) + 1)}


# ---------------------------------------------------------------------------
# 与现存载体的适配（items_loader / import_cleaning / questionnaire_schema.json）
# ---------------------------------------------------------------------------


def codebook_from_schema(
    schema: Mapping[str, Any], *, version: str | None = None
) -> Codebook:
    """从既有 ``questionnaire_schema.json`` 形态构造字典。

    现存 schema 没有版本键，也没有缺失值编码声明；这里**不伪造**版本号，
    缺版本时统一落到 ``NO_VERSION_MARKER``，由 ``conflicts()`` 报 ``E_VERSION``。
    """

    resolved = version or str(schema.get("version") or NO_VERSION_MARKER)
    entries: list[CodebookEntry] = []
    seen: dict[str, int] = {}
    for dim in schema.get("dimensions", []) or []:
        dim_name = str(dim.get("name", ""))
        reverse = {str(x) for x in (dim.get("reverse_items") or [])}
        lo = dim.get("min_score", 1)
        hi = dim.get("max_score", 5)
        for item in dim.get("items", []) or []:
            var_name = str(item)
            seen[var_name] = seen.get(var_name, 0) + 1
            entries.append(CodebookEntry(
                item_no=var_name,
                var_name=var_name,
                scale=str(schema.get("title", "")),
                dimension=dim_name,
                reverse=var_name in reverse,
                scale_min=lo if isinstance(lo, (int, float)) else 1,
                scale_max=hi if isinstance(hi, (int, float)) else 5,
            ))
    non_item = [NonItemField(str(c), "demographic") for c in schema.get("demographics", []) or []]
    non_item += [NonItemField(str(c), "metadata") for c in schema.get("metadata", []) or []]
    return Codebook(
        version=resolved,
        title=str(schema.get("title", "")),
        entries=entries,
        non_item_fields=non_item,
    )


def codebook_from_items_doc(doc: Any, *, dimension: str = "", scale: str = "") -> Codebook:
    """从 ``items_loader.ItemsDoc`` 构造字典。

    ``ItemsDoc.reverse_indices`` 是 0 基题号下标，``ScaleDimension.reverse_items`` 是列名；
    本函数把前者翻成后者，使"反向题"在字典里只有一种书写（``reverse: bool``）。
    """

    reverse_idx = set(getattr(doc, "reverse_indices", []) or [])
    entries: list[CodebookEntry] = []
    for i, text in enumerate(getattr(doc, "items", []) or []):
        var_name = f"Q{i + 1}"
        entries.append(CodebookEntry(
            item_no=var_name,
            var_name=var_name,
            scale=scale,
            dimension=dimension,
            reverse=i in reverse_idx,
            label=str(text),
        ))
    return Codebook(title=getattr(doc, "title", ""), entries=entries)
