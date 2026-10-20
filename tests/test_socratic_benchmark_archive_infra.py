"""scripts/evaluate_socratic_benchmark.py 归档基建的离线钉桩（s922-125）。

只钉 `HISTORY_DIR` / `_last_history_entry`（末次归档读取）/ `_archive_to_history`（归档动作）三件 #L3
基建：**全程 tmp_path、不跑 judge、不写 `data/benchmark_history`、不带网、不起子进程**。
autouse 夹具给真实历史目录做"名字＋字节数＋mtime_ns"面簿，用例跑完逐位比对 ⇒ 判据 2 自证。

🔴 派单前提否证（按实况收窄，未改 src/ 一个字节）
1. 「断言 `_last_history_entry` 取 mtime 最新」方向反了：`evaluate_socratic_benchmark.py:128-142`
   实测是 **按文件名字典序** 取末位（注释自己写明"UTC 时间戳保证字典序＝时间序"），
   mtime 只用于姊妹函数 `_latest_report`（`:120-126`）。⇒ 本件用"名字晚、mtime 反而旧"的
   交叉样本把两面的差别钉死（哪天有人把读取改成按 mtime 排，这条立刻红）。
2. 「基建无任何单测」半否证，三件事各自不同：
   - `HISTORY_DIR` 常量：`tests/test_benchmark_relay_paths.py:81` 已钉（默认跑，实测 6 passed）；
   - `_archive_to_history`：`tests/test_socratic_drift_tracker.py:85-97` **有用例且默认全跑**——
     s923-34 拆分后该件已不带文件级 `pytestmark = pytest.mark.benchmark`（见该件 :6 标记口径注），
     2026-10-05 实测 `10 passed, 0 skipped` ⇒ 默认全量里在跑（本条订正 d507 时代的 `10 skipped` 旧读数）；
   - `_last_history_entry`：全仓 `tests/` **零引用** ⇒ 这才是真空缺。
   ⇒ 本件**不打 benchmark 标记**（基建与 LLM 无关，不该被基准门禁挡着），并把上面三条现状各钉一处。
3. 顺带钉出两个现状风险（s922-125 只登记；**s924-65 已修，生产码与本件同笔**）：
   ① 同秒两次归档会撞同一个文件名（时间戳只到秒）⇒ `_archive_to_history` 现在在目标已存在时
   追加定宽序号 `_001`；② Windows 侧 `glob("*.json")` 大小写不敏感会把 `UPPER.JSON` 认成历史项
   ⇒ `_last_history_entry` 现在改用 `iterdir()` ＋ 区分大小写的 `.json` 后缀过滤 ＋ 排除下划线前缀件。
   下面两处原先"登记现状"的用例已按修复后的语义改写（见 `test_two_archives_inside_the_same_second_do_not_collide`
   与 `test_uppercase_json_suffix_is_not_claimed_on_windows`），并补两条新钉：
   `test_underscore_prefixed_json_sidecar_is_not_claimed_as_history_entry`（修②的 sidecar 面）与
   `test_ten_same_second_archives_stay_lexically_monotonic`（修①的序号定宽面）。
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import evaluate_socratic_benchmark as evaluate

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_HISTORY_DIR = REPO_ROOT / "data" / "benchmark_history"
# s924-65 修①之后，同秒撞名的追加件形如 `..._001.json` —— `(_\d{3})?` 是**新增形态**而非放宽：
# 时间戳部分仍逐位锁死，且 `test_same_second_archives_stay_isomorphic_with_the_archive_pattern`
# 会把基础名与追加名两头都塞进这条正则验一遍。
ARCHIVE_NAME_PATTERN = r"socratic_benchmark_\d{8}T\d{6}Z(_\d{3})?\.json"
FROZEN_UTC = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


class _FrozenDatetime:
    """替换 `evaluate.datetime`：让归档时间戳可预测（monkeypatch 进程内替身，模块真身不动）。"""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self, tz=None) -> datetime:      # noqa: ANN001 - 与真实 datetime.now 同签名
        return self._instant


def _report(tag: str) -> str:
    return json.dumps({"version": "v3.3", "tag": tag, "results": []}, ensure_ascii=False)


@pytest.fixture(autouse=True)
def real_history_dir_untouched():
    """判据 2 的自证：真实 `data/benchmark_history` 在每条用例前后逐位不变（面簿含名字/字节数/mtime_ns）。"""
    def inventory() -> list[tuple[str, int, int]]:
        if not REAL_HISTORY_DIR.exists():
            return []
        return sorted(
            (p.name, p.stat().st_size, p.stat().st_mtime_ns)
            for p in REAL_HISTORY_DIR.iterdir()
        )

    before = inventory()
    yield
    assert inventory() == before, "有用例把东西写进了真实历史目录（本件只许用 tmp_path）"


@pytest.fixture
def history_dir(tmp_path) -> Path:
    return tmp_path / "history"


@pytest.fixture
def report_dir(tmp_path) -> Path:
    d = tmp_path / "reports"
    d.mkdir(parents=True)
    return d


# ══════════════════ 一、末次归档读取 _last_history_entry ══════════════════


def test_last_history_entry_is_none_when_the_dir_does_not_exist(history_dir):
    assert evaluate._last_history_entry(history_dir) is None


def test_last_history_entry_is_none_when_no_json_is_archived_yet(history_dir):
    history_dir.mkdir()
    (history_dir / "_latest_drift.md").write_text("# 漂移报告", encoding="utf-8")
    (history_dir / "notes.txt").write_text("x", encoding="utf-8")

    assert evaluate._last_history_entry(history_dir) is None, "非 .json 条目不该被当成历史归档"


def test_last_history_entry_orders_by_filename_and_ignores_mtime(history_dir):
    """🔴 前提否证 1 落地：名字序与 mtime 序**故意相反**，取的是名字大的那个。

    判别力自证（注入交叉样本）：若实现哪天改成按 mtime 排，本条当场红——
    这也是与姊妹函数 `_latest_report`（`:120-126`，真按 mtime）的分工边界。
    """
    history_dir.mkdir()
    name_later_mtime_older = history_dir / "socratic_benchmark_20260102T000000Z.json"
    name_earlier_mtime_newer = history_dir / "socratic_benchmark_20260101T000000Z.json"
    name_later_mtime_older.write_text(_report("A"), encoding="utf-8")
    name_earlier_mtime_newer.write_text(_report("B"), encoding="utf-8")
    os.utime(name_later_mtime_older, (1_600_000_000, 1_600_000_000))     # 2020
    os.utime(name_earlier_mtime_newer, (1_900_000_000, 1_900_000_000))   # 2030

    assert max([name_later_mtime_older, name_earlier_mtime_newer],
               key=lambda p: p.stat().st_mtime) is name_earlier_mtime_newer
    assert evaluate._last_history_entry(history_dir) == name_later_mtime_older


def test_last_history_entry_does_not_recurse_into_subdirectories(history_dir):
    """子目录里的 .json 不算归档项（`glob` 非递归）：漂移序列不能被杂物打断。"""
    history_dir.mkdir()
    (history_dir / "socratic_benchmark_20260101T000000Z.json").write_text(_report("A"), encoding="utf-8")
    nested = history_dir / "attic"
    nested.mkdir()
    (nested / "socratic_benchmark_20990101T000000Z.json").write_text(_report("future"), encoding="utf-8")

    picked = evaluate._last_history_entry(history_dir)

    assert picked is not None and picked.parent == history_dir


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 侧 glob 大小写不敏感，POSIX 不成立")
def test_uppercase_json_suffix_is_not_claimed_on_windows(history_dir):
    """s924-65 修②：误命名的大写后缀件不得进入末次归档候选。

    原用例（s922-125）钉的是**反方向**的现状（`.name == "UPPER.JSON"`，即"它确实会盖掉末次读数"），
    随修复一并改写；登记语义见模块 docstring 前提 3。判别力：把 `_last_history_entry` 的收集面
    换回 `glob("*.json")` 本条当场红 —— win32 上 `Path` 比较走 casefold，`UPPER.JSON` 会排到
    真实归档**之后**。
    """
    history_dir.mkdir()
    real = history_dir / "socratic_benchmark_20260101T000000Z.json"
    real.write_text(_report("A"), encoding="utf-8")
    (history_dir / "UPPER.JSON").write_text(_report("noise"), encoding="utf-8")

    assert evaluate._last_history_entry(history_dir) == real
    assert (history_dir / "UPPER.JSON").exists(), "过滤只许发生在读取面，不许顺手删别人的文件"

    upper_only = history_dir.parent / "upper_only"
    upper_only.mkdir()
    (upper_only / "UPPER.JSON").write_text(_report("noise"), encoding="utf-8")
    assert evaluate._last_history_entry(upper_only) is None, "目录里只剩误命名件时宁缺毋滥"


def test_underscore_prefixed_json_sidecar_is_not_claimed_as_history_entry(history_dir):
    """修②的另一面：`_` 前缀的 sidecar 哪怕后缀是 `.json` 也不算归档（跨平台都成立）。

    只有一枚 `_latest_drift_backup.json` 时**必须读成 None** —— 修复前 `glob("*.json")` 会把它
    当成末次归档，`_track_drift` 就拿 sidecar 当 previous 去比了。同名**目录**那半验的是 `is_file()`：
    修复前 `glob` 会把它取中，而它的时间戳字段比真归档新。
    """
    history_dir.mkdir()
    (history_dir / "_latest_drift_backup.json").write_text(_report("sidecar"), encoding="utf-8")
    assert evaluate._last_history_entry(history_dir) is None

    real = history_dir / "socratic_benchmark_20260101T000000Z.json"
    real.write_text(_report("A"), encoding="utf-8")
    assert evaluate._last_history_entry(history_dir) == real

    (history_dir / "socratic_benchmark_20260201T000000Z.json").mkdir()
    assert evaluate._last_history_entry(history_dir) == real, "目录不是归档"


# ══════════════════ 二、归档动作 _archive_to_history ══════════════════


def test_archived_file_name_is_deterministic_under_a_frozen_clock(history_dir, report_dir, monkeypatch):
    """时间戳只到秒 ⇒ 冻表后能逐字比对命名，并与真实归档同构（判据 3）。"""
    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(FROZEN_UTC))
    source = report_dir / "benchmark_NEW.json"
    source.write_text(_report("cand"), encoding="utf-8")

    archived = evaluate._archive_to_history(source, history_dir)

    assert archived.name == "socratic_benchmark_20260304T050607Z.json"
    assert re.fullmatch(ARCHIVE_NAME_PATTERN, archived.name), archived.name


def test_generated_name_is_isomorphic_with_the_real_archive(history_dir, report_dir):
    """判据 3 的另一半：真实历史目录里的归档名走同一条正则（只读列名，不读内容不写盘）。"""
    real_names = [p.name for p in REAL_HISTORY_DIR.glob("socratic_benchmark_*.json")] \
        if REAL_HISTORY_DIR.exists() else []
    assert real_names, "真实历史目录里没有基准归档，判据 3 的同构对照失去对象"

    for name in real_names:
        assert re.fullmatch(ARCHIVE_NAME_PATTERN, name), f"真实归档名与正则不同构：{name}"

    source = report_dir / "benchmark_NEW.json"
    source.write_text(_report("cand"), encoding="utf-8")
    archived = evaluate._archive_to_history(source, history_dir)
    assert re.fullmatch(ARCHIVE_NAME_PATTERN, archived.name)
    assert archived.parent == history_dir


def test_archive_copies_and_leaves_the_source_byte_identical(history_dir, report_dir):
    """归档=复制：原件在、字节同、`copy2` 连 mtime 一起保留（判据 2 的"不动原件"）。"""
    source = report_dir / "benchmark_NEW.json"
    payload = _report("cand")
    source.write_text(payload, encoding="utf-8")
    source_mtime = source.stat().st_mtime_ns

    archived = evaluate._archive_to_history(source, history_dir)

    assert source.exists(), "原件被搬走了（归档应当只复制）"
    assert archived.read_bytes() == source.read_bytes()
    assert json.loads(archived.read_text(encoding="utf-8")) == json.loads(payload)
    assert archived.stat().st_mtime_ns == source_mtime


def test_archive_creates_the_history_dir_when_missing(tmp_path, report_dir):
    target_dir = tmp_path / "deep" / "nested" / "history"
    source = report_dir / "benchmark_NEW.json"
    source.write_text(_report("cand"), encoding="utf-8")

    archived = evaluate._archive_to_history(source, target_dir)

    assert target_dir.is_dir() and archived.parent == target_dir


def test_two_archives_inside_the_same_second_do_not_collide(history_dir, report_dir, monkeypatch):
    """s924-65 修①：同秒两次归档产出**两个不同路径**，首份不再被静默覆盖。

    原用例（s922-125）钉的是"同秒必撞名、历史目录只留一份"的现状，随修复改写；
    登记表见模块 docstring 前提 3。判别力：把 `_archive_to_history` 的 `while target.exists()`
    那一圈去掉，本条在 `path_a != path_b` 上当场红。
    """
    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(FROZEN_UTC))
    first = report_dir / "benchmark_A.json"
    first.write_text(_report("first"), encoding="utf-8")
    second = report_dir / "benchmark_B.json"
    second.write_text(_report("second"), encoding="utf-8")

    path_a = evaluate._archive_to_history(first, history_dir)
    path_b = evaluate._archive_to_history(second, history_dir)

    assert path_a != path_b, "同秒撞名这条现状又回来了：首份会被静默覆盖"
    assert json.loads(path_a.read_text(encoding="utf-8"))["tag"] == "first", "第二份盖掉了第一份"
    assert json.loads(path_b.read_text(encoding="utf-8"))["tag"] == "second"
    assert sorted(p.name for p in history_dir.iterdir()) == sorted([path_a.name, path_b.name])
    assert evaluate._last_history_entry(history_dir) == path_b, "追加件必须排在被追加件之后"
    assert re.fullmatch(ARCHIVE_NAME_PATTERN, path_b.name), path_b.name


def test_ten_same_second_archives_stay_lexically_monotonic(history_dir, report_dir, monkeypatch):
    """修①的边界面：序号**定宽**才守得住"字典序＝时间序"这条模块级不变量。

    若后缀写成不定宽的 `_1`…`_10`，第 10 次的名字会字典序回退到第 2 次之前 ⇒
    `_last_history_entry` 读到的是九份之前的旧归档，漂移对比静默错位。
    """
    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(FROZEN_UTC))
    source = report_dir / "benchmark_A.json"
    names = []
    for run in range(10):
        source.write_text(_report(f"run{run}"), encoding="utf-8")
        names.append(evaluate._archive_to_history(source, history_dir).name)

    assert len(set(names)) == 10, f"同秒 10 次归档只产出 {len(set(names))} 个名字"
    assert names == sorted(names), f"落盘序与字典序不再一致：{names}"
    assert [p.name for p in sorted(history_dir.iterdir())] == names
    assert evaluate._last_history_entry(history_dir).name == names[-1]
    assert names[0] == "socratic_benchmark_20260304T050607Z.json"
    assert names[1] == "socratic_benchmark_20260304T050607Z_001.json"
    assert names[-1] == "socratic_benchmark_20260304T050607Z_009.json"
    for name in names:
        assert re.fullmatch(ARCHIVE_NAME_PATTERN, name), name


def test_next_second_produces_a_distinct_entry(history_dir, report_dir, monkeypatch):
    """对照面，证明上一条不是"归档永远同名"的假阳：跨秒就分叉。"""
    source = report_dir / "benchmark_A.json"
    source.write_text(_report("A"), encoding="utf-8")
    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(FROZEN_UTC))
    first = evaluate._archive_to_history(source, history_dir)
    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(
        FROZEN_UTC.replace(second=8, microsecond=0)))
    second = evaluate._archive_to_history(source, history_dir)

    assert first != second and second.name == "socratic_benchmark_20260304T050608Z.json"
    assert sorted(p.name for p in history_dir.glob("*.json")) == [first.name, second.name]


def test_the_read_then_archive_pair_chains_as_track_drift_expects(history_dir, report_dir, monkeypatch):
    """把"先读末次、再归档"的调用序（`_track_drift` 的 `:211-212`）在 tmp 里复演一遍：
    第二次跑时 previous 必须正是第一次的归档。"""
    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(FROZEN_UTC))
    assert evaluate._last_history_entry(history_dir) is None
    source = report_dir / "benchmark_NEW.json"
    source.write_text(_report("run1"), encoding="utf-8")
    archived = evaluate._archive_to_history(source, history_dir)

    monkeypatch.setattr(evaluate, "datetime", _FrozenDatetime(
        FROZEN_UTC.replace(minute=7, microsecond=0)))
    source.write_text(_report("run2"), encoding="utf-8")
    previous = evaluate._last_history_entry(history_dir)
    archived2 = evaluate._archive_to_history(source, history_dir)

    assert previous == archived
    assert archived2.name == "socratic_benchmark_20260304T050707Z.json"
    assert evaluate._last_history_entry(history_dir) == archived2


# ══════════════════ 三、离线与不越界（判据 4 的机检面） ══════════════════


def test_this_test_file_starts_no_network_stack_and_never_runs_the_main_flow():
    """判据 4 的机检面（对本文件自己 AST 取证）：

    - 模块级 import 里不得出现网络栈；
    - 不得调用 `_track_drift` / `main` / `argparse`（带网主流程的入口）；
    - 允许 `subprocess`，但只许 `-c` 内联探针（psy 第 10 段：证"不导某模块"必须子进程），
      且argv 里不得出现被脚本名＋参数直接拉起的主流程。
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    top_level = [n for n in tree.body]

    banned_network = {"socket", "urllib", "requests", "http", "https", "ssl"}
    module_level_imports: set[str] = set()
    for node in top_level:
        if isinstance(node, ast.Import):
            module_level_imports |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_level_imports.add(node.module.split(".")[0])
    assert module_level_imports & banned_network == set(), f"模块级出现网络栈：{module_level_imports & banned_network}"
    assert "argparse" not in module_level_imports

    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert called & {"_track_drift", "main"} == set(), f"调到了带网主流程：{called & {'_track_drift', 'main'}}"
    attrs = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert attrs & {"_track_drift"} == set()

    spawns = [n for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
              and n.func.attr in {"run", "Popen", "check_output", "check_call", "getoutput", "getstatusoutput"}]
    assert spawns, "本件应至少留一条子进程探针（否则'不导网络栈'的断言不可证）"
    for spawn in spawns:
        segment = ast.get_source_segment(Path(__file__).read_text(encoding="utf-8"), spawn) or ""
        assert "-c" in segment, f"子进程必须在解释器里跑内联探针，不许按脚本名拉起：{segment[:120]}"
        assert "evaluate_socratic_benchmark.py" not in segment, "按脚本名执行＝可能跑主流程"
        for flag in ("--track-drift", "--baseline", "--candidate", "--run-benchmark"):
            assert flag not in segment, f"子进程里出现主流程参数 {flag}"


