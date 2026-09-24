"""s923-50：把零接线的 `validate_method_contracts` 复活成三层契约门禁测试。

被试者：`src/analysis/method_catalog.py:139 validate_method_contracts(registry, card_builders)`
三层注册表（读数取自 2026-09-24 现码实测，HEAD `ecd7c98`）：
  · runner 层   `AnalysisRegistry`   48 键
  · catalog 层  `METHOD_CATALOG`     52 个定义／`_BY_ID` 收录 75 个 id（含别名）
  · card 层     `_CARD_BUILDERS`     44 键／29 个去重 builder

接线前的状态（卷宗前提，本班逐条实测复证）：本仓 **src/tests 对该函数零调用**——
`$ rg -n "validate_method_contracts" .` ⇒ 代码侧唯一命中是定义处 `src\\analysis\\method_catalog.py:139`，
另 6 行命中全在 3 份 docs/insights 文件里（散文引用，不是调用方）。
而 `runner._register`（:45-49）只在 import 期锁 runner→catalog 单向（未登记即 `RuntimeError`），
`_BY_ID` 建表时还会拒重复 id（:100-104）⇒ **card_builders→catalog** 与
**catalog.card_id→card_builders** 两个方向此前无任何门禁 ⇒ 本件补的就是这两向的看守。

================================================================================
gate 首跑原始输出（完成标准第 3 条要求原文入账）
================================================================================
`$ .venv/Scripts/python.exe -c "from src.analysis.method_catalog import validate_method_contracts as v;`
   `from src.analysis.runner import AnalysisRegistry as r;`
   `from src.analysis.result_card import _CARD_BUILDERS as c; print(v(r, c))"`

    []

⇒ 现值零错，故按卷宗「空则直接钉 assert errors == []」落断言；本文件因此**不含任何快照豁免清单**。

================================================================================
本门禁拦得住什么／拦不住什么（下面两组用例把两件事分别钉成断言，不留在注释里）
================================================================================
拦得住（`TestGateTeeth` 逐臂实测，每臂"注入一个违规 ⇒ 恰红一条"）：
  1) 注册了但目录未登记的方法        → `registered method is missing from catalog: <id>`
  2) 建了卡但目录未登记的键          → `card builder is missing from catalog: <id>`
  3) 目录声明的 card 目标没有对应卡  → `catalog card target is not registered: <method> -> <card>`

拦不住（`TestGateBlindSpots` 逐臂实测）：
  a) **card 别名复用**：`_CARD_BUILDERS["binary_logistic"] is _CARD_BUILDERS["logistic_regression"]` 为真，
     `ordinal_logistic`／`multinomial_logistic` 连键都没有（`method_catalog.py:70-71` 声明
     `card="logistic_regression"`，靠回落到同一个 builder），而 gate 现值仍是 `[]`。
     ⇒ **"0 错"绝不能当"每型方法都有专用结果卡"的证据**（此点与 docs/insights 的别名普查结论一致）。
  b) catalog→registry 方向：`validate_method_contracts({}, _CARD_BUILDERS)` 返回 `[]` ⇒
     runner 一个 handler 都不注册 gate 也不红（今日确有 10 个目录方法没有 handler）。
  c) 注册键是别名而非 canonical：6 个键能过 gate，只因它们也在 `_BY_ID` 里。
  d) 卡片内容对不对、builder 是否真写出卡：gate 只看**键的存在性**，不看函数体。

分工（避免双份维护）：`tests/test_result_card_registry_snapshot.py`（s922-122）已钉 `_CARD_BUILDERS` 的
44 键／29 builder／14 别名组快照，本件**不重复钉那三个数**；**"新引入别名复用"由该件的
`test_alias_group_table_snapshot` 拦**（BASELINE_ALIAS_GROUPS 逐字比对），本件拦不到——
collapse_cards 变异实测：把 44 个键全塌成一个 builder 时本文件 17 例**全绿**（见 `TestGateBlindSpots`
第一条注释，那是在陈述失明面而非在检测它）。本件另补的是 gate 接线、三条判据的牙，
以及"15 个已注册方法无可达专用卡"这一 gate 自己看不见的面（`TestCardCoverageLedger`）。

红线：全程只用合成假对象/字典副本驱动 gate，未改 `src/` 任何字节，不涉任何统计数值结论。
"""
import sys

from src.analysis import method_catalog, result_card, runner
from src.analysis.method_catalog import METHOD_CATALOG, validate_method_contracts

# ---------------------------------------------------------------------------
# 实测基线（2026-09-24 现码输出；**import 期取的活表快照**，不靠手抄）
# ---------------------------------------------------------------------------
REGISTRY_KEYS_AT_IMPORT = frozenset(runner.AnalysisRegistry)
CARD_KEYS_AT_IMPORT = frozenset(result_card._CARD_BUILDERS)

BASELINE_GATE_ERRORS: list = []

