"""用户偏好持久化测试（v3.7）。"""

import json
import tempfile
from pathlib import Path

import pytest

from src.utils import user_prefs


@pytest.fixture
def tmp_prefs(monkeypatch, tmp_path):
    fake_dir = tmp_path / ".psy_analysis"
    fake_file = fake_dir / "user_prefs.json"
    monkeypatch.setattr(user_prefs, "PREFS_DIR", fake_dir)
    monkeypatch.setattr(user_prefs, "PREFS_FILE", fake_file)
    yield fake_file


class TestLoadSavePrefs:
    def test_load_when_no_file_returns_empty(self, tmp_prefs):
        assert user_prefs.load_prefs() == {}

    def test_save_and_load_round_trip(self, tmp_prefs):
        prefs = {"privacy_accepted": True, "onboarding_completed": True, "language": "zh"}
        assert user_prefs.save_prefs(prefs)
        loaded = user_prefs.load_prefs()
        assert loaded == prefs

    def test_corrupted_file_returns_empty(self, tmp_prefs):
        tmp_prefs.parent.mkdir(parents=True)
        tmp_prefs.write_text("not json", encoding="utf-8")
        assert user_prefs.load_prefs() == {}

    def test_failed_atomic_save_keeps_previous_preferences(self, tmp_prefs, monkeypatch):
        assert user_prefs.save_prefs({"language": "zh"})

        def fail_replace(_src, _dst):
            raise OSError("interrupted")

        monkeypatch.setattr(user_prefs.os, "replace", fail_replace)
        assert not user_prefs.save_prefs({"language": "en"})
        assert json.loads(tmp_prefs.read_text(encoding="utf-8"))["language"] == "zh"
        assert list(tmp_prefs.parent.glob(".user_prefs.*.tmp")) == []


class TestUpdatePref:
    def test_update_creates_file(self, tmp_prefs):
        assert user_prefs.update_pref("privacy_accepted", True)
        assert tmp_prefs.exists()
        loaded = user_prefs.load_prefs()
        assert loaded["privacy_accepted"] is True

    def test_update_preserves_others(self, tmp_prefs):
        user_prefs.save_prefs({"privacy_accepted": True, "language": "zh"})
        user_prefs.update_pref("onboarding_completed", True)
        loaded = user_prefs.load_prefs()
        assert loaded["privacy_accepted"] is True
        assert loaded["onboarding_completed"] is True
        assert loaded["language"] == "zh"


class TestApplyToSession:
    def test_applies_persisted_keys(self, tmp_prefs):
        user_prefs.save_prefs({
            "privacy_accepted": True,
            "onboarding_completed": True,
            "irrelevant_key": "should_not_apply",
        })
        session = {"privacy_accepted": False, "onboarding_completed": False}
        user_prefs.apply_to_session(session)
        assert session["privacy_accepted"] is True
        assert session["onboarding_completed"] is True
        # 非 PERSISTED_KEYS 不应被覆盖
        assert "irrelevant_key" not in session

    def test_no_file_no_change(self, tmp_prefs):
        session = {
            "privacy_accepted": False,
            "onboarding_completed": False,
            "_onboarding_skipped": False,
        }
        user_prefs.apply_to_session(session)
        assert session["privacy_accepted"] is False
        assert session["onboarding_completed"] is False
        assert session["_onboarding_skipped"] is False


class TestSyncFromSession:
    def test_writes_changed_values(self, tmp_prefs):
        session = {"privacy_accepted": True, "onboarding_completed": True}
        user_prefs.sync_from_session(session)
        loaded = user_prefs.load_prefs()
        assert loaded["privacy_accepted"] is True


class TestResetPrefs:
    def test_reset_removes_file(self, tmp_prefs):
        user_prefs.save_prefs({"x": 1})
        assert tmp_prefs.exists()
        user_prefs.reset_prefs()
        assert not tmp_prefs.exists()

    def test_reset_when_no_file_succeeds(self, tmp_prefs):
        # 文件不存在时 reset 应返回 True，不报错
        assert user_prefs.reset_prefs()


class TestIntegration:
    def test_typical_flow_first_visit_then_subsequent(self, tmp_prefs):
        """模拟首次访问 → 同意隐私 → 第二次访问应跳过。"""
        # 首次：session 默认 privacy_accepted=False
        session_first = {"privacy_accepted": False}
        user_prefs.apply_to_session(session_first)
        assert session_first["privacy_accepted"] is False    # 文件不存在

        # 用户点同意 → 持久化
        session_first["privacy_accepted"] = True
        user_prefs.update_pref("privacy_accepted", True)

        # 第二次访问：模拟新启动
        session_second = {"privacy_accepted": False}     # streamlit 默认值
        user_prefs.apply_to_session(session_second)
        assert session_second["privacy_accepted"] is True    # 已从文件恢复
