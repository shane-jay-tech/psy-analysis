"""错误信息友好化 — 把技术性 traceback 翻译成本科生看得懂的中文提示。

设计：
- ERROR_PATTERNS 列表：每条 (regex, friendly_title, friendly_explanation, suggested_action)
- 高层函数 friendly_explain(exc) 返回 (title, explanation, action)
- UI 层调用 render_friendly_error(st, exc) 统一渲染
- 装饰器 @friendly_handler 包装 runner 入口
"""

from __future__ import annotations

import re
import traceback
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class FriendlyError:
    title: str
    explanation: str
    suggested_action: str
    technical_detail: str = ""


# 模式按特异度从高到低排序：先匹配具体错误，最后兜底
ERROR_PATTERNS: List[Tuple[str, str, str, str]] = [
    # ====== 数据相关 ======
    (
        r"could not convert.*to (float|numeric)",
        "数据中存在非数值",
        "你选择的变量里包含文字、空格或特殊符号，无法做数值运算。",
        "请检查数据：是否把数字写成了「20岁」「none」「N/A」之类的形式？把这些值改为纯数字或留空。",
    ),
    (
        r"empty.*frame|0 rows|len.*== 0|cannot do.*on.*empty",
        "没有可用数据",
        "处理后没有任何数据剩下。",
        "可能原因：(1) 你选的列全为空；(2) 缺失值剔除后剩 0 行。请回到上一步检查。",
    ),
    (
        r"only one (group|level|class|category)",
        "只检测到一个分组",
        "你选的「分组变量」在数据里只有一种取值，无法做组间比较。",
        "请改选有 2 个或更多类别的变量做分组（例如「性别」=男/女）。",
    ),
    (
        r"all.*nan|all values are nan|all-nan",
        "所选变量全是缺失值",
        "你选的变量里没有任何有效数据。",
        "请回到「数据预览」检查变量名是否选对，或更换其他完整变量。",
    ),
    (
        r"sample size.*too small|n[ _]?too[ _]?small|n\s*<\s*\d+",
        "样本量太小",
        "样本数量不足以可靠地完成这个检验。",
        "建议：(1) 收集更多数据（每组至少 30 人）；(2) 改用对小样本更稳健的非参数检验。",
    ),
    (
        r"singular matrix|linalg.*singular|matrix is singular",
        "矩阵奇异（变量高度相关或完全共线）",
        "某些预测变量之间几乎完全重复，统计模型无法识别它们的独立贡献。",
        "请检查：(1) 是否同时放入了某变量和它的衍生变量；(2) 删除高度相关的变量之一。",
    ),
    (
        r"variance.*zero|0 variance|constant column",
        "变量没有变化（方差为 0）",
        "选中的变量里所有人都是同一个值，无法计算方差或相关。",
        "请换一个有变化的变量（例如别选「全部都是大学生」这种常数变量）。",
    ),
    (
        r"degrees of freedom|df\s*[<=]\s*0|negative.*df",
        "自由度不足",
        "样本量减去参数数量后小于等于 0，无法估计模型。",
        "样本量不足以支撑这个模型，请减少自变量数量或增加样本。",
    ),
    (
        r"too few groups|fewer than 2 groups",
        "组数太少",
        "方差分析至少需要 3 个组（独立样本 t 检验需要 2 组）。",
        "请检查分组变量的水平数是否足够。",
    ),

    # ====== 文件相关 ======
    (
        r"file not found|no such file|errno 2",
        "文件未找到",
        "系统在指定路径找不到这个文件。",
        "请重新上传，或检查文件是否被移动/删除。",
    ),
    (
        r"unicodedecodeerror|codec can't decode|invalid (start|continuation) byte",
        "文件编码不兼容",
        "文件不是 UTF-8 编码，含有无法识别的字符。",
        "请用 Excel 或记事本打开后「另存为 → 编码：UTF-8」，然后重新上传。",
    ),
    (
        r"excel|openpyxl|xlrd",
        "Excel 文件读取失败",
        "Excel 文件可能损坏，或包含合并单元格、公式等复杂内容。",
        "请把数据另存为 .csv（CSV UTF-8）后重新上传，会更稳定。",
    ),
    (
        r"empty.*column|columns? not found|key.*not in",
        "找不到指定的列",
        "你选的变量名在数据中不存在。",
        "请检查列名是否拼写正确（区分中英文标点、大小写、空格）。",
    ),

    # ====== 网络/外部 API ======
    (
        r"connection (refused|reset|timed?[- ]?out)|timeout|max retries",
        "网络连接失败",
        "无法连接到外部服务（如文献检索 API、LLM API）。",
        "请检查：(1) 网络是否正常；(2) 是否需要科学上网；(3) 稍后重试。本地分析功能不受影响。",
    ),
    (
        r"unauthorized|401|invalid api key|incorrect api key",
        "API Key 无效或过期",
        "AI 服务拒绝了你的 API Key。",
        "请到侧边栏「LLM 配置」重新输入正确的 API Key，或检查账户是否欠费/被限流。",
    ),
    (
        r"rate limit|429|too many requests",
        "请求频率过高",
        "AI 服务限制了你的访问频率。",
        "请等 30 秒后重试。如果频繁出现，考虑切换到其他模型或自建 Ollama 服务。",
    ),

    # ====== 内存相关 ======
    (
        r"memoryerror|out of memory|cannot allocate",
        "内存不足",
        "数据太大或运算太复杂，内存放不下。",
        "建议：(1) 减少变量数；(2) 抽样后再分析；(3) 关闭其他程序释放内存。",
    ),

    # ====== 软依赖 ======
    (
        r"no module named ['\"]?(semopy|kaleido|playwright)",
        "缺少可选组件",
        "这个功能需要额外的 Python 包，但还没安装。",
        "请打开终端运行：`pip install <包名>`（错误信息里有具体名字）。安装后重启程序即可。",
    ),
]


