"""src/paper_writer/defense_qa_kb.py 答辩题库**数据面**现状钉桩（s922-114）。

动手前实测 `grep -rIn defense_qa_kb tests/` 命中 0 行：既有 `tests/test_defense_qa.py`
与 `tests/test_defense_qa_paper_aware.py` 测的是**问答引擎**（选哪几题、怎么填占位符），
题库本身（135 条 QATemplate + 三张索引表）此前零测试面。本件只钉数据形状与索引口径，
**不与引擎用例重叠**；s922-114 交付时不改 `src/paper_writer/defense_qa_kb.py` 一个字，
s924-56／s924-57 起钉桩与 KB 同笔改（生产码＋测试件是一体，见各行标注）。

钉桩面：
1. CATEGORIES / DIFFICULTY_LEVELS / DIFFICULTY_ORDER 三张表的键集与取值快照；
2. difficulty_emoji / difficulty_label 的三档映射 + 未知档的 🟡 兜底；
3. QATemplate 全量 137 条条目的字段完整性（question / category / difficulty 齐且合法）；
4. 占位符声明与 answer_template 实际取用的对账（s924-57 起**全量一致**，白名单已清零，
   判别力由两条合成探针自证）；
5. 索引表形状：26 个方法 × 每法 4-6 题、4 条通用题、类别兜底覆盖 6 类全部。

⚠ 口径登记（s924-56 翻正）：s922-114 当时实测「CATEGORIES 是 **6 类**，而
CATEGORY_FALLBACK_QA 只有 **4 类兜底**（缺 assumption / limit）」，按白名单钉成现状。
本班按卷宗补上 assumption / limit 两条兜底模板 ⇒ 题库 135→137 条（**纯增量**，无删除、
无去重），兜底覆盖 4/6→6/6；引擎侧 `REQUIRED_CATEGORIES` 仍是 4 类（method/data/effect/
infer），新两条只作数据面兜底，不改变引擎选题行为——该行为不变量由消费面用例复验。

源文件里的 emoji 一律用 chr(0xXXXX) 写，避免本机 cp936 控制台与 Write 通道对
不可见/宽字符的干扰（同一份字面量在 src 里是 UTF-8 原文，两处取值由断言绑定）。
"""

from dataclasses import fields
from string import Formatter

import pytest

from src.paper_writer.defense_qa_kb import (
    CATEGORIES,
    CATEGORY_FALLBACK_QA,
    DIFFICULTY_LEVELS,
    DIFFICULTY_ORDER,
    GENERIC_QA,
    TEST_SPECIFIC_QA,
    QATemplate,
    difficulty_emoji,
    difficulty_label,
)

# 与 src 内字面量等价的 ASCII 写法（取值由断言双向绑定，非另造常量）
E_TARGET = chr(0x1F3AF)   # 方法选择
E_BAR = chr(0x1F4CA)      # 数据合规
E_TRI = chr(0x1F4D0)      # 效应量
E_CHECK = chr(0x2705)     # 假设验证
E_WARN = chr(0x26A0)      # 研究局限（无 VS16）
E_GLASS = chr(0x1F50D)    # 推论谨慎
E_GREEN = chr(0x1F7E2)    # 必问
E_YELLOW = chr(0x1F7E1)   # 常问 / 未知兜底
E_RED = chr(0x1F534)      # 刁钻


# --------------------------------------------------------------------------- #
# 全量条目的规范枚举（顺序固定：通用 -> 类别兜底 -> 逐方法）
# --------------------------------------------------------------------------- #

def _all_entries():
    """[(case_id, source_tag, QATemplate)]，覆盖题库三张表的全量条目。"""
    out = [("gen-%02d" % i, "GENERIC", q) for i, q in enumerate(GENERIC_QA)]
    out += [("fb-" + k, "FALLBACK", q) for k, q in sorted(CATEGORY_FALLBACK_QA.items())]
    for m in sorted(TEST_SPECIFIC_QA):
        out += [("%s-%02d" % (m, i), "METHOD", q)
                for i, q in enumerate(TEST_SPECIFIC_QA[m])]
    return out


ENTRIES = _all_entries()
CASE_IDS = [cid for cid, _, _ in ENTRIES]
TOTAL_ENTRIES = 137          # 4 GENERIC + 6 FALLBACK + 127（26 方法）


