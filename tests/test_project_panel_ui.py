# -*- coding: utf-8 -*-
"""s922-14：`src/ui/project_panel.py` 四符号的 AppTest 实弹钉桩。

四个符号（`render_project_panel` / `_show_locked_banner` / `_save_active_then_load` /
`ensure_active_project_on_first_visit`）在 tests 下原本**零命中**（grep 只指到 `app.py:344-345`
与 `src/utils/autosave.py` 的两段注释）⇒ 本单是它们的第一层网。

手法沿用 s921-12/15 建的 AppTest 模板（`tests/test_e2e_qimport_upload.py`）：
`AppTest.from_string` 跑**真渲染路径**（真 widget、真 `st.rerun()`、真落盘的 index.json），
不在 dict 层自说自话。文件名已登记 `tests/conftest.py:_APP_TEST_FILES` ⇒ 运行期
`PSY_ANALYSIS_*` 与 `project_manager.PROJECTS_DIR/INDEX_FILE` 全指向 `tmp_path`，
不碰用户真实项目/偏好/档案/事件日志。锁库分支用**真锁文件**触发（往隔离后的
`PROJECTS_DIR/.psy_project.lock` 写本机 pid），走 `instance_lock.project_lock` 的原路，
不 monkeypatch、不模拟异常。

**零生产码改动**：`src/ui/project_panel.py` 与 `src/utils/*` 一行未动。
三处「现状与直觉不符」的行为按现场实测钉死（见 test_locked_copy_banner_is_wiped_by_the_rerun /
test_banner_has_no_holder_because_the_exception_carries_only_one_arg /
test_switch_to_the_same_project_skips_the_snapshot），一律不"顺手修好"。

红线自约：只测项目管理 UI 与项目文件读写路径；不触碰统计数值、鉴权、加密凭据、医疗内容。
项目名/文件名/备注全是「甲项目」「A的人造文件.csv」这类人造文案，零被试数据。

行尾实况：`src/ui/project_panel.py` 本机是 CRLF（291 行 291 个 CRLF），`tests/conftest.py` 是纯 LF；
本文件不就地编辑 CRLF 源码（零改动），只在纯 LF 的 conftest 上加一行登记。
"""
import datetime
import json
import os
import pathlib
import re

from src.utils import instance_lock, project_manager as pm
from streamlit.testing.v1 import AppTest

_ROOT = pathlib.Path(__file__).resolve().parents[1].as_posix()

# 每段脚本都自己 sys.path 注入 + 重新 import：AppTest 用 exec 跑字符串，拿不到测试模块的全局名
_PREAMBLE = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
import streamlit as st
from src.utils import instance_lock, project_manager as pm
""".replace("__ROOT__", _ROOT)

_RENDER_ONLY = _PREAMBLE + """
from src.ui.project_panel import render_project_panel
render_project_panel()
"""

# 播种活跃项目用「不在才播」：真 app 里 `ensure_active_project_on_first_visit()` 就是这个语义，
# 无条件播种会让 st.rerun() 之后的那一帧又被按回旧项目（本单实测踩过，见 result 的锚点复核段）
_RENDER_SEEDED = _PREAMBLE + """
from src.ui.project_panel import render_project_panel
if "_active_project_id" not in st.session_state:
    st.session_state["_active_project_id"] = "__ACTIVE__"
render_project_panel()
"""

# 播种活跃项目的**同一防护块**里再播种工作区内容：切换会清空 session_state，
# 下一帧防护块不再执行 ⇒ 读回的值只可能来自磁盘上的那份快照，不是脚本自己按回去的
_RENDER_SEEDED_WITH_STATE = _PREAMBLE + """
from src.ui.project_panel import render_project_panel
if "_active_project_id" not in st.session_state:
    st.session_state["_active_project_id"] = "__ACTIVE__"
    st.session_state["file_name"] = "__PLANT__"