_BACKUP_TRANSLATIONS = [
    (r"valueerror", "数值错误"),
    (r"keyerror", "找不到指定的键/列"),
    (r"typeerror", "数据类型不匹配"),
    (r"indexerror", "索引越界"),
    (r"zerodivisionerror", "除零错误"),
    (r"runtimeerror", "运行时错误"),
    (r"importerror", "组件导入失败"),
    (r"attributeerror", "对象缺少所需属性"),
]


def friendly_explain(exc: BaseException) -> FriendlyError:
    """把异常翻译为本科生友好的提示。"""
    msg = f"{type(exc).__name__}: {exc}"
    msg_lower = msg.lower()

    for pattern, title, explanation, action in ERROR_PATTERNS:
        if re.search(pattern, msg_lower):
            return FriendlyError(
                title=title,
                explanation=explanation,
                suggested_action=action,
                technical_detail=msg,
            )

    # 兜底：根据异常类型给一个粗略的中文标签
    type_label = type(exc).__name__
    for pattern, label in _BACKUP_TRANSLATIONS:
        if re.search(pattern, type_label.lower()):
            return FriendlyError(
                title=f"分析过程出错：{label}",
                explanation=str(exc) or "未提供详细信息。",
                suggested_action=(
                    "请回到上一步检查数据或参数是否正确。"
                    "若问题持续，可以尝试用「演示数据」验证流程是否正常。"
                ),
                technical_detail=msg,
            )

    return FriendlyError(
        title="出现了意外错误",
        explanation="系统遇到了未预期的问题。",
        suggested_action="请重试，或在反馈渠道附上下方技术信息。",
        technical_detail=msg,
    )


# --------------------------------------------------------------------------- #
# v2.8: 未知错误兜底引导
# --------------------------------------------------------------------------- #