# --------------------------------------------------------------------------- #
# 1. 索引表快照
# --------------------------------------------------------------------------- #

def test_categories_snapshot():
    """6 大类别：键集、顺序、emoji 前缀文案全为现状。"""
    assert list(CATEGORIES) == ["method", "data", "effect", "assumption", "limit", "infer"]
    assert CATEGORIES == {
        "method": E_TARGET + " 方法选择",
        "data": E_BAR + " 数据合规",
        "effect": E_TRI + " 效应量",
        "assumption": E_CHECK + " 假设验证",
        "limit": E_WARN + " 研究局限",
        "infer": E_GLASS + " 推论谨慎",
    }
    assert len({v[0] for v in CATEGORIES.values()}) == 6      # emoji 互不重复


def test_difficulty_order_snapshot():
    assert DIFFICULTY_ORDER == {"必问": 0, "常问": 1, "刁钻": 2}


def test_difficulty_levels_snapshot_and_cross_consistency():
    """DIFFICULTY_LEVELS 三元组 (emoji, rank, 说明) 与 DIFFICULTY_ORDER 逐档一致。"""
    assert DIFFICULTY_LEVELS == {
        "必问": (E_GREEN, 0, "导师答辩几乎一定会问"),
        "常问": (E_YELLOW, 1, "常见追问"),
        "刁钻": (E_RED, 2, "进阶质疑，视情况准备"),
    }
    assert list(DIFFICULTY_LEVELS) == list(DIFFICULTY_ORDER)
    for level, (emoji, rank, note) in DIFFICULTY_LEVELS.items():
        assert rank == DIFFICULTY_ORDER[level]
        assert emoji == difficulty_emoji(level)
        assert note.strip()


@pytest.mark.parametrize("level", sorted(DIFFICULTY_ORDER))
def test_difficulty_emoji_three_levels(level):
    assert difficulty_emoji(level) == DIFFICULTY_LEVELS[level][0]


@pytest.mark.parametrize("level", sorted(DIFFICULTY_ORDER))
def test_difficulty_label_format_three_levels(level):
    """label = f'{emoji} {level}'：单半角空格分隔，无多余空白。"""
    label = difficulty_label(level)
    assert label == DIFFICULTY_LEVELS[level][0] + " " + level
    assert label.count(" ") == 1


def test_unknown_difficulty_falls_back_to_yellow():
    """现状：未知档不抛错，emoji 退化成 🟡，label 退化成 '🟡 <原文>'。"""
    assert difficulty_emoji("不存在") == E_YELLOW
    assert difficulty_emoji("") == E_YELLOW
    assert difficulty_label("不存在") == E_YELLOW + " 不存在"
    assert "不存在" not in DIFFICULTY_ORDER


# --------------------------------------------------------------------------- #
# 2. 题库规模与索引形状
# --------------------------------------------------------------------------- #

def test_generic_qa_snapshot():
    assert len(GENERIC_QA) == 4
    assert [q.category for q in GENERIC_QA] == ["data", "data", "limit", "infer"]
    assert [q.difficulty for q in GENERIC_QA] == ["必问", "常问", "刁钻", "必问"]


def test_method_index_snapshot():
    """26 个方法键（现状清单），每法 4-6 题，合计 127 条。"""
    assert sorted(TEST_SPECIFIC_QA) == [
        "ancova", "chi_square_gof", "chi_square_independence", "cronbach_alpha",
        "efa", "friedman", "hierarchical_regression", "independent_ttest",
        "kruskal_wallis", "linear_regression", "mann_whitney", "mediation",
        "moderation", "multiple_regression", "one_sample_ttest", "one_way_anova",
        "paired_ttest", "partial_corr", "pearson_corr", "point_biserial",
        "repeated_anova", "spearman_corr", "split_half", "two_way_anova",
        "welch_anova", "wilcoxon",
    ]
    assert len(TEST_SPECIFIC_QA) == 26
    sizes = {m: len(v) for m, v in TEST_SPECIFIC_QA.items()}
    assert all(4 <= n <= 6 for n in sizes.values()), sizes
    assert sum(sizes.values()) == 127
    assert all(isinstance(v, list) for v in TEST_SPECIFIC_QA.values())