# catalog 中声明了 card 目标的定义数 ⇒ 两张空表时第三条判据应逐条报出这么多条
CARD_TARGET_DECLARATIONS = 33

# 注册键里属于"别名 id"的那 6 个（能过 gate，因为它们在 _BY_ID 里）
REGISTRY_ALIAS_KEYS = frozenset({
    "ave", "chi_square_independence", "discriminant_fl",
    "discriminant_htmt", "mcdonald_omega", "repeated_anova",
})

# 走 result_card.py:107-112 那条三级回退链后仍拿不到专用 builder 的已注册方法
REGISTERED_WITHOUT_REACHABLE_CARD = frozenset({
    "ai_item_review", "cohens_kappa", "composite_reliability", "criterion_validity",
    "cvi", "fleiss_kappa", "friedman", "icc", "known_groups_validity",
    "linear_regression", "manova", "point_biserial", "split_half",
    "test_retest", "welch_anova",
})

MSG_MISSING_IN_CATALOG = "registered method is missing from catalog: {}"
MSG_CARD_NOT_IN_CATALOG = "card builder is missing from catalog: {}"
MSG_CARD_TARGET_MISSING = "catalog card target is not registered: {} -> {}"
GENERIC_CARD_WARNING = "方法 '{}' 暂无专用结果卡模板"


def _live_registry() -> dict:
    """生产活对象的**副本**——任何注入都只改副本，不碰 runner 的表。"""
    return dict(runner.AnalysisRegistry)


def _live_cards() -> dict:
    return dict(result_card._CARD_BUILDERS)


def _reachable_card(method_id: str):
    """复刻 result_card.py:107-112 的三级回退链（键 → 声明的 card 目标 → canonical id）。"""
    builders = result_card._CARD_BUILDERS
    card_id = method_catalog.get_card_builder_id(method_id)
    return (
        builders.get(method_id)
        or builders.get(card_id or "")
        or builders.get(result_card.resolve_method_id(method_id))
    )


# ===========================================================================
# 1) 接线：把 gate 挂回收集/运行链，并钉现值
# ===========================================================================

class TestGateWiring:
    def test_current_registries_pass_gate(self):
        """卷宗主断言：现值三层自洽 ⇒ 钉死为"零错"，任何一层长歪立刻红。"""
        errors = validate_method_contracts(_live_registry(), _live_cards())
        assert errors == BASELINE_GATE_ERRORS, f"三层契约出现新错误：{errors}"

    def test_gate_and_registries_are_the_live_objects(self):
        """同一性护栏：调的是生产函数、喂的是生产活表（防"金档改成钉副本"型静默失明的绿）。"""
        mods = sys.modules
        assert validate_method_contracts is mods["src.analysis.method_catalog"].validate_method_contracts
        assert runner.AnalysisRegistry is mods["src.analysis.runner"].AnalysisRegistry
        assert result_card._CARD_BUILDERS is mods["src.analysis.result_card"]._CARD_BUILDERS

    def test_inputs_are_non_empty_so_the_gate_is_not_vacuous(self):
        """防"两张空表也能拿 0 错"被当成通过：三层都得真有内容。"""
        assert len(runner.AnalysisRegistry) > 40
        assert len(result_card._CARD_BUILDERS) > 40
        assert len(METHOD_CATALOG) > 40


# ===========================================================================
# 2) 牙：三条判据各自独红（合成违规只进副本）
# ===========================================================================

class TestGateTeeth:
    def test_arm_registry_method_missing_from_catalog(self):
        reg = _live_registry()
        reg["__bogus_registered_method__"] = lambda *a, **k: None
        assert validate_method_contracts(reg, _live_cards()) == [
            MSG_MISSING_IN_CATALOG.format("__bogus_registered_method__")
        ]

    def test_arm_card_builder_missing_from_catalog(self):
        cards = _live_cards()
        cards["__bogus_card_key__"] = result_card._CARD_BUILDERS["descriptive"]
        assert validate_method_contracts(_live_registry(), cards) == [
            MSG_CARD_NOT_IN_CATALOG.format("__bogus_card_key__")
        ]

    def test_arm_declared_card_target_missing(self):
        cards = _live_cards()
        cards.pop("descriptive")
        assert validate_method_contracts(_live_registry(), cards) == [
            MSG_CARD_TARGET_MISSING.format("descriptive", "descriptive")
        ]

    def test_declarative_sweep_covers_every_card_declaration(self):
        """第三条判据是"全量声明式普查"：两张空表应逐条报出全部 33 处 card 声明。"""
        errors = validate_method_contracts({}, {})
        assert len(errors) == CARD_TARGET_DECLARATIONS, errors[:3]
        prefix = "catalog card target is not registered: "
        assert all(e.startswith(prefix) for e in errors), errors[:3]

    def test_three_arms_can_fire_in_one_call(self):
        """三条判据互不吞：一次注入三个违规 ⇒ 三条各在，且按 registry→card→catalog 排序。"""
        reg = _live_registry()
        reg["__bogus_registered_method__"] = lambda *a, **k: None
        cards = _live_cards()
        cards["__bogus_card_key__"] = result_card._CARD_BUILDERS["ancova"]
        cards.pop("ancova")
        errors = validate_method_contracts(reg, cards)
        assert errors == [
            MSG_MISSING_IN_CATALOG.format("__bogus_registered_method__"),
            MSG_CARD_NOT_IN_CATALOG.format("__bogus_card_key__"),
            MSG_CARD_TARGET_MISSING.format("ancova", "ancova"),
        ]

    def test_production_registries_untouched_by_this_file(self):
        """本文件只往副本里注入 ⇒ 生产两张表必须与 import 期快照逐位相同。"""
        assert frozenset(runner.AnalysisRegistry) == REGISTRY_KEYS_AT_IMPORT
        assert frozenset(result_card._CARD_BUILDERS) == CARD_KEYS_AT_IMPORT


