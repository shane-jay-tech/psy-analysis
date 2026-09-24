# -*- coding: utf-8 -*-
"""s924-55 · 标点过滤串上收为模块常量 ``_PUNCT_CHARS`` 后的**两函数等价钉桩**

钉什么
------
`tokenizer.tokenize` 与 `tokenizer.tokenize_keep_numbers` 过去各自内联一份**逐字相同**的纯
标点过滤串，任何一边单独改都会让两函数的标点过滤口径静默分叉。现在两处都引用模块级
`_PUNCT_CHARS`。本件锁三件事：

1. 常量的**值**等于改前那份孪生串的快照（33 字符／31 个去重，值 sha256_8 `12cdf698`）；
2. 源码里这份标点串**只出现一次**，且**两个函数都按名字引用**它（拦"又长出第二份"与"只改一边"）；
3. 同一含全类标点的样本喂两函数，**标点片全被过滤**，且两函数输出之差**恰为纯数字片**
   （即除 `isdigit` 那条既定差异外，两函数对标点常量的语义完全一致）。

判别性（为什么这些断言咬得住）
------------------------------
- `PINNED_PUNCT` 故意**不**从 `tokenizer` 取，而是把改前的值抄成独立快照；否则"改常量 ⇒
  断言跟着一起绿"的假绿形态就成立了（内容变异靠它钉红）。
- 全角单字符标点（`，` `。` `！` `？` `、` `；` `：` `（` `）` …）同时会被前面那条
  "长度 ≤1 且非 ASCII" 的规则吃掉 ⇒ **双保险**，对"标点过滤器被改坏"不敏感。真正只有
  标点过滤器能拦下的是 **ASCII 单字符标点**（`?` `!` `,` `.` `;` `:` `(` `)` `[` `]` `{` `}`
  与半角引号族）和**多字符标点串**（`，。` `！？` `……` `——` `（）` `【】` `《》`）；
  用例因此按这两类挑弹药。空格不在弹药里：它在 `strip()` 后已是空片段，走不到过滤器。
- 本文件里的引号族与非 ASCII 标点一律写成 Unicode 转义形态（反斜杠＋u＋四位码点）：本机实测
  编辑工具链会改写行内引号字符，转义形态才能逐字复算。
- 每条行为断言都配了非空集自检（样本里没有纯标点片段就直接红），免得退化成空集上的假绿。

与同族既有件的分工（不重复钉）
------------------------------
- `tests/test_tokenizer_negative_pins.py`（s924-54）钉 `-7` 拆片／`α` 丢失／半角 `-` 存活三条
  **负例现状**。"`-` 不在标点串里"与本件"标点片全被过滤"是同一条规则的两侧，本件因此只钉
  "确在过滤集里"的字符，不碰 `-`，两类桩不互替。
- `tests/test_tokenize_keep_numbers.py`（s922-142）钉 golden 现值表，本件不复制该表。
- 常量化（生产码）与本用例是**同一笔**改动：只入生产码侧本件立刻红（常量与串份数判据），
  只入本件侧则 `AttributeError: module ... has no attribute '_PUNCT_CHARS'`。

可复跑：`python -m pytest tests/test_tokenizer_punct_constant.py -q`（纯函数、离线、无 IO）。
"""

import ast
from pathlib import Path

from src.parser import tokenizer
from src.parser.tokenizer import tokenize, tokenize_keep_numbers

# 改前 tokenizer.py 两处内联串的**值**快照（33 字符／31 去重，sha256_8 12cdf698）。
# 原文是两段相邻字面量隐式拼接，这里归一为一个 \u 转义串，逐字符等值。
PINNED_PUNCT = (
    "\uff0c\u3002\uff01\uff1f\u3001\uff1b\uff1a\u0027\u0027"
    "\uff08\uff09\u3010\u3011\u300a\u300b\u2026\u2014\u00b7"
    "\u002c\u002e\u003b\u003a\u0021\u003f\u0028\u0029\u005b\u005d\u007b\u007d"
    "\u0022\u0027\u0020"
)

