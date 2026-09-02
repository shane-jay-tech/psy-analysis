"""Central method metadata used by execution, cards, tables, and UI exposure.

The catalog deliberately separates a public canonical ID from an execution ID.
Some legacy execution IDs (for example ``repeated_anova``) must remain accepted
because they are persisted in workspaces, while downstream renderers use a newer
canonical/card ID.  Keeping that translation here prevents each layer from
maintaining its own alias list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping


MethodLevel = Literal["default", "advanced", "experimental"]


@dataclass(frozen=True)
class MethodDefinition:
    method_id: str
    aliases: tuple[str, ...] = ()
    table_group: str | None = None
    card_id: str | None = None
    level: MethodLevel = "experimental"

    @property
    def all_ids(self) -> tuple[str, ...]:
        return (self.method_id, *self.aliases)


def _m(
    method_id: str,
    *,
    aliases: tuple[str, ...] = (),
    table: str | None = None,
    card: str | None = None,
    level: MethodLevel = "experimental",
) -> MethodDefinition:
    return MethodDefinition(method_id, aliases, table, card, level)


METHOD_CATALOG: tuple[MethodDefinition, ...] = (
    _m("descriptive", aliases=("descriptive_statistics",), table="descriptive", card="descriptive", level="default"),
    _m("pearson_corr", aliases=("pearson_correlation",), table="pearson_corr", card="pearson_corr", level="default"),
    _m("spearman_corr", aliases=("spearman_correlation",), table="pearson_corr", card="spearman_corr", level="default"),
    _m("partial_corr", aliases=("partial_correlation",), card="partial_corr", level="advanced"),
    _m("point_biserial"),
    _m("independent_ttest", aliases=("independent_t_test",), table="independent_ttest", card="independent_ttest", level="default"),
    _m("paired_ttest", aliases=("paired_t_test",), table="paired_ttest", card="paired_ttest", level="default"),
    _m("one_sample_ttest", table="one_sample_ttest", card="one_sample_ttest", level="default"),
    _m("one_way_anova", table="one_way_anova", card="one_way_anova", level="default"),
    _m("two_way_anova", aliases=("factorial_anova",), table="two_way_anova", card="two_way_anova", level="default"),
    _m("repeated_measures_anova", aliases=("repeated_anova", "rm_anova"), table="repeated_measures_anova", card="repeated_measures_anova", level="default"),
    _m("mixed_anova", table="mixed_anova", card="mixed_anova", level="advanced"),
    _m("welch_anova"),
    _m("ancova", card="ancova", level="advanced"),
    _m("mann_whitney", aliases=("mann_whitney_u",), table="mann_whitney", card="mann_whitney", level="default"),
    _m("wilcoxon", aliases=("wilcoxon_signed_rank",), table="wilcoxon", card="wilcoxon", level="default"),
    _m("kruskal_wallis", table="kruskal_wallis", card="kruskal_wallis", level="default"),
    _m("friedman"),
    _m("chi_square", aliases=("chi_square_test", "chi_square_independence"), table="chi_square", card="chi_square", level="default"),
    _m("chi_square_gof", table="chi_square", card="chi_square", level="advanced"),
    _m("fisher_exact"),
    _m("linear_regression", table="multiple_regression", level="advanced"),
    _m("multiple_regression", table="multiple_regression", card="multiple_regression", level="default"),
    _m("hierarchical_regression", table="multiple_regression", card="hierarchical_regression", level="default"),
    _m("logistic_regression", table="logistic_regression", card="logistic_regression", level="advanced"),
    _m("binary_logistic", table="logistic_regression", card="binary_logistic", level="advanced"),
    _m("ordinal_logistic", table="logistic_regression", card="logistic_regression", level="advanced"),
    _m("multinomial_logistic", table="logistic_regression", card="logistic_regression", level="advanced"),
    _m("manova"),
    _m("cronbach_alpha", table="cronbach_alpha", card="cronbach_alpha", level="default"),
    _m("mcdonalds_omega", aliases=("mcdonald_omega", "omega"), table="cronbach_alpha", card="mcdonalds_omega", level="default"),
    _m("split_half"),
    _m("composite_reliability"),
    _m("icc"),
    _m("test_retest"),
    _m("cohens_kappa"),
    _m("fleiss_kappa"),
    _m("efa", aliases=("exploratory_factor_analysis",), table="efa", card="efa", level="advanced"),
    _m("cfa", aliases=("confirmatory_factor_analysis",), table="cfa", card="cfa", level="advanced"),
    _m("sem", aliases=("structural_equation_model",), table="cfa", card="sem", level="advanced"),
    _m("ave_cr", aliases=("ave",), card="ave_cr", level="advanced"),
    _m("discriminant_validity", aliases=("discriminant_fl", "discriminant_htmt"), card="discriminant_validity", level="advanced"),
    _m("cvi"),
    _m("criterion_validity"),
    _m("known_groups_validity"),
    _m("ai_item_review"),
    _m("mediation", table="mediation", card="mediation", level="advanced"),
    _m("moderation", table="moderation", card="moderation", level="advanced"),
    _m("moderated_mediation"),
    _m("hlm", aliases=("hierarchical_linear_model", "mixed_effects"), table="hlm", card="hlm", level="advanced"),
    _m("normality_test"),
    _m("levene_test"),
)


_BY_ID: dict[str, MethodDefinition] = {}
for _definition in METHOD_CATALOG:
    for _method_id in _definition.all_ids:
        if _method_id in _BY_ID:
            raise RuntimeError(f"duplicate method ID in catalog: {_method_id}")
        _BY_ID[_method_id] = _definition


def get_method_definition(method_id: str) -> MethodDefinition | None:
    return _BY_ID.get(method_id)


def resolve_method_id(method_id: str) -> str:
    definition = get_method_definition(method_id)
    return definition.method_id if definition else method_id


def get_table_route_group(method_id: str) -> str | None:
    definition = get_method_definition(method_id)
    return definition.table_group if definition else None


def get_card_builder_id(method_id: str) -> str | None:
    definition = get_method_definition(method_id)
    return definition.card_id if definition else None


def get_method_level(method_id: str) -> MethodLevel:
    definition = get_method_definition(method_id)
    return definition.level if definition else "experimental"


def known_method_ids() -> frozenset[str]:
    return frozenset(_BY_ID)


def canonical_id_map() -> dict[str, str]:
    return {method_id: definition.method_id for method_id, definition in _BY_ID.items()}


def validate_method_contracts(
    registry: Mapping[str, object], card_builders: Mapping[str, object]
) -> list[str]:
    """Return cross-layer catalog errors without importing the layers here."""
    errors: list[str] = []
    for method_id in registry:
        if method_id not in _BY_ID:
            errors.append(f"registered method is missing from catalog: {method_id}")
    for method_id in card_builders:
        if method_id not in _BY_ID:
            errors.append(f"card builder is missing from catalog: {method_id}")
    for definition in METHOD_CATALOG:
        if definition.card_id and definition.card_id not in card_builders:
            errors.append(
                f"catalog card target is not registered: {definition.method_id} -> {definition.card_id}"
            )
    return errors

