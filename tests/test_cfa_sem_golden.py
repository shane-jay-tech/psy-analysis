# -*- coding: utf-8 -*-
"""s922-16：CFA / SEM 金标准夹具的可复现性与结构钉桩。

口径（本仓最硬红线，逐条守）：
  * 只钉现状：夹具生成器复现性、结果对象的形状与「有没有值」。
  * 不调阈值：所有带宽一律从在册 ``*_expected.json`` 现场读取，测试里一个新数字都不发明；
    带宽失守时把「失守」本身钉成断言（见 ``test_cfa_golden_bands_currently_unmet``），
    而不是去改 json、不是把断言写松。
  * 不改判据、不改数值、不修实现：CFA 在当前环境下 semopy 拟合必失败（``obj=estimator``
    把字符串 'ML' 传给 semopy 的目标函数位），本文件只把这处降级透出钉住并给出口，不碰
    ``src/analysis/cfa.py``。
  * 夹具 CSV 只读：生成器在沙箱里 exec，``to_csv`` 被替换成内存捕获，绝不让它写盘。
"""
import contextlib
import hashlib
import io
import json
import warnings
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
GENERATOR = REPO / "scripts" / "generate_cfa_sem_golden.py"
PSY_DIR = REPO / "tests" / "fixtures" / "golden_stats" / "psychometrics"
ADV_DIR = REPO / "tests" / "fixtures" / "golden_stats" / "advanced"

# 生成器落点（脚本里写的是绝对盘符路径，这里只按文件名认，见 test 的绝对路径耦合登记）
FIXTURES = {
    "cfa": PSY_DIR / "cfa.csv",
    "sem": ADV_DIR / "sem.csv",
}
GOLDEN = {
    "cfa": PSY_DIR / "cfa_expected.json",
    "sem": ADV_DIR / "sem_expected.json",
}

CFA_FACTORS = {f"F{i + 1}": [f"q{j}" for j in range(1 + 3 * i, 4 + 3 * i)] for i in range(4)}
SEM_MEASUREMENT = {
    "F1": ["x1", "x2", "x3"],
    "F2": ["x4", "x5", "x6"],
    "F3": ["y1", "y2", "y3"],
}
# 金标准 json 里的 model_spec 拆出来的两段
SEM_GOLDEN_PATHS = ["F3 ~ F1 + F2"]
# 把 F2 也当中介，才可能出间接效应（金标准式没有中介链，见下方前提订正例）
SEM_MEDIATED_PATHS = ["F2 ~ F1", "F3 ~ F1 + F2"]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _run_generator_in_sandbox() -> dict:
    """exec 生成器源码，但把 ``DataFrame.to_csv`` 换成内存捕获，返回 {落点名: CSV 文本}。

    不给 ``__file__`` 等模块上下文（源码不依赖），并确保异常直接抛出而不是被静默吞掉。
    """
    source = GENERATOR.read_text(encoding="utf-8")
    captured: dict = {}
    real_to_csv = pd.DataFrame.to_csv

    def fake_to_csv(self, path_or_buf=None, *args, **kwargs):
        captured[str(path_or_buf)] = real_to_csv(self, None, *args, **kwargs)
        return None

    pd.DataFrame.to_csv = fake_to_csv
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, str(GENERATOR), "exec"), {"__name__": "cfa_sem_golden_src"})
    finally:
        pd.DataFrame.to_csv = real_to_csv
    return captured


@pytest.fixture(scope="module")
def generator_runs():
    """同一进程里跑两遍生成器，外加跑前后在册夹具的 sha（证明没被写脏）。"""
    before = {k: _sha256_bytes(v.read_bytes()) for k, v in FIXTURES.items()}
    first = _run_generator_in_sandbox()
    second = _run_generator_in_sandbox()
    after = {k: _sha256_bytes(v.read_bytes()) for k, v in FIXTURES.items()}
    return {"first": first, "second": second, "before": before, "after": after}


@pytest.fixture(scope="module")
def cfa_df():
    return pd.read_csv(FIXTURES["cfa"])


@pytest.fixture(scope="module")
def sem_df():
    return pd.read_csv(FIXTURES["sem"])


