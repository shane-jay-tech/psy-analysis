# -*- coding: utf-8 -*-
"""src/utils/environment_diagnosis.py 诊断器离线钉桩（s922-118）。

锚点复核（开工第一动作，磁盘实测，0 漂移）
----------------------------------------
- `:50 def run_full_diagnosis(project_root: Optional[Path] = None) -> EnvironmentDiagnosis:` —— 未漂移。
- `:157 def format_diagnosis_for_streamlit(diag: EnvironmentDiagnosis) -> list[dict]:` —— 未漂移。
- 模块实测 163 行：两个 dataclass（DiagnosisItem :14 / EnvironmentDiagnosis :22）＋两个函数，无第三方依赖。

任务书三处前提与磁盘实况不符（按实况钉，不据此判 failed）
--------------------------------------------------------
1. 「钉桩 DiagnosisItem 的 level/message 字段」→ 实际字段是 **`name` / `status` / `detail` / `required`**
   （:15-18），全模块无 `level`、无 `message`。本件按真名钉。
2. 「format_diagnosis_for_streamlit 每项含 icon/status 键」→ 实测渲染键集是
   **{icon, name, detail, required}**，**没有 `status` 键**（status 被 :159 的 icons 表映射掉了）。
3. 「对本仓真根跑一次快照断言（本机已知项：不缺 requirements 相关文件）」→
   `run_full_diagnosis` **从头到尾不检查任何 requirements 文件**（:50-154 的检查项是
   Python/Streamlit/Pandas/NumPy/SciPy/python-docx/Matplotlib/PDF/字体/Playwright/LLM Key/缓存目录/WebView2）。
   快照因此改成：断言 item 数 ≥ 实测基线 ＋ **显式钉住「requirements 不在检查面」这个事实**，
   将来谁加了该检查项本用例即红，提醒同步更新本档。
4. `Path.home()` 在本模块**零调用**（实测 grep），完成标准 2 的隔离因此落在真正的宿主读取点：
   `shutil.which`（:94/:95/:144）与 `os.environ["LOCALAPPDATA"]`（:145）；
   另加一条 `Path.home` 地雷夹具，真读即炸。

s922-118 曾在此钉住一条**在册缺陷**，**s923-30 已按建议修法修掉**：`environment_diagnosis.py:109`
原对 `set(zh_fonts)[:3]` 取值 —— set 不可下标访问，抛 TypeError 被 :112 的裸 `except Exception` 吞掉，
导致「中文字体」的 ok 分支在任何机器上都不可达（本机装了 11 个常用中文字体也恒报 warning）。
现改为 `list(dict.fromkeys(zh_fonts))[:3]`（有序去重后截三），并把
原来那条「ok 分支永不可达」的缺陷钉桩翻正为 `test_chinese_font_ok_branch_reports_deduped_names`。
:112 裸 `except Exception` 过宽的登记**保持不动**（本件不覆盖它）；
同笔给 ok 分支补 `required=False` 的理由与两案见 s923-30 result 的「需裁决」段。

红线自查：本件只读环境、不装依赖、不建目录（除 pytest 自带 tmp_path），不碰统计/医疗数值面。
"""

import platform
import re
import shutil
from pathlib import Path

import pytest

# 预热：run_full_diagnosis 把 matplotlib / streamlit 的 import 写在函数体内（:66、:88、:105），
# 首次冷导入会走第三方自己的 Path.home() 目录发现逻辑，和下面的 Path.home 地雷打架。
# 在夹具生效前把冷导入做完，地雷才能只裁决「诊断模块自己有没有读真实主目录」。
import matplotlib  # noqa: F401
import matplotlib.font_manager  # noqa: F401  必须显式导入子模块，否则包属性不存在，setattr 撤销时会 delattr 出空
import streamlit  # noqa: F401

