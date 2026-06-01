"""输出系统 — 分析结果格式化、解释和报告生成"""

from .snapshot import (
    SnapshotConfig,
    create_snapshot,
    load_snapshot,
)

try:
    from .plotly_renderers import (
        plotly_correlation_heatmap,
        plotly_interaction_plot,
        plotly_meta_forest,
        HAS_PLOTLY,
    )
except Exception:
    plotly_correlation_heatmap = None
    plotly_interaction_plot = None
    plotly_meta_forest = None
    HAS_PLOTLY = False

__all__ = [
    "SnapshotConfig",
    "create_snapshot",
    "load_snapshot",
    "plotly_correlation_heatmap",
    "plotly_interaction_plot",
    "plotly_meta_forest",
    "HAS_PLOTLY",
]
