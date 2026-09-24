"""s924-54 · tokenizer 三形态**负例钉桩**（不改行为，只锁现状）＋「-7 保持」裁决注记

═══════════════════════════════════════════════════════════════════════════
本件钉的是三个**实测到的现状**（不是理想行为），每条都用列表全等等值锁死，
任何一条被"顺手修好"都会当场红，由人工决定去留（见下方裁决）。
取数版本：`src/parser/tokenizer.py` HEAD 字节（本班未改任何 `src/`，见「裁决」末与 result）。

钉桩对象（本机 `.venv` Python 3.12 实测，读数见各例）
1. **负数拆片**：`tokenize_keep_numbers("样本量 n=-7 是否足够")`
   → `["样本量", "n", "=", "-", "7", "是否", "足够"]`——`-7` 出两片；
   `tokenize()` 同串 → `["样本量", "n", "=", "-", "是否", "足够"]`（`tokenizer.py:51` 的
   `w.isdigit()` 把 `7` 再吃掉，只留 `-`）。
2. **α 丢失**：`tokenize("Cronbach α=.91")` → `["Cronbach", "="]`——
   `tokenizer.py:49` 的 `if len(w) <= 1 and not w.isascii():` 让**所有单字非 ASCII 符号全灭**
   （α / β 同罪）；同串走 `tokenize_keep_numbers` 也只剩 `["Cronbach", "=", "91"]`
   （小数点 `.` 落在 `:54`/`:73` 的标点串里被吃，故 `.91` 变成 `91`）。
   ⚠ 归因边界：该规则只管「长度 ≤1 的非 ASCII」，**不是**"非 ASCII 一律丢"
   ——`样本量`/`相关`/`系数` 这些多字非 ASCII 词条存活（各例里有对照断言）。
3. **半角连字符存活**：`-` 不在 `tokenizer.py:54`（`tokenize`）/`:73`（`tokenize_keep_numbers`）
   那份标点串里，所以 `-` 与 `-.` 都能穿过纯标点过滤器；全角 `（）`「。」则被吃
   （见例 3 的 `相关 r=-.31（p<.01）` 整串对照）。

裁决：「-7 拆片」保持 or 修改？——**本班不代人工拍板，本件按「列修改案待日间」出口落**
--------------------------------------------------------------------------------
卷宗给的保持条件是「intent_resolver 消费侧未因拆片出错即不动」，并附「若有 join/重组逻辑
则保持理由成立」。**该前提在本机实测下不成立**，材料如下（行号为 `src/parser/intent_resolver.py`）：

- `:8` `from .tokenizer import tokenize, tokenize_keep_numbers`——消费入口。
- `:112-125` `_extract_test_value()`：逐个 token 直接 `float(t)`（`:116`），
  **没有任何"相邻符号片 + 数字片"的重组/join 逻辑**。
- `:231` `test_value = _extract_test_value(tokens_with_nums)` → `:279` 原样写进 `AnalysisPlan`。
- 全仓 `join` 普查：该文件只有 `:299` 的 `", ".join(columns[:8])`，是报错文案，与词条重组无关。
- 后果实测（例 1 把它钉成断言）：`_extract_test_value(["样本量","n","=","-","7","是否","足够"])`
  返回 **`7.0`**（`float("-")` 抛 `ValueError` 后被跳过，下一片 `7` 被当作答案）⇒ **符号静默翻正**。
  端到端同值：`resolve(df, "对x做单样本t检验，检验值为-7").test_value == 7.0`，
  与 `"检验值为7"` 的读数**逐字相同**（两份请求在 plan 层不可区分）。
- 反面对照：`tests/test_parser_core.py:55-59` 已钉 `_extract_test_value(["-2.5"]) == -2.5`
  ⇒ **同一条链在 jieba 给出单片 `-2.5` 时符号是活的**，受害面只落在"被拆开的整数负数"上。
- 既存重叠（不重复建设）：`tests/test_tokenize_keep_numbers.py:133` 已钉裸串
  `tokenize_keep_numbers("-7") == ["-", "7"]`；本件例 1 钉的是**句子级完整输出 + 两函数分化 + 消费侧后果**，
  与该行不互替（删掉本件的句子级断言，裸串钉桩看不见 `n=-7` 与 `tokenize()` 的分化）。

⇒ 保持理由（"消费侧不出错"）已被否证，但**改分词行为超出本单授权**（卷宗：不改分词行为），
所以本件只做两件事：把现状钉到不可无声漂移，并把两条候选修改案交给日间裁决：
  案 A（分词侧）：`:49`/`:54` 之前把 `[-+]?[0-9]*\\.?[0-9]+` 连成单片（影响面大，全仓消费方都要复跑）。
  案 B（消费侧）：`_extract_test_value` 检测「前一片恰为 `-` 且本片是纯数字」时合并取负（影响面小，
      但要同步 `tests/test_parser_core.py` 的 `["-2.5"]` 对照表）。
本案若被采纳，本文件三条断言**必须同批改**，不得只改生产码留本件红。

另：卷宗「α 丢失」在 `tokenizer_keep_numbers` 侧同样成立（`:71` 与 `:49` 同一条规则），
本件两函数都钉，防止"只修一个分支"的半修复。
"""

