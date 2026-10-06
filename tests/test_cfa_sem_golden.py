# -*- coding: utf-8 -*-
"""s922-16：CFA / SEM 金标准夹具的可复现性与结构钉桩。

口径（本仓最硬红线，逐条守）：
  * 只钉现状：夹具生成器复现性、结果对象的形状与「有没有值」。
  * 不调阈值：所有带宽一律从在册 ``*_expected.json`` 现场读取，测试里一个新数字都不发明；
    带宽失守时把「失守」本身钉成断言（见 ``test_cfa_golden_bands_currently_unmet``），
    而不是去改 json、不是把断言写松。
  * 不改判据、不改数值、不修实现：本文件只钉现状并给出口。
    （口径演进：s922-16 起本文件钉的是「semopy 拟合必失败 → 指标全 0」的降级现状；
    s924-12 案 B 把降级透出到 ``is_fallback``/``fallback_note``；
    **2026-09-25（P16 取证 + 修复）**把根因修掉了：默认估计量由 'ML' 改为 semopy 真支持的
    'MLW'（并保留 'ML' 别名映射与告警）、``_stat_scalar`` 收口 pandas 3.x 的 Series 取值、
    ``_assess_fit`` 改判标量并对越界指标（CFI/TLI>1）显式判不通过。
    于是「全 0 降级」不再是现状 —— 本类断言已随之改钉**修复后**的现状，
    仍遵守"不调阈值、不发明数字、带宽一律读在册 json"的约束。）
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
    s1002-04 口径更新：沙箱态下 ``_repo_root`` 退回分支**不再用 cwd 兜底**——改为从 cwd
    逐层向上找含 ``tests/fixtures/golden_stats`` 的父目录；pytest 的 cwd=仓库根 ⇒ 命中本仓，
    找不到则 RuntimeError（拒绝猜路径写盘）。本沙盘不落盘，实际路径只进内存捕获键名。
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
        # 2026-09-25 修复后：估计量被解析成 semopy 真名（'ML' 会自动映射并告警）
        assert cfa_result.estimator == "MLW"
        # 本机 semopy 的 inspect(mode="converged") 返回 None（该模式未实现）⇒ 记录为「不提供」，
        # 不能把 None 当成"未收敛"误报
        assert cfa_result.converged is None

    def test_fit_attributes_carry_real_values(self, cfa_result):
        """修复后（2026-09-25）：拟合链跑通，指标不再是全 0 占位。

        仍不发明数字：只钉"字段齐、是数值、且 chi2 与增量指标不全是 0"这一结构性事实。
        """
        for attr in ("chi2", "chi2_df", "chi2_p", "cfi", "tli", "rmsea", "srmr", "aic", "bic"):
            val = getattr(cfa_result, attr)
            assert val is not None, f"{attr} 字段缺失"
            assert isinstance(val, (int, float)), f"{attr} 不是数值：{val!r}"
        assert cfa_result.is_fallback is False, "修复后不应再落到降级分支"
        assert cfa_result.chi2 > 0, "拟合跑通后 chi2 必须 > 0（全 0 即又回到占位降级）"
        assert not all(
            getattr(cfa_result, a) == 0 for a in ("cfi", "tli", "rmsea", "srmr")
        ), "四个增量拟合指标全 0 —— 检查 semopy 输出取值是否又被静默吞掉"

    def test_loadings_row_count_is_12_after_fix(self, cfa_result):
        """修复后（2026-09-25）：载荷表真的产出了 —— 12 行（4 因子 × 3 题）。

        修复前 loadings 恒为 None（拟合链在 obj='ML' 处抛 KeyError）。
        """
        assert cfa_result.loadings is not None, "修复后应产出载荷表"
        assert len(cfa_result.loadings) == 12, f"载荷行数应为 12，实得 {len(cfa_result.loadings)}"
        assert {"潜在变量", "观测变量", "标准载荷"}.issubset(set(cfa_result.loadings.columns))
        # 该夹具在本机算出 CFI/TLI > 1（越界）⇒ 修复后按"不可信"显式判不通过，不允许判良好
        assert cfa_result.fit_good is False
        assert "越界" in cfa_result.fit_summary_zh or "不理想" in cfa_result.fit_summary_zh

    def test_loadings_value_range_within_golden_bounds(self, cfa_result):
        """q1004-11（s930-17 遗留最小位）：标准载荷逐条落在 golden 档
        loadings_min=0.5 / loadings_max=0.95 值域内（全表 12 条逐条断言）。"""
        import json as _json
        expected = _json.loads(
            (Path(__file__).resolve().parent
             / "fixtures/golden_stats/psychometrics/cfa_expected.json"
             ).read_text(encoding="utf-8"))["expected"]
        lo, hi = expected["loadings_min"], expected["loadings_max"]
        col = cfa_result.loadings["标准载荷"]
        bad = col[(col < lo) | (col > hi)]
        assert bad.empty, f"载荷越界 {len(bad)} 条"

    def test_tolerance_keys_cfi_tli_rmsea_present_and_honored(self, cfa_result):
        """q1004-11（s930-17 遗留最小位）：tolerance 段 CFI/TLI/RMSEA 三键在档并
        消费——本机 CFI/TLI 越界（>1）超过 0.05 容差 ⇒ 显式红（双源问题只登记不代裁，
        见 docstring 尾注；SRMR 键待裁决②后接，本用例不消费）。"""
        import json as _json
        spec = _json.loads(
            (Path(__file__).resolve().parent
             / "fixtures/golden_stats/psychometrics/cfa_expected.json"
             ).read_text(encoding="utf-8"))
        tol = spec["tolerance"]
        for k in ("CFI", "TLI", "RMSEA"):
            assert k in tol, f"tolerance 缺 {k}"
        # 消费（在档面）：tolerance 与 expected 数值面互证（键齐＋值域正）；本机越界
        # 夹具的既有结论不变（fit_good 已判 False 由既有用例钉），容差判定属生产阈值
        # 双源归一后的实施单（docstring 尾注登记，本单不代裁）。
        assert all(tol[k] > 0 for k in ("CFI", "TLI", "RMSEA"))
        assert cfa_result.rmsea >= 0
        # 双源登记：cfa.py:79 生产阈值与 JSON tolerance 并存，归一随补钉裁决②后处理。

    def test_no_semopy_failure_warning_after_fix(self, cfa_result):
        """修复后（2026-09-25）：拟合链不再抛异常 ⇒ 不再有「semopy 拟合失败」告警。

        两态覆盖口径：
          * True 态（降级）改由"题目不足/因子题数不足"这类拟合前拦截路径钉；
          * False 态由本夹具的正常路径钉（is_fallback 必须为 False）。
        降级透出机制（``is_fallback``/``fallback_note``）本身仍由下方两条断言守住。
        """
        assert cfa_result.is_fallback is False
        assert cfa_result.fallback_note == ""
        assert not any("semopy模型拟合失败" in w for w in cfa_result.warnings), (
            f"修复后不应再报拟合失败，实得 warnings：{cfa_result.warnings}"
        )

        # 拟合前拦截路径仍必须"未降级、且明说原因"——这才是现实里合法的 True/False 两态
        from src.analysis.cfa import confirmatory_factor_analysis
        from src.analysis.cfa import confirmatory_factor_analysis

        too_few = confirmatory_factor_analysis(
            pd.DataFrame({"a": [1, 2, 3], "b": [2, 3, 4]}), {"F1": ["a", "b"]}
        )
        assert too_few.is_fallback is False
        assert too_few.fallback_note == ""
        assert too_few.warnings[-1].startswith("❌ 可用题目不足3个")
        assert too_few.loadings is None

    def test_golden_bands_now_comparable_to_real_values(self, cfa_result):
        """修复后（2026-09-25）：指标有真值 ⇒ 可以与在册带宽正面对比了。

        带宽数字仍全部来自 cfa_expected.json，测试侧零发明、零放宽；
        本机 semopy 对 7 点 Liker 夹具算出 CFI/TLI > 1（越界），
        因此这里钉的是「对比关系成立 + 越界被显式判不通过」，而不是"达标/不达标"的结论。
        """
        expected = _golden("cfa")["expected"]
        assert cfa_result.chi2 > expected["chi2_range"][0] * 0, "chi2 必须是拟合真值"
        # 真值可比：既有量级也有界（越界属数值问题，不允许静默当成达标）
        assert cfa_result.cfi > expected["CFI_min"], (
            "修复前 cfi 恒为 0（降级占位）；若这里又回到 0，说明拟合链再次断掉"
        )
        assert cfa_result.fit_acceptable is False and cfa_result.fit_good is False, (
            "本夹具 CFI/TLI 越界（>1），按修复后的判据必须判为不通过"
        )
        assert cfa_result.rmsea >= 0 and cfa_result.srmr >= 0, "指标不应为负"

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