render_project_panel()
"""

_ENSURE = _PREAMBLE + """
from src.ui.project_panel import ensure_active_project_on_first_visit
ensure_active_project_on_first_visit()
"""

_SWITCH = _PREAMBLE + """
from src.ui.project_panel import _save_active_then_load
__PLANT__
_save_active_then_load("__TARGET__")
"""

_BANNER = _PREAMBLE + """
from src.ui.project_panel import _show_locked_banner
__BUILD__
_show_locked_banner(exc)
"""

# 源码原文（Streamlit 会把 warning/error 文案开头的图标串吃掉，比对一律走 _visible）
_SRC_NO_ACTIVE = "⚠ 当前无活跃项目"
_SRC_CONFIRM_DELETE = "⚠ 确认删除「{name}」？此操作不可恢复。"
_ICON_PREFIX = re.compile(r"^\W+(?=\S)")


def _visible(text: str) -> str:
    """`st.warning/st.error` 会把开头的图标（⚠ / 🔒）连同空格吞掉，比对时同样吞掉。"""
    return _ICON_PREFIX.sub("", text)


def _locked_prompt(resource: str = "项目", holder: str = "") -> str:
    """锁库文案的唯一真相在 `instance_lock.locked_user_prompt`（4acb 同源化）。"""
    return _visible(instance_lock.locked_user_prompt(resource, holder))


def _at(script: str) -> AppTest:
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    return at


def _click(at: AppTest, label: str) -> AppTest:
    hits = [b for b in at.button if b.label == label]
    assert [b.label for b in at.button] and len(hits) == 1, f"{label!r} 不唯一：{[b.label for b in at.button]}"
    hits[0].click().run()
    return at


def _labels(at: AppTest) -> list:
    return [b.label for b in at.button]


def _warnings(at: AppTest) -> list:
    return [w.value for w in at.warning]


def _errors(at: AppTest) -> list:
    return [e.value for e in at.error]


def _captions(at: AppTest) -> list:
    return [c.value for c in at.caption]


def _active(at: AppTest) -> str:
    return at.session_state["_active_project_id"]


def _seed_lock_file() -> pathlib.Path:
    """在隔离目录里放一把**本机 pid 持有的**真锁文件 ⇒ `project_lock` 必抛 ProjectLockedError。

    锁龄按 `time.time() - mtime` 算，刚写的文件远小于 `DEFAULT_STALE_SECONDS=600` ⇒
    走 `_pid_alive` 为真的那条 `raise ProjectLockedError`，不是陈旧锁接管。
    """
    lock = pm.PROJECTS_DIR / instance_lock.LOCK_FILENAME
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        f"{os.getpid()} {datetime.datetime.now().isoformat(timespec='seconds')}",
        encoding="ascii",
    )
    return lock


def _force_updated_at(project_id: str, stamp: str) -> None:
    """直写隔离目录里的 index.json，把某个项目的 `updated_at` 钉成固定值（排序前置条件用）。"""
    rows = json.loads(pm.INDEX_FILE.read_text(encoding="utf-8"))
    assert any(r["id"] == project_id for r in rows)
    for row in rows:
        if row["id"] == project_id:
            row["updated_at"] = stamp
    pm.INDEX_FILE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


# ─────────────────────── render_project_panel：首访（无活跃项目）分支 ───────────────────────
def test_first_visit_without_active_project_renders_only_the_create_entry():
    """`:120-130` 的空态：只有警告 + 一个入口按钮，面板其余部分（含 `:291` 的计数尾注）都不渲染。"""
    at = _at(_RENDER_ONLY)

    assert not at.exception
    assert _warnings(at) == [_visible(_SRC_NO_ACTIVE)]
    assert _labels(at) == ["➕ 新建项目"]
    assert _captions(at) == []                       # 早退 ⇒ 连「共 N 个项目」都不出现
    assert list(at.selectbox) == [] and list(at.expander) == []
    assert "_active_project_id" not in at.session_state
    assert pm.list_projects() == []                  # 光是看一眼面板不落任何盘
    assert not pm.INDEX_FILE.exists()


def test_empty_state_create_button_makes_the_default_project_and_reopens_the_panel():
    """`:122-129`：空态按钮走真 `pm.create_project("我的研究")` + `set_active_project` + `st.rerun()`。

    rerun 后 AppTest 交出的是**重跑那一帧**，所以「警告消失 + 四按钮出现」本身就是要钉的接线。
    """
    at = _at(_RENDER_ONLY)
    _click(at, "➕ 新建项目")

    assert not at.exception
    projects = pm.list_projects()
    assert [p.name for p in projects] == ["我的研究"]
    assert _active(at) == projects[0].id
    assert _warnings(at) == []
    assert _captions(at) == ["**当前**：我的研究", "共 1 个项目"]
    assert _labels(at) == ["➕ 新建", "✏️ 重命名", "📋 复制", "🗑 删除"]


# ─────────────────────── render_project_panel：登录态（有活跃项目）分支 ───────────────────────
def test_logged_in_panel_with_single_project_shows_name_note_and_count():
    """`:132-134 / :159-178 / :291`：单项目时不给切换下拉（`len(projects) > 1` 拦掉），四按钮齐全。"""
    proj = pm.create_project("甲项目", note="人造备注")
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", proj.id))

    assert not at.exception
    assert _warnings(at) == []
    assert _captions(at) == ["**当前**：甲项目", "📝 人造备注", "共 1 个项目"]
    assert _labels(at) == ["➕ 新建", "✏️ 重命名", "📋 复制", "🗑 删除"]
    assert list(at.selectbox) == []
    assert [e.label for e in at.expander] == ["📤 导出 / 导入项目"]


def test_note_caption_is_skipped_for_a_project_without_note():
    """`if active.note:` 的假分支：没备注就不该多出一行 📝（否则计数与行序都变）。"""
    proj = pm.create_project("乙项目")
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", proj.id))

    assert not at.exception
    assert _captions(at) == ["**当前**：乙项目", "共 1 个项目"]
    assert not any(c.startswith("📝") for c in _captions(at))


def test_two_projects_render_the_switcher_with_today_labels_and_active_selected():
    """`:137-153`：两个项目才出下拉；`format_func` 拼的是「名称（updated_at[:10]）」；index 落在当前项。"""
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", a.id))

    assert not at.exception
    assert len(at.selectbox) == 1
    box = at.selectbox[0]
    assert box.label == "切换项目"
    assert box.value == a.id                          # 下拉当前选中的就是活跃项目
    names = [o.split("（")[0] for o in box.options]
    assert sorted(names) == ["乙项目", "甲项目"]       # 两项都在（顺序按 updated_at 倒序，同秒不稳）
    assert all(len(o.split("（")[1].rstrip("）")) == 10 for o in box.options)   # 日期段是 10 字符
    assert box.index in (0, 1)
    assert {p.id for p in pm.list_projects()} == {a.id, b.id}


def test_choosing_another_project_in_the_switcher_runs_the_real_switch():
    """`:154-156`：下拉选中别的项目 ⇒ 真走 `_save_active_then_load` + `st.rerun()`。

    读回的 `file_name` 只可能来自磁盘快照：防护块仅在活跃键缺失时播种，切换后活跃键已在 ⇒
    「A 的内存态写进 A 的文件」与「B 的文件回到内存」两条各自可证伪。
    """
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    pm.save_workspace(b.id, {"_schema": "v2.9", "file_name": "B的人造文件.csv"})
    script = _RENDER_SEEDED_WITH_STATE.replace("__ACTIVE__", a.id).replace("__PLANT__", "A的人造文件.csv")
    at = _at(script)

    assert not at.exception and at.selectbox[0].value == a.id
    at.selectbox[0].set_value(b.id).run()

    assert not at.exception
    assert _active(at) == b.id
    assert _captions(at)[0] == "**当前**：乙项目"
    assert pm.load_workspace(a.id)["file_name"] == "A的人造文件.csv"
    assert at.session_state["file_name"] == "B的人造文件.csv"


# ─────────────────────── 锁库分支：ProjectLockedError → _show_locked_banner ───────────────────────
def test_lock_on_empty_state_create_shows_the_banner_and_writes_nothing():
    """`:125-127`：锁住时 `create_project` 抛错 ⇒ 横幅 + `return`（不 rerun），所以文案**看得见**。"""
    _seed_lock_file()
    at = _at(_RENDER_ONLY)
    _click(at, "➕ 新建项目")

    assert not at.exception
    # s1023-05 起横幅带 since 段；真异常 args 恒长 1 ⇒ 无持有者段，期望按锁文件实写内容构造
    _since_txt = (pm.PROJECTS_DIR / instance_lock.LOCK_FILENAME).read_text(encoding="ascii").split(" ", 1)[1].strip()
    assert _errors(at) == [_visible(instance_lock.locked_user_prompt("项目", "", since=_since_txt))]
    assert _warnings(at) == [_visible(_SRC_NO_ACTIVE)]          # 仍停在空态
    assert pm.list_projects() == [] and "_active_project_id" not in at.session_state


def test_locked_copy_button_is_caught_but_the_rerun_wipes_the_banner():
    """`:169-172`（现状钉桩，不改判据）：copy 分支是 `banner` 紧跟 `st.rerun()` ⇒ 横幅被下一帧冲掉。

    钉的三件事：①锁异常**没有**冒到会话外（`at.exception` 空）；②一个副本都没建出来；
    ③用户侧看不到文案——这四条 except（copy / 新建表单 / 重命名 / 删除）全同样写法，
    只有空态那条 `:126-127` 是 `return` 不 `rerun`。差异属实测，见 result 遗留问题。
    """
    proj = pm.create_project("甲项目")
    _seed_lock_file()
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", proj.id))
    _click(at, "📋 复制")

    assert not at.exception
    assert _errors(at) == []
    assert [p.name for p in pm.list_projects()] == ["甲项目"]
    assert _active(at) == proj.id


def test_lock_on_new_project_form_leaves_the_form_open_and_creates_nothing():
    """`:181-200` 表单路：锁抛错时 `return` 在「关表单」之前 ⇒ 表单还在、名字没丢、没建项目。"""
    proj = pm.create_project("甲项目")
    _seed_lock_file()
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", proj.id))
    _click(at, "➕ 新建")

    assert "新项目名" in [t.label for t in at.text_input]
    at.text_input(key="_new_proj_name").set_value("丙项目").run()
    _click(at, "创建")

    assert not at.exception
    assert [p.name for p in pm.list_projects()] == ["甲项目"]
    assert at.session_state["_proj_show_new"] is True            # 表单没被关掉
    assert "创建" in _labels(at)


def test_lock_mid_delete_leaves_the_switch_done_and_the_delete_undone():
    """`:231-245`：确认删除先 `_save_active_then_load(兄弟)` 再 `delete_project`。

    锁抛在第二步 ⇒ 第一步已成：活跃项目切走了，目标项目**还在**。
    （`touch_project` / `_write_index` 没挂 `@_locked`，切换那一步压根不查锁——现状如此，本单只钉不改。）
    """
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    _seed_lock_file()
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", a.id))
    _click(at, "🗑 删除")
    _click(at, "✅ 确认删除")

    assert not at.exception
    assert {p.name for p in pm.list_projects()} == {"甲项目", "乙项目"}   # 一个都没删掉
    assert _active(at) == b.id                                          # 但活跃已经切走了


# ─────────────────────── _show_locked_banner 文案本体 ───────────────────────
def test_banner_has_no_holder_because_the_exception_carries_only_one_arg():
    """`:20-25`（现状钉桩）：`ProjectLockedError.__init__` 只用一个 f-string 调 `super().__init__`
    ⇒ `exc.args` 恒长 1 ⇒ `pid = exc.args[1] if len(exc.args) > 1 else None` 恒 None ⇒
    `holder` 恒空串，「（持有者: pid=…）」这段在真异常下永远出不来。

    钉法两面：①真异常走一遍，文案与 `locked_user_prompt("项目", "")` 逐字相同、不含「持有者」；
    ②把 args 手工撑成两元组，同一段代码立刻吐出 pid ⇒ 说明死的是取数那一行，不是排版那一行。
    """
    exc = instance_lock.ProjectLockedError("/tmp/x/.psy_project.lock", 4242, "2026-01-01T00:00:00")
    assert len(exc.args) == 1 and exc.holder_pid == 4242        # 信息在属性上，不在 args[1] 上

    at = _at(_BANNER.replace("__BUILD__", "exc = instance_lock.ProjectLockedError('/tmp/x.lock', 4242, '2026-01-01T00:00:00')"))
    assert not at.exception
    # s1023-05 起横幅带 since 段（holder_since 接线）；holder 仍缺（args 恒长 1）
    assert _errors(at) == [_visible(instance_lock.locked_user_prompt("项目", "", since="2026-01-01T00:00:00"))]
    assert "持有者" not in _errors(at)[0]

    with_holder = _at(_BANNER.replace("__BUILD__", "exc = instance_lock.ProjectLockedError('/tmp/x.lock', 4242)\nexc.args = ('locked', 77)"))
    assert not with_holder.exception
    assert _errors(with_holder) == [_locked_prompt(holder="pid=77")]
    assert _errors(with_holder) == ["项目正被另一实例占用（持有者: pid=77），请关闭对方或稍后重试。"]


def test_banner_with_a_bare_exception_still_emits_the_same_prompt():
    """`len(exc.args) > 1` 的假分支（`:23`）：单参异常走同一条文案，且**不**抛 IndexError。"""
    at = _at(_BANNER.replace("__BUILD__", "exc = RuntimeError('裸异常，没有 pid')"))

    assert not at.exception
    assert _errors(at) == [_locked_prompt()]


# ─────────────────────── 删除确认流（登录态内的子分支） ───────────────────────
def test_delete_button_opens_the_confirmation_in_the_same_frame():
    """`:177-178 → :227-230`：置标志后同帧继续往下渲染，确认区不需要额外一帧。"""
    a = pm.create_project("甲项目")
    pm.create_project("乙项目")
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", a.id))
    _click(at, "🗑 删除")

    assert not at.exception
    assert _warnings(at) == [_visible(_SRC_CONFIRM_DELETE.format(name="甲项目"))]
    assert _labels(at)[-2:] == ["✅ 确认删除", "取消"]
    assert at.session_state["_proj_show_delete"] is True


def test_confirm_delete_switches_to_the_sibling_and_then_removes_the_target():
    """`:233-247`：先 `_save_active_then_load(others[0])` 再 `delete_project(target)` ⇒ 顺序反了就会删掉活跃项。"""
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", a.id))
    _click(at, "🗑 删除")
    _click(at, "✅ 确认删除")

    assert not at.exception
    assert [p.name for p in pm.list_projects()] == ["乙项目"]
    assert pm.get_project(a.id) is None
    assert _active(at) == b.id
    assert at.session_state["_proj_show_delete"] is False
    assert _captions(at)[-1] == "共 1 个项目"


def test_delete_of_the_last_project_creates_the_replacement_before_deleting():
    """`:237-240`：删到只剩一个时**先建后删**，任何时刻都有活跃项目（空态分支只留给首访用）。"""
    only = pm.create_project("甲项目")
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", only.id))
    _click(at, "🗑 删除")
    _click(at, "✅ 确认删除")

    assert not at.exception
    projects = pm.list_projects()
    assert [p.name for p in projects] == ["我的研究"]
    assert projects[0].id != only.id
    assert _active(at) == projects[0].id


def test_cancel_delete_keeps_every_project_and_closes_the_prompt():
    """`:248-250`：取消只清标志，磁盘一个字节都不该动。"""
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    before = pm.INDEX_FILE.read_bytes()
    at = _at(_RENDER_SEEDED.replace("__ACTIVE__", a.id))
    _click(at, "🗑 删除")
    _click(at, "取消")

    assert not at.exception
    assert at.session_state["_proj_show_delete"] is False
    assert pm.INDEX_FILE.read_bytes() == before
    assert {p.id for p in pm.list_projects()} == {a.id, b.id}
    assert _active(at) == a.id


# ─────────────────────── _save_active_then_load 本体 ───────────────────────
def test_switch_saves_current_then_clears_then_loads_the_target():
    """`:32-64` 三步全走真路：旧项目落盘 → 会话清空（只留 8 把全局键）→ 目标工作区 restore 回来。"""
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    pm.save_workspace(a.id, {"_schema": "v2.9", "file_name": "A的旧文件.csv"})
    pm.save_workspace(b.id, {"_schema": "v2.9", "file_name": "B的人造文件.csv"})

    plant = """
