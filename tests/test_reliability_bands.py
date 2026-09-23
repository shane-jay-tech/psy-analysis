# -*- coding: utf-8 -*-
"""信度档位常量收口（s920-05）：`src/analysis/reliability_bands.py` 单一来源，两处引用。

改前两处各写一份「α ≥ 0.90 优秀」（`questionnaire/psychometrics.reliability_guidance` 与
`output/reasoning.TEST_TEMPLATES["cronbach_alpha"]`）⇒ 改阈值必漏一处。
本文件钉的是**收口本身**：两处档位集合一致、两处都只由常量拼出、源码里不再有裸阈值。
阈值数值与档位文字一律按现状，本单没动过任何一个字。
"""
import pathlib
import re

import pytest

from src.analysis.reliability_bands import (
    ACCEPTABLE,
    EXCELLENT,
    EXPLORATORY,
    GOOD,
    RELIABILITY_BANDS,
    UNACCEPTABLE,
    AlphaBand,
)
from src.output.reasoning import TEST_TEMPLATES
from src.questionnaire.psychometrics import reliability_guidance

GUIDE = TEST_TEMPLATES["cronbach_alpha"]["guide"]
PSY = reliability_guidance({})
NUM_RE = re.compile(r"0\.\d0")
GUIDE_SENTENCE = GUIDE.partition("查看")[0]                      # 判据那一句（后面还有 CITC≥0.30 等别的线）
PSY_LINES = [ln for ln in PSY.splitlines() if ln.startswith("- α")]


def test_both_sites_are_now_built_from_the_same_numbers():
    assert set(NUM_RE.findall(GUIDE_SENTENCE)) == set(NUM_RE.findall("".join(PSY_LINES)))         == {EXCELLENT.text, GOOD.text, ACCEPTABLE.text, UNACCEPTABLE.text}


def test_reasoning_sentence_is_exactly_the_constant_rearrangement():
    """解读指南那段必须能用常量原样重排出来——这就是"漏改一处"再也不可能出现。"""
    expected = (
        f"α ≥ {EXCELLENT.text} {EXCELLENT.label}；{GOOD.text}-{EXCELLENT.text} {GOOD.label}；"
        f"{ACCEPTABLE.text}-{GOOD.text} {ACCEPTABLE.label}；{EXPLORATORY.text}-{ACCEPTABLE.text} "
        f"{EXPLORATORY.label}；< {UNACCEPTABLE.text} {UNACCEPTABLE.label}。"
    )

    assert GUIDE.startswith("当前α=")
    assert GUIDE[len("当前α="):].startswith(expected)


def test_psychometrics_four_lines_are_the_same_constants_with_its_own_wording():
    lines = PSY_LINES

    assert lines == [
        f"- α ≥ {EXCELLENT.text}：优秀",
        f"- α ≥ {GOOD.text}：良好",
        f"- α ≥ {ACCEPTABLE.text}：可接受（探索性研究可放宽至{UNACCEPTABLE.text}）",
        f"- α < {UNACCEPTABLE.text}：需要修订",
    ]


def test_display_text_must_stay_two_decimals_of_the_number():
    """`str(0.90)=="0.9"`：只改数值不改 text（或反之）会让两处文案口径分裂，这条当场拦。"""
    for band in (*RELIABILITY_BANDS, UNACCEPTABLE):
        assert isinstance(band, AlphaBand)
        assert band.text == f"{band.threshold:.2f}"


def test_bands_are_ordered_and_the_floor_is_shared():
    thresholds = [b.threshold for b in RELIABILITY_BANDS]

    assert thresholds == sorted(thresholds, reverse=True)
    assert UNACCEPTABLE.threshold == EXPLORATORY.threshold       # 「<0.60」与「探索性边界」同一条线
    assert {b.label for b in RELIABILITY_BANDS} == {"优秀", "良好", "可接受", "探索性边界"}


@pytest.mark.parametrize("module_file", ["src/output/reasoning.py", "src/questionnaire/psychometrics.py"])
def test_no_bare_alpha_threshold_left_in_the_two_sources(module_file):
    text = pathlib.Path(module_file).read_text(encoding="utf-8")

    assert not re.search(r"α\s*[≥<]\s*0\.\d", text), "又写回裸阈值了"
    assert "EXCELLENT.text" in text and "reliability_bands" in text


def test_the_two_tasked_sites_are_clean_but_seven_more_still_hardcode_bands():
    """本单只收口任务点名的两处。全仓扫下来**还有七处**裸写 α 档位（数量按现状钉死，
    谁再新增一处、或悄悄收口掉一处，本用例都会红——这是台账，不是终点）。

    2026-09-22 s922-18 追加第 7 个持有者 app_pages_text.py：那 2 处是 app.py 片 3
    （_generate_method_description 的中英文方法说明文案）**原样迁入**，不是新增债；
    app.py 从来不在本扫描的 src/ 范围内，迁入 src/ui 后才被登记到。

    改名依据（s923-15，2026-09-23）：原名 `..._six_more_...` 写于只有 6 个持有者时，
    s922-18 把 app_pages_text.py 计入后已是 **7 个**（下面 dict 的 7 个键、合计 12 处
    裸阈值即现状），名实差一 ⇒ 按 s922-18 遗留问题 4「改名与否请主班定口」执行改名，
    **函数体一字未动**（含 dict 与两条 assert）。原名：
    `test_the_two_tasked_sites_are_clean_but_six_more_still_hardcode_bands`。
    选 `seven_more` 而非去数字化命名，是为了保留本台账「数量与名字同时钉死」的意图：
    持有者数再变时，assert 会红、名字也会跟着失配，两道一起提醒，不会静默漂成假名。
    """
    root = pathlib.Path("src")
    holders = {}
    for path in root.rglob("*.py"):
        if path.name == "reliability_bands.py":                 # 常量模块自己的历史注释
            continue
        n = len(re.findall(r"α\s*[≥<]\s*0\.\d", path.read_text(encoding="utf-8", errors="replace")))
        if n:
            holders[path.name] = n

    assert holders == {
        "app_pages_text.py": 2,                                 # 自 app.py 迁入的说明文案，见 docstring
        "learning_card.py": 1,
        "literature_manager.py": 1,
        "llm_engine.py": 1,
        "llm_engine_premium.py": 1,
        "questionnaire_panel.py": 2,
        "undergrad_wizard.py": 4,
    }
    bands_src = (root / "analysis" / "reliability_bands.py").read_text(encoding="utf-8")
    assert bands_src.count('"0.90"') == 1 and bands_src.count('"0.60"') == 2


def test_labels_are_not_shared_and_that_is_intentional():
    """同一条线两处的叫法本来就不同（需要修订 / 不可接受；可接受 / 可接受（放宽…））：
    收口收的是阈值，不是把两处话术强行并成一句。"""
    assert "需要修订" in PSY and "不可接受" in GUIDE
    assert UNACCEPTABLE.label == "不可接受"