@pytest.fixture(scope="module")
def cfa_result(cfa_df):
    from src.analysis.cfa import confirmatory_factor_analysis

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return confirmatory_factor_analysis(cfa_df, CFA_FACTORS)


@pytest.fixture(scope="module")
def sem_golden_result(sem_df):
    from src.analysis.sem import structural_equation_model

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return structural_equation_model(sem_df, SEM_MEASUREMENT, SEM_GOLDEN_PATHS)


@pytest.fixture(scope="module")
def sem_mediated_result(sem_df):
    from src.analysis.sem import structural_equation_model

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return structural_equation_model(sem_df, SEM_MEASUREMENT, SEM_MEDIATED_PATHS)


def _golden(name: str) -> dict:
    return json.loads(GOLDEN[name].read_text(encoding="utf-8"))


# ============================ ① 生成器可复现性 ============================


class TestGeneratorReproducibility:
    def test_generator_source_declares_its_seeds(self):
        """seed 是复现性的唯一凭据，被人摘掉时这条先红并点名是哪一颗。"""
        source = GENERATOR.read_text(encoding="utf-8")
        assert "np.random.seed(42)" in source, "CFA 段的 seed=42 不在了"
        assert "np.random.seed(123)" in source, "SEM 段的 seed=123 不在了"

    def test_sandbox_run_touches_no_disk_file(self, generator_runs):
        """沙箱必须真的没写盘：跑前跑后在册 CSV 的 sha256 全等。"""
        assert generator_runs["before"] == generator_runs["after"], (
            "生成器把在册金标准夹具改掉了，沙箱 to_csv 拦截失效"
        )

    def test_two_runs_produce_identical_sha256(self, generator_runs):
        """任务书 ①：seed 固定时两次生成的 CSV 文本 sha256 必一致。"""
        first, second = generator_runs["first"], generator_runs["second"]
        assert len(first) == 2, f"生成器应当只产出 2 份 CSV，实得 {sorted(first)}"
        assert sorted(first) == sorted(second)
        for key in first:
            assert _sha256_text(first[key]) == _sha256_text(second[key]), (
                f"{key} 两次生成不一致 —— 生成器已不再可复现（seed 被动过或有随机源漏在 seed 之外）"
            )

    def test_generated_files_land_on_the_two_golden_fixture_names(self, generator_runs):
        names = sorted(Path(k).name for k in generator_runs["first"])
        assert names == ["cfa.csv", "sem.csv"]

    def test_generated_content_equals_committed_fixture(self, generator_runs):
        """最强的那枚钉：沙箱产物与入库夹具逐字节同（含 numpy/pandas 版本流）。

        异环境下若红，红的是 RNG 流/CSV 格式化版本差异，不是数据被人改；
        出口：按 requirements-lock.txt 复原版本后重跑，不要改夹具。
        """
        for name, path in FIXTURES.items():
            key = next(k for k in generator_runs["first"] if Path(k).name == path.name)
            assert _sha256_text(generator_runs["first"][key]) == _sha256_bytes(path.read_bytes()), (
                f"{path.name} 与生成器产物不再同字节（版本漂移请查 numpy/pandas，勿手改夹具）"
            )

    def test_committed_fixture_shape_matches_generator_docstring(self, cfa_df, sem_df):
        assert cfa_df.shape == (200, 12)
        assert sem_df.shape == (200, 9)
        assert list(cfa_df.columns) == [f"q{i + 1}" for i in range(12)]
        assert list(sem_df.columns) == ["x1", "x2", "x3", "x4", "x5", "x6", "y1", "y2", "y3"]
        # Likert 1-7 且为整数（生成器 clip 的结果，属结构不属统计结论）
        for df in (cfa_df, sem_df):
            vals = df.values
            assert vals.min() >= 1 and vals.max() <= 7
            assert all(str(t) in ("int64", "int32") for t in map(str, df.dtypes))


# ============================ ② CFA 黄金断言（钉现状） ============================