def test_total_entry_count_links_parametrization():
    """规模快照 + 参数化联动：题库增删条目时两侧必须同时反映。"""
    assert len(ENTRIES) == TOTAL_ENTRIES
    assert len(CASE_IDS) == len(GENERIC_QA) + len(CATEGORY_FALLBACK_QA) + \
        sum(len(v) for v in TEST_SPECIFIC_QA.values())


def test_fallback_covers_all_six_categories():
    """s924-56 口径变更：6 大类别**全部**有兜底模板（assumption / limit 已补）。

    原钉桩（s922-114）把「只有 4/6 类有兜底」当现状登记，并自述"补上兜底后本用例
    应当红"——本班按任务书把钉桩翻正为 6/6 全覆盖，保留键-类别对齐与难度不变量。
    ⚠ 覆盖面自证：`== set()` 一类的空集判据必须同时钉住"扫描面非空"
    （len(CATEGORY_FALLBACK_QA) == len(CATEGORIES) == 6），否则条目掉光也会假绿。
    """
    assert sorted(CATEGORY_FALLBACK_QA) == sorted(CATEGORIES)
    assert set(CATEGORIES) - set(CATEGORY_FALLBACK_QA) == set()
    assert len(CATEGORY_FALLBACK_QA) == len(CATEGORIES) == 6
    for key, q in CATEGORY_FALLBACK_QA.items():
        assert q.category == key                 # 键与自身 category 对齐
        assert q.difficulty == "必问"


@pytest.mark.parametrize("method", sorted(TEST_SPECIFIC_QA))
def test_every_method_keeps_method_and_must_ask_categories(method):
    """两个不变量：每法至少 1 条 method 类问题、至少 1 条"必问"难度。"""
    qs = TEST_SPECIFIC_QA[method]
    assert any(q.category == "method" for q in qs), method
    assert any(q.difficulty == "必问" for q in qs), method


# --------------------------------------------------------------------------- #
# 3. 逐条目字段完整性（参数化遍历 135 条，新增条目自动纳入）
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("case_id,source,tmpl", ENTRIES, ids=CASE_IDS)
def test_entry_difficulty_in_order(case_id, source, tmpl):
    """任务书主判据：difficulty 必属 DIFFICULTY_ORDER 三档（禁止自由文本）。"""
    assert isinstance(tmpl, QATemplate)
    assert tmpl.difficulty in DIFFICULTY_ORDER, (case_id, tmpl.difficulty)


@pytest.mark.parametrize("case_id,source,tmpl", ENTRIES, ids=CASE_IDS)
def test_entry_category_in_registry(case_id, source, tmpl):
    assert tmpl.category in CATEGORIES, (case_id, tmpl.category)


@pytest.mark.parametrize("case_id,source,tmpl", ENTRIES, ids=CASE_IDS)
def test_entry_required_fields(case_id, source, tmpl):
    """每题必含非空 question / answer_template / category / difficulty；placeholders 是字符串列表。"""
    assert tmpl.question.strip(), case_id
    assert tmpl.answer_template.strip(), case_id
    assert tmpl.category.strip(), case_id
    assert isinstance(tmpl.placeholders, list), case_id
    assert all(isinstance(p, str) and p.strip() for p in tmpl.placeholders), (case_id, tmpl.placeholders)


@pytest.mark.parametrize("case_id,source,tmpl", ENTRIES, ids=CASE_IDS)
def test_entry_dataclass_field_set(case_id, source, tmpl):
    assert [f.name for f in fields(QATemplate)] == \
        ["question", "answer_template", "category", "placeholders", "difficulty"]


def test_dataclass_defaults_are_safe():
    """placeholders 用 default_factory（不是共享可变默认值）；difficulty 默认"常问"。"""
    f = fields(QATemplate)
    by_name = {x.name: x for x in f}
    assert by_name["difficulty"].default == "常问"
    assert by_name["placeholders"].default_factory is list
    a, b = QATemplate(question="q", answer_template="a", category="method"), \
           QATemplate(question="q2", answer_template="a2", category="data")
    a.placeholders.append("x")
    assert b.placeholders == []


