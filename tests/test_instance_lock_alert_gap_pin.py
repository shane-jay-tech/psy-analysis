# -*- coding: utf-8 -*-
"""instance_lock 告警日志**缺口现状**钉桩（s922-130，KNOWN_ISSUES P1 余留防误抵账）。

锚点开工实测复核（2026-09-23，HEAD f6fc82d 脏工作树）：
- `src/utils/instance_lock.py:88`「def project_lock(lock_dir, *, stale_seconds: float = DEFAULT_STALE_SECONDS):」
  —— 与工单**逐字一致**，无漂移。
- `src/utils/project_manager.py:85`「        with project_lock(PROJECTS_DIR):」
  —— 逐字一致；且全仓 `src/` 下 `project_lock(` 的**唯一**调用点（另一处命中是
  `src/ui/literature_review_panel.py:83` 的注释文本，不是调用）。PROJECTS_DIR 由
  `src/utils/app_paths.py:19` 定义（`APP_HOME / "projects"`），project_manager 经 `src/utils/app_paths` 导入。
- `KNOWN_ISSUES.md:101` P1 行 —— 行在、语义在，但**工单只引了前半句**：磁盘实况在该行尾部另有
  2026-09-21 追加的限定「feed 侧 `lock_manager._alert_once`（d914-19）与 untracked
  `tests/test_lock_alert_log.py` 是**另一把锁**，勿混为抵账」⇒ 本套件按磁盘实况钉，并把这条边界
  一起钉死（见 test_feed_side_alert_hook_is_a_different_lock）。

原状登记（s922-130 立钉时）与现况：
1. 告警面：s922-130 立钉时源内 0 告警（连 logging 都没 import）；**1c81986（s1011-03）接线
   logging.warning 后已非此态**——本面已由「现状断言」改写为「行为断言」（见下 ⚠️ 节）；
2. 锁粒度＝**目录级**一把锁（`lock_dir / LOCK_FILENAME`，单一固定文件名），不是按项目分锁；
3. 陈旧锁接管路径**存在**（`age > stale_seconds` + pid 探活 + `os.replace` 挪走再删）。

⚠️ 2026-10-24 回写（s1023-05）：告警接线已落地（1c81986，s1011-03），上节两条
「0 告警」现状断言按本文件自述指令改写为行为断言（warning 三要素＋logging 设施在位）；
teeth 自证随零探测器一并退役。粒度/消费点/stale 接管要件/600s 窗各钉不变。

零 IO、零子进程、零网络、零 Streamlit：全部是源码文本 + ast 静态判定。
**不改 src/utils/instance_lock.py，也不改 src/utils/project_manager.py。**
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LOCK_SRC = REPO / "src" / "utils" / "instance_lock.py"
PM_SRC = REPO / "src" / "utils" / "project_manager.py"
APP_PATHS_SRC = REPO / "src" / "utils" / "app_paths.py"
KNOWN_ISSUES = REPO / "KNOWN_ISSUES.md"
FEED_LOCK_MANAGER_SRC = REPO / "src" / "literature_feed" / "scheduler" / "lock_manager.py"


def _read(path: Path) -> str:
    assert path.exists(), f"锚点文件缺失：{path}"
    return path.read_text(encoding="utf-8", errors="replace")


def _alert_hits(text: str) -> list[int]:
    """返回出现 `alert`（忽略大小写）的行号。"""
    return [n for n, line in enumerate(text.splitlines(), 1) if "alert" in line.lower()]


def _func_node(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"源内找不到函数 {name}")


@pytest.fixture(scope="module")
def lock_text() -> str:
    return _read(LOCK_SRC)


# ------------------------------------------------- 告警接线行为断言（s1023-05 回写）
# 前史：s922-130 曾钉「0 告警」现状；1c81986（s1011-03）接线 logging.warning 后两条
# 现状断言翻红（本文件 docstring 自述的预期信号）——s1023-05 按指令改写为行为断言。

def test_instance_lock_source_has_zero_alert_reference(lock_text):
    """告警命名面：接管告警走 stdlib logging.warning（无自造 alert 钩子命名）。"""
    assert _alert_hits(lock_text) == [], "instance_lock.py 出现 alert 字样 ⇒ 告警命名偏离 stdlib warning 口径"


def test_stale_override_warning_includes_path_pid_age(lock_text):
    """行为断言（替代原「0 warning」现状断言）：stale 接管分支必须带 path/holder/age
    三要素告警（1c81986 契约原文 'stale lock override on %s (holder=%s, age=%.0fs)'）。"""
    fn_src = ast.get_source_segment(lock_text, _func_node(lock_text, "project_lock")) or ""
    assert "logging.warning(" in fn_src, "stale 接管分支缺 logging.warning——告警日志面被拆"
    assert "stale lock override on %s (holder=%s, age=%.0fs)" in fn_src, "告警三要素格式串被改"


def test_instance_lock_imports_logging(lock_text):
    """行为断言（替代原「从不 import logging」现状断言）：日志设施在位。"""
    assert any(
        line.lstrip().startswith("import logging") or line.lstrip().startswith("from logging")
        for line in lock_text.splitlines()
    ), "instance_lock.py 无日志设施 import——告警日志面被拆"


# --------------------------------------------------------------------------- 锁粒度与消费点


def test_only_production_consumer_is_project_manager():
    """唯一消费点：src/ 下 `project_lock(...)` 的调用点恰好 1 处，且位于 project_manager.py。"""
    calls: list[tuple[Path, ast.Call]] = []
    for py in sorted((REPO / "src").rglob("*.py")):
        text = _read(py)
        if "project_lock" not in text:
            continue
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "project_lock":
                calls.append((py, node))
    assert len(calls) == 1, [str(p) for p, _ in calls]
    path, _ = calls[0]
    assert path.resolve() == PM_SRC.resolve()


def test_consumer_locks_projects_dir_constant():
    """完成标准 3：project_manager 传入的是 PROJECTS_DIR **常量本身**（目录级），非按项目派生路径。"""
    tree = ast.parse(_read(PM_SRC))
    call = next(
        n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "project_lock"
    )
    assert len(call.args) == 1, "project_lock 只应有一个位置参数（锁目录）"
    arg = call.args[0]
    assert isinstance(arg, ast.Name) and arg.id == "PROJECTS_DIR", ast.dump(arg)
    # 未在调用点偷偷改 stale_seconds ⇒ 陈旧窗口仍是全局默认 600s
    assert not call.keywords, [kw.arg for kw in call.keywords]


def test_projects_dir_is_the_shared_projects_root():
    """PROJECTS_DIR 的来源与形状：app_paths 里的 `APP_HOME / "projects"` 目录常量。"""
    pm_text = _read(PM_SRC)
    assert "from src.utils.app_paths import" in pm_text and "PROJECTS_DIR" in pm_text
    tree = ast.parse(_read(APP_PATHS_SRC))
    assign = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "PROJECTS_DIR" for t in n.targets)
    )
    assert isinstance(assign.value, ast.BinOp) and isinstance(assign.value.op, ast.Div)


def test_lock_granularity_is_one_file_per_directory(lock_text):
    """目录级粒度：锁路径 = lock_dir / LOCK_FILENAME（单一固定文件名），函数体内不按项目 id 派生路径。"""
    fn_src = ast.get_source_segment(lock_text, _func_node(lock_text, "project_lock")) or ""
    assert "lock_dir = Path(lock_dir)" in fn_src
    assert "lock_path = lock_dir / LOCK_FILENAME" in fn_src
    for token in ("project_id", "LOCK_FILENAME %", ".json"):
        assert token not in fn_src, f"project_lock 出现按项目派生路径的 {token!r} ⇒ 锁粒度已改变，须回写 KNOWN_ISSUES"
    # 模块级 LOCK_FILENAME 是单个文件名（不含路径分隔符）
    m = ast.parse(lock_text)
    value = next(
        n.value
        for n in m.body
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "LOCK_FILENAME" for t in n.targets)
    )
    assert isinstance(value, ast.Constant) and isinstance(value.value, str)
    assert "/" not in value.value and "\\" not in value.value


# --------------------------------------------------------------------------- stale 接管路径


def test_stale_takeover_path_present(lock_text):
    """钉「接管路径存在」：告警接线时的改动热点就在这一段，缺件即判红。"""
    fn_src = ast.get_source_segment(lock_text, _func_node(lock_text, "project_lock")) or ""
    for token in ("stale_seconds: float = DEFAULT_STALE_SECONDS", "age > stale_seconds", "_pid_alive(", "os.replace("):
        assert token in fn_src, f"project_lock 缺少陈旧接管要件 {token!r}"
    assert ".stale-" in fn_src, "陈旧锁挪走标记（防双夺取竞态）被删"
    assert "ProjectLockedError" in fn_src


def test_default_stale_window_constant_is_pinned(lock_text):
    """默认陈旧窗口 600s：告警/回退策略改动常顺手动这个数，钉住现值以便改动显式化。"""
    tree = ast.parse(lock_text)
    value = next(
        n.value
        for n in tree.body
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "DEFAULT_STALE_SECONDS" for t in n.targets)
    )
    assert isinstance(value, ast.Constant) and float(value.value) == 600.0


# --------------------------------------------------------------------------- 文档与「另一把锁」边界


def test_known_issues_p1_row_still_declares_alert_residual():
    """KNOWN_ISSUES 的 P1「多实例项目写入」行仍声明余留＝告警日志，并保留「另一把锁」限定。"""
    row = next(
        (line for line in _read(KNOWN_ISSUES).splitlines() if line.startswith("| P1 | 多实例项目写入 |")),
        None,
    )
    assert row is not None, "P1 行被删除 ⇒ 请同步处置 tests/test_instance_lock_alert_gap_pin.py"
    assert "instance_lock.project_lock" in row
    assert "余留＝可选告警日志" in row, "余留项被改写 ⇒ 若告警已落地，本套件与工单口径需同步更新"
    assert "另一把锁" in row, "「feed 侧是另一把锁」的限定被删，存在误抵账风险"


def test_feed_side_alert_hook_is_a_different_lock(lock_text):
    """防误抵账：feed 侧 LockManager 确实有 _alert_once，但它与 instance_lock 无任何导入关系。"""
    feed_text = _read(FEED_LOCK_MANAGER_SRC)
    assert "def _alert_once" in feed_text, "feed 侧告警钩子消失 ⇒ KNOWN_ISSUES:101 的限定需重述"
    assert "logging.warning" in feed_text, "feed 侧 _alert_once 已失效 ⇒ 不能再用它抵 instance_lock 的账"
    assert "literature_feed" not in lock_text and "LockManager" not in lock_text
    assert _alert_hits(lock_text) == [], "instance_lock 自身出现 alert ⇒ 缺口已闭合，本用例与 KNOWN_ISSUES:101 需同步改写"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([str(Path(__file__).relative_to(REPO)), "-q"]))