# ===========================================================================
# 3) 失明面：拦不住的东西同样钉成断言（现状刻画，不是愿望清单）
# ===========================================================================

class TestGateBlindSpots:
    def test_card_alias_reuse_is_invisible_to_the_gate(self):
        """logistic 四型共用一个 builder，gate 依旧 0 错 ⇒ "0 错"不等于"卡已专用"。"""
        builders = result_card._CARD_BUILDERS
        assert builders["binary_logistic"] is builders["logistic_regression"]
        assert "ordinal_logistic" not in builders and "multinomial_logistic" not in builders
        assert validate_method_contracts(_live_registry(), _live_cards()) == []

    def test_collapsing_every_card_to_one_builder_still_passes(self):
        """极端形态：44 个键全指向同一个 builder，gate 仍一声不吭 ⇒ 它只看键存在性。"""
        single = next(iter(_live_cards().values()))
        collapsed = {k: single for k in _live_cards()}
        assert len({id(v) for v in collapsed.values()}) == 1
        assert validate_method_contracts(_live_registry(), collapsed) == []

    def test_empty_registry_passes_so_catalog_to_runner_is_unchecked(self):
        """gate 不查 catalog→registry：一张空注册表也能过（今日无 handler 的 10 个目录方法即证据）。"""
        assert validate_method_contracts({}, _live_cards()) == []
        without_handler = {
            d.method_id for d in METHOD_CATALOG if d.method_id not in runner.AnalysisRegistry
        }
        assert len(without_handler) == 10, sorted(without_handler)

    def test_shared_card_target_reports_three_methods_when_dropped(self):
        """反过来看：删掉被共用的那个键会一次报出 3 条 ⇒ 三型方法确实吊在同一个 builder 上。"""
        cards = _live_cards()
        cards.pop("logistic_regression")
        assert validate_method_contracts(_live_registry(), cards) == [
            MSG_CARD_TARGET_MISSING.format("logistic_regression", "logistic_regression"),
            MSG_CARD_TARGET_MISSING.format("ordinal_logistic", "logistic_regression"),
            MSG_CARD_TARGET_MISSING.format("multinomial_logistic", "logistic_regression"),
        ]

    def test_registered_alias_keys_pass_the_gate(self):
        assert REGISTRY_ALIAS_KEYS <= frozenset(runner.AnalysisRegistry)
        canonical = {d.method_id for d in METHOD_CATALOG}
        for alias in REGISTRY_ALIAS_KEYS:
            assert alias not in canonical, alias


# ===========================================================================
# 4) gate 看不见的卡片缺口账（补卡后这条会红 ⇒ 正确处置是补卡并同步账，不是改本件）
# ===========================================================================

class TestCardCoverageLedger:
    def test_registered_methods_without_reachable_card_snapshot(self):
        missing = {k for k in runner.AnalysisRegistry if not _reachable_card(k)}
        assert missing == REGISTERED_WITHOUT_REACHABLE_CARD, (
            f"新无可达卡：{sorted(missing - REGISTERED_WITHOUT_REACHABLE_CARD)}；"
            f"已被补卡：{sorted(REGISTERED_WITHOUT_REACHABLE_CARD - missing)}"
        )

    def test_ledger_members_really_take_the_generic_card_branch(self):
        """账上 15 条今日都真的落到 `暂无专用结果卡模板` 分支（防"清单是抄来的"）。
        只用 `{"test_type": id}` 的合成 output 驱动派发，不喂任何统计数值。"""
        for method_id in sorted(REGISTERED_WITHOUT_REACHABLE_CARD):
            card = result_card.build_card_from_output({"test_type": method_id})
            assert GENERIC_CARD_WARNING.format(method_id) in card.warnings, method_id

    def test_a_carded_method_takes_the_other_branch(self):
        """反向对照：有卡的方法不该出现这条告警 ⇒ 上一条用例不是恒真断言。"""
        card = result_card.build_card_from_output({"test_type": "descriptive"})
        assert GENERIC_CARD_WARNING.format("descriptive") not in card.warnings
