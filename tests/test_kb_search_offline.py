"""s922-143：kb_search 离线面钉桩（clear_cache / _truncate）。

零联网、零写库：只调用 src/questionnaire/kb_search.py 里的这两个函数，
不触发 Crossref / LLM 搜索路径，也不读写真实缓存目录——测试期内 CACHE_DIR
全程被 monkeypatch 重定向到 tmp_path，真实目录仅做「未被触碰」核对。

开工锚点复核（2026-09-22 实测，python 3.12.9，命令见 tmp/probe_s922_143.py）：
    .venv/Scripts/python.exe tmp/probe_s922_143.py
    -> clear_cache 定义行 333；_truncate 定义行 354（与任务书锚点一致，无漂移）
    -> inspect.signature 实测：clear_cache(source: str = None)
                                _truncate(text: str, max_len: int) -> str
    -> 两者均无入参校验、无异常处理（见 TestClearCacheHazards 与 -1 边界用例）

钉住三块：
1) clear_cache(source) 的定向两态、全清态，以及 else 兜底吞掉未知 source 的现状；
2) clear_cache 只删文件、不递归、命中 *.json 之外一律不动；
3) _truncate 的清洗（去 HTML / 折叠空白）与 len > max_len 时的截断形态。

与既有测试的分工（开工前 grep 实测）：
- tests/test_apa7_manual_string_pin.py 只覆盖 _search_crossref 的引用串形态；
- 全仓 tests/ 下没有任何用例触及 clear_cache / _truncate，本件补的正是这个空档；
- academic_literature.py:453 与 literature_review/summarize.py:51 各有一份同名
  _truncate（语义相近、属别的模块），不在本件范围内，避免越界改动。
"""
import inspect
import sys

import pytest

from src.questionnaire import kb_search as K


# ===========================================================================
# 夹具：把模块级 CACHE_DIR 重定向到 tmp_path，绝不碰真实缓存目录
# ===========================================================================

@pytest.fixture()
def fake_cache_dir(tmp_path, monkeypatch):
    """把 K.CACHE_DIR 换到临时目录；真实目录只做存在性核对，全程不写。"""
    real = K.CACHE_DIR
    fake = tmp_path / ".kb_cache"
    fake.mkdir()
    monkeypatch.setattr(K, "CACHE_DIR", fake)
    yield fake
    assert real.exists(), "真实缓存目录被本次测试动掉了（应全程只读）"


def _seed(cache_dir, names):
    """按给定文件名铺一批文件，并返回 (json 名单, 非 json 名单)。"""
    for name in names:
        (cache_dir / name).write_text("{}", encoding="utf-8")
    return (
        sorted(n for n in names if n.endswith(".json")),
        sorted(n for n in names if not n.endswith(".json")),
    )


def _names(cache_dir):
    return sorted(p.name for p in cache_dir.iterdir())


_MIXED = ("api_1.json", "api_2.json", "llm_1.json", "other.json", "notes.txt", "api_1.txt")


# ===========================================================================
# 锚点与默认缓存目录：签名 / 归属模块 / CACHE_DIR 解析
# ===========================================================================

class TestAnchors:
    """锚点钉：签名或归属漂移即翻红，提醒同步复核调用方。"""

    def test_signatures_are_stable(self):
        assert str(inspect.signature(K.clear_cache)) == "(source: str = None)"
        assert str(inspect.signature(K._truncate)) == "(text: str, max_len: int) -> str"

    def test_functions_are_defined_in_kb_search_module(self):
        assert inspect.getsourcefile(K.clear_cache) == K.__file__
        assert inspect.getsourcefile(K._truncate) == K.__file__
        assert K.__file__.replace("\\", "/").endswith("src/questionnaire/kb_search.py")

    def test_default_cache_dir_is_adjacent_to_module(self):
        """缓存目录约定：模块同级的 .kb_cache（改约定会牵动 clear_cache 的语义）。"""
        assert K.CACHE_DIR.name == ".kb_cache"
        assert K.CACHE_DIR.parent.name == "questionnaire"
        assert K.CACHE_DIR.exists(), "导入即 mkdir(exist_ok=True)，目录应存在"