st.session_state["_active_project_id"] = "__A__"
st.session_state["quick_model_id"] = "model-合成"
st.session_state["privacy_accepted"] = True
st.session_state["_autosave_dismissed"] = True
st.session_state["file_name"] = "A的人造文件.csv"
st.session_state["junk_transient"] = "这把键不该活过切换"
""".replace("__A__", a.id)
    at = _at(_SWITCH.replace("__PLANT__", plant).replace("__TARGET__", b.id))

    assert not at.exception
    assert _active(at) == b.id
    # ① 旧项目的内存态真写到磁盘了（不是只写了个空快照）
    assert pm.load_workspace(a.id)["file_name"] == "A的人造文件.csv"
    # ② 目标工作区 restore 回来
    assert at.session_state["file_name"] == "B的人造文件.csv"
    # ③ 白名单里的全局键活过 `session_state.clear()`，白名单外的死了
    assert at.session_state["quick_model_id"] == "model-合成"
    assert at.session_state["privacy_accepted"] is True
    assert at.session_state["_autosave_dismissed"] is True
    assert "junk_transient" not in at.session_state


def test_switch_to_the_same_project_skips_the_snapshot():
    """`:38` 的 `and active_id != target_id`：自己切自己不落快照 ⇒ 内存里未保存的编辑会被磁盘版覆盖。

    钉成两条断言是因为这两半会被不同的改法分别打破：去掉守卫 ⇒ 第一条红；
    去掉 `if target_ws:` 的判空 ⇒ 第二条红。
    """
    a = pm.create_project("甲项目")
    pm.save_workspace(a.id, {"_schema": "v2.9", "file_name": "磁盘上的旧文件.csv"})
    plant = """
