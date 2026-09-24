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
       ⚠️ s923-41 已把 clear_cache 这一侧收口（白名单 + is_file 过滤 + 逐文件 try），
          上方两条"现状钉"随之翻正；_truncate 仍是无校验现状，-1 边界钉保留。

钉住三块：
1) clear_cache(source) 的定向两态、全清态，以及未识别 source 的白名单拒绝（s923-41）；
2) clear_cache 只删文件、不递归、命中 *.json 之外一律不动；目录/删不掉的件只跳过不中断；
3) _truncate 的清洗（去 HTML / 折叠空白）与 len > max_len 时的截断形态。

与既有测试的分工（开工前 grep 实测）：
- tests/test_apa7_manual_string_pin.py 只覆盖 _search_crossref 的引用串形态；
- 全仓 tests/ 下没有任何用例触及 clear_cache / _truncate，本件补的正是这个空档；
- academic_literature.py:453 与 literature_review/summarize.py:51 各有一份同名
  _truncate（语义相近、属别的模块），不在本件范围内，避免越界改动。
"""
import inspect
import sys
from pathlib import Path

import pytest

from src.questionnaire import kb_search as K

# s923-41 补：夹具里 `monkeypatch.setattr(K, "CACHE_DIR", fake)` 之后，
# 测试体内再取 K.CACHE_DIR 拿到的已经是**假目录** ⇒ 原先两条
# "真实缓存目录不被触碰" 的钉其实是在跟自己比（假绿）。真实路径必须自行推出来。
_REAL_CACHE_DIR = Path(K.__file__).resolve().parent / ".kb_cache"


def _real_names():
    return sorted(p.name for p in _REAL_CACHE_DIR.iterdir()) if _REAL_CACHE_DIR.exists() else []


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
    def test_unknown_source_raises_and_deletes_nothing(self, fake_cache_dir, source):
        """s923-41 翻正 s922-143 的现状钉：else 兜底「误传＝全清」已改成白名单校验。
        未识别 source 必须先拒绝，一个文件都不许掉。"""
        _seed(fake_cache_dir, _MIXED)
        with pytest.raises(ValueError, match="未知的缓存来源"):
            K.clear_cache(source)
        assert _names(fake_cache_dir) == sorted(_MIXED)

    @pytest.mark.parametrize("source", [[], object(), 0, b"academic_api"])
    def test_non_string_source_is_value_error_not_typeerror(self, fake_cache_dir, source):
        """白名单查表前先挡非字符串：不可哈希的对象也不能冒出 TypeError，
        更不能再走老的 else 分支（那等于全清）。"""
        _seed(fake_cache_dir, _MIXED)
        with pytest.raises(ValueError):
            K.clear_cache(source)
        assert _names(fake_cache_dir) == sorted(_MIXED)

    def test_whitelist_covers_every_on_disk_cache_prefix(self):
        """白名单必须覆盖盘上真实前缀：只写 api_*/llm_* 两种缓存文件，
        漏一支就会留下清不掉的孤儿。CACHE_TTL 的 "unknown" 是 TTL 兜底标签、不落文件。"""
        assert {K.CACHE_CLEAR_PATTERNS["academic_api"],
                K.CACHE_CLEAR_PATTERNS["llm_generated"]} == {"api_*.json", "llm_*.json"}
        assert K.CACHE_CLEAR_PATTERNS[None] == "*.json"

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
    """s923-41 收口后的守卫面：目录/删不掉的文件都不再中断整轮清理。"""

    def test_directory_named_json_is_skipped_not_fatal(self, fake_cache_dir, caplog):
        """s923-41 翻正 s922-143 的现状钉：老实现无 is_file 过滤，
        目录名撞上 *.json 时 unlink 直接抛 OSError 并中断（Windows PermissionError /
        POSIX IsADirectoryError）。现改为 is_file 先跳过目录、其余照清、仍返回 True。
        caplog 那两条是给 is_file 过滤本身留判别力的：只靠逐文件 try 也能"不抛"，
        但目录会被当成一次删除失败而告警——目录不是缓存文件，不该进失败账。"""
        import logging

        _seed(fake_cache_dir, ("a.json",))
        (fake_cache_dir / "zz_dir.json").mkdir()
        with caplog.at_level(logging.WARNING, logger="src.questionnaire.kb_search"):
            assert K.clear_cache() is True
        assert (fake_cache_dir / "zz_dir.json").is_dir(), "目录必须原地保留"
        assert not (fake_cache_dir / "a.json").exists(), "同层真文件仍要被清掉"
        assert "zz_dir.json" not in caplog.text, "目录须被识别为非缓存文件、不记删除失败"

    def test_unlink_failure_only_skips_that_file_and_warns(self, fake_cache_dir, monkeypatch, caplog):
        """逐文件 try 的覆盖：单个文件删不掉（占用/只读/竞态）不得带走整轮清理，
        也不得静默——必须留一条 warning。"""
        import logging

        _seed(fake_cache_dir, ("a.json", "b.json"))
        real_unlink = Path.unlink

        def flaky(p):
            if p.name == "a.json":
                raise PermissionError("simulated locked cache file")
            return real_unlink(p)

        monkeypatch.setattr(Path, "unlink", flaky)
        with caplog.at_level(logging.WARNING, logger="src.questionnaire.kb_search"):
            assert K.clear_cache() is True
        assert (fake_cache_dir / "a.json").exists(), "删不掉的件留在原地即可，不得抛"
        assert not (fake_cache_dir / "b.json").exists(), "同轮其余件必须清干净"
        assert "a.json" in caplog.text, "失败必须留痕，不许静默吞掉"

    def test_real_cache_dir_is_not_touched_by_full_clear(self, fake_cache_dir):
        """本件最要紧的安全属性：全清只作用于被重定向的目录。
        （s923-41 修假绿：原先写 `real = K.CACHE_DIR` 拿到的是已被 monkeypatch 的
        假目录，等于跟自己比；现按 _REAL_CACHE_DIR 取真实路径逐名核对。）"""
        before = _real_names()
        _seed(fake_cache_dir, _MIXED)
        K.clear_cache()
        assert _names(fake_cache_dir) == ["api_1.txt", "notes.txt"]
        assert _REAL_CACHE_DIR.exists(), "导入即 mkdir(exist_ok=True)，目录应存在"
        assert _real_names() == before, "真实缓存目录内容被本次全清改动了"

    def test_real_cache_dir_is_not_touched_by_rejected_source(self, fake_cache_dir):
        """白名单拒绝路径同样不许碰真实目录（ValueError 早于任何 unlink 发生）。"""
        before = _real_names()
        _seed(fake_cache_dir, _MIXED)
        with pytest.raises(ValueError):
            K.clear_cache("typo_academic")
        assert _real_names() == before
        assert _names(fake_cache_dir) == sorted(_MIXED)


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
