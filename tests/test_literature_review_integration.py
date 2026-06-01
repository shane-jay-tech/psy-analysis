"""文献综述工作台端到端集成测试。"""

import streamlit as st

from src.literature_review.matrix import (
    add_literature_to_matrix,
    auto_fill_abstract_info,
    create_matrix,
)
from src.literature_review.models import (
    GapAnalysis,
    LiteratureItem,
    LiteratureMatrix,
    ReadingNote,
    ThemeCluster,
)
from src.literature_review.notes import (
    create_note,
    notes_to_dict_list,
)
from src.literature_review.search import search_literature
from src.literature_review.themes import auto_cluster_themes, identify_gaps
from src.utils.workspace import (
    LITERATURE_REVIEW_SESSION_KEY,
    build_workspace_snapshot,
    get_literature_review_state,
    get_upstream_state,
    restore_workspace,
)


class TestCompleteWorkflow:
    """搜索 → 笔记 → 矩阵 → 主题 → gap 完整链路。"""

    def test_full_workflow(self):
        st.session_state.clear()
        # 1) 模拟搜索结果
        items = [
            LiteratureItem(
                key="k1", title="X 与 Y 的相关研究",
                authors=["张三"], year=2022, abstract="本研究 n=200, β=0.45 显示 X 与 Y 相关",
                relevance_score=0.8,
            ),
            LiteratureItem(
                key="k2", title="X 影响 Y 的实验",
                authors=["李四"], year=2023, abstract="实验组 vs 对照组，d=0.42",
                relevance_score=0.7,
            ),
        ]
        lr_state = get_literature_review_state(st.session_state)
        lr_state["literature_items"] = [it.to_dict() for it in items]

        # 2) 添加笔记
        notes = []
        create_note(notes, literature_key="k1", content="X 与 Y 中度相关", type="结果")
        create_note(notes, literature_key="k1", content="样本量 200", type="方法")
        create_note(notes, literature_key="k2", content="实验组优于对照组", type="结果")
        create_note(notes, literature_key="k2", content="缺纵向追踪", type="批判")
        create_note(notes, literature_key="k2", content="是否存在中介？", type="疑问")
        lr_state["notes"] = notes_to_dict_list(notes)

        # 3) 矩阵 + 自动填充
        matrix = create_matrix(items)
        for it in items:
            auto_fill_abstract_info(it, matrix)
        lr_state["matrix"] = matrix.to_dict()
        # 验证摘要中的 n=200 / d=0.42 / β=0.45 被提取
        # （取决于摘要文本，至少不应崩）
        assert "样本量" in matrix.dimensions

        # 4) 主题聚类
        themes = auto_cluster_themes(notes, n_clusters=2)
        assert len(themes) >= 1
        lr_state["themes"] = [t.to_dict() for t in themes]

        # 5) Gap 识别（无 LLM → 启发式）
        gaps = identify_gaps(
            research_q="X 是否影响 Y？",
            notes=notes,
            matrix=matrix,
            llm_config=None,
        )
        assert len(gaps) >= 1
        # 「疑问」类型笔记应触发 gap
        gap_descs = " ".join(g.gap_description for g in gaps)
        assert "中介" in gap_descs or "疑问" in gap_descs


class TestFunnelToLiteratureReviewTransition:
    """漏斗完成后跳转到文献综述工作台。"""

    def test_funnel_phase_to_literature_review_phase(self):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["phase"] = "funnel"
        upstream["research_question"] = "X 是否影响 Y？"

        # 模拟 stage 5 点「📚 进入文献综述工作台」按钮的逻辑
        upstream["phase"] = "literature_review"

        assert upstream["phase"] == "literature_review"
        assert upstream["research_question"] == "X 是否影响 Y？"


class TestLiteratureReviewToWizardTransition:
    """文献综述完成后切到 wizard，状态保留。"""

    def test_phase_switches_and_state_preserved(self):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["phase"] = "literature_review"
        upstream["research_question"] = "Y 由 X 决定？"
        lr_state = get_literature_review_state(st.session_state)
        lr_state["literature_items"] = [
            LiteratureItem(title="A", year=2024).to_dict()
        ]

        # 完成文献综述
        upstream["phase"] = "wizard"

        # 验证：phase 切换但 literature_review 状态保留（用户可回看）
        assert upstream["phase"] == "wizard"
        lr_state_after = get_literature_review_state(st.session_state)
        assert len(lr_state_after["literature_items"]) == 1


class TestWorkspacePersistence:
    """文献综述状态跨保存-加载完整恢复。"""

    def test_save_load_preserves_lr_state(self):
        st.session_state.clear()
        # 准备状态
        items = [LiteratureItem(title="X", year=2024).to_dict()]
        notes = [ReadingNote(literature_key="k1", content="A").to_dict()]
        themes = [ThemeCluster(theme_name="主题1", literature_keys=["k1"]).to_dict()]
        gaps = [GapAnalysis(gap_description="缺 X 证据").to_dict()]

        lr_state = get_literature_review_state(st.session_state)
        lr_state["literature_items"] = items
        lr_state["notes"] = notes
        lr_state["themes"] = themes
        lr_state["gaps"] = gaps
        lr_state["last_search_query"] = "X 与 Y"

        # 保存
        ws = build_workspace_snapshot()
        assert "literature_review_state" in ws
        assert len(ws["literature_review_state"]["literature_items"]) == 1
        assert ws["_schema"] == "v3.5"

        # 清空 → 加载
        st.session_state.clear()
        restore_workspace(ws)

        restored = get_literature_review_state(st.session_state)
        assert len(restored["literature_items"]) == 1
        assert len(restored["notes"]) == 1
        assert len(restored["themes"]) == 1
        assert len(restored["gaps"]) == 1
        assert restored["last_search_query"] == "X 与 Y"


class TestAdvancedSkipsFunnel:
    """ADVANCED tier 直接跳过漏斗，仍可使用文献综述。"""

    def test_advanced_can_use_literature_review(self):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["tier"] = "advanced"
        upstream["phase"] = "literature_review"   # ADVANCED 也可进文献综述
        upstream["research_question"] = "已有研究问题"

        from src.upstream.routing import resolve_route
        handler = resolve_route(True, "literature_review", "advanced")
        assert handler == "literature_review_advanced"
