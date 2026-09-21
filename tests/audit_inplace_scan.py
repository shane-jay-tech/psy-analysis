#!/usr/bin/env python
"""psy session_state 就地变更「报告型」扫描（tests/audit_inplace_scan.py）.

来源：docs/insights/psy-dfinplace-blindspot-20260919.md 建议 3——把第四节 v4 扫描规则
（作用域 ＋ 顺序重绑定 ＋ .get()/.setdefault()/整体别名 DI 形 ＋ 嵌套左值 ＋ 先建后发布判局部）
做成一条 **报告型** 检查：只打印命中清单，**不进任何断言**（首晚基线未定，见psy-dfinplace §六.3：
与 test_export_gate_global_scan.py 同构，先报告、不 gate）。

三类输出口径（对应完成标准 1）：
- 严格命中 strict          ：作用域内可证「就地写」＋被写键 ∈ build_workspace_snapshot() 读取键集。
- 键不在快照 not_in_snapshot：可证就地写，但键不在快照读取清单 ⇒ 无危害（psy-dfinplace §二末）。
- 宽口径召回 recall         ：上面两类的并集 ＋ 键不可静态解析（动态 f-string 键）＋ 属性式就地写
                            （psy-dfinplace §四「未覆盖面①」）——召回上限，只能当线索不能当结论。

键清单**从 workspace.py 的 build_workspace_snapshot() 源码 AST 现场提取**（不手抄字面量表，
完成标准 4）；前缀族（如 `_tutor_history_`）单独收集。属性式就地写只进召回不进严格，
以对齐 psy-dfinplace §二「严格可证 13 处」的口径。

用法：
    .venv/Scripts/python.exe tests/audit_inplace_scan.py        # 分组打印命中清单
    .venv/Scripts/python.exe tests/audit_inplace_scan.py -q      # 只打印三类计数，退出码恒 0

本脚本不是 pytest 用例（文件名不带 test_ 前缀，且 main() 挂在 __main__ 门后）；
报告型 ⇒ 无论命中多少都 exit 0，不做门禁。

================================================================================
基线（s922-110 首跑，解释器 .venv/Scripts/python.exe，命令 `python tests/audit_inplace_scan.py`；
     数字随码漂移请重跑本脚本再取，勿照抄）：
================================================================================
扫描生产 .py 252 个（解析失败 0）；快照读取键 = 具名 22 个 + 前缀族 ['_tutor_history_']
（由 build_workspace_snapshot() 源码 AST 现场解析，不手抄）。

三类计数：
- 严格命中 strict        = 20
- 键不在快照 not_in_snap = 35
- 宽口径召回 recall      = 68

对照 psy-dfinplace §二『严格可证 13 处』：13 处逐条复现（app.py:1137、onboarding.py:216/217/218/239/240、
undergrad_wizard.py:1941/1942/1331/1333/870、memory_manager.py:128、quick_entries.py:705）；
多出的 7 处是——① undergrad_wizard.py:2155/2161/2168/2178/2183/2193（6 处，§二『数据流外 28 处』里
v4 正则「只数到 :2155–2193 的 6 处」者；本工具经「整体别名.key == session_state[key]」把
`wiz_data = wiz.undergrad_wizard_data` 正确解析成 undergrad_wizard_data 活对象，故归入严格——§二第五节
已自证这 28 处「同样落在活对象上」，属真违写，非本工具误报）；② paper_writing_ui.py:327
`engine.state.logs.append(...)`（engine 绑到快照键 paper_engine，经属性链解析到活对象，
§四『未覆盖面①属性式/跨对象』所致，本工具补上）。

文本口径召回（§三 独立复算，与 AST 口径互补）：整体别名_行尾即止 15、键值别名_纯键式 22 处 / 12 键
（与 §三『15 处』/『22 处 / 12 键』逐字吻合，佐证扫描可信）；宽召回上限 184（§三 记 159，差在如今多扫
4 个迁出文件）。
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import warnings
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# 独立运行（python tests/audit_inplace_scan.py）时 sys.path[0] 是 tests/，补上仓根才能 import src
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
# 被扫描的生产码里有历史 invalid-escape 字符串，ast.parse 会往 stderr 喷 SyntaxWarning；
# 报告型脚本只关心计数，压掉噪声。
warnings.filterwarnings("ignore")

# psy-dfinplace §三：生产码扫描目录排除面（.venv/tests/scripts/archive/tmp/node_modules/.git）
EXCLUDE_TOP = {".venv", "tests", "scripts", "archive", "tmp", "node_modules",
               ".git", "__pycache__", "dist", "build", ".pytest_cache", ".mypy_cache"}

# 会就地改容器内容的可变方法（下标写之外的形态）
MUTATORS = {
    "append", "extend", "insert", "remove", "pop", "popitem", "clear",
    "update", "setdefault", "add", "discard", "sort", "reverse",
}

WHOLE = "\u0000WHOLE\u0000"      # 整体别名（变量 == st.session_state）
UNRES = "\u0000UNRES\u0000"      # 绑到 session_state 读取，但键是动态表达式无法静态解析


# --------------------------------------------------------------------------
# 快照键清单：从 build_workspace_snapshot() 源码现场提取（不手抄）
# --------------------------------------------------------------------------
def _snap_constant_values() -> dict[str, str]:
    """把快照函数里以常量标识符引用的键（SESSION_KEY 等）解析成字面值。

    优先用 import 现取；失败再退回全仓模块级 `NAME = "str"` 扫描的结果。
    """
    resolved: dict[str, str] = {}
    try:
        from src.utils.workspace import (
            LITERATURE_REVIEW_SESSION_KEY,
            UPSTREAM_SESSION_KEY,
        )
        resolved["UPSTREAM_SESSION_KEY"] = UPSTREAM_SESSION_KEY
        resolved["LITERATURE_REVIEW_SESSION_KEY"] = LITERATURE_REVIEW_SESSION_KEY
    except Exception:  # noqa: BLE001 - 报告型脚本，环境不满足时降级为未解析
        pass
    try:
        from src.utils.figure_collection import SESSION_KEY
        resolved["SESSION_KEY"] = SESSION_KEY
    except Exception:  # noqa: BLE001
        pass
    try:
        from src.utils.workspace_state import WORKSPACE_KEY
        resolved["WORKSPACE_KEY"] = WORKSPACE_KEY
    except Exception:  # noqa: BLE001
        pass
    return resolved


def _literal_or_name(node: ast.AST) -> tuple[str | None, bool]:
    """返回 (值, 是否字面量)。字面字符串 -> (s,True)；标识符 -> (name,False)；其它 -> (None,False)。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, True
    if isinstance(node, ast.Name):
        return node.id, False
    return None, False


