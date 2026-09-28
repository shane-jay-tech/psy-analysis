# -*- coding: utf-8 -*-
"""s927-41：`tests/conftest.py::_APP_TEST_FILES` 的白名单漂移守门（只加判据，零 conftest／零生产码改动）。

锚点复核（开工第一动作实测，**与卷宗不符之处按磁盘实况收窄**）
--------------------------------------------------------------
卷宗来账 `zcode-bridge/done/s923-01.result.md` 遗留问题 1：
「要升级成真 AppTest，必须先改 `tests/conftest.py::_APP_TEST_FILES`（追加
`test_questionnaire_import_panel_render.py`，或届时改名的新件名）」。
盘上实况：该件名**已在名单里**（`tests/conftest.py:29`，登记笔 = `c03d7a2 test(psy): s924-01 问卷导入面板真
AppTest 用例 ＋ conftest 白名单登记 1 行`），且该文件已是真 AppTest（`from streamlit.testing.v1 import AppTest`
＋ 2 处构造 ＋ 97 条断言，本件单跑 21 passed RC=0）。⇒ 判据①「追加」与②「升级绿」**已由前手闭合，本单不重做。**

本单按实况改做这个域里**仍然活着的那半**：白名单是**手工文件名集合**，两种漂移都会**静默**发生
（静默＝没有红灯，只有真实目录被写脏）：

1. **漏登记**：新起／改名的 AppTest 件不在名单 ⇒ 拿不到 `isolate_streamlit_app_test_storage`
   的 `PSY_ANALYSIS_HOME`／archive／logs 重定向 ⇒ 真 AppTest 往**用户真实项目目录**里写。
2. **死登记**：名单里的名字对应的文件不在盘上（改名／删除没同步）⇒ 白名单覆盖面自欺，
   看着有 10 项、实际护着 7 件。

这两条正是 s923-01 → s924-01 → 本单这条链的**根因**：链条每修一次都只补一个名字，
而「忘记补名字」这件事本身从来没有判据守着。本件把那层缺失补上，**方向是变严**（覆盖面＋1 条机器判据），
不是豁免：零白名单加项、零 `NEEDS_MIGRATION`、零 skip、零放宽任何既有断言。

口径：判据走 **AST** 而不是文本匹配。本守门件自己也写着 `AppTest`／`_APP_TEST_FILES` 字样，
文本判据会自己咬自己；AST 只认「真的从 `streamlit.testing` 拿到了 AppTest 并真的构造」，
对本件自己的结果是 False ⇒ 规则对守门件同样成立，**不自外豁免**（末例把这点也钉住）。

红线自查：只读文件系统与 AST，零 app 启动、零网络、零写盘（除 pytest 自带 tmp_path）、
不碰统计数值／隐私医疗／判分口径面。
"""

import ast
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
CONFTEST = TESTS_DIR / "conftest.py"
# 只认这两个工厂调用；`AppTest()` 直接构造也一并认（现实中 streamlit 禁它，但形状变了就该由本件说话）
_APPTTEST_FACTORY_ATTRS = {"from_file", "from_string"}
_ISOLATION_FIXTURE = "isolate_streamlit_app_test_storage"