UNKNOWN_ERROR_GUIDE = (
    "💡 这个错误暂未收录到我们的常见问题库\n"
    "建议尝试以下方式获取帮助：\n"
    "1. 复制下方技术信息，发送给老师或师兄师姐\n"
    "2. 粘贴到 ChatGPT/Claude，描述你正在做什么\n"
    "3. 在系统反馈渠道提交 Bug 报告"
)


def is_unknown_error(fe: FriendlyError) -> bool:
    """判断 FriendlyError 是否属于"未匹配模板的未知错误"。"""
    return fe.title in ("出现了意外错误", "分析过程出错：运行时错误")


def build_help_request_markdown(
    exc: BaseException,
    *,
    operation: str = "",
    test_type: str = "",
    variables: Optional[List[str]] = None,
    sample_size: Optional[int] = None,
) -> str:
    """生成可粘贴到 ChatGPT/GitHub Issue 的求助信息（Markdown 格式）。"""
    fe = friendly_explain(exc)
    parts = [
        "# 错误求助",
        "",
        "## 我正在做什么",
    ]
    if operation:
        parts.append(f"- 操作：{operation}")
    if test_type:
        parts.append(f"- 统计方法：{test_type}")
    if variables:
        parts.append(f"- 变量：{', '.join(variables)}")
    if sample_size is not None:
        parts.append(f"- 样本量：n = {sample_size}")
    if not (operation or test_type or variables or sample_size is not None):
        parts.append("- （未提供操作上下文）")

    parts.extend([
        "",
        "## 系统给出的友好提示",
        f"**{fe.title}**",
        "",
        fe.explanation,
        "",
        "## 技术错误信息",
        "```",
        fe.technical_detail,
        "```",
        "",
        "## 完整 traceback",
        "```python",
        traceback.format_exc(),
        "```",
        "",
        "## 我希望解决",
        "（在这里描述你期望的结果）",
    ])
    return "\n".join(parts)


def render_friendly_error(st_module, exc: BaseException, *, show_technical: bool = True,
                          context: Optional[Dict[str, Any]] = None):
    """在 Streamlit 中渲染友好错误信息。

    Args:
        st_module: streamlit 模块（避免顶层硬依赖）
        exc: 异常实例
        show_technical: 是否显示技术细节展开框
    """
    fe = friendly_explain(exc)
    is_unknown = is_unknown_error(fe)

    st_module.error(f"❌ **{fe.title}**\n\n{fe.explanation}")

    if is_unknown:
        # v2.8: 未知错误显示三步求助引导 + 复制按钮
        st_module.info(UNKNOWN_ERROR_GUIDE)
        try:
            help_md = build_help_request_markdown(
                exc,
                operation=(context or {}).get("operation", ""),
                test_type=(context or {}).get("test_type", ""),
                variables=(context or {}).get("variables"),
                sample_size=(context or {}).get("sample_size"),
            )
            with st_module.expander(
                "📋 复制技术信息（粘贴到 ChatGPT / GitHub Issue / 邮件）",
                expanded=False,
            ):
                st_module.code(help_md, language="markdown")
                st_module.caption(
                    "↑ 全选复制后粘贴。AI 工具/老师能据此快速定位问题。"
                )
        except Exception:
            pass
    else:
        st_module.info(f"💡 **怎么办**：{fe.suggested_action}")

    if show_technical and fe.technical_detail and not is_unknown:
        with st_module.expander("🔧 技术信息（出问题反馈时复制）", expanded=False):
            st_module.code(fe.technical_detail, language="text")
            tb = traceback.format_exc()
            if tb and "NoneType" not in tb:
                st_module.code(tb, language="python")


def friendly_handler(default_return=None):
    """装饰器：把异常包装成 (result, FriendlyError|None) 元组。

    使用：
        @friendly_handler(default_return=None)
        def my_func(...):
            ...
        result, err = my_func(...)
        if err:
            render_friendly_error(st, ...)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs), None
            except Exception as exc:  # noqa: BLE001
                return default_return, friendly_explain(exc)
        return wrapper
    return decorator