import pytest

from src.parser.intent_resolver import _extract_test_value
from src.parser.tokenizer import tokenize, tokenize_keep_numbers


def test_negative_number_splits_into_sign_and_digit():
    """现状 1：`-7` 拆成 `-` + `7` 两片；`tokenize()` 还把 `7` 再吃掉；消费侧符号丢失。"""
    text = "样本量 n=-7 是否足够"

    assert tokenize_keep_numbers(text) == ["样本量", "n", "=", "-", "7", "是否", "足够"]
    # :51 的 isdigit 分支只在 tokenize() 里存在 ⇒ 两函数在此串上必然分化
    assert tokenize(text) == ["样本量", "n", "=", "-", "是否", "足够"]

    # 消费侧（钉的是"现在错着"，不是"现在对着"）：相邻 '-' 与 '7' 两片无重组 ⇒ 返回 7.0
    assert _extract_test_value(tokenize_keep_numbers(text)) == 7.0
    # 对照：jieba 肯给单片时符号是活的 ⇒ 受害面限定在"被拆开的负整数"
    assert _extract_test_value(["-2.5"]) == -2.5


def test_single_non_ascii_symbol_is_dropped_alpha_lost():
    """现状 2：`tokenizer.py:49` 让单字非 ASCII 全灭 ⇒ `α=.91` 里的 α 连值一起变形。"""
    assert tokenize("Cronbach α=.91") == ["Cronbach", "="]
    assert tokenize_keep_numbers("Cronbach α=.91") == ["Cronbach", "=", "91"]

    flat = tokenize_keep_numbers("信度 α 与 β")
    assert flat == ["信度"], "α/β 两个单字非 ASCII 应全被丢掉（现状）"

    # 归因边界：规则只管 len<=1 的非 ASCII，多字非 ASCII 存活 ⇒ 别把它读成"非 ASCII 全灭"
    assert "样本量" in tokenize_keep_numbers("样本量 n=-7 是否足够")
    assert "系数" in tokenize_keep_numbers("Cronbach α系数=.91")


def test_halfwidth_hyphen_survives_the_punctuation_filter():
    """现状 3：半角 `-` 不在 `:54`/`:73` 标点串里所以存活；全角括号/句号被吃。"""
    assert tokenize_keep_numbers("n=-7") == ["n", "=", "-", "7"]
    assert tokenize("n=-7") == ["n", "=", "-"]

    # 同一串里两种命运：`-.` 活下来（含 `-`），`（）` 整片被标点串吃掉
    assert tokenize_keep_numbers("相关 r=-.31（p<.01）") == [
        "相关", "r", "=", "-.", "31", "p", "<", "01",
    ]
    assert "-" in tokenize("值为-7 的样本")
