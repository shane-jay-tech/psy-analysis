"""LLM 抽取器：摘要 → 构念 + 方法 → grounding → 入候选表。

Grounding 规则：
- evidence_quote 必须 ≥ 10 字符且为摘要 NFKC 折叠空白后的逐字子串
- confidence < 0.4 视为低置信，丢弃
- JSON 解析失败 / 全部 grounding 失败 → 重试 1 次（带收紧提示）
- 二次失败该 kind 抛 ExtractionError，另一 kind 仍可独立完成

Idempotency：用 (article_id, kind, normalized_name, prompt_version) 直查 SQL，
重复 article 调用第二次不会塞副本。
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..storage.budget_tracker import BudgetExceededError, BudgetTracker
from ..storage.feed_store import CandidateRow, FeedStore, hash_abstract
from .grounding import parse_llm_json, quote_in_abstract
from .prompts import (
    PROMPT_VERSION,
    build_construct_prompt,
    build_method_prompt,
)

logger = logging.getLogger(__name__)

_MIN_QUOTE_LEN = 10
_MIN_CONFIDENCE = 0.4
_VALID_METHOD_CATEGORIES = {
    "experimental", "survey", "qualitative",
    "meta_analysis", "computational", "other",
}


class ExtractionError(RuntimeError):
    """LLM 调用 / 解析 / grounding 全部失败。预算阻断仍走 BudgetExceededError。"""


@dataclass
class ExtractionStats:
    article_id: int
    cache_hit: bool = False
    constructs_kept: int = 0
    methods_kept: int = 0
    constructs_rejected: int = 0
    methods_rejected: int = 0
    needs_review: int = 0


def _estimate_tokens(text: str) -> int:
    """中文 ~1.5 字符/token，其他 ~4 字符/token 的粗估。"""
    if not text:
        return 0
    cn = sum(1 for c in text if "一" <= c <= "鿿")
    other = len(text) - cn
    return int(cn / 1.5) + int(other / 4) + 1


def _llm_config_hash(model: str, prompt_version: str, temperature: float) -> str:
    payload = json.dumps(
        {"model": model, "prompt_version": prompt_version, "temperature": temperature},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _extract_usage(
    fields: Dict[str, Any],
    messages: List[Dict[str, str]],
    content: str,
) -> Tuple[int, int]:
    """优先用 response.fields['usage']，否则启发式估算。"""
    usage = (fields or {}).get("usage")
    if isinstance(usage, dict):
        pt = usage.get("prompt_tokens") or usage.get("input_tokens")
        ct = usage.get("completion_tokens") or usage.get("output_tokens")
        if pt is not None and ct is not None:
            return int(pt), int(ct)
    prompt_text = " ".join(m.get("content", "") for m in messages)
    return _estimate_tokens(prompt_text), _estimate_tokens(content)


def _ground_items(
    items: List[Dict[str, Any]],
    abstract: str,
    *,
    kind: str,
    article_id: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """按规则筛 items，返回 (passing, rejected_count)。"""
    passing: List[Dict[str, Any]] = []
    rejected = 0
    seen_norm: Set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            rejected += 1
            continue
        name = (item.get("name") or "").strip()
        quote = item.get("evidence_quote", "") or ""
        confidence = item.get("confidence")
        if not name:
            rejected += 1
            continue
        norm = name.lower().strip()
        if norm in seen_norm:  # 同一次响应内 LLM 重复给同一个 name
            logger.warning("article %d: drop dup-in-response %s %r", article_id, kind, name)
            rejected += 1
            continue
        if len(quote) < _MIN_QUOTE_LEN:
            logger.warning(
                "article %d: drop %s %r (quote=%d chars)",
                article_id, kind, name, len(quote),
            )
            rejected += 1
            continue
        if not quote_in_abstract(quote, abstract):
            logger.warning(
                "article %d: drop %s %r (quote not verbatim in abstract)",
                article_id, kind, name,
            )
            rejected += 1
            continue
        try:
            conf = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            conf = None
        # 关键：math.isnan 必须先检（NaN<0.4 在 IEEE754 下是 False，会绕过下界）
        if conf is None or math.isnan(conf) or conf < _MIN_CONFIDENCE or conf > 1.0:
            logger.warning(
                "article %d: drop %s %r (confidence=%s)",
                article_id, kind, name, confidence,
            )
            rejected += 1
            continue
        if kind == "method":
            cat = item.get("method_category")
            if cat not in _VALID_METHOD_CATEGORIES:
                logger.warning(
                    "article %d: method %r unknown category=%r → 'other'",
                    article_id, name, cat,
                )
                item["method_category"] = "other"
        seen_norm.add(norm)
        passing.append(item)
    return passing, rejected


def _existing_candidate_norms(
    store: FeedStore,
    *,
    article_id: int,
    kind: str,
    prompt_version: str,
) -> Set[str]:
    """一次拉齐已有候选的 normalized_name，本地 set 去重，避免 N+1 SELECT。"""
    rows = store.connection.execute(
        "SELECT normalized_name FROM llm_candidates "
        "WHERE article_id=? AND kind=? AND prompt_version=?",
        (article_id, kind, prompt_version),
    ).fetchall()
    return {r["normalized_name"] for r in rows}


class LLMExtractor:
    """对一篇文章先 cache-lookup，再两次 LLM 调用，再 grounding，再写候选表。"""

    def __init__(
        self,
        store: FeedStore,
        budget: BudgetTracker,
        *,
        llm_chat_fn: Optional[Callable[..., Any]] = None,
        model: str = "gpt-5.5-pro",
        temperature: float = 1.0,
        max_attempts: int = 2,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self.store = store
        self.budget = budget
        self.model = model
        self.temperature = temperature
        self.max_attempts = max(1, int(max_attempts))
        self.prompt_version = prompt_version
        self._config_hash = _llm_config_hash(model, prompt_version, temperature)
        self._llm_chat = llm_chat_fn  # 真实后端走懒加载，便于测试 mock

    def _llm(self, messages: List[Dict[str, str]]) -> Any:
        if self._llm_chat is None:
            from src.llm_gateway.gateway import llm_chat as _real
            self._llm_chat = _real
        return self._llm_chat(messages, model=self.model, temperature=self.temperature)

    # ------------------------------------------------------------------ #
    # 单 kind：调用 + 解析 + grounding（含 1 次重试）
    # ------------------------------------------------------------------ #

    def _record_call_budget(self, prompt_tokens: int, completion_tokens: int) -> None:
        """每次 LLM 调用结束都登记，无论后续 grounding 是否通过。失败的尝试也吃 token。"""
        if prompt_tokens <= 0 and completion_tokens <= 0:
            return
        try:
            self.budget.record(
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                caller="literature_feed_extract",
                cache_hit=False,
            )
        except Exception as exc:  # noqa: BLE001 - 记账失败别拖垮抽取
            logger.error("budget.record 失败：%s", exc)

    def _call_and_ground(
        self,
        *,
        build_fn: Callable[..., List[Dict[str, str]]],
        title: str,
        abstract: str,
        journal: str,
        items_key: str,
        kind: str,
        article_id: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """返回 (passing_items, rejected_count)。每次 LLM 调用立刻入预算账。失败抛 ExtractionError。"""
        last_err = ""

        for attempt in range(self.max_attempts):
            retry = attempt > 0
            messages = build_fn(title=title, abstract=abstract, journal=journal, retry=retry)

            self.budget.precheck(essential=False)  # 超额抛 BudgetExceededError，向上传

            try:
                response = self._llm(messages)
            except BudgetExceededError:
                raise
            except Exception as exc:
                last_err = f"LLM 调用异常: {exc}"
                logger.error("article %d kind=%s attempt=%d %s", article_id, kind, attempt + 1, last_err)
                if attempt + 1 >= self.max_attempts:
                    raise ExtractionError(
                        f"article {article_id} kind={kind}: {last_err}"
                    ) from exc
                continue

            content = getattr(response, "content", "") or ""
            fields = getattr(response, "fields", {}) or {}
            pt, ct = _extract_usage(fields, messages, content)
            self._record_call_budget(pt, ct)  # 每次调用立刻入账，不再延后到末尾

            parsed = parse_llm_json(content)
            if parsed is None:
                last_err = f"JSON 解析失败 (attempt {attempt + 1})"
                logger.error("article %d kind=%s %s", article_id, kind, last_err)
                if attempt + 1 >= self.max_attempts:
                    raise ExtractionError(f"article {article_id} kind={kind}: {last_err}")
                continue

            raw_items = parsed.get(items_key, [])
            if not isinstance(raw_items, list):
                raw_items = []

            passing, rejected = _ground_items(raw_items, abstract, kind=kind, article_id=article_id)

            # 全部 grounding 失败：重试一次；二次失败抛 ExtractionError
            if len(raw_items) > 0 and len(passing) == 0:
                last_err = f"全部 {len(raw_items)} 项 grounding 失败 (attempt {attempt + 1})"
                logger.error("article %d kind=%s %s", article_id, kind, last_err)
                if attempt + 1 >= self.max_attempts:
                    raise ExtractionError(f"article {article_id} kind={kind}: {last_err}")
                continue

            return passing, rejected

        raise ExtractionError(f"article {article_id} kind={kind}: {last_err}")

    # ------------------------------------------------------------------ #
    # 写候选表
    # ------------------------------------------------------------------ #

    def _write_candidates(
        self,
        items: List[Dict[str, Any]],
        *,
        article_id: int,
        kind: str,
        iohr_hits: List[str],
    ) -> int:
        # 一次性拉齐已有 normalized_name，本地 set 去重（替代每行一次的 N+1 SELECT）
        existing = _existing_candidate_norms(
            self.store,
            article_id=article_id,
            kind=kind,
            prompt_version=self.prompt_version,
        )
        inserted = 0
        for item in items:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            try:
                conf_raw = float(item["confidence"]) if item.get("confidence") is not None else None
            except (TypeError, ValueError):
                conf_raw = None
            conf = conf_raw if (conf_raw is not None and not math.isnan(conf_raw)) else None
            row = CandidateRow(
                article_id=article_id,
                kind=kind,
                name=name,
                evidence_quote=item.get("evidence_quote", ""),
                evidence_valid=True,
                definition=item.get("definition") if kind == "construct" else None,
                method_category=item.get("method_category") if kind == "method" else None,
                confidence=conf,
                novelty_hint=item.get("novelty_hint"),
                iohr_hits=list(iohr_hits or []),
                llm_config_hash=self._config_hash,
                prompt_version=self.prompt_version,
                status="pending",
            )
            if row.normalized_name in existing:
                logger.info("article %d: skip dup %s %r", article_id, kind, name)
                continue
            # INSERT OR IGNORE 是最后一道防线（防并发同时写）；rowid=0 就当无事发生
            new_id = self.store.insert_candidate(row)
            if new_id == 0:
                logger.info("article %d: race-skipped dup %s %r", article_id, kind, name)
                continue
            existing.add(row.normalized_name)
            inserted += 1
        return inserted

    # ------------------------------------------------------------------ #
    # 主入口
    # ------------------------------------------------------------------ #

    def extract_for_article(self, article_id: int, *, force: bool = False) -> ExtractionStats:
        stats = ExtractionStats(article_id=article_id)

        article = self.store.get_article(article_id)
        if article is None:
            logger.warning("article %d 不存在，跳过", article_id)
            return stats

        abstract = (article.get("abstract") or "").strip()
        if not abstract:
            logger.info("article %d 无摘要，跳过", article_id)
            return stats

        title = article.get("title", "") or ""
        journal = article.get("container_title", "") or ""
        iohr_raw = article.get("iohr_hits_json")
        try:
            iohr_hits: List[str] = json.loads(iohr_raw) if iohr_raw else []
        except (TypeError, ValueError):
            iohr_hits = []
        if not isinstance(iohr_hits, list):
            iohr_hits = []

        abstract_h = hash_abstract(abstract)

        # ---------- 缓存命中 ----------
        cached: Optional[Dict[str, Any]] = None
        if not force:
            cached = self.store.get_cached_extraction(
                abstract_hash=abstract_h,
                prompt_version=self.prompt_version,
                model=self.model,
            )
        if cached is not None:
            stats.cache_hit = True
            c_items = cached.get("constructs", []) or []
            m_items = cached.get("methods", []) or []
            # 重新 grounding：保证 evidence_valid 反映当前摘要（罕见但可能 abstract 被回填修正）
            c_pass, c_rej = _ground_items(c_items, abstract, kind="construct", article_id=article_id)
            m_pass, m_rej = _ground_items(m_items, abstract, kind="method", article_id=article_id)
            stats.constructs_kept = self._write_candidates(
                c_pass, article_id=article_id, kind="construct", iohr_hits=iohr_hits,
            )
            stats.methods_kept = self._write_candidates(
                m_pass, article_id=article_id, kind="method", iohr_hits=iohr_hits,
            )
            stats.constructs_rejected = c_rej
            stats.methods_rejected = m_rej
            self.budget.record(
                model=self.model,
                prompt_tokens=0,
                completion_tokens=0,
                caller="literature_feed_extract",
                cache_hit=True,
            )
            logger.info(
                "article %d cache: kept c=%d m=%d rej=%d/%d",
                article_id, stats.constructs_kept, stats.methods_kept, c_rej, m_rej,
            )
            return stats

        # ---------- 实调 LLM（每次调用内部已即时入预算账）----------
        construct_items: List[Dict[str, Any]] = []
        method_items: List[Dict[str, Any]] = []
        construct_fail = False
        method_fail = False
        c_rej = m_rej = 0

        try:
            construct_items, c_rej = self._call_and_ground(
                build_fn=build_construct_prompt,
                title=title, abstract=abstract, journal=journal,
                items_key="constructs", kind="construct", article_id=article_id,
            )
        except ExtractionError as exc:
            logger.error("article %d construct 抽取失败：%s", article_id, exc)
            construct_fail = True
            stats.needs_review += 1

        try:
            method_items, m_rej = self._call_and_ground(
                build_fn=build_method_prompt,
                title=title, abstract=abstract, journal=journal,
                items_key="methods", kind="method", article_id=article_id,
            )
        except ExtractionError as exc:
            logger.error("article %d method 抽取失败：%s", article_id, exc)
            method_fail = True
            stats.needs_review += 1

        stats.constructs_rejected = c_rej
        stats.methods_rejected = m_rej
        stats.constructs_kept = self._write_candidates(
            construct_items, article_id=article_id, kind="construct", iohr_hits=iohr_hits,
        ) if construct_items else 0
        stats.methods_kept = self._write_candidates(
            method_items, article_id=article_id, kind="method", iohr_hits=iohr_hits,
        ) if method_items else 0

        # 关键：两边全失败就别缓存空结果（否则下一轮 cache hit 永远没东西）
        if not (construct_fail and method_fail):
            self.store.cache_extraction(
                abstract_hash=abstract_h,
                prompt_version=self.prompt_version,
                model=self.model,
                response={
                    "constructs": list(construct_items),
                    "methods": list(method_items),
                },
            )

        logger.info(
            "article %d live: kept c=%d m=%d rej=%d/%d review=%d",
            article_id, stats.constructs_kept, stats.methods_kept,
            c_rej, m_rej, stats.needs_review,
        )
        return stats

    def extract_batch(self, article_ids: List[int], *, force: bool = False) -> List[ExtractionStats]:
        results: List[ExtractionStats] = []
        for aid in article_ids:
            try:
                results.append(self.extract_for_article(aid, force=force))
            except BudgetExceededError:
                logger.warning("预算超额，提前停止 batch（已处理 %d 篇）", len(results))
                break
            except ExtractionError as exc:
                logger.error("article %d 抽取异常（继续下一篇）：%s", aid, exc)
                results.append(ExtractionStats(article_id=aid))
        return results
