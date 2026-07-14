"""统一的 session_state key 常量定义。

所有 UI 面板和服务层共用的 session_state key 集中在此，
避免 key 拼写不一致导致面板间状态联动断裂。
"""

# 数据与分析
DATA_FRAME_KEY = "df"
DATA_META_KEY = "meta"
DATA_INSPECTOR_KEY = "inspector"
ANALYSIS_OUTPUT_KEY = "analysis_output"
ANALYSIS_PLAN_KEY = "plan"
ANALYSIS_CARDS_KEY = "analysis_cards"

# 文献审核
REVIEW_QUEUE_FILTERS_KEY = "review_queue_filters"
REVIEW_QUEUE_LAST_ACTION_KEY = "review_queue_last_action"

# 论文写作
PAPER_BUNDLE_KEY = "paper_bundle"
PAPER_REVISED_BUNDLE_KEY = "paper_revised_bundle"
PAPER_DIFF_SELECTION_KEY = "paper_diff_selection"

# 项目健康
PROJECT_HEALTH_ISSUES_KEY = "project_health_issues"
PROJECT_HEALTH_CHECKED_AT_KEY = "project_health_checked_at"

# 方法推荐 → 分析联动
ANALYSIS_RECIPE_KEY = "analysis_recipe"
RECIPE_EXECUTED_KEY = "recipe_executed"

# 导出
EXPORT_ALLOWED_KEY = "export_allowed"
EXPORT_BLOCK_REASONS_KEY = "export_block_reasons"