def build_snapshot_keys(const_map: dict[str, str]) -> tuple[set[str], list[str]]:
    """解析 build_workspace_snapshot() 源码，返回 (具名读取键集, 前缀族列表)。"""
    import inspect  # 延迟导入，避免影响顶层可导入性

    from src.utils.workspace import build_workspace_snapshot

    src = inspect.getsource(build_workspace_snapshot)
    tree = ast.parse(src.strip())
    func = tree.body[0]
    snap_names: set[str] = set()
    prefixes: list[str] = []

    def resolve(node: ast.AST | None) -> str | None:
        if node is None:
            return None
        val, is_lit = _literal_or_name(node)
        if val is None:
            return None
        if is_lit:
            return val
        return const_map.get(val)  # 常量标识符 -> 字面值

    def add_keys_from_list(node: ast.AST) -> None:
        if isinstance(node, (ast.List, ast.Tuple)):
            for elt in node.elts:
                k = resolve(elt)
                if k:
                    snap_names.add(k)

    for node in ast.walk(func):
        # st.session_state.get("k") / st.session_state.setdefault("k", ...) / st.session_state.pop("k")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in {"get", "setdefault", "pop"} and node.args:
            base = node.func.value
            if _is_session_state(base):
                k = resolve(node.args[0])
                if k:
                    snap_names.add(k)
        # st.session_state["k"]
        if isinstance(node, ast.Subscript) and _is_session_state(node.value):
            k = resolve(node.slice)
            if k:
                snap_names.add(k)
        # st.session_state.k （属性式读取，排除写入 —— 读点也计入键集无妨）
        if isinstance(node, ast.Attribute) and _is_session_state(node.value):
            if node.attr not in {"keys", "get", "setdefault", "pop"}:
                snap_names.add(node.attr)
        # for k in ["a","b",...]:
        if isinstance(node, ast.For) and isinstance(node.iter, (ast.List, ast.Tuple)):
            add_keys_from_list(node.iter)
        # key.startswith("PREFIX")  -> 前缀族
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "startswith" and node.args:
            p, is_lit = _literal_or_name(node.args[0])
            if p and is_lit:
                prefixes.append(p)

    return snap_names, prefixes


