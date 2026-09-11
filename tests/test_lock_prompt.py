"""dab0：锁占用同源提示单测（1 条起，可扩）。

锁定行为：locked_user_prompt 是 project 锁异常横幅与文献面板 SessionLock 占用提示的
唯一文案来源——含资源名与持有者，不再允许各处自拼文案。
"""
from src.utils.instance_lock import locked_user_prompt


def test_locked_prompt_contains_resource_and_holder():
    msg = locked_user_prompt("当前数据", "tab-xyz")
    assert "正被另一实例占用" in msg
    assert "tab-xyz" in msg
    assert msg.startswith("🔒")


def test_locked_prompt_without_holder():
    msg = locked_user_prompt("文献面板")
    assert "文献面板" in msg
    assert "持有者" not in msg