class TestCfaGoldenOnFourFactorFixture:
    def test_result_identity_fields(self, cfa_result):
        assert cfa_result.test_type == "cfa"
        assert cfa_result.n_factors == 4
        assert cfa_result.n_items == 12
        assert cfa_result.n_obs == 200
        assert cfa_result.estimator == "ML"

    def test_fit_attributes_exist_but_currently_zeroed(self, cfa_result):
        """任务书说的「拟合指标非空」在现状只能钉成：字段都在、值全是 0.0。"""
        for attr in ("chi2", "chi2_df", "chi2_p", "cfi", "tli", "rmsea", "srmr", "aic", "bic"):
            val = getattr(cfa_result, attr)
            assert val is not None, f"{attr} 字段缺失"
            assert isinstance(val, (int, float)), f"{attr} 不是数值：{val!r}"
            assert val == 0.0, (
                f"{attr} 现值为 {val!r}；本钉桩记录的是「semopy 拟合失败→全 0 降级」这一现状，"
                "若它不再是 0，说明拟合链被修好了，需人工复核后连同下方带宽例一起更新"
            )

    def test_loadings_are_none_so_row_count_12_premise_fails(self, cfa_result):
        """任务书 ② 的「载荷行数=12」在现状不成立：loadings 是 None，不是空表。

        按磁盘实况改钉为 None + 降级说明，不为此去改实现凑出 12 行。
        """
        assert cfa_result.loadings is None
        assert cfa_result.fit_acceptable is False
        assert cfa_result.fit_good is False
        assert cfa_result.fit_summary_zh.startswith("模型拟合出错")

    def test_failure_is_surfaced_as_exactly_one_semopy_warning(self, cfa_result):
        assert len(cfa_result.warnings) == 1
        assert cfa_result.warnings[0].startswith("⚠ semopy模型拟合失败")
        assert "unknown objective function" in cfa_result.warnings[0]
        # 走的是 semopy 分支而不是 factor_analyzer 降级分支
        assert cfa_result.is_fallback is False
        assert cfa_result.fallback_note == ""

    def test_golden_bands_currently_unmet(self, cfa_result):
        """在册金标准带宽（R lavaan 0.6-18）现值一条都不满足 —— 把「未达标」钉死。

        带宽数字全部来自 cfa_expected.json，测试侧零发明、零放宽。
        """
        expected = _golden("cfa")["expected"]
        assert cfa_result.cfi < expected["CFI_min"]
        assert cfa_result.tli < expected["TLI_min"]
        assert cfa_result.chi2 < expected["chi2_range"][0]
        assert cfa_result.chi2_df != expected["df"]
        # RMSEA/SRMR「越小越好」，0.0 反而「假达标」，所以这里钉的是它们同为 0（同一降级来源）
        assert cfa_result.rmsea == expected["RMSEA_max"] * 0
        assert cfa_result.srmr == expected["SRMR_max"] * 0

    def test_validity_metrics_are_still_produced_after_the_failure(self, cfa_result):
        """拟合链断了，AVE/CR/HTMT 仍由独立支路算出（test_validity 已依赖此行为）。"""
        assert set(cfa_result.ave_per_factor) == set(CFA_FACTORS)
        assert set(cfa_result.cr_per_factor) == set(CFA_FACTORS)
        for value in list(cfa_result.ave_per_factor.values()) + list(cfa_result.cr_per_factor.values()):
            assert 0 < value <= 1.5, f"AVE/CR 越出结构范围：{value!r}"
        assert cfa_result.htmt_matrix is not None
        assert cfa_result.fl_matrix is not None


# ============================ ② SEM 黄金断言（只钉桩不调阈值） ============================