# --------------------------------------------------------------------------
# st.session_state 表达式识别
# --------------------------------------------------------------------------
def _is_session_state(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "session_state"
            and isinstance(node.value, ast.Name) and node.value.id == "st")


def _resolve_slice(node: ast.AST | None, const_map: dict[str, str]) -> str:
    """把 session_state 的下标/get 参数解析成键字符串；不可静态解析 -> UNRES。"""
    if node is None:
        return UNRES
    val, is_lit = _literal_or_name(node)
    if val is None:
        return UNRES
    return val if is_lit else const_map.get(val, UNRES)


def _key_of_read(node: ast.AST, bindings: dict[str, str], const_map: dict[str, str]):
    """把「一个读取表达式」解析成它背后指向的 session_state 对象所属键。WHOLE / 键字符串 / UNRES / None。

    注意：整体别名（st.session_state 或绑到它的变量）本身返回 WHOLE；而 `别名.key`
    / `别名[key]` / `别名.get(key)` 返回该 key —— 读到的就是那个活对象（psy-dfinplace §三 15 处整体别名
    下游的写正是这么落到活对象上的）。
    """
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    if _is_session_state(node):
        return WHOLE
    if isinstance(node, ast.Attribute):
        if node.attr in {"keys", "values", "items", "get", "setdefault", "pop"}:
            return None
        base = _key_of_read(node.value, bindings, const_map)
        if base == WHOLE:                     # 整体别名.key == session_state[key]
            return node.attr
        if base is not None:                  # x.field：x 已绑具体键，仍指向该键对象
            return base
        return None
    if isinstance(node, ast.Subscript):
        base = _key_of_read(node.value, bindings, const_map)
        if base == WHOLE:                     # 整体别名[k] == session_state[k]
            return _resolve_slice(node.slice, const_map)
        if base is not None:                  # x["a"]：x 已绑具体键，读写仍归属该键
            return base
        return None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr in {"get", "setdefault", "pop"} and node.args:
        # x = st.session_state.get("k", {}) / setdefault("k", []) -> 返回活对象
        base = _key_of_read(node.func.value, bindings, const_map)
        if base == WHOLE or _is_session_state(node.func.value):
            return _resolve_slice(node.args[0], const_map)
    return None


def _store_subscript_key(t: ast.Subscript, bindings, const_map):
    """下标「写」目标 -> 被就地改的键；对 publish（`session_state[k] = v`）返回 None。

    psy-dfinplace §三：`wiz.undergrad_step = 2` / `wiz["k"] = v` 与 `st.session_state.x = …`
    同义（键级整体赋值 = 整体替换，安全）；只有 **嵌套下标**（`别名[k]['j'] =`）或
    **已绑到具体键的对象**（`wiz_data['a'] =`）才是就地写。
    """
    subs: list[ast.AST] = []
    cur: ast.AST = t
    while isinstance(cur, ast.Subscript):
        subs.append(cur.slice)
        cur = cur.value
    base = _key_of_read(cur, bindings, const_map)   # 链的最左根对象
    if base == WHOLE:
        if len(subs) >= 2:                          # 别名[k]['j'] = -> 就地改 k
            return _resolve_slice(subs[-1], const_map)
        return None                                  # 别名[k] = / st.session_state[k] = -> publish
    if base is not None:                             # KEY 绑定变量的下标写（任意深度）= 就地写
        return base
    return None


# --------------------------------------------------------------------------
# 作用域扫描器
# --------------------------------------------------------------------------
class Hit:
    __slots__ = ("file", "line", "key", "form")

    def __init__(self, file: str, line: int, key: str, form: str):
        self.file, self.line, self.key, self.form = file, line, key, form

    def label(self) -> str:
        return f"{self.file}:{self.line}  [{self.form}]  键={self.key}"


def _flatten_scope(body: list[ast.stmt]) -> list[ast.stmt]:
    """把 if/for/while/try/with 展平成顺序简单语句；def/class 不进（它们自成作用域）。"""
    out: list[ast.stmt] = []
    for s in body:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(s, ast.If):
            out.extend(_flatten_scope(s.body))
            out.extend(_flatten_scope(s.orelse))
        elif isinstance(s, (ast.For, ast.AsyncFor, ast.While)):
            out.extend(_flatten_scope(s.body))
            out.extend(_flatten_scope(s.orelse))
        elif isinstance(s, ast.Try):
            out.extend(_flatten_scope(s.body))
            for h in s.handlers:
                out.extend(_flatten_scope(h.body))
            out.extend(_flatten_scope(s.orelse))
            out.extend(_flatten_scope(s.finalbody))
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            out.extend(_flatten_scope(s.body))
        else:
            out.append(s)
    return out


