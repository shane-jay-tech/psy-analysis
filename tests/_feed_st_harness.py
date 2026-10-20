# -*- coding: utf-8 -*-
"""feed 两测试件共享的假 st harness 基座（s930-15，s927-58 遗留「单点抽出」）。

抽出的只是**两份拷贝经比对确认逐字一致的公共面**：
  FakeState / _Ctx / 收集桶初始化 / markdown-warning-divider / __getattr__ 拒绝语义。
行为契约已分叉的面**不抽**（button 返回值、columns 宽度语义、dataframe 记录形状、
column_config 列类型）——各测试件在自己的子类里保留原实现（断言逐字不动）。
分叉清单见 s930-15 result §一。
"""
from typing import Any, Dict, List, Tuple


class FakeState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Ctx:
    def __init__(self, host, label="", kind="ctx"):
        self.host, self.label, self.kind = host, label, kind

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FeedStBase:
    """公共基座：收集桶 + 两版逐字一致的四方法 + 未预期调用拒绝。"""

    strict_unexpected = True   # 两版同款：未预期 st.X 调用当场 AssertionError

    def __init__(self) -> None:
        self.session_state = FakeState()
        self.markdowns: List[str] = []
        self.warnings: List[str] = []
        self.dividers = 0
        self.buttons: List[Any] = []
        self.dataframes: List[Any] = []

    # —— 两版逐字一致的四方法 ——
    def markdown(self, msg, **k):
        self.markdowns.append(msg)

    def warning(self, msg, **k):
        self.warnings.append(msg)

    def divider(self, **k):
        self.dividers += 1

    def dataframe(self, data, **k):
        """⚠ 形状分叉：panel 版记 (list(data), k) 元组、summary 版记 list(data)——
        子类必须覆写本方法保留各自断言形状，基座不提供默认实现。"""
        raise NotImplementedError("子类必须覆写 dataframe（两版记录形状已分叉）")

    def button(self, label, **k):
        """⚠ 行为分叉：panel 版返回 label in clicked、summary 版恒 False——同上，子类覆写。"""
        raise NotImplementedError("子类必须覆写 button（两版返回语义已分叉）")

    def columns(self, widths=None, **k):
        """⚠ 语义分叉：summary 版断言 int、panel 版记 widths——子类覆写。"""
        raise NotImplementedError("子类必须覆写 columns（两版宽度语义已分叉）")

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")
