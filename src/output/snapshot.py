"""分析报告快照生成器

将分析结果打包为可重复使用的 ZIP 快照文件，包含：
- data.csv: 分析所用的数据
- analysis_params.json: 分析参数记录
- report.md: 分析报告（Markdown）
- README.txt: 使用说明
"""

import json
import csv
import zipfile
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class SnapshotConfig:
    """快照配置"""
    title: str = "心理学数据分析报告"
    author: str = ""
    description: str = ""
    include_raw_data: bool = True
    include_analysis_params: bool = True
    include_report: bool = True
    compress: bool = True


def create_snapshot(
    data: pd.DataFrame,
    analysis_results: Dict,
    report_text: str = "",
    output_path: Optional[str] = None,
    config: Optional[SnapshotConfig] = None,
) -> bytes:
    """
    创建分析报告的快照 ZIP 文件。

    参数：
        data: 分析所用的 DataFrame
        analysis_results: 分析结果字典（各种检验的结果对象或摘要）
        report_text: Markdown 格式的分析报告文本
        output_path: 保存路径（可选），不指定则返回 bytes
        config: 快照配置

    返回：
        ZIP 文件的 bytes 内容（当 output_path 为 None 时）
    """
    if config is None:
        config = SnapshotConfig()

    buf = io.BytesIO()
    compress_type = zipfile.ZIP_DEFLATED if config.compress else zipfile.ZIP_STORED

    with zipfile.ZipFile(buf, "w", compression=compress_type) as zf:
        # 1. README.txt
        readme = _build_readme(config, data, analysis_results)
        zf.writestr("README.txt", readme)

        # 2. data.csv
        if config.include_raw_data and data is not None and not data.empty:
            csv_buf = io.StringIO()
            data.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            zf.writestr("data.csv", csv_buf.getvalue())

        # 3. analysis_params.json
        if config.include_analysis_params:
            params = _extract_params(analysis_results)
            params["snapshot_created"] = datetime.now().isoformat()
            params["title"] = config.title
            params["author"] = config.author
            params["description"] = config.description
            params["n_rows"] = len(data) if data is not None else 0
            params["n_cols"] = len(data.columns) if data is not None else 0
            params["columns"] = list(data.columns) if data is not None else []
            zf.writestr(
                "analysis_params.json",
                json.dumps(params, ensure_ascii=False, indent=2, default=str),
            )

        # 4. report.md
        if config.include_report and report_text:
            zf.writestr("report.md", report_text)

    buf.seek(0)
    zip_bytes = buf.getvalue()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(zip_bytes)

    return zip_bytes


def load_snapshot(
    filepath_or_bytes,
) -> Dict:
    """
    加载快照文件，返回包含数据和报告的字典。

    返回：
        {
            "data": pd.DataFrame,
            "params": dict,
            "report": str,
            "readme": str,
        }
    """
    if isinstance(filepath_or_bytes, (str, Path)):
        with open(filepath_or_bytes, "rb") as f:
            content = f.read()
    else:
        content = filepath_or_bytes

    buf = io.BytesIO(content)
    result = {}

    with zipfile.ZipFile(buf, "r") as zf:
        if "data.csv" in zf.namelist():
            result["data"] = pd.read_csv(
                io.BytesIO(zf.read("data.csv")), encoding="utf-8-sig"
            )

        if "analysis_params.json" in zf.namelist():
            result["params"] = json.loads(
                zf.read("analysis_params.json").decode("utf-8")
            )

        if "report.md" in zf.namelist():
            result["report"] = zf.read("report.md").decode("utf-8")

        if "README.txt" in zf.namelist():
            result["readme"] = zf.read("README.txt").decode("utf-8")

    return result


# ============================================================
# 内部
# ============================================================


def _build_readme(config: SnapshotConfig, data: pd.DataFrame,
                  results: Dict) -> str:
    """生成 README.txt 内容"""
    n_rows = len(data) if data is not None else 0
    n_cols = len(data.columns) if data is not None else 0

    lines = [
        f"{'='*50}",
        f"  {config.title}",
        f"{'='*50}",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if config.author:
        lines.append(f"作者: {config.author}")
    if config.description:
        lines.append(f"描述: {config.description}")

    lines.extend([
        "",
        "## 文件结构",
        "",
        "- data.csv             分析所用的原始数据",
        "- analysis_params.json 分析参数与结果摘要",
        "- report.md            完整分析报告（Markdown）",
        "- README.txt           本说明文件",
        "",
        "## 数据概览",
        "",
        f"- 样本量: {n_rows} 行",
        f"- 变量数: {n_cols} 列",
    ])

    if data is not None and not data.empty:
        lines.append(f"- 列名: {', '.join(data.columns[:15])}")

    lines.extend([
        "",
        "## 分析方法",
        "",
    ])

    for key in results:
        lines.append(f"- {key}")

    lines.extend([
        "",
        "## 使用说明",
        "",
        "1. 将 data.csv 导入任意统计软件（SPSS/JASP/Jamovi/R/Python）即可复现分析。",
        "2. analysis_params.json 记录了所有分析参数，可配合自动化脚本使用。",
        "3. report.md 为 APA 7 格式的分析报告初稿。",
        "",
        "## 隐私声明",
        "",
        "本快照仅包含分析所需的数据和分析参数，不含个人身份信息。",
        "请在分享快照前确认数据已脱敏。",
        "",
        f"---",
        f"由 心理学研究工具系统 自动生成。",
    ])

    return "\n".join(lines)


def _extract_params(results: Dict) -> Dict:
    """从分析结果中提取可序列化的参数摘要"""
    params = {"analyses": {}}

    for key, value in results.items():
        try:
            if hasattr(value, "__dataclass_fields__"):
                # 数据类对象
                params["analyses"][key] = {
                    k: str(v) for k, v in value.__dict__.items()
                    if k not in ("raw_data", "forest_fig", "table",
                                 "group_stats", "fixed_effects",
                                 "random_effects")
                }
            elif isinstance(value, dict):
                params["analyses"][key] = _serialize_dict(value)
            elif isinstance(value, (int, float, str, bool)):
                params["analyses"][key] = str(value)
            else:
                params["analyses"][key] = str(value)[:200]
        except Exception:
            params["analyses"][key] = "无法序列化"

    return params


def _serialize_dict(d: Dict, depth: int = 0) -> Dict:
    """递归序列化字典（限制深度防止过大）"""
    if depth > 3:
        return "..."
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _serialize_dict(v, depth + 1)
        elif isinstance(v, (list, tuple)):
            result[k] = [str(x)[:100] for x in v][:10]
        elif hasattr(v, "__dataclass_fields__"):
            result[k] = str(v)[:200]
        else:
            result[k] = str(v)[:200]
    return result