def test_question_text_duplicates_are_registered():
    """现状：137 条里有 128 个不同问题文本，4 个短问题跨方法重复（共 9 条冗余）。

    重复都是"效应量怎么算？"这类通用短问句被塞进各自方法表——**是否合并属内容口径**，
    本班不判、不改，只把重复组钉成快照：新增重复或原有重复被合并都会红，逼一次显式复核。
    （s924-56 补的 assumption / limit 两条兜底各用全新问题文本，重复组数与冗余条数不变。）
    """
    groups = {}
    for cid, _, tmpl in ENTRIES:
        groups.setdefault(tmpl.question, []).append(cid)
    dup = {q: sorted(ids) for q, ids in groups.items() if len(ids) > 1}
    assert len(groups) == 128
    assert len(dup) == 4
    assert sum(len(v) for v in dup.values()) - len(dup) == 9       # 冗余条数
    assert sorted(dup.values()) == [
        ["ancova-04", "moderation-04", "multiple_regression-03", "two_way_anova-03"],   # 样本量需要多大？
        ["chi_square_gof-04", "welch_anova-02", "wilcoxon-02"],                          # 效应量怎么算？
        ["friedman-02", "kruskal_wallis-02", "point_biserial-01", "repeated_anova-02"],  # 效应量？
        ["friedman-04", "partial_corr-04"],                                              # 样本量需求？
    ]


def test_answer_templates_are_all_unique():
    """答案模板侧无重复：137 条 answer_template 逐条互异（问题有重、答案不重）。"""
    answers = [t.answer_template for _, _, t in ENTRIES]
    assert len(answers) == len(set(answers)) == TOTAL_ENTRIES


# --------------------------------------------------------------------------- #
# 4. 占位符声明与模板实际取用的对账
# --------------------------------------------------------------------------- #

def _used_fields(tmpl):
    used = set()
    for text in (tmpl.question, tmpl.answer_template):
        for _, field_name, _, _ in Formatter().parse(text):
            if field_name:
                used.add(field_name)
    return used


# s924-57 清零：friedman-02 的 answer_template 用了 {effect_size}/{effect_label}，
# src 侧 placeholders 已补这两键 ⇒ 现库全量条目"声明==取用"，例外表留空。
# ⚠ 空表会让下面的反向判据失去扫描对象 ⇒ 判别力改由两条 *_still_bites 探针自证
#   （探针是内存里的合成条目，不写 src、不改 ENTRIES）。
PLACEHOLDER_MISMATCH_IDS: set = set()


def _mismatch_ids(entries=None):
    """声明与取用不等值的条目 id；entries 缺省＝真表（探针可喂合成条目）。"""
    entries = ENTRIES if entries is None else entries
    return {cid for cid, _, tmpl in entries if _used_fields(tmpl) != set(tmpl.placeholders)}


def _stray_brace_ids(entries=None):
    """正文有花括号却没声明任何占位符的条目 id（反向对账判据的单源，供主用例与探针共用）。"""
    entries = ENTRIES if entries is None else entries
    return sorted(cid for cid, _, tmpl in entries
                  if not tmpl.placeholders
                  and any(ch in text for text in (tmpl.question, tmpl.answer_template)
                          for ch in "{}"))


def test_placeholder_declarations_match_usage_for_all_entries():
    """s924-57 翻正：声明的 placeholders 与 question/answer_template 取用的字段**全量等值**。

    原用例（s922-114）把唯一不符项钉进白名单，并自述"修好 friedman-02 后本用例应当红，
    届时请删掉白名单条目"——本班按该设计意图执行：src 补声明＋白名单清成 set()。
    ⚠ 三刀覆盖面自证在 test_placeholder_mismatch_detector_still_bites，防"扫不到东西"假绿。
    """
    assert len(ENTRIES) == TOTAL_ENTRIES == 137          # 扫描面非空，清空才谈得上"全量一致"
    assert PLACEHOLDER_MISMATCH_IDS == set()
    assert _mismatch_ids() == PLACEHOLDER_MISMATCH_IDS


def test_placeholder_mismatch_detector_still_bites():
    """覆盖面自证①：白名单清空后，正向对账判据仍有牙（不是"没东西可查"的恒绿）。

    三刀都在内存合成条目上跑：
    ① 正对照——声明缺一键，检测器必须点名它；
    ② 负对照——声明与取用一致，检测器不得误报（证明①的红来自"不符"本身）；
    ③ 承重对照——把探针混进真表，主用例判据当场转假 ⇒ 主用例的绿是"查过且为空"。
    """
    probe_bad = ("probe-bad", "PROBE", QATemplate(
        question="探针 {a}", answer_template="探针 {b}", category="limit",
        placeholders=["a"]))
    probe_good = ("probe-good", "PROBE", QATemplate(
        question="探针 {a}", answer_template="探针 {b}", category="limit",
        placeholders=["a", "b"]))
    assert _mismatch_ids([probe_bad]) == {"probe-bad"}
    assert _mismatch_ids([probe_good]) == set()
    assert _mismatch_ids([*ENTRIES, probe_good]) == set()
    assert _mismatch_ids([*ENTRIES, probe_bad]) == {"probe-bad"}
    assert _mismatch_ids([*ENTRIES, probe_bad]) != PLACEHOLDER_MISMATCH_IDS


