"""Backward-compatible exports for the central method catalog."""

from __future__ import annotations

from .method_catalog import (
    canonical_id_map,
    get_table_route_group,
    resolve_method_id,
)


CANONICAL_IDS: dict[str, str] = canonical_id_map()


__all__ = ["CANONICAL_IDS", "get_table_route_group", "resolve_method_id"]
