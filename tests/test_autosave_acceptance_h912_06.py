"""h912-06 方案 B 收尾测试：「返回＝受理」窗口语义＋换案阈值分支＋异常路径。

不改动 test_autosave_bg.py / test_autosave.py 既有断言。
"""

from __future__ import annotations

import threading

import pytest

from src.utils import autosave as autosave_mod
from src.utils import autosave_bg
from src.utils import project_manager as pm


@pytest.fixture
def temp_projects(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(pm, "INDEX_FILE", tmp_path / "index.json")
    yield tmp_path


def test_accepted_return_true_before_persist(temp_projects, monkeypatch):
    """受理窗口：trigger_autosave 返回 True 时真落盘（orig_save）尚未被调用，flush 后完成。"""
    proj = pm.create_project("accept")
    gate = threading.Event()
    calls = []
    orig_save = pm.save_workspace

    def slow_save(project_id, ws):
        calls.append(project_id)
        gate.wait(timeout=5)
        return orig_save(project_id, ws)

    monkeypatch.setattr(pm, "save_workspace", slow_save)
    fss = autosave_mod.FakeSessionState({"meta": {"who": "accept"}, "file_name": "x.csv"})
    pm.set_active_project(fss, proj.id)
    try:
        accepted = autosave_mod.trigger_autosave(fss, lambda: {}, force=True)
        assert accepted is True  # 受理
        assert calls == []  # 返回≠已落盘：worker 还没走到 save_workspace
    finally:
        gate.set()
    done, _ = autosave_bg.flush(timeout=5)
    assert done
    assert calls == [proj.id]  # flush 后真正落盘恰好一次


def test_threshold_warning_logged_over(temp_projects, monkeypatch, caplog):
    """df 序列化体量超实测换案阈值 → worker 告警日志。"""
    proj = pm.create_project("big")
    # 快照配方的 df_b64 来自 df.to_csv 产物：CSV 11MB → b64 ≈14.7MB > 阈值（CSV 10MB）
    csv_chars = int(autosave_bg.SNAPSHOT_WORKER_B64_BYTES_THRESHOLD * 3 / 4) + 1_000_000

    class BigDF:
        def to_csv(self, buf, *a, **k):
            buf.write("x" * csv_chars)

    fss = autosave_mod.FakeSessionState({"df": BigDF(), "file_name": "big.csv"})
    pm.set_active_project(fss, proj.id)
    with caplog.at_level("WARNING", logger="src.utils.autosave_bg"):
        assert autosave_mod.trigger_autosave(fss, lambda: {}, force=True) is True
        done, _ = autosave_bg.flush(timeout=10)
        assert done
    assert "超换案阈值" in caplog.text


def test_no_warning_below_threshold(temp_projects, monkeypatch, caplog):
    """小快照不触发换案告警。"""
    proj = pm.create_project("small")
    fss = autosave_mod.FakeSessionState({"meta": {"who": "small"}, "file_name": "s.csv"})
    pm.set_active_project(fss, proj.id)
    with caplog.at_level("WARNING", logger="src.utils.autosave_bg"):
        assert autosave_mod.trigger_autosave(fss, lambda: {}, force=True) is True
        done, _ = autosave_bg.flush(timeout=10)
        assert done
    assert "超换案阈值" not in caplog.text


def test_sync_path_builder_exception_returns_false(temp_projects):
    """同步路径 workspace 构建异常 → False＋错误键，不抛出。"""
    proj = pm.create_project("boom")

    def bad_builder():
        raise RuntimeError("builder exploded")

    state = {"df": None}
    pm.set_active_project(state, proj.id)
    ok = autosave_mod.trigger_autosave(state, bad_builder, force=True)
    assert ok is False
    assert "自动保存准备失败" in state[autosave_mod.SESSION_LAST_ERROR_KEY]


def test_worker_exception_drains_error_key(temp_projects):
    """worker 内序列化异常 → 错误经 _drain_background_result 结转进错误键。"""

    class PoisonDF:
        def to_csv(self, *a, **k):
            raise ValueError("poison df")

    proj = pm.create_project("poison")
    fss = autosave_mod.FakeSessionState({"df": PoisonDF(), "file_name": "p.csv"})
    pm.set_active_project(fss, proj.id)
    assert autosave_mod.trigger_autosave(fss, lambda: {}, force=True) is True
    done, _ = autosave_bg.flush(timeout=10)
    assert done
    # 不预取 drain_result——结转由 trigger 入口/_drain_background_result 原子 swap 完成
    autosave_mod._drain_background_result(fss)
    assert "自动保存写入失败" in fss[autosave_mod.SESSION_LAST_ERROR_KEY]
    assert autosave_bg.drain_result() is None  # swap 后槽已清空