def test_stray_brace_reverse_check_still_bites():
    """覆盖面自证②：白名单例外支变死支后，反向对账判据仍有牙、且确有扫描对象。

    原 `test_entries_without_placeholders_have_no_braces` 里 `cid in PLACEHOLDER_MISMATCH_IDS`
    那一支随白名单清空变成永不命中的死支 ⇒ 用同一单源判据（_stray_brace_ids）亲见
    "没声明却带花括号"会被点名，并钉住 67 条真在反向判据的扫描面里。
    """
    probe_stray = ("probe-stray", "PROBE", QATemplate(
        question="探针 {orphan}", answer_template="纯文案正文", category="limit",
        placeholders=[]))
    probe_clean = ("probe-clean", "PROBE", QATemplate(
        question="探针", answer_template="纯文案正文", category="limit", placeholders=[]))
    assert _stray_brace_ids([probe_stray]) == ["probe-stray"]
    assert _stray_brace_ids([probe_clean]) == []
    assert _stray_brace_ids([*ENTRIES, probe_stray]) == ["probe-stray"]
    assert sum(1 for _, _, t in ENTRIES if not t.placeholders) == TOTAL_ENTRIES - 70 == 67


@pytest.mark.parametrize("case_id,source,tmpl", ENTRIES, ids=CASE_IDS)
def test_entry_declared_placeholders_are_substitutable(case_id, source, tmpl):
    """声明出来的每个占位符都必须是可 format 的裸名字（无属性/下标/冒号转换语法）。"""
    for p in tmpl.placeholders:
        assert p.replace("_", "").isalnum() and not p[0].isdigit(), (case_id, p)


def test_entries_without_placeholders_have_no_braces():
    """反向对账（67/137 条不声明占位符）：这些条目正文里不得出现孤立花括号。

    s924-57：friedman-02 补上 {effect_size}/{effect_label} 的声明后，原"白名单里的唯一
    例外"文案作废（例外集已空），判据改为单源 `_stray_brace_ids() == []`；
    判别力由 test_stray_brace_reverse_check_still_bites 用合成探针盯住。
    """
    assert _stray_brace_ids() == []


def test_stray_brace_entries_count_snapshot():
    """现状计数（s924-57 起两侧闭合）：67 条正文不含花括号；70 条有花括号＝70 条声明了占位符。

    s924-56 补 2 条兜底 ⇒ brace_full 68→70、with_decl 67→69；
    s924-57 修 friedman-02 的声明 ⇒ with_decl 69→70 ⇒ 70 - 70 = 0 = 空白名单。
    原"68 - 1 = 67"的减式（第四确证）自此**消失**，两侧必须同时读 70，
    任一侧重复出现不符项即红。
    """
    brace_free = sum(1 for _, _, t in ENTRIES
                     if "{" not in t.answer_template and "{" not in t.question)
    brace_full = TOTAL_ENTRIES - brace_free
    with_decl = sum(1 for _, _, t in ENTRIES if t.placeholders)
    assert (brace_free, brace_full, with_decl) == (67, 70, 70)
    assert brace_full - with_decl == len(PLACEHOLDER_MISMATCH_IDS) == 0


def test_kb_read_only_for_the_suite():
    """本件只读：跑完不改动任何索引表（防"顺手补题"改变题库）。"""
    before = (len(GENERIC_QA), len(CATEGORY_FALLBACK_QA), len(TEST_SPECIFIC_QA),
              sum(len(v) for v in TEST_SPECIFIC_QA.values()))
    for level in DIFFICULTY_ORDER:
        difficulty_label(level)
    after = (len(GENERIC_QA), len(CATEGORY_FALLBACK_QA), len(TEST_SPECIFIC_QA),
             sum(len(v) for v in TEST_SPECIFIC_QA.values()))
    assert before == after == (4, 6, 26, 127)
