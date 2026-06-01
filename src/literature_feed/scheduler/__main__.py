"""``python -m src.literature_feed.scheduler`` CLI 入口。

Windows Task Scheduler 通过 ``scripts/run_daily_feed.bat`` 调用本入口。

退出码：
    0  完成（即使 partial 也算 0，靠 summary 看具体）
    1  锁被占用（已有进程在跑）
    2  顶层未捕获异常
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .daily_runner import (
    DEFAULT_DAYS_BACK,
    DEFAULT_FETCH_LIMIT,
    MAX_EXTRACT_ARTICLES_PER_RUN,
    run_daily,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m src.literature_feed.scheduler",
        description="文献雷达每日抓取 + LLM 抽取 + 打分回填",
    )
    p.add_argument("--trigger", default="scheduler", help="run trigger 标记（默认 scheduler）")
    p.add_argument("--source", action="append", default=None,
                   help="只跑指定 source（可多次），不指定=所有 enabled")
    p.add_argument("--days-back", type=int, default=DEFAULT_DAYS_BACK,
                   help="抓取时间窗口（天，默认 14）")
    p.add_argument("--fetch-limit", type=int, default=DEFAULT_FETCH_LIMIT,
                   help="单 source 单次最多抓多少（默认 20）")
    p.add_argument("--no-extract", action="store_true",
                   help="跳过 LLM 抽取（仅抓 + 入库 + 打分）")
    p.add_argument("--max-extract", type=int, default=MAX_EXTRACT_ARTICLES_PER_RUN,
                   help="单次抽取的最多文章数（默认 12）")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--json-summary", action="store_true",
                   help="把 RunSummary 以 JSON 输出到 stdout（最后一行）")
    p.add_argument("--compute-trending", action="store_true", default=True,
                   dest="compute_trending",
                   help="compute trending weights during the run (default: on)")
    p.add_argument("--no-compute-trending", action="store_false",
                   dest="compute_trending",
                   help="skip trending weights computation")
    p.add_argument("--trending-window", type=int, default=30,
                   help="rolling window in days for trending detection (default 30)")
    p.add_argument("--trending-cap", type=float, default=1.3,
                   help="multiplier cap for trending boost (default 1.3)")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        summary = run_daily(
            trigger=args.trigger,
            sources=args.source,
            days_back=args.days_back,
            fetch_limit=args.fetch_limit,
            do_extract=not args.no_extract,
            max_extract=args.max_extract,
            compute_trending=args.compute_trending,
            trending_window=args.trending_window,
            trending_cap=args.trending_cap,
        )
    except Exception as exc:  # noqa: BLE001
        logging.exception("scheduler 顶层异常：%s", exc)
        return 2

    if args.json_summary:
        print(json.dumps(summary.to_dict(), ensure_ascii=False))

    if summary.status == "skipped_locked":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
