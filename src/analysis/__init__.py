"""分析子包。

导入即安装 sklearn 兼容垫片（见 _sklearn_compat.py）：本机 scikit-learn 已把
check_array(force_all_finite=...) 改名为 ensure_all_finite，而 factor_analyzer 仍按旧名调用，
会让 EFA / McDonald ω / CFA 载荷回退全部抛 TypeError。垫片只做参数改名转发，不改数值语义。
任何异常都不允许影响子包导入。
"""

try:  # pragma: no cover - 环境相关，失败即静默降级
    from . import _sklearn_compat as _compat  # noqa: F401

    _compat.install()
except Exception:  # pragma: no cover
    pass
