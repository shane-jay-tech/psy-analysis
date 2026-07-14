"""分析使用日志，生成摘要报告。

Usage:
    python scripts/analyze_usage_logs.py [--days 30] [--output reports/usage_summary.md]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"


def load_events(days: int) -> list[dict]:
    """加载最近 N 天的事件。"""
    events = []
    if not LOG_DIR.exists():
        return events
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y%m%d")
    for f in sorted(LOG_DIR.glob("usage_events_*.jsonl")):
        file_date = f.stem.replace("usage_events_", "")
        if file_date >= cutoff:
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events


def load_errors(days: int) -> list[dict]:
    """加载最近 N 天的错误事件。"""
    errors = []
    if not LOG_DIR.exists():
        return errors
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y%m%d")
    for f in sorted(LOG_DIR.glob("error_events_*.jsonl")):
        file_date = f.stem.replace("error_events_", "")
        if file_date >= cutoff:
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        errors.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return errors


def analyze(events: list[dict], errors: list[dict]) -> str:
    """生成 markdown 摘要。"""
    lines = [
        f"# 使用日志分析摘要",
        f"",
        f"**生成时间**: {date.today()}",
        f"**事件总数**: {len(events)}",
        f"**错误总数**: {len(errors)}",
        f"",
    ]

    if not events:
        lines.append("暂无使用记录。")
        return "\n".join(lines)

    # 事件类型分布
    event_types = Counter(e.get("event", "unknown") for e in events)
    lines.append("## 事件类型分布\n")
    lines.append("| 事件类型 | 次数 |")
    lines.append("|---------|------|")
    for etype, count in event_types.most_common():
        lines.append(f"| {etype} | {count} |")
    lines.append("")

    # 方法使用分布
    methods = Counter(
        e.get("method_id", e.get("method", ""))
        for e in events
        if e.get("event") == "analysis_execute" and (e.get("method_id") or e.get("method"))
    )
    if methods:
        lines.append("## 分析方法使用分布\n")
        lines.append("| 方法 | 次数 |")
        lines.append("|------|------|")
        for method, count in methods.most_common(15):
            lines.append(f"| {method} | {count} |")
        lines.append("")

    # 模板使用
    templates = Counter(
        e.get("template_id", "")
        for e in events
        if e.get("event") == "template_select" and e.get("template_id")
    )
    if templates:
        lines.append("## 模板使用分布\n")
        lines.append("| 模板 | 次数 |")
        lines.append("|------|------|")
        for t, count in templates.most_common():
            lines.append(f"| {t} | {count} |")
        lines.append("")

    # 导出统计
    exports = [e for e in events if e.get("event") == "export"]
    if exports:
        export_formats = Counter(e.get("format", "unknown") for e in exports)
        lines.append("## 导出统计\n")
        lines.append(f"- 总导出次数: {len(exports)}")
        for fmt, count in export_formats.most_common():
            lines.append(f"- {fmt}: {count} 次")
        lines.append("")

    # 分析耗时
    timed = [e for e in events if e.get("event") == "analysis_execute" and e.get("duration_ms")]
    if timed:
        durations = [e["duration_ms"] for e in timed]
        avg_ms = sum(durations) / len(durations)
        max_ms = max(durations)
        lines.append("## 分析耗时\n")
        lines.append(f"- 平均: {avg_ms:.0f}ms")
        lines.append(f"- 最大: {max_ms:.0f}ms")
        lines.append(f"- 样本数: {len(timed)}")
        lines.append("")

    # 活跃天数
    active_days = set()
    for e in events:
        ts = e.get("timestamp", "")
        if ts:
            active_days.add(ts[:10])
    lines.append(f"## 活跃度\n")
    lines.append(f"- 活跃天数: {len(active_days)}")
    lines.append(f"- 日均事件: {len(events) / max(len(active_days), 1):.1f}")
    lines.append("")

    # 错误摘要
    if errors:
        error_types = Counter(e.get("error", "unknown") for e in errors)
        lines.append("## 高频错误\n")
        lines.append("| 错误类型 | 次数 |")
        lines.append("|---------|------|")
        for etype, count in error_types.most_common(10):
            lines.append(f"| {etype} | {count} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="分析使用日志")
    parser.add_argument("--days", type=int, default=30, help="分析最近几天 (default: 30)")
    parser.add_argument("--output", default="reports/usage_summary.md", help="输出路径")
    args = parser.parse_args()

    events = load_events(args.days)
    errors = load_errors(args.days)
    report = analyze(events, errors)

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"摘要已生成: {output_path} ({len(events)} 事件, {len(errors)} 错误)")


if __name__ == "__main__":
    main()