def _collect_scopes(tree: ast.AST) -> list[list[ast.stmt]]:
    scopes: list[list[ast.stmt]] = [list(tree.body)]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scopes.append(list(node.body))
    return scopes


def scan_file(path: Path, snap_names: set[str], prefixes: list[str],
              const_map: dict[str, str]) -> tuple[list[Hit], list[Hit], list[Hit], int]:
    """返回 (strict, not_in_snapshot, recall_only, parse_errors)。"""
    rel = path.relative_to(REPO).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return [], [], [], 1

    strict: list[Hit] = []
    not_snap: list[Hit] = []
    recall_only: list[Hit] = []

    def in_snapshot(key: str) -> bool:
        return key in snap_names or any(key.startswith(p) for p in prefixes)

    def record(line: int, key, form: str) -> None:
        if key is None or key == WHOLE:
            # key is None：非 session_state 派生；== WHOLE：`st.session_state.pop(k)` /
            # `ss.update(...)` 这类作用在 session_state 容器本身的键级操作，
            # psy-dfinplace §三 认定与 `st.session_state.x = …` 同义（整体替换），不算就地写。
            return
        hit = Hit(rel, line, key, form)
        if key == UNRES:
            recall_only.append(hit)
        elif in_snapshot(key):
            if form == "attr-store":       # 属性式就地写：psy-dfinplace §四未覆盖面，只进召回
                recall_only.append(hit)
            else:
                strict.append(hit)
        else:
            not_snap.append(hit)

    for scope in _collect_scopes(tree):
        bindings: dict[str, str] = {}
        for stmt in _flatten_scope(scope):
            # ---- 赋值：更新绑定 + 处理下标/属性写目标 ----
            if isinstance(stmt, ast.Assign):
                k = _key_of_read(stmt.value, bindings, const_map)
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        if k is None:
                            bindings.pop(t.id, None)     # 顺序重绑定 / 局部新建 -> 注销别名
                        else:
                            bindings[t.id] = k
                    elif isinstance(t, ast.Subscript):
                        record(stmt.lineno, _store_subscript_key(t, bindings, const_map), "index-write")
                    elif isinstance(t, ast.Attribute):
                        # publish：`st.session_state.k = v` / `wiz.k = v`（根是 WHOLE）= 键级整体替换，安全
                        base = _key_of_read(t.value, bindings, const_map)
                        if base not in (None, WHOLE, UNRES):
                            # x.field = v（x 已绑具体键）：属性式就地写，psy-dfinplace §四未覆盖面① -> 只进召回
                            record(stmt.lineno, base, "attr-store")
                continue
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) \
                    and stmt.value is not None:
                k = _key_of_read(stmt.value, bindings, const_map)
                if k is None:
                    bindings.pop(stmt.target.id, None)
                else:
                    bindings[stmt.target.id] = k
                continue
            # ---- 表达式里的就地变更方法调用 ----
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr in MUTATORS:
                    obj = call.func.value
                    # 接收者是「读取」语境：_key_of_read 已能解析 history / st.session_state.k /
                    # st.session_state['k'] / engine.state.logs 等，落到背后的活键
                    record(stmt.lineno, _key_of_read(obj, bindings, const_map), f"mutate:{call.func.attr}")
    return strict, not_snap, recall_only, 0


# --------------------------------------------------------------------------
# 文本口径召回（psy-dfinplace §三 四式，独立复算对照，与 AST 口径互补）
# --------------------------------------------------------------------------
_TEXT_PATTERNS = OrderedDict([
    ("整体别名(行尾即止)  ^\\s*\\w+ = st\\.session_state\\s*(#.*)?$",
     re.compile(r"^\s*(\w+)\s*=\s*st\.session_state\s*(?:#.*)?$")),
    ("键值别名(纯键式)     ^\\s*\\w+ = st\\.session_state\\.(key)\\s*$",
     re.compile(r"^\s*(\w+)\s*=\s*st\.session_state\.(\w+)\s*$")),
    ("宽召回上限          ^\\s*\\w+ = st\\.session_state\\b",
     re.compile(r"^\s*\w+\s*=\s*st\.session_state\b")),
])