from src.utils import environment_diagnosis as ed
from src.utils.environment_diagnosis import (
    DiagnosisItem,
    EnvironmentDiagnosis,
    format_diagnosis_for_streamlit,
    run_full_diagnosis,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# 真根快照基线（**先跑命令打印再固化**，见 result「证据」）：
# 本机实测 13 项 = 11 项恒定 + 缓存目录(本项目根有 __pycache__/.streamlit) + WebView2(Windows)
# 稳定下限取 12：缓存目录是条件项（项目根无那四个目录时不追加），WebView2 只认 Windows。
SNAPSHOT_FLOOR = 12

REQUIRED_ALWAYS_OK = ("Python 版本", "Streamlit", "Pandas", "NumPy", "SciPy")

API_KEY_VARS = ("OPENAI_API_KEY", "LLM_API_KEY", "DEEPSEEK_API_KEY")


@pytest.fixture
def host_isolated(tmp_path, monkeypatch):
    """把宿主差异全部关进笼子：PATH 查找、LOCALAPPDATA、API Key、Path.home。"""
    monkeypatch.setattr(shutil, "which", lambda *_a, **_k: None)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "nonexistent-localappdata"))
    for var in API_KEY_VARS:
        monkeypatch.delenv(var, raising=False)

    def _no_home(*_a, **_k):
        raise AssertionError("离线钉桩失败：诊断器试图读真实用户主目录")

    monkeypatch.setattr(Path, "home", _no_home)
    yield tmp_path


def _by_name(diag, name):
    hits = [i for i in diag.items if i.name == name]
    return hits[0] if hits else None


def test_module_source_reads_no_home_directory():
    """完成标准 2 的静态面：模块本体零 `Path.home()`／零 `expanduser`。

    真正的宿主读取点是 `shutil.which`（:94/:95/:144）与 `os.environ["LOCALAPPDATA"]`（:145），
    两者由 `host_isolated` 夹具接管。
    """
    src = Path(ed.__file__).read_text(encoding="utf-8")
    assert "Path.home" not in src
    assert "expanduser" not in src
    assert "LOCALAPPDATA" in src, "若哪天去掉 LOCALAPPDATA 读取，请同步改本判据与夹具"


# ===========================================================================
# 数据结构
# ===========================================================================

def test_diagnosis_item_field_names_and_defaults():
    """完成标准 1 的地基：字段名按盘上真名钉（任务书写的 level/message 不存在）。"""
    item = DiagnosisItem(name="X", status="ok", detail="d")
    assert item.required is True
    assert (item.name, item.status, item.detail) == ("X", "ok", "d")
    assert not hasattr(item, "level") and not hasattr(item, "message")
    assert not hasattr(DiagnosisItem(name="Y", status="missing", detail="", required=False), "optional")


def test_summary_counts_and_all_ok_ignores_optional():
    diag = EnvironmentDiagnosis(items=[
        DiagnosisItem("a", "ok", ""),
        DiagnosisItem("b", "warning", ""),
        DiagnosisItem("c", "missing", ""),
        DiagnosisItem("d", "error", ""),
        DiagnosisItem("e", "missing", "", required=False),
    ])
    assert diag.summary == {
        "total": 5, "ok": 1, "warning": 1, "missing": 2, "error": 1, "all_required_ok": False,
    }
    assert diag.all_ok is False
    only_optional_broken = EnvironmentDiagnosis(items=[
        DiagnosisItem("a", "ok", ""),
        DiagnosisItem("e", "error", "", required=False),
    ])
    assert only_optional_broken.all_ok is True, "required=False 的项不得拖垮门禁"


def test_to_dict_shape():
    diag = EnvironmentDiagnosis(items=[DiagnosisItem("a", "ok", "d1")])
    payload = diag.to_dict()
    assert set(payload) == {"summary", "items"}
    assert payload["items"] == [{"name": "a", "status": "ok", "detail": "d1", "required": True}]


# ===========================================================================
# run_full_diagnosis 离线检查项
# ===========================================================================

def test_fake_root_item_set_is_scoped(host_isolated):
    """tmp_path 假根：无那四个缓存目录 ⇒ 缓存目录项不出现，其余项齐。"""
    diag = run_full_diagnosis(host_isolated)
    names = [i.name for i in diag.items]
    assert len(diag.items) == 12, f"假根稳定项数应为 12，实得 {names}"
    assert "缓存目录" not in names
    assert _by_name(diag, "PDF 转换").status == "warning", "which 被拦成 None 时应走双缺分支"
    assert _by_name(diag, "PDF 转换").required is False
    assert _by_name(diag, "WebView2").status == "warning"
    assert _by_name(diag, "LLM API Key").status == "warning", "三个 Key 变量清掉后应为 warning"
    for name in REQUIRED_ALWAYS_OK:
        assert _by_name(diag, name).status == "ok", f"{name} 在 .venv 里必在"
    assert diag.all_ok is True


