# -*- coding: utf-8 -*-
"""`tokenize_keep_numbers` 分支现状钉测（s922-142）。

被钉对象：`src/parser/tokenizer.py:61 def tokenize_keep_numbers(text: str) -> list:`
（锚点复核于 2026-09-22：磁盘行号 61 与该 def 逐字一致，无漂移。）

钉的是什么：四类输入（中英混合 / 纯数字 / 空串 / 带标点数字）此前无直接测试。
本文件把探针跑出的**现值快照**固化为 golden，给后续任何分词改动提供回归面——
**不评价现值对不对**，只保证「要么不变，要么改动者必须显式改这里」。

探针实测发现的分支边界（写进钉测，供后来人少走弯路）：
两函数唯一差异是「`w.isdigit()` 为真的整数字串」——`tokenize()` 丢弃、`tokenize_keep_numbers()` 保留。
**小数与科学计数法 `3.14`/`1e5` 在两边都保留**（`"3.14".isdigit()` 为 False，旧过滤器本就拦不住），
故「保留数字」实为「保留整数字串」。本文件按实测现值钉，不按直觉钉。

golden 来源（先命令后数字）：`python -c "exec(open('tmp/probe_tokenize_keep_numbers_pin.py',
encoding='utf-8').read())"`（探针见 tmp/，只读、零写库；jieba 0.42.1 / py3.12）。

可复跑：`python -m pytest tests/test_tokenize_keep_numbers.py -q`（纯函数、离线、无 IO）。
"""
from src.parser.tokenizer import tokenize, tokenize_keep_numbers

# 探针实测现值（2026-09-22 固化）。key = 用例名，value = (输入, 期望输出)
FROZEN = {
    # —— 一、中英混合 ——
    "mixed_cn_en": (
        "t检验结果显示 p=0.032，效应量 Cohen's d=0.58",
        ["t检验", "结果显示", "p", "=", "0.032", "效应量", "Cohen", "s", "d", "=", "0.58"],
    ),
    "mixed_anova": (
        "ANOVA结果显示F(2,45)=3.87，p<0.05",
        ["ANOVA", "结果显示", "F", "2", "45", "=", "3.87", "p", "<", "0.05"],
    ),
    "mixed_n_subjects": (
        "被试32人，男生15人，女生17人",
        ["被试", "32", "男生", "15", "女生", "17"],
    ),
    "mixed_likert": (
        "采用Likert 5点量表，共20个题目",
        ["采用", "Likert", "5", "量表", "20", "题目"],
    ),
    # —— 二、纯数字 ——
    "pure_digits": ("12345", ["12345"]),
    "pure_zero": ("0", ["0"]),
    "pure_decimal": ("3.14", ["3.14"]),
    "pure_year": ("2024", ["2024"]),
    "pure_sci": ("1e5", ["1e5"]),
    # 注意：负号被 jieba 切走，`-7` 并不保持为一个 token（现值即如此，照钉）
    "pure_negative": ("-7", ["-", "7"]),
    # —— 三、空串 / 纯空白 ——
    "empty_str": ("", []),
    "spaces_only": ("   ", []),
    "ws_tab_newline": (" \t\n ", []),
    # —— 四、带标点数字 ——
    "num_punct_eq": ("p=0.032", ["p", "=", "0.032"]),
    "num_punct_comma": ("3.14,2.71", ["3.14", "2.71"]),
    "num_punct_paren": ("(45)", ["45"]),
    "num_punct_cn_period": ("n=100。", ["n", "=", "100"]),
    "num_punct_t_stat": ("t(28)=2.05", ["t", "28", "=", "2.05"]),
}

# 双函数对照现值（同一输入下 tokenize 与 tokenize_keep_numbers 各自输出），探针实测。
CONTRAST = {
    "12345": ([], ["12345"]),
    "0": ([], ["0"]),
    "2024": ([], ["2024"]),
    "3.14": (["3.14"], ["3.14"]),
    "1e5": (["1e5"], ["1e5"]),
    "-7": (["-"], ["-", "7"]),
    "(45)": ([], ["45"]),
    "n=100。": (["n", "="], ["n", "=", "100"]),
    "t(28)=2.05": (["t", "=", "2.05"], ["t", "28", "=", "2.05"]),
    "被试32人，男生15人，女生17人": (
        ["被试", "男生", "女生"],
        ["被试", "32", "男生", "15", "女生", "17"],
    ),
    "ANOVA结果显示F(2,45)=3.87，p<0.05": (
        ["ANOVA", "结果显示", "F", "=", "3.87", "p", "<", "0.05"],
        ["ANOVA", "结果显示", "F", "2", "45", "=", "3.87", "p", "<", "0.05"],
    ),
    "采用Likert 5点量表，共20个题目": (
        ["采用", "Likert", "量表", "题目"],
        ["采用", "Likert", "5", "量表", "20", "题目"],
    ),
}


def test_frozen_table_all_cases():
    """18 个用例逐一比对探针现值（一处漂移即红）。"""
    for name, (text, expected) in FROZEN.items():
        assert tokenize_keep_numbers(text) == expected, f"用例 {name!r} 输出漂移"


def test_mixed_cn_en_keeps_numeric_tokens():
    """中英混合：数字串（含小数）与英文词都被保留，不再被过滤掉。"""
    out = tokenize_keep_numbers(FROZEN["mixed_cn_en"][0])
    assert "0.032" in out and "0.58" in out
    assert "Cohen" in out and "效应量" in out


def test_branch_diff_is_exactly_integer_digit_tokens():
    """分支本意：差异**只**发生在整数字串上；小数/科学计数法两边都留。"""
    # 整数字串：tokenize 丢、keep_numbers 留 —— 这才是分支存在的理由
    assert tokenize("12345") == []
    assert tokenize_keep_numbers("12345") == ["12345"]
    assert tokenize("2024") == []
    assert tokenize_keep_numbers("2024") == ["2024"]
    # 反直觉项：小数与科学计数法在**两个**函数里都活下来（isdigit() 为 False）
    assert tokenize("3.14") == ["3.14"] == tokenize_keep_numbers("3.14")
    assert tokenize("1e5") == ["1e5"] == tokenize_keep_numbers("1e5")


def test_both_functions_contrast_table():
    """13 项双函数对照现值逐项钉（改动任一侧都会红）。"""
    for text, (expected_plain, expected_keep) in CONTRAST.items():
        assert tokenize(text) == expected_plain, f"tokenize({text!r}) 输出漂移"
        assert tokenize_keep_numbers(text) == expected_keep, f"keep({text!r}) 输出漂移"


def test_empty_and_whitespace_return_empty_list():
    """空串与纯空白：一律返回空列表，不是 None，也不抛异常。"""
    for text in ("", "   ", " \t\n ", "\u3000"):
        result = tokenize_keep_numbers(text)
        assert result == []
        assert isinstance(result, list)


def test_numbers_with_punctuation_split_and_keep_digits():
    """带标点数字：标点被切走/丢弃，数字本体一律留存。"""
    assert tokenize_keep_numbers("p=0.032") == ["p", "=", "0.032"]
    assert tokenize_keep_numbers("(45)") == ["45"]
    assert tokenize_keep_numbers("n=100。") == ["n", "=", "100"]
    assert tokenize_keep_numbers("-7") == ["-", "7"]