# ===========================================================================
# clear_cache：定向清理两态 + 全清态
# ===========================================================================

class TestClearCacheModes:
    """三个分支各钉一条：改错分支会导致「清了不该清的」或「该清的没清」。"""

    def test_academic_api_clears_only_api_json(self, fake_cache_dir):
        _seed(fake_cache_dir, _MIXED)
        assert K.clear_cache("academic_api") is True
        assert _names(fake_cache_dir) == ["api_1.txt", "llm_1.json", "notes.txt", "other.json"]

    def test_llm_generated_clears_only_llm_json(self, fake_cache_dir):
        _seed(fake_cache_dir, _MIXED)
        assert K.clear_cache("llm_generated") is True
        assert _names(fake_cache_dir) == [
            "api_1.json", "api_1.txt", "api_2.json", "notes.txt", "other.json"
        ]

    def test_none_clears_every_json(self, fake_cache_dir):
        _seed(fake_cache_dir, _MIXED)
        assert K.clear_cache() is True
        assert _names(fake_cache_dir) == ["api_1.txt", "notes.txt"]

    def test_none_and_explicit_source_agree_only_on_full_clear(self, fake_cache_dir):
        """全清态必须同时收走 api_* 与 llm_*，而不是只收一支。"""
        _seed(fake_cache_dir, _MIXED)
        K.clear_cache(None)
        assert not (fake_cache_dir / "api_1.json").exists()
        assert not (fake_cache_dir / "llm_1.json").exists()

    @pytest.mark.parametrize("source", ["unknown", "bogus_source", "", "ACADEMIC_API"])
    def test_unknown_source_falls_back_to_full_clear(self, fake_cache_dir, source):
        """现状钉：匹配不上就落 else 全清——传错 source 等于清空整个缓存。"""
        _seed(fake_cache_dir, _MIXED)
        assert K.clear_cache(source) is True
        assert _names(fake_cache_dir) == ["api_1.txt", "notes.txt"]

    def test_full_clear_leaves_non_json_files_alone(self, fake_cache_dir):
        """*.json 之外一律不动：证明 glob 不是 *.json* 也不是 *。"""
        _seed(fake_cache_dir, ("a.json", "c.json.bak", "d.txt", "no_ext"))
        K.clear_cache()
        assert _names(fake_cache_dir) == ["c.json.bak", "d.txt", "no_ext"]

    @pytest.mark.skipif(sys.platform != "win32", reason="glob 大小写敏感性随平台变化，此钉只锁 Windows 口径")
    def test_windows_glob_treats_json_suffix_case_insensitively(self, fake_cache_dir):
        """现状钉（本机实测）：Windows 上 Path.glob 走 os.path.normcase，
        大小写不敏感——b.JSON / c.Json 也会被 *.json 全清收走。
        POSIX 上同样用例会留下它们，故本钉只在 win32 生效，不制造跨平台假红。"""
        _seed(fake_cache_dir, ("a.json", "b.JSON", "c.Json", "d.txt"))
        K.clear_cache()
        assert _names(fake_cache_dir) == ["d.txt"]

    def test_full_clear_does_not_recurse_into_subdirs(self, fake_cache_dir):
        """只清本层，不递归（子目录里的同名缓存会留下来）。"""
        _seed(fake_cache_dir, ("top.json",))
        nested = fake_cache_dir / "sub"
        nested.mkdir()
        (nested / "nested.json").write_text("{}", encoding="utf-8")
        K.clear_cache()
        assert _names(fake_cache_dir) == ["sub"]
        assert (nested / "nested.json").exists()

    def test_empty_dir_is_a_noop(self, fake_cache_dir):
        assert K.clear_cache() is True
        assert _names(fake_cache_dir) == []