def test_no_project_root_skips_cache_section(host_isolated):
    diag = run_full_diagnosis(None)
    assert _by_name(diag, "缓存目录") is None
    assert len(diag.items) == 12


def test_cache_dirs_only_scan_injected_root(host_isolated):
    """完成标准 2/3 的核心：缓存目录只认传进来的根，真实仓根的 __pycache__ 不得漏进来。"""
    (host_isolated / ".cache").mkdir()
    (host_isolated / ".cache" / "blob.bin").write_bytes(b"z" * 2048)
    (host_isolated / "temp_exports").mkdir()
    (host_isolated / "unrelated").mkdir()
    (host_isolated / "unrelated" / "x.txt").write_text("ignore me", encoding="utf-8")

    diag = run_full_diagnosis(host_isolated)
    cache = _by_name(diag, "缓存目录")
    assert cache is not None and cache.status == "ok"
    assert ".cache" in cache.detail and "temp_exports" in cache.detail
    assert ".streamlit" not in cache.detail and "__pycache__" not in cache.detail
    assert "unrelated" not in cache.detail, "检查面只有那四个目录名"
    assert str(host_isolated) not in cache.detail, "detail 只给名字和大小，不外泄绝对路径"
    assert len(diag.items) == 13, "缓存目录是唯一的项目根条件项"


def test_api_key_detection_is_env_driven(host_isolated, monkeypatch):
    assert _by_name(run_full_diagnosis(host_isolated), "LLM API Key").status == "warning"
    for var in API_KEY_VARS:
        monkeypatch.setenv(var, "")
        assert _by_name(run_full_diagnosis(host_isolated), "LLM API Key").status == "warning", \
            "空串等同未配置（bool() 语义）"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not-a-real-key-just-a-sentinel")
    key_item = _by_name(run_full_diagnosis(host_isolated), "LLM API Key")
    assert key_item.status == "ok"
    assert "not-a-real-key" not in key_item.detail, "detail 不得回显密钥内容"


def test_optional_items_never_break_the_gate(host_isolated):
    """五个可选项在任何机器上都不得进门禁：`required is False` 是硬约束。

    s923-30 起「中文字体」本机走 ok 分支（修好切片后可达），两个分支都必须仍带
    `required=False`，否则该项必选性会随机器字体变化——正是下面 :199 断言拦的事。
    """
    diag = run_full_diagnosis(host_isolated)
    for name in ("Playwright", "中文字体", "PDF 转换", "WebView2", "LLM API Key"):
        item = _by_name(diag, name)
        assert item is not None, f"{name} 项必在"
        assert item.required is False, f"{name} 变成必选会翻门禁语义"
        assert item.status in {"ok", "warning", "missing"}
    assert diag.summary["error"] == 0
    assert diag.all_ok is True


def test_chinese_font_ok_branch_reports_deduped_names(host_isolated, monkeypatch):
    """s923-30 翻正：`set(zh_fonts)[:3]` → `list(dict.fromkeys(zh_fonts))[:3]` 后，
    「有字体」时该项**可报 ok**，detail 按 ttflist 出现顺序去重再截前三。

    本件由 s922-118 的「ok 分支永不可达」缺陷钉桩翻正而来：
    原桩断言任何机器都拿不到 ok，:109 修好后那条判据必须跟着翻，不能悄悄留着当绿。
    :112 裸 `except Exception` 过宽的登记保持不动，本函数不覆盖它。

    四条断言各有独立杀伤力（本机变异实测五刀：换回 `set(zh_fonts)[:3]` 会被 :112 吞成
    warning 而红；`list(set(...))[:3]`（合法但乱序）三连红；`zh_fonts[:3]`（不去重）因首位
    SimHei 重复而红；不截断会让 KaiTi 漏进 detail 而红；漏掉 `required=False` 则本件与
    `test_optional_items_never_break_the_gate` 双双红。喂真 fontManager 会因为真机前三是
    `Microsoft YaHei*` 族而不是 `SimHei` 而红 —— 所以本件还顺带自证了 fake 真生效
    （旧桩拿不到这个自证：真机与假数据都会落进同一句「无法检测字体」）。
    """
    import matplotlib  # noqa: F401  确保子模块已进 sys.modules，便于按包属性替换

    class _Font:
        def __init__(self, name):
            self.name = name

    class _Manager:
        # 6 条含 2 处重名：有序去重后 4 名，截三 ⇒ 同时钉住「顺序 / 去重 / 截断」三件事
        ttflist = [_Font(n) for n in ("SimHei", "SimHei", "Microsoft YaHei",
                                      "SimSun", "KaiTi", "Microsoft YaHei")]

    fake = type("_FM", (), {"fontManager": _Manager()})
    monkeypatch.setattr(matplotlib, "font_manager", fake, raising=True)

    item = _by_name(run_full_diagnosis(host_isolated), "中文字体")
    assert item.status == "ok", f"修好切片后有字体必报 ok，实得 {item.status} / {item.detail}"
    assert item.detail == "可用：SimHei, Microsoft YaHei, SimSun", item.detail
    assert "KaiTi" not in item.detail, "只取前三，第四名不得出现"
    assert item.required is False, "ok 分支也得是可选项，否则必选性随机器字体漂移（见 :199）"