def _read(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _whitelist_from_conftest() -> tuple[set[str], int]:
    """从 conftest 的 AST 里取 `_APP_TEST_FILES` 的字面集合（返回 (名字集, 赋值行号)）。"""
    for node in _read(CONFTEST).body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_APP_TEST_FILES" for t in node.targets):
            continue
        value = node.value
        if not isinstance(value, (ast.Set, ast.List)):
            raise AssertionError(f"conftest:{node.lineno} 的 _APP_TEST_FILES 不再是 set/list 字面量，本判据无法读它")
        names = {e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        assert names, "白名单读出来是空的——那等于所有 AppTest 件零隔离，请先修 conftest 再谈本判据"
        return names, node.lineno
    raise AssertionError("tests/conftest.py 里找不到 `_APP_TEST_FILES` 赋值：隔离 fixture 已失去数据源")


def _chain(node) -> str | None:
    """把 `a.b.c` 形式的 Attribute/Name 链拉平成字符串；混入其它节点就返回 None。"""
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _constructs_apptest(path: Path) -> bool:
    """该件是否真的构造 streamlit 的 AppTest。两条识别路，覆盖本仓两种写法＋将来第三种：

    * 别名路：`from streamlit.testing.v1 import AppTest [as X]` 之后 `X.from_file(...)`／`X(...)`；
    * 全链路：`import streamlit.testing.v1` 之后 `streamlit.testing.v1.AppTest.from_file(...)`
      （链尾以 `AppTest.from_*` 结尾即认，不依赖有没有起别名）。
    """
    tree = _read(path)
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("streamlit.testing"):
            for alias in node.names:
                if alias.name == "AppTest":
                    aliases.add(alias.asname or alias.name)
    if not aliases:
        # 没有 from-import 时，只有全链写法也可能构造；先用一条便宜的文本粗筛省掉解析成本
        if "streamlit.testing" not in path.read_text(encoding="utf-8"):
            return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _APPTTEST_FACTORY_ATTRS:
            chain = _chain(func)
            if chain and (chain.split(".")[-2] in aliases or chain.endswith("AppTest." + func.attr)):
                return True
        if isinstance(func, ast.Name) and func.id in aliases:
            return True  # AppTest(...) 直接构造也算（现实中 streamlit 禁它，形状变了就该由本件说话）
    return False


def _test_files() -> list[Path]:
    """普查面＝tests 下全部 `test_*.py`，**含本守门件自己**（规则不自外豁免）。"""
    return sorted(TESTS_DIR.rglob("test_*.py"))


def _apptest_users() -> set[str]:
    return {p.name for p in _test_files() if _constructs_apptest(p)}


# ===========================================================================
# 判据
# ===========================================================================

def test_every_apptest_constructor_file_is_registered():
    """漂移 1（漏登记＝零隔离）：构造 AppTest 的件必须逐个出现在 `_APP_TEST_FILES` 里。

    命中本例时的正确处置**只有追加登记**（把隔离覆盖面变严），
    不得反过来把 AppTest 改成手桩来「消红」——那是把真运行时面换成假面。
    """
    registered, decl_line = _whitelist_from_conftest()
    users = _apptest_users()
    assert users, "普查到零枚 AppTest 构造件——说明本判据的 AST 识别失效了，请先修判据"
    unregistered = sorted(users - registered)
    assert not unregistered, (
        f"这些件构造了真 AppTest 却没登记进 tests/conftest.py:{decl_line} 的 _APP_TEST_FILES ⇒ "
        f"它们拿不到 PSY_ANALYSIS_HOME/archive/logs 隔离，会往用户真实项目目录写："
        f"{unregistered}。追加名字即可（这是加严，不是豁免）；见 docs/insights/s927-41-note.md"
    )


def test_every_registered_name_exists_on_disk():
    """漂移 2（死登记＝覆盖面自欺）：名单里每个名字都必须对得上盘上的真件。"""
    registered, decl_line = _whitelist_from_conftest()
    dead = sorted(n for n in registered if not any(p.name == n for p in TESTS_DIR.rglob("*.py")))
    assert not dead, (
        f"_APP_TEST_FILES（conftest:{decl_line}）里有 {len(dead)} 个名字在盘上不存在：{dead}。"
        f"要么是件被改名／删除而名单没跟着走（那件现在就零隔离），要么是名字打错。"
    )


def test_isolation_fixture_still_reads_the_whitelist():
    """把「白名单确实被消费」钉住：fixture 改名／改逻辑 ⇒ 名单退化成装饰，本例当场红。

    s923-01 的整条推论都建立在 `if ... not in _APP_TEST_FILES: return` 这一行上；
    谁把那行删了或把变量换了名，前两例就会变成永远绿的摆设。
    """
    tree = _read(CONFTEST)
    fixture = next(
        (n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == _ISOLATION_FIXTURE),
        None,
    )
    assert fixture is not None, f"conftest 里找不到 {_ISOLATION_FIXTURE}：AppTest 存储隔离整体失效，请立即排查"
    consumed = {n.id for n in ast.walk(fixture) if isinstance(n, ast.Name)}
    assert "_APP_TEST_FILES" in consumed, (
        f"{_ISOLATION_FIXTURE}（conftest:{fixture.lineno}）不再读 `_APP_TEST_FILES` ⇒ "
        "白名单成了装饰，隔离要么全量生效要么全量失效，两种都不是设计口径"
    )


def test_guard_itself_is_not_an_apptest_constructor():
    """自证守门件不给自己开后门：规则①对本件同样成立，而本件确实构造不了 AppTest。

    若哪天有人往本件加 `AppTest.from_file(...)`，本例红 ⇒ 那个人必须去 conftest 登记，
    而不是把本例改掉。
    """
    assert not _constructs_apptest(Path(__file__)), (
        "守门件自己成了 AppTest 构造件——请去 _APP_TEST_FILES 登记本文件名，别改本例"
    )
