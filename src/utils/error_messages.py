"""用户友好错误提示模板 — v5.2 新增。

针对 v5.2 新增功能的关键错误场景，提供结构化的错误信息：
- 发生了什么
- 为什么会发生
- 会影响什么
- 你可以怎么做
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserFriendlyError:
    """结构化错误信息。"""
    what: str
    why: str
    impact: str
    actions: list[str]
    severity: str = "error"  # error | warning | info

    def to_markdown(self) -> str:
        lines = [
            f"**发生了什么**: {self.what}",
            f"**为什么会发生**: {self.why}",
            f"**会影响什么**: {self.impact}",
            "**你可以怎么做**:",
        ]
        for i, action in enumerate(self.actions, 1):
            lines.append(f"  {i}. {action}")
        return "\n".join(lines)

    def to_streamlit_dict(self) -> dict:
        return {
            "type": self.severity,
            "title": self.what,
            "detail": self.to_markdown(),
        }


# --- 预定义错误模板 ---

def table_generation_failed(method: str, card_id: str, reason: str = "") -> UserFriendlyError:
    """APA 表格生成失败。"""
    return UserFriendlyError(
        what=f"“{method}”方法的 APA 表格生成失败",
        why=f"结果卡片（ID: {card_id}）缺少表格生成所需的关键字段。{reason}",
        impact="导出的 Word/ZIP 文件中将缺少该方法对应的统计表格，但其他内容不受影响。",
        actions=[
            "检查该分析方法是否正常完成（结果卡片是否完整）",
            "尝试重新运行该分析方法",
            "如果问题持续，可以先跳过该表格继续导出",
        ],
        severity="warning",
    )


def privacy_precheck_blocked(findings_count: int, high_count: int, examples: Optional[list] = None) -> UserFriendlyError:
    """隐私预检阻断导出。"""
    example_text = ""
    if examples:
        example_text = f" 包括：{'、'.join(examples[:3])}"
    return UserFriendlyError(
        what=f"导出前隐私预检发现 {findings_count} 处敏感信息（其中 {high_count} 处高风险）",
        why=f"当前文本中疑似包含高风险敏感信息。{example_text}",
        impact="系统已阻断 Word/ZIP 导出，避免敏感内容进入交付包。",
        actions=[
            "删除或替换文本中的敏感内容（如 API Key、身份证号、密码）",
            "重新运行导出前检查",
            "如果确认是误报，可在确认风险后手动继续（不推荐）",
        ],
        severity="error",
    )


def llm_unavailable(reason: str = "未知") -> UserFriendlyError:
    """LLM 服务不可用。"""
    return UserFriendlyError(
        what="AI 语言模型服务暂时不可用",
        why=f"可能的原因：{reason}（常见：网络连接中断、API Key 过期、服务限流、请求超时）",
        impact="无法使用 AI 辅助功能（方法推荐、论文生成、智能解释），但统计分析和导出功能不受影响。",
        actions=[
            "检查网络连接是否正常",
            "确认 API Key 是否正确配置（设置页面查看）",
            "稍后重试（服务限流通常 1-2 分钟恢复）",
            "可以先使用不依赖 AI 的功能继续工作",
        ],
        severity="warning",
    )


def pdf_unavailable() -> UserFriendlyError:
    """PDF 导出不可用。"""
    return UserFriendlyError(
        what="PDF 导出功能当前不可用",
        why="系统未检测到 Microsoft Word 或 LibreOffice，无法将 Word 文档转换为 PDF。",
        impact="Word (.docx) 和 ZIP 导出正常，仅 PDF 格式不可用。",
        actions=[
            "安装 LibreOffice（免费，推荐）或 Microsoft Office",
            "先导出 Word 文件，手动用 Word/WPS 另存为 PDF",
            "使用在线 Word 转 PDF 工具（注意隐私）",
        ],
        severity="info",
    )


def cfa_sem_not_converged(method: str, possible_reasons: Optional[list] = None) -> UserFriendlyError:
    """CFA/SEM 模型不收敛。"""
    reasons = possible_reasons or ["样本量不足（建议 ≥200）", "模型设定过于复杂", "数据分布不符合正态假设"]
    return UserFriendlyError(
        what=f"{method} 模型估计未能收敛",
        why="迭代过程未在最大步数内达到收敛标准。常见原因：" + "、".join(reasons),
        impact="无法获得可靠的模型拟合指标和参数估计。结果卡片和 APA 表格将不可用。",
        actions=[
            "检查样本量是否充足（CFA 建议 N≥200，SEM 建议 N≥300）",
            "简化模型结构（减少潜变量或路径）",
            "检查数据中是否有严重偏态或极端值",
            "尝试不同的估计方法（如 MLR 替代 ML）",
        ],
        severity="error",
    )


def next_steps_empty() -> UserFriendlyError:
    """下一步推荐为空。"""
    return UserFriendlyError(
        what="当前没有推荐的下一步操作",
        why="项目可能已完成所有主要步骤，或处于中间状态（系统无法判断最佳下一步）。",
        impact="不影响任何功能使用，你可以自行选择要执行的操作。",
        actions=[
            "检查项目状态页，确认各项是否完成",
            "如果所有步骤已完成，可以直接进行最终审阅和导出",
            "如果觉得有遗漏，检查一致性报告中是否有未解决的问题",
        ],
        severity="info",
    )


def export_missing_dependency(missing: str) -> UserFriendlyError:
    """导出缺少依赖。"""
    return UserFriendlyError(
        what=f"导出所需的组件缺失：{missing}",
        why="该组件可能未安装或版本不兼容。",
        impact="相关格式的导出将不可用，但其他格式不受影响。",
        actions=[
            f"运行 pip install {missing} 安装缺失组件",
            "检查 requirements.txt 确认所需版本",
            "如果问题持续，尝试重新创建虚拟环境",
        ],
        severity="warning",
    )


# --- 辅助函数 ---

def format_error_for_streamlit(error: UserFriendlyError) -> str:
    """将错误格式化为 Streamlit 可直接显示的文本。"""
    icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(error.severity, "❓")
    return f"{icon} {error.to_markdown()}"