st.session_state["_active_project_id"] = "__A__"
st.session_state["file_name"] = "只在内存里的人造文件.csv"
""".replace("__A__", a.id)
    at = _at(_SWITCH.replace("__PLANT__", plant).replace("__TARGET__", a.id))

    assert not at.exception
    assert _active(at) == a.id
    assert pm.load_workspace(a.id)["file_name"] == "磁盘上的旧文件.csv"
    assert at.session_state["file_name"] == "磁盘上的旧文件.csv"


def test_switch_with_nothing_saved_yet_still_activates_the_target():
    """`:59` 的 `if target_ws:` 假分支：目标没有工作区文件时不 restore，但活跃键照切。"""
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    (pm.PROJECTS_DIR / f"{b.id}.json").unlink()          # 造「有索引、没工作区」的半边状态
    plant = f'st.session_state["_active_project_id"] = "{a.id}"\nst.session_state["junk"] = 1\n'
    at = _at(_SWITCH.replace("__PLANT__", plant).replace("__TARGET__", b.id))

    assert not at.exception
    assert _active(at) == b.id
    assert "junk" not in at.session_state                 # 清空照做
    assert "file_name" not in at.session_state            # 没东西可 restore


# ─────────────────────── ensure_active_project_on_first_visit ───────────────────────
def test_brand_new_user_first_visit_creates_one_default_project_and_revisit_reuses_it(monkeypatch):
    """`:67-105`：首访建「我的研究」；同一会话第二访走 `:73` 的早退——**不重建、不改盘、不 restore**。

    时间戳走 monkeypatch 的秒递增假钟：`_now_str` 是 `%Y-%m-%d %H:%M:%S`，真钟同秒内两次写盘
    字节完全一样，早退被改坏也测不出来（M3 变异实测漏网，故把时钟钉住再看盘）。
    """
    ticks = iter(f"2026-09-22 10:00:{i:02d}" for i in range(1, 60))
    monkeypatch.setattr(pm, "_now_str", lambda: next(ticks))

    at = _at(_ENSURE)

    assert not at.exception
    first = pm.list_projects()
    assert [p.name for p in first] == ["我的研究"]
    assert _active(at) == first[0].id
    assert first[0].created_at == "2026-09-22 10:00:01"
    index_after_first = pm.INDEX_FILE.read_bytes()
    assert "_workspace_migration_info" not in at.session_state      # 新建路径不碰 restore

    at.run()                                              # 第二访（同会话刷新）
    assert not at.exception
    assert [p.name for p in pm.list_projects()] == ["我的研究"]
    assert _active(at) == first[0].id
    assert pm.INDEX_FILE.read_bytes() == index_after_first          # 早退连 touch 都不该发生
    # 走漏到 `:89-101` 认领分支的话，`restore_workspace` 会留下这三把键——磁盘没变也照样抓到
    for leaked in ("_workspace_migration_info", "literature_review_state", "upstream_state"):
        assert leaked not in at.session_state, leaked


def test_fresh_session_with_existing_projects_adopts_the_latest_instead_of_creating():
    """`:89-101`：新会话（session 里没有活跃键）+ 磁盘已有项目 ⇒ 认领 `list_projects()[0]`，数量不变。

    `updated_at` 用手工写死的两个日期：`list_projects` 按它倒序，而同一秒内建两个项目是并列的，
    靠真实时间戳排出来的顺序不可复现（本例第一版就这么飘过一次）。
    """
    old = pm.create_project("旧项目")
    newer = pm.create_project("新项目")
    _force_updated_at(old.id, "2026-09-01 10:00:00")
    _force_updated_at(newer.id, "2026-09-02 10:00:00")

    at = _at(_ENSURE)

    assert not at.exception
    assert [p.name for p in pm.list_projects()] == ["新项目", "旧项目"]   # 前置：倒序确实成立
    assert _active(at) == newer.id
    assert not any(p.name == "我的研究" for p in pm.list_projects())      # 一个都没新建


def test_legacy_autosave_is_migrated_instead_of_creating_a_default_project():
    """`:76-87`：v3.0 的 `autosave.json` 优先于「新建默认项目」，迁移后旧文件被清走（幂等）。"""
    legacy = pm.PROJECTS_DIR.parent / "autosave.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text('{"_schema": "workspace_v1", "file_name": "旧版自动保存.csv"}', encoding="utf-8")

    at = _at(_ENSURE)

    assert not at.exception
    projects = pm.list_projects()
    assert [p.name for p in projects] == ["自动恢复的工作区"]
    assert projects[0].note == "从 v3.0 autosave 迁移"
    assert _active(at) == projects[0].id
    assert not legacy.exists()
    assert pm.load_workspace(projects[0].id)["file_name"] == "旧版自动保存.csv"

    at.run()                                              # 二访：迁移是幂等的，不再冒出第二个项目
    assert [p.name for p in pm.list_projects()] == ["自动恢复的工作区"]


def test_dangling_active_id_is_repaired_without_duplicating_the_project():
    """`:72-74` 的半真条件：活跃键指向已删项目 ⇒ 不走早退，认领现存项目，磁盘数量不变。"""
    kept = pm.create_project("还活着的项目")
    at = _at(
        _ENSURE.replace(
            "ensure_active_project_on_first_visit()",
            'st.session_state["_active_project_id"] = "ghost-id-not-on-disk"\n'
            "ensure_active_project_on_first_visit()",
        )
    )

    assert not at.exception
    assert _active(at) == kept.id
    assert [p.id for p in pm.list_projects()] == [kept.id]


def test_dangling_active_id_with_no_projects_on_disk_falls_through_to_create():
    """幽灵键 + 磁盘全空（既没得迁移也没得认领）⇒ 只能走 `:103-105` 新建。"""
    at = _at(
        _ENSURE.replace(
            "ensure_active_project_on_first_visit()",
            'st.session_state["_active_project_id"] = "ghost-id-not-on-disk"\n'
            "ensure_active_project_on_first_visit()",
        )
    )

    assert not at.exception
    projects = pm.list_projects()
    assert [p.name for p in projects] == ["我的研究"]
    assert _active(at) == projects[0].id