class TestSemGoldenOnThreeFactorFixture:
    def test_model_syntax_is_built_from_the_two_dicts(self, sem_golden_result):
        assert sem_golden_result.test_type == "sem"
        for line in ["F1 =~ x1 + x2 + x3", "F2 =~ x4 + x5 + x6", "F3 =~ y1 + y2 + y3", "F3 ~ F1 + F2"]:
            assert line in sem_golden_result.model_syntax
        assert sem_golden_result.n_obs == 200
        assert sem_golden_result.warnings == []

    def test_fit_indices_non_empty_and_of_the_expected_key_set(self, sem_golden_result):
        fit = sem_golden_result.fit_indices
        assert fit, "拟合指标为空"
        assert {"CFI", "TLI", "RMSEA", "chi2"} <= set(fit)
        for key in ("CFI", "TLI", "RMSEA"):
            assert isinstance(fit[key], float)
        assert sem_golden_result.fit_acceptable is True
        assert sem_golden_result.fit_good is True

    def test_golden_bands_hold_using_the_json_numbers_only(self, sem_golden_result):
        """黄金断言：带宽全部现场读 sem_expected.json，测试里不写死任何阈值。"""
        golden = _golden("sem")
        expected, tol = golden["expected"], golden["tolerance"]
        fit = sem_golden_result.fit_indices
        assert fit["CFI"] >= expected["CFI_min"] - tol["CFI"]
        assert fit["TLI"] >= expected["TLI_min"]
        assert fit["RMSEA"] <= expected["RMSEA_max"] + tol["RMSEA"]
        paths = sem_golden_result.path_coefficients
        b = {
            (row["因变量"], row["自变量"]): float(row["B"])
            for _, row in paths.iterrows()
        }
        assert abs(b[("F3", "F1")] - expected["path_F1_to_F3"]) <= tol["path_coefficients"]
        assert abs(b[("F3", "F2")] - expected["path_F2_to_F3"]) <= tol["path_coefficients"]

    def test_loadings_and_path_rows_shapes(self, sem_golden_result):
        assert len(sem_golden_result.path_coefficients) == 2
        assert list(sem_golden_result.loadings["潜变量"].unique()) == ["F1", "F2", "F3"]
        assert len(sem_golden_result.loadings) == 9
        assert set(sem_golden_result.r_squared) == {"F3"}

    def test_golden_spec_has_no_mediation_so_indirect_effects_are_none(self, sem_golden_result):
        """任务书 ② 的「间接效应存在」对金标准式不成立：F3 ~ F1 + F2 没有中介链。

        按磁盘实况改钉为 None（实现里 ``if indirect_rows`` 才建表），不为了凑出表去改 spec。
        """
        assert sem_golden_result.indirect_effects is None

    def test_mediated_spec_on_same_fixture_yields_indirect_effect_table(self, sem_mediated_result):
        """要钉「间接效应存在」就得给真中介式；这里只钉结构与算术闭合，不钉显著性。"""
        ie = sem_mediated_result.indirect_effects
        assert ie is not None
        assert list(ie.columns) == ["路径", "a (X→M)", "b (M→Y)", "间接效应 (a×b)"]
        assert len(ie) == 1
        row = ie.iloc[0]
        assert row["路径"] == "F1 → F2 → F3"
        b = {
            (r["因变量"], r["自变量"]): float(r["B"])
            for _, r in sem_mediated_result.path_coefficients.iterrows()
        }
        assert float(row["a (X→M)"]) == pytest.approx(b[("F2", "F1")], abs=1e-3)
        assert float(row["b (M→Y)"]) == pytest.approx(b[("F3", "F2")], abs=1e-3)
        assert float(row["间接效应 (a×b)"]) == pytest.approx(
            round(b[("F2", "F1")] * b[("F3", "F2")], 3), abs=1e-3
        )

    def test_sem_is_deterministic_across_two_calls_on_same_data(self, sem_df):
        """SEM 侧的「两次生成 sha256 一致」等价物：同数据两次拟合，全字段文本同哈希。"""
        from src.analysis.sem import structural_equation_model

        def fingerprint(res):
            chunks = [
                res.model_syntax,
                json.dumps(res.fit_indices, sort_keys=True, default=str),
                json.dumps(res.r_squared, sort_keys=True, default=str),
                res.path_coefficients.to_csv(index=False),
                res.loadings.to_csv(index=False),
                "" if res.indirect_effects is None else res.indirect_effects.to_csv(index=False),
            ]
            return _sha256_text("\n".join(chunks))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            a = structural_equation_model(sem_df, SEM_MEASUREMENT, SEM_MEDIATED_PATHS)
            b = structural_equation_model(sem_df, SEM_MEASUREMENT, SEM_MEDIATED_PATHS)
        assert fingerprint(a) == fingerprint(b), "同数据两次 SEM 拟合结果不同（存在 seed 之外的随机源）"