def test_the_real_history_dir_is_never_an_argument_to_the_archiving_infra():
    """第二道界（判据 2）：本件对 `_archive_to_history` / `_last_history_entry` 的每次调用，
    目的地实参都必须来自 tmp_path 派生变量，不得是真实 `HISTORY_DIR`/`REAL_HISTORY_DIR`。"""
    text = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(text, filename=__file__)
    monitored = {"_archive_to_history", "_last_history_entry"}

    checked = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in monitored):
            continue
        for arg in node.args:
            segment = ast.get_source_segment(text, arg) or ""
            assert "evaluate.HISTORY_DIR" not in segment and "REAL_HISTORY_DIR" not in segment, \
                f"真实历史目录被当成归档目的地：{segment}"
            checked += 1

    assert checked >= 12, f"只核到 {checked} 个实参，调用点被改少了（本件的越界面缩水）"


def test_evaluate_module_imports_no_outbound_network_stack_in_a_fresh_process():
    """子进程法（psy 第 10 段：同进程断言 sys.modules 必假绿）：干净解释器里 import 本脚本，
    出站网络栈一个都不许出现。

    🔎 探针实测：`import scripts.evaluate_socratic_benchmark` 确实会让 sys.modules 多出
    `urllib` 与 `urllib.parse` —— 但它俩是 **stdlib `pathlib` 的传递依赖**
    （`-X importtime` 树里挂在 pathlib 下，供 `Path.as_uri()` 用），不是"脚本会联网"。
    ⇒ 判据按实况写成两条：① 出站能力（`socket`/`ssl`/`http.client`/`urllib.request`/`ftplib`/
    第三方 `requests`/`httpx`）零加载；② `urllib.parse` 允许，但若哪天 `urllib.request` 出现就红。
    """
    probe = (
        "import sys\n"
        "import scripts.evaluate_socratic_benchmark as m\n"
        "outbound = [k for k in sys.modules if k in ('socket', 'ssl', 'http', 'http.client',\n"
        "    'urllib.request', 'urllib.error', 'ftplib', 'telnetlib', 'requests', 'httpx',\n"
        "    'aiohttp', 'urllib3', 'subprocess')]\n"
        "parsed = [k for k in sys.modules if k.startswith('urllib.parse')]\n"
        "print('HISTORY', m.HISTORY_DIR.name)\n"
        "print('OUTBOUND', sorted(set(outbound)))\n"
        "print('PARSE_ONLY', sorted(set(parsed)))\n"
    )

    proc = subprocess.run(
        [sys.executable, "-c", probe], cwd=str(REPO_ROOT), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=180,
    )

    assert proc.returncode == 0, proc.stderr[-600:]
    assert "HISTORY benchmark_history" in proc.stdout
    tail = proc.stdout.splitlines()[-2:]
    assert tail[0] == "OUTBOUND []", f"import 阶段就装了出站网络能力：{tail[0]}"
    assert tail[1] == "PARSE_ONLY ['urllib.parse']", \
        f"urllib.parse 的传递依赖面变了，本件的'离线'口径要重述：{tail[1]}"