# ===========================================================================
# format_diagnosis_for_streamlit
# ===========================================================================

def test_streamlit_render_keys_icon_mapping_and_order():
    diag = EnvironmentDiagnosis(items=[
        DiagnosisItem("a", "ok", "d-a"),
        DiagnosisItem("b", "warning", "d-b", required=False),
        DiagnosisItem("c", "missing", "d-c"),
        DiagnosisItem("d", "error", "d-d"),
        DiagnosisItem("e", "solar-flare", "d-e"),
    ])
    rows = format_diagnosis_for_streamlit(diag)
    assert len(rows) == 5
    assert [r["name"] for r in rows] == ["a", "b", "c", "d", "e"], "顺序必须与 items 一致"
    assert all(set(r) == {"icon", "name", "detail", "required"} for r in rows)
    assert "status" not in rows[0], "任务书前提里的 status 键实际不存在（status 被映射成 icon）"
    assert [r["icon"] for r in rows] == ["✅", "⚠️", "❌", "\U0001f6ab", "❓"]
    assert rows[1]["required"] is False and rows[0]["required"] is True


def test_streamlit_render_empty_and_json_serialisable():
    import json

    assert format_diagnosis_for_streamlit(EnvironmentDiagnosis()) == []
    rows = format_diagnosis_for_streamlit(run_full_diagnosis(None))
    assert json.dumps(rows, ensure_ascii=False), "渲染结构必须可直接序列化给前端"


def test_repo_root_snapshot_floor(host_isolated, monkeypatch):
    """真根快照：只断言下限 ＋ 门禁语义，宿主差异仍用夹具压住（不动真实 PATH/env）。"""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    for var in API_KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    diag = run_full_diagnosis(REPO_ROOT)
    assert len(diag.items) >= SNAPSHOT_FLOOR, f"实测基线 {SNAPSHOT_FLOOR}，现得 {len(diag.items)}"
    assert diag.summary["total"] == len(diag.items)
    assert diag.all_ok is True, "真根必选六项在 .venv 下不得红"
    assert diag.summary["error"] == 0
    names = {i.name for i in diag.items}
    assert set(REQUIRED_ALWAYS_OK) <= names
    assert not any("requirements" in n.lower() for n in names), \
        "本模块不检查 requirements 文件（任务书前提里的这项不存在）；若新增请同步本判据"


def test_cache_detail_format_is_stable_across_roots(tmp_path, monkeypatch):
    """同一份代码在真根/假根上只该差目录名，不该差结构：钉住缓存项的 detail 格式。"""
    monkeypatch.setattr(shutil, "which", lambda *_a, **_k: None)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    for var in API_KEY_VARS:
        monkeypatch.delenv(var, raising=False)

    def _segments(diag):
        item = _by_name(diag, "缓存目录")
        assert item is not None
        return [s.strip() for s in item.detail.split(";")]

    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"q" * 10)
    fake_segments = _segments(run_full_diagnosis(tmp_path))
    real_segments = _segments(run_full_diagnosis(REPO_ROOT))

    pattern = re.compile(r"^[A-Za-z._]\S*: \d+\.\d+MB$")
    for seg in fake_segments + real_segments:
        assert pattern.match(seg), f"缓存目录 detail 段格式变了：{seg!r}"
    assert fake_segments == ["__pycache__: 0.0MB"], "空目录也照报 0.0MB（size 求和为 0）"
    assert any(s.startswith(".streamlit:") for s in real_segments) or \
           any(s.startswith("__pycache__:") for s in real_segments), \
           f"真根至少有那四个目录之一，实得 {real_segments}"
