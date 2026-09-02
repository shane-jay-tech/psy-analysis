"""隐私、伦理与 AI 安全声明模块。

在系统关键节点提供：
1. 非诊断免责声明
2. LLM 数据外发提示
3. 一键缓存清理
4. 敏感信息扫描
5. 数据治理声明
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re
import os
import glob as glob_module
import shutil


# --- 声明文本 ---

NON_DIAGNOSTIC_DISCLAIMER = (
    "⚠️ 本系统仅为学术研究辅助工具，不具备临床诊断功能。"
    "系统输出的任何心理学分析结果不构成心理健康评估或诊断意见。"
    "如需心理健康服务，请咨询持证专业人士。"
)

LLM_DATA_DISCLOSURE = (
    "📤 本操作将通过大语言模型（LLM）处理数据。"
    "数据会发送至外部 API 服务。请确保数据中不含敏感个人信息。"
    "系统已内置 PII 脱敏机制，但建议您在上传前自行检查。"
)

DATA_GOVERNANCE_NOTICE = (
    "📋 数据治理声明：\n"
    "• 所有数据默认仅存储在本地，不自动上传至云端\n"
    "• 临时文件在会话结束后自动清理\n"
    "• 导出包中不含原始数据，仅含统计结果\n"
    "• 您可随时使用「清理缓存」功能删除所有本地临时数据"
)

AI_USAGE_DISCLOSURE = (
    "🤖 AI 使用声明：本系统部分功能使用 AI 大语言模型辅助生成。"
    "AI 生成内容已标注来源，最终学术判断和论文内容应由研究者本人负责。"
    "建议在提交论文前向导师披露 AI 辅助工具的使用情况。"
)


@dataclass
class SensitiveFinding:
    """敏感信息扫描发现。"""
    pattern_type: str   # id_card / phone / email / api_key / password
    location: str       # 文件名或字段名
    masked_sample: str  # 脱敏后的样本
    severity: str       # high / medium / low


# 敏感信息正则
_PATTERNS = {
    "id_card": (r"(?<!\d)\d{17}[\dXx](?!\w)", "high"),
    "phone": (r"(?<!\d)1[3-9]\d{9}(?!\d)", "high"),
    "landline": (r"(?i)(?:电话|座机|tel(?:ephone)?)\s*[：:=]?\s*0\d{2,3}-?\d{7,8}(?!\d)", "high"),
    "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "medium"),
    "api_key": (r"\b(sk-|ak_|AKIA)[A-Za-z0-9]{20,}\b", "high"),
    "password": (r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+", "medium"),
    "messenger": (r"(?i)(微信|wechat|qq)\s*[：:=]?\s*[A-Za-z0-9_-]{5,20}", "high"),
}


def scan_text_for_sensitive(text: str, source: str = "unknown") -> list[SensitiveFinding]:
    """扫描文本中的敏感信息。"""
    findings = []
    for pattern_type, (regex, severity) in _PATTERNS.items():
        for match in re.finditer(regex, text):
            raw = match.group()
            masked = raw[:3] + "***" + raw[-2:] if len(raw) > 5 else "***"
            findings.append(SensitiveFinding(
                pattern_type=pattern_type,
                location=source,
                masked_sample=masked,
                severity=severity,
            ))
    return findings


def redact_sensitive_text(text: str) -> tuple[str, dict[str, int]]:
    """替换文本中的可识别信息，返回脱敏文本与按类型计数。

    使用与导出预检完全相同的模式，避免出现“门禁能发现、归档却未处理”的分叉。
    """
    redacted = str(text)
    counts: dict[str, int] = {}
    for pattern_type, (regex, _severity) in _PATTERNS.items():
        redacted, count = re.subn(regex, f"[REDACTED_{pattern_type.upper()}]", redacted)
        if count:
            counts[pattern_type] = count
    return redacted, counts


def scan_dataframe_for_sensitive(df, column_names_only: bool = False) -> list[SensitiveFinding]:
    """扫描 DataFrame 中的敏感信息（列名 + 可选内容）。"""
    findings = []
    # 检查列名
    sensitive_col_keywords = ["姓名", "name", "身份证", "id_card", "手机", "phone", "邮箱", "email", "密码", "password", "地址", "address"]
    for col in df.columns:
        col_lower = str(col).lower()
        for kw in sensitive_col_keywords:
            if kw in col_lower:
                findings.append(SensitiveFinding(
                    pattern_type="column_name",
                    location=f"列: {col}",
                    masked_sample=col,
                    severity="medium",
                ))
                break

    if not column_names_only:
        # 抽样检查前 100 行
        sample = df.head(100)
        for col in sample.columns:
            text = " ".join(sample[col].astype(str).tolist())
            col_findings = scan_text_for_sensitive(text, source=f"列: {col}")
            findings.extend(col_findings)

    return findings


def get_cache_dirs(project_root: str = ".") -> list[dict]:
    """获取可清理的缓存目录列表。"""
    cache_candidates = [
        ("data/cache", "分析缓存"),
        ("data/literature_feed/cache", "文献缓存"),
        ("data/tmp", "临时文件"),
        (".streamlit/cache", "Streamlit 缓存"),
        ("__pycache__", "Python 字节码"),
    ]
    result = []
    for rel_path, label in cache_candidates:
        full_path = os.path.join(project_root, rel_path)
        if os.path.exists(full_path):
            size = _dir_size(full_path)
            result.append({
                "path": rel_path,
                "label": label,
                "size_mb": round(size / 1024 / 1024, 2),
                "exists": True,
            })
    return result


def clear_cache(project_root: str = ".", targets: Optional[list[str]] = None) -> dict:
    """清理指定缓存目录。返回清理结果。"""
    all_dirs = get_cache_dirs(project_root)
    cleared = []
    errors = []

    for d in all_dirs:
        if targets and d["path"] not in targets:
            continue
        full_path = os.path.join(project_root, d["path"])
        try:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
                os.makedirs(full_path, exist_ok=True)
                cleared.append(d["path"])
        except OSError as e:
            errors.append(f"{d['path']}: {e}")

    return {"cleared": cleared, "errors": errors}


def _dir_size(path: str) -> int:
    """计算目录大小（字节）。"""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def export_pre_check(text_content: str, source: str = "export") -> dict:
    """导出前敏感信息预检。返回 {'safe': bool, 'findings': [...]}。"""
    findings = scan_text_for_sensitive(text_content, source)
    high_severity = [f for f in findings if f.severity == "high"]
    return {
        "safe": len(high_severity) == 0,
        "findings": findings,
        "high_count": len(high_severity),
        "total_count": len(findings),
    }
