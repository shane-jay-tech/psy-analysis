# -*- coding: utf-8 -*-
"""research_release_gate.py 测试补位（s927-11，未跟踪件入库前的可测性钉）。

被测件：scripts/research_release_gate.py（研究发布门禁·五环节·三态）。
钉四件事，全部与脚本 docstring 的契约逐字对应：
  ① 三态判定：任何环节失败→FAIL(1)；全绿未签收→BLOCKED(2)；全绿＋--confirm-review→PASS(0)
     且 HUMAN_REVIEW.json 落盘（reviewer 姓名＋时间）；
  ② --fail-probe 注入的必败环节无论是否签收都把结论压到 FAIL；
  ③ check_data_sources：库缺失→False；库在但 integrity 非 ok / sources 空→False；
     库完好且非空→True（monkeypatch rg.BASE 指向 tmp_path，不碰真库）；
  ④ run_cmd：退出码透传、输出尾截到 2000 字符、超时→(124, "TIMEOUT")。
隔离手段：monkeypatch rg.BASE→tmp_path（证据目录落 tmp）＋ monkeypatch rg.run_cmd/
rg.check_data_sources（不跑重 pytest 环节，全件 <2s）。零网络、零真库触碰。

复跑：PYTHONIOENCODING=utf-8 python -m pytest tests/test_research_release_gate.py -q
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import research_release_gate as rg  # noqa: E402


@pytest.fixture
def gate_env(tmp_path, monkeypatch):
    """把 BASE 拐进 tmp：证据目录与（如需）feed.sqlite 全部落 tmp_path。"""
    monkeypatch.setattr(rg, "BASE", tmp_path)
    return tmp_path


def _run_main(monkeypatch, *args):
    """main() 经 argparse 读 sys.argv——测试侧用 argv 注入替代位置参数。"""
    monkeypatch.setattr(sys, "argv", ["research_release_gate.py", *args])
    return rg.main()


def _ev_files(base: Path) -> list[str]:
    ev_root = base / "tmp" / "gate-evidence"
    dirs = sorted(ev_root.iterdir())
    assert len(dirs) == 1, f"一次运行只应产生一个证据目录，实得 {len(dirs)}"
    return sorted(p.name for p in dirs[0].iterdir())


# ---------------------------------------------------------------- ① 三态判定
def test_全绿未签收_blocked(gate_env, monkeypatch):
    monkeypatch.setattr(rg, "check_data_sources", lambda: (True, "ok"))
    monkeypatch.setattr(rg, "run_cmd", lambda cmd, timeout=600: (0, "ok"))
    assert _run_main(monkeypatch) == 2
    files = _ev_files(gate_env)
    assert "HUMAN_REVIEW.json" not in files          # 未签收不该有签收件
    assert "1-数据来源.json" in files                 # 五环节证据逐环节落盘
    assert "5-匿名化.json" in files


def test_全绿签收_PASS_且签收件落盘(gate_env, monkeypatch):
    monkeypatch.setattr(rg, "check_data_sources", lambda: (True, "ok"))
    monkeypatch.setattr(rg, "run_cmd", lambda cmd, timeout=600: (0, "ok"))
    assert _run_main(monkeypatch, "--confirm-review", "测试复核人") == 0
    ev_dir = sorted((gate_env / "tmp" / "gate-evidence").iterdir())[0]
    signed = json.loads((ev_dir / "HUMAN_REVIEW.json").read_text(encoding="utf-8"))
    assert signed["reviewer"] == "测试复核人"
    assert "at" in signed                            # 签收时间留痕


def test_任一环节失败_FAIL_优先于签收(gate_env, monkeypatch):
    monkeypatch.setattr(rg, "check_data_sources", lambda: (True, "ok"))

    def fake_run(cmd, timeout=600):
        # 仅统计环节失败（第二条命令起全部返 1），其余环节绿
        joined = " ".join(cmd)
        if "test_golden_stats_v2" in joined:
            return 1, "boom: 3 failed"
        return 0, "ok"

    monkeypatch.setattr(rg, "run_cmd", fake_run)
    assert _run_main(monkeypatch, "--confirm-review", "测试复核人") == 1   # fail 压过签收


# ---------------------------------------------------------------- ② fail-probe
def test_fail_probe必败演练_压过签收(gate_env, monkeypatch):
    monkeypatch.setattr(rg, "check_data_sources", lambda: (True, "ok"))

    def fake_run(cmd, timeout=600):
        if any("sys.exit(3)" in a for a in cmd):
            return 3, "probe fail"                   # 必败演练命令
        return 0, "ok"

    monkeypatch.setattr(rg, "run_cmd", fake_run)
    assert _run_main(monkeypatch, "--confirm-review", "测试复核人", "--fail-probe") == 1


# ---------------------------------------------------------------- ③ check_data_sources
def test_数据源_库缺失_False(gate_env):
    ok, detail = rg.check_data_sources()
    assert ok is False
    assert "missing" in detail


def test_数据源_完好非空_True(gate_env):
    db = gate_env / "data" / "literature_feed"
    db.mkdir(parents=True)
    con = sqlite3.connect(db / "feed.sqlite")
    con.execute("create table sources(id integer)")
    con.execute("insert into sources values (1)")
    con.commit()
    con.close()
    ok, detail = rg.check_data_sources()
    assert ok is True
    assert "integrity=ok" in detail and "sources=1" in detail


def test_数据源_空表_False(gate_env):
    db = gate_env / "data" / "literature_feed"
    db.mkdir(parents=True)
    con = sqlite3.connect(db / "feed.sqlite")
    con.execute("create table sources(id integer)")
    con.commit()
    con.close()
    ok, _ = rg.check_data_sources()
    assert ok is False                               # sources=0 不得放行


def test_数据源_库损坏_返False不抛(gate_env):
    """修后钉（2026-09-30 主班）：损坏库按契约返回 (False, "corrupt: …")，不再抛 DatabaseError。

    s927-11 登记的缺陷（connect/pragma 段无 try/except）已修；原「登记不钉」用例按
    其 docstring 预告的修法翻转为现值钉。"""
    db = gate_env / "data" / "literature_feed"
    db.mkdir(parents=True)
    (db / "feed.sqlite").write_bytes(b"not a sqlite file at all" * 10)
    ok, detail = rg.check_data_sources()
    assert ok is False and detail.startswith("corrupt:")


# ---------------------------------------------------------------- ④ run_cmd
def test_run_cmd_退出码与输出(gate_env):
    code, out = rg.run_cmd([sys.executable, "-c", "print('hello-gate')"])
    assert code == 0 and "hello-gate" in out


def test_run_cmd_输出尾截2000(gate_env):
    code, out = rg.run_cmd([sys.executable, "-c", "print('x' * 5000)"])
    assert code == 0 and len(out) <= 2000 and out.rstrip().endswith("x" * 10)


def test_run_cmd_超时_124(gate_env):
    code, out = rg.run_cmd([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
    assert code == 124 and out == "TIMEOUT"


def test_run_cmd_非零退出透传(gate_env):
    code, _ = rg.run_cmd([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert code == 3