# 只有标点过滤器拦得下的片段：ASCII 单字符标点（长度 1 但 isascii，躲过前置规则）
# ＋ 多字符标点串（躲过"长度 ≤1"规则）。
ONLY_PUNCT_FILTER_KILLS = (
    "?", "!", ",", ";", ":", ".", "(", ")", "[", "]", "{", "}",
    "\u0022", "\u0027",
    "\uff0c\u3002", "\uff01\uff1f", "\u2026\u2026", "\u2014\u2014",
    "\uff08\uff09", "\u3010\u3011", "\u300a\u300b",
)
WORDS = ("ANOVA", "效应量")
DIGIT = "42"
# 覆盖标点集里每一个字符（含空格），保证"全类标点"这句可机检
ALL_PUNCT_RUN = "".join(sorted(set(PINNED_PUNCT)))
SAMPLE = (
    "被试（n=32）的得分，范围 1—5 分……均数=3.2；标准差《0.8》【显著】p<0.05, "
    "效应量 d=0.58: 是否可靠?! \u0022问卷\u0022 \u0027量表\u0027 {ANOVA} [F] (2,45) "
    + ALL_PUNCT_RUN + " 收尾"
)


def _punct_only(tokens):
    """返回"整片都是标点"的存活片段（用独立快照判定，不读生产常量）。"""
    return [t for t in tokens if t and all(ch in PINNED_PUNCT for ch in t)]


def _func(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_constant_value_matches_pre_refactor_twin_snapshot():
    """常量内容＝改前那份孪生串的值；逐字符钉住，改一个字符就红。"""
    assert tokenizer._PUNCT_CHARS == PINNED_PUNCT
    assert len(tokenizer._PUNCT_CHARS) == 33
    assert len(set(tokenizer._PUNCT_CHARS)) == 31


def test_punctuation_string_exists_once_and_both_functions_reference_it():
    """源码面：串只有一份（孪生回归即红），且两函数都按名字引用这个模块级常量。"""
    tree = ast.parse(Path(tokenizer.__file__).read_text(encoding="utf-8"))

    copies = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value == PINNED_PUNCT
    ]
    assert len(copies) == 1, f"标点串有 {len(copies)} 份，常量化被打穿"

    assigns = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "_PUNCT_CHARS"
    ]
    assert len(assigns) == 1, "常量必须是模块级唯一赋值"
    assert assigns[0].value is copies[0], "那唯一一份就是常量的定义值"

    for name in ("tokenize", "tokenize_keep_numbers"):
        fn = _func(tree, name)
        assert "_PUNCT_CHARS" in {
            n.id for n in ast.walk(fn) if isinstance(n, ast.Name)
        }, f"{name} 没引用常量（只改一边＝口径分叉）"
        inlined = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Constant)
            and isinstance(n.value, str)
            and len(n.value) > 1
            and set(n.value) <= set(PINNED_PUNCT)
        ]
        assert not inlined, f"{name} 里又内联了纯标点串"


def test_both_functions_drop_every_pure_punctuation_fragment(monkeypatch):
    """同一批标点片段喂两函数：全被过滤；两函数输出只差那个纯数字片（语义一致）。"""
    fragments = [WORDS[0], DIGIT, WORDS[1], *ONLY_PUNCT_FILTER_KILLS]
    assert len(_punct_only(list(ONLY_PUNCT_FILTER_KILLS))) == len(ONLY_PUNCT_FILTER_KILLS)
    monkeypatch.setattr(tokenizer.jieba, "lcut", lambda _text: list(fragments))

    plain = tokenize("ignored")
    keep = tokenize_keep_numbers("ignored")

    assert plain == list(WORDS), "tokenize 里混进了标点片或数字片"
    assert keep == [WORDS[0], DIGIT, WORDS[1]], "keep_numbers 的保留面漂移"
    assert _punct_only(plain) == [] and _punct_only(keep) == []
    assert [t for t in keep if not t.isdigit()] == plain


def test_full_punctuation_sample_drops_all_punct_tokens():
    """卷宗字面判据：含全类标点的真实样本喂两函数，标点片全被过滤。"""
    assert set(PINNED_PUNCT) <= set(SAMPLE), "样本没覆盖标点集，判据会假绿"
    raw = [t.strip() for t in tokenizer.jieba.lcut(SAMPLE) if t.strip()]
    assert _punct_only(raw), "样本经 jieba 后没有纯标点片段 ⇒ 本例退化成空判据"

    plain = tokenize(SAMPLE)
    keep = tokenize_keep_numbers(SAMPLE)

    assert plain and keep, "两函数返回空列表 ⇒ 断言变成空集上的假绿"
    assert _punct_only(plain) == []
    assert _punct_only(keep) == []
    assert [t for t in keep if not t.isdigit()] == plain
    for word in WORDS:
        assert word in plain and word in keep, f"存活面被误伤：{word}"
