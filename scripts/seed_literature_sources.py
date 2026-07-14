"""注册文献雷达的数据源（一次性 / 可重复跑的 seed 脚本）。

背景：自学习调度（PsyLiteratureFeed 每日 09:00）一直在跑，但
``sources`` 表为空，导致每天空转、抓 0 篇。本脚本把一批 I-O / HR / OB
方向的期刊源 upsert 进库，让每日抓取真正有源可抓。

数据源全部走 Crossref（按 ISSN 抓增量，免 API key，仅需 polite mailto）。
upsert 幂等：重复跑只更新不重复插入。

用法：
    python scripts/seed_literature_sources.py            # 写入 + 列出当前源
    python scripts/seed_literature_sources.py --probe     # 写入后逐源实测（只抓不抽取）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许直接 `python scripts/seed_literature_sources.py`
REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.literature_feed.storage.feed_store import FeedStore  # noqa: E402


# ---------------------------------------------------------------------------
# 策展源清单：用户研究方向 = 工业/管理心理学 + 人力资源 + 组织行为学
# fetcher_type 全部用 crossref（按 ISSN 抓）。ISSN 用各刊的印刷版或电子版，
# 以 --probe 实测为准。
# ---------------------------------------------------------------------------
SOURCES = [
    # —— 中文旗舰刊（心理所主办，DOI 前缀 10.3724，系统原本就是为这两本设计的）——
    dict(source_id="acta_psych_sinica", journal_name="心理学报 (Acta Psychologica Sinica)",
         issn="0439-755X", doi_prefix="10.3724", fetcher_type="crossref"),
    dict(source_id="adv_psych_science", journal_name="心理科学进展 (Advances in Psychological Science)",
         issn="1671-3710", doi_prefix="10.3724", fetcher_type="crossref"),

    # —— 英文 I-O / 组织行为 / 人力核心刊 ——
    dict(source_id="jap", journal_name="Journal of Applied Psychology",
         issn="0021-9010", fetcher_type="crossref"),
    dict(source_id="personnel_psych", journal_name="Personnel Psychology",
         issn="0031-5826", fetcher_type="crossref"),
    dict(source_id="job", journal_name="Journal of Organizational Behavior",
         issn="0894-3796", fetcher_type="crossref"),
    dict(source_id="jvb", journal_name="Journal of Vocational Behavior",
         issn="0001-8791", fetcher_type="crossref"),
    dict(source_id="hrm", journal_name="Human Resource Management",
         issn="0090-4848", fetcher_type="crossref"),
    dict(source_id="johp", journal_name="Journal of Occupational Health Psychology",
         issn="1076-8998", fetcher_type="crossref"),
]


def seed(store: FeedStore) -> None:
    for s in SOURCES:
        store.upsert_source(
            s["source_id"],
            journal_name=s["journal_name"],
            issn=s.get("issn"),
            doi_prefix=s.get("doi_prefix"),
            fetcher_type=s["fetcher_type"],
            enabled=True,
        )
    print(f"[seed] upserted {len(SOURCES)} sources")


def list_current(store: FeedStore) -> None:
    rows = store.list_sources()
    print(f"[seed] sources 表现有 {len(rows)} 行：")
    for r in rows:
        print(f"  - {r['source_id']:20s} enabled={r['enabled']} "
              f"issn={r.get('issn')!s:12s} {r['journal_name']}")


def probe(store: FeedStore) -> None:
    """逐源实测 Crossref 抓取（只抓不入库不抽取），打印每源返回数。"""
    from src.literature_feed.scheduler.daily_runner import build_fetcher

    print("\n[probe] 逐源实测 Crossref（窗口 60 天，每源最多 10 篇，仅探活）：")
    for r in store.list_sources(enabled_only=True):
        sid = r["source_id"]
        try:
            fetcher = build_fetcher(r)
            result = fetcher.fetch_since(None, limit=10)  # None -> 默认 60 天前
            n = len(result.articles)
            sample = result.articles[0].title[:60] if result.articles else "(无)"
            print(f"  - {sid:20s} 抓到 {n:2d} 篇  | 样例: {sample}")
        except Exception as exc:  # noqa: BLE001
            print(f"  - {sid:20s} [失败] {type(exc).__name__}: {exc}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="注册文献雷达数据源")
    ap.add_argument("--probe", action="store_true", help="写入后逐源实测抓取（只抓不抽取）")
    args = ap.parse_args(argv)

    store = FeedStore()
    try:
        seed(store)
        list_current(store)
        if args.probe:
            probe(store)
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