class TestClearCacheHazards:
    """现状钉：无异常处理 + 真实目录不被触碰。"""

    def test_directory_named_json_raises_and_aborts(self, fake_cache_dir):
        """目录名撞上 *.json 时 unlink 失败：Windows 抛 PermissionError、
        POSIX 抛 IsADirectoryError，两者都是 OSError；函数不吞异常。"""
        _seed(fake_cache_dir, ("a.json",))
        (fake_cache_dir / "zz_dir.json").mkdir()
        with pytest.raises(OSError):
            K.clear_cache()
        # 中断式清理：出错前已删的不会回滚，出错后的条目仍在
        assert (fake_cache_dir / "zz_dir.json").is_dir()

    def test_real_cache_dir_is_not_touched_by_full_clear(self, fake_cache_dir):
        """本件最要紧的安全属性：全清只作用于被重定向的目录。"""
        real = K.CACHE_DIR
        before = set(_names(real)) if real.exists() else set()
        _seed(fake_cache_dir, _MIXED)
        K.clear_cache()
        assert _names(fake_cache_dir) == ["api_1.txt", "notes.txt"]
        assert real.exists()
        assert before <= set(_names(real)), "真实缓存目录里原有文件被删了"


# ===========================================================================
# _truncate：清洗面
# ===========================================================================

class TestTruncateCleaning:
    """清洗发生在长度判断之前，顺序错了边界就会漂。"""

    @pytest.mark.parametrize("raw", ["", "   \n\t  ", "<br/>", "<p></p>", "<p>   </p>"])
    def test_blank_or_tag_only_input_collapses_to_empty(self, raw):
        assert K._truncate(raw, 10) == ""

    def test_short_text_is_returned_asis(self):
        assert K._truncate("  hello world  ", 100) == "hello world"

    def test_html_tags_are_stripped(self):
        assert K._truncate("<p>hello <b>world</b></p>", 100) == "hello world"
        assert K._truncate("<div><span>x</span></div>", 100) == "x"

    def test_inner_whitespace_is_collapsed(self):
        assert K._truncate("a   b\n\tc", 100) == "a b c"

    @pytest.mark.parametrize("raw", ["a\u3000b", "a\u00a0b", "a\r\nb"])
    def test_unicode_and_crlf_whitespace_collapse_to_single_space(self, raw):
        assert K._truncate(raw, 100) == "a b"

    def test_loose_angle_brackets_are_eaten(self):
        """现状钉：<[^>]+> 会连带吃掉没配对的尖括号内容（不是纯 HTML 解析）。"""
        assert K._truncate("a < b and c > d", 100) == "a d"


# ===========================================================================
# _truncate：长度边界与截断形态
# ===========================================================================

class TestTruncateBoundary:
    """判据是 len(text) > max_len（严格大于），省略号不计入 max_len。"""

    def test_exactly_at_limit_has_no_ellipsis(self):
        assert K._truncate("a" * 10, 10) == "a" * 10

    def test_one_over_limit_is_cut_then_ellipsis(self):
        got = K._truncate("a" * 11, 10)
        assert got == "a" * 10 + "..."
        assert len(got) == 13  # max_len + 3，省略号额外占位

    def test_length_is_measured_after_cleaning(self):
        """50 个字符 + 标签，max_len=10：先清洗成 50 字符再截断。"""
        assert K._truncate("<p>" + "a" * 50 + "</p>", 10) == "a" * 10 + "..."

    def test_html_only_does_not_count_toward_limit(self):
        """清洗后恰好等于上限，不得因原始长度超限而加省略号。"""
        assert K._truncate("<p>" + "a" * 5 + "</p>", 5) == "a" * 5

    def test_cjk_counts_characters_not_bytes(self):
        assert K._truncate("中文" * 5, 3) == "中文中..."

    def test_zero_max_len_yields_ellipsis_only(self):
        assert K._truncate("abc", 0) == "..."

    def test_negative_max_len_follows_python_slice(self):
        """现状钉：无入参校验，负数直接走切片 text[:-1]。"""
        assert K._truncate("abc", -1) == "ab..."

    def test_prefix_is_preserved_for_long_text(self):
        text = "".join(str(i % 10) for i in range(40))
        assert K._truncate(text, 12) == text[:12] + "..."