def text_recall(files: list[Path]) -> dict[str, object]:
    counts: dict[str, object] = {}
    whole_alias = 0
    kv_alias_lines = 0
    kv_keys: set[str] = set()
    broad_upper = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for line in lines:
            if _TEXT_PATTERNS["整体别名(行尾即止)  ^\\s*\\w+ = st\\.session_state\\s*(#.*)?$"].match(line):
                whole_alias += 1
            m = _TEXT_PATTERNS["键值别名(纯键式)     ^\\s*\\w+ = st\\.session_state\\.(key)\\s*$"].match(line)
            if m:
                kv_alias_lines += 1
                kv_keys.add(m.group(2))
            if _TEXT_PATTERNS["宽召回上限          ^\\s*\\w+ = st\\.session_state\\b"].search(line):
                broad_upper += 1
    counts["整体别名_行尾即止"] = whole_alias
    counts["键值别名_纯键式_处"] = kv_alias_lines
    counts["键值别名_纯键式_键数"] = len(kv_keys)
    counts["宽召回上限_含派生"] = broad_upper
    return counts


def iter_production_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO.rglob("*.py"):
        rel_parts = path.relative_to(REPO).parts
        if any(part in EXCLUDE_TOP for part in rel_parts):
            continue
        files.append(path)
    return sorted(files)


def _build_const_map(files: list[Path]) -> dict[str, str]:
    """全仓模块级 `NAME = "字符串"` 汇总，用于解析 .get(NAME) 常量键。import 现取者优先。"""
    const_map: dict[str, str] = {}
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name):
                val, is_lit = _literal_or_name(stmt.value)
                if val is not None and is_lit:
                    const_map.setdefault(stmt.targets[0].id, val)
    const_map.update(_snap_constant_values())  # import 现取的权威值覆盖同名
    return const_map


def run(quiet: bool) -> int:
    files = iter_production_files()
    const_map = _build_const_map(files)
    snap_names, prefixes = build_snapshot_keys(const_map)

    strict: list[Hit] = []
    not_snap: list[Hit] = []
    recall_only: list[Hit] = []
    parse_errors = 0
    for path in files:
        s, n, r, e = scan_file(path, snap_names, prefixes, const_map)
        strict.extend(s)
        not_snap.extend(n)
        recall_only.extend(r)
        parse_errors += e

    recall_total = len(strict) + len(not_snap) + len(recall_only)
    recall_counts = text_recall(files)

    print("# psy df/session_state 就地写报告型扫描（只报告，不 gate）")
    print(f"扫描生产 .py 文件数：{len(files)}（解析失败 {parse_errors}）")
    print(f"快照读取键：具名 {len(snap_names)} 个"
          + (f" + 前缀族 {prefixes}" if prefixes else ""))
    print()
    print(f"[严格命中 strict]          {len(strict):>4}   可证就地写 且 键 in 快照")
    print(f"[键不在快照 not_in_snap]   {len(not_snap):>4}   可证就地写 但 键 not in 快照（无危害）")
    print(f"[宽口径召回 recall]        {recall_total:>4}   = 严格 + 键不在快照 + 未解析/属性写")
    print()
    print("文本口径召回（psy-dfinplace §三 独立复算，与 AST 口径互补）：")
    for kk, vv in recall_counts.items():
        print(f"  {kk} = {vv}")
    print()

    if not quiet:
        print("=== 严格命中清单（应可与 psy-dfinplace §二『严格可证 13 处』逐条对照）===")
        for h in sorted(strict, key=lambda x: (x.file, x.line)):
            print("  " + h.label())
        print()
        print("=== 键不在快照（可证就地写，无危害）===")
        for h in sorted(not_snap, key=lambda x: (x.file, x.line)):
            print("  " + h.label())
        print()
        print("=== 宽口径召回中的未解析/属性式项（仅线索，需人工读码）===")
        for h in sorted(recall_only, key=lambda x: (x.file, x.line)):
            print("  " + h.label())

    # 报告型：恒 exit 0，不做门禁（首晚基线未定）
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="psy 就地变更报告型扫描（只报告，不 gate）")
    parser.add_argument("-q", "--quiet", action="store_true", help="只打印三类计数")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # 本控 cp936 会因中文/符号 UnicodeEncodeError
    except Exception:  # noqa: BLE001 - 非 tty（如已重定向）时 reconfigure 可能不可用，忽略
        pass
    return run(quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
