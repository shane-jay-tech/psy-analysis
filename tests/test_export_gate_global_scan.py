"""全局导出门禁静态扫描 — 确保所有导出按钮有门禁或白名单覆盖。

扫描所有 st.download_button 调用，验证：
1. 论文/交付包类导出必须有 export_gate 保护
2. 其它导出有明确白名单理由
3. state_keys 统一使用
"""

import ast
import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock

SRC_DIR = Path(__file__).parent.parent / "src"
APP_FILE = Path(__file__).parent.parent / "app.py"

WHITELIST_EXPORTS = {
    "src/ui/experiment_design_ui.py": "实验设计方案导出（非论文，无需门禁）",
    "src/ui/items_upload_panel.py": "题目模板/分析报告导出（开发辅助，无需门禁）",
    "src/ui/renderers.py": "分析结果图表/JSON 导出（中间产物，无需门禁）",
    "src/ui/result_card_panel.py": "结果卡 Markdown 导出（中间产物，无需门禁）",
    "src/ui/literature_review_panel.py": "文献审核结果导出（中间产物，非正式交付）",
    "src/ui/project_panel.py": "项目快照导出（开发辅助）",
    "src/ui/paper_preview_panel.py": "论文预览面板导出（门禁由 app.py 集成层控制）",
    "src/output/docx_exporter.py": "docx 导出器（注释中提及，非实际按钮）",
    "src/ui/evidence_table_panel.py": "文献证据表导出（Markdown/CSV/BibTeX/RIS，中间产物供整理用）",
    "src/ui/questionnaire_import_panel.py": "问卷清洗日志导出（中间产物，供数据处理追溯）",
}

GATED_EXPORTS = {
    "app.py": "主应用论文导出（已接入 export_gate）",
    "src/ui/deliverable_center_panel.py": "研究交付包导出中心（已接入 export_gate 门禁检查）",
    "src/ui/undergrad_wizard.py": "本科论文向导（4个正式导出已接入 export_gate，3个教学模板/手册白名单豁免）",
}

NEEDS_MIGRATION = {
}


def _find_download_buttons(filepath: Path) -> list[int]:
    """返回文件中所有 st.download_button 的行号。"""
    lines = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if "st.download_button" in line and not line.strip().startswith("#"):
                    lines.append(i)
    except (OSError, UnicodeDecodeError):
        pass
    return lines


def _get_all_download_button_files() -> dict[str, list[int]]:
    """收集所有包含 download_button 的文件。"""
    results = {}
    for root, dirs, files in os.walk(SRC_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = Path(root) / f
                lines = _find_download_buttons(path)
                if lines:
                    rel = path.relative_to(SRC_DIR.parent).as_posix()
                    results[rel] = lines

    app_lines = _find_download_buttons(APP_FILE)
    if app_lines:
        results["app.py"] = app_lines
    return results


class TestExportGateGlobalScan:
    """全局导出门禁静态扫描。"""

    def test_all_download_buttons_accounted_for(self):
        """所有 download_button 必须在白名单、门禁名单或待迁移名单中。"""
        all_files = _get_all_download_button_files()
        known = set(WHITELIST_EXPORTS) | set(GATED_EXPORTS) | set(NEEDS_MIGRATION)

        unaccounted = []
        for filepath in all_files:
            if filepath not in known:
                unaccounted.append(filepath)

        assert unaccounted == [], (
            f"以下文件的 download_button 未被门禁覆盖或加入白名单: {unaccounted}"
        )

    def test_gated_files_have_export_gate_import(self):
        """门禁名单中的文件必须导入或调用 export_gate。"""
        for filepath in GATED_EXPORTS:
            full_path = SRC_DIR.parent / filepath
            if not full_path.exists():
                continue
            content = full_path.read_text(encoding="utf-8")
            assert "export_gate" in content, (
                f"{filepath} 在门禁名单中但未导入 export_gate"
            )

    def test_whitelist_has_reasons(self):
        """白名单中每个文件都有理由。"""
        for filepath, reason in WHITELIST_EXPORTS.items():
            assert reason, f"{filepath} 白名单缺少理由"
            assert len(reason) > 5, f"{filepath} 白名单理由太短"

    def test_no_new_download_button_without_gate(self):
        """回归测试：如果新增了 download_button，必须加入某个名单。"""
        all_files = _get_all_download_button_files()
        total_buttons = sum(len(lines) for lines in all_files.values())
        assert total_buttons >= 20, "download_button 数量不应突然大幅减少（可能是扫描逻辑异常）"

    def test_undergrad_wizard_gated(self):
        """undergrad_wizard 已完成迁移，在门禁名单中。"""
        assert "src/ui/undergrad_wizard.py" in GATED_EXPORTS

    def test_undergrad_wizard_hides_official_download_when_gate_blocks(self, monkeypatch):
        """不能只检查 import：门禁失败后下载控件必须不存在。"""
        from src.ui import undergrad_wizard

        fake_st = MagicMock()
        fake_st.session_state = {"df": object(), "_delivery_zip": b"sensitive"}
        monkeypatch.setattr(undergrad_wizard, "st", fake_st)
        monkeypatch.setattr(
            undergrad_wizard,
            "run_export_gate",
            lambda _state: (False, ["[PRIVACY_HIGH] 敏感信息"], []),
        )

        shown = undergrad_wizard._render_official_download(
            "正式交付",
            artifact_state_keys=("_delivery_zip",),
            data=b"x",
            file_name="x.zip",
            mime="application/zip",
        )

        assert shown is False
        fake_st.download_button.assert_not_called()
        fake_st.error.assert_called_once()
        assert "_delivery_zip" not in fake_st.session_state

    def test_four_formal_artifact_blocks_use_gated_helper(self):
        """锁住四个正式调用点，避免未来又直接改回 download_button。"""
        source = (SRC_DIR / "ui" / "undergrad_wizard.py").read_text(encoding="utf-8")
        for state_key in ("_delivery_zip", "_collection_zip", "_docx_bytes", "_figures_zip"):
            marker = f'if st.session_state.get("{state_key}"):'
            start = source.index(marker)
            block = source[start:start + 700]
            assert "_render_official_download(" in block, state_key

    def test_no_pending_migrations(self):
        """待迁移名单为空。"""
        assert len(NEEDS_MIGRATION) == 0


class TestStateKeysConsistency:
    """检查 state_keys 使用一致性。"""

    def test_state_keys_module_importable(self):
        from src.ui.state_keys import (
            DATA_FRAME_KEY, ANALYSIS_CARDS_KEY, PAPER_BUNDLE_KEY,
            PAPER_DIFF_SELECTION_KEY, PROJECT_HEALTH_ISSUES_KEY, EXPORT_ALLOWED_KEY,
        )
        assert DATA_FRAME_KEY
        assert ANALYSIS_CARDS_KEY

    def test_state_store_uses_state_keys(self):
        """state_store 应使用 state_keys 中的常量。"""
        from src.ui import state_store
        import inspect
        source = inspect.getsource(state_store)
        assert "state_keys" in source or "DATA_FRAME_KEY" in source

    def test_export_gate_uses_state_keys(self):
        """export_gate 应使用 state_keys 中的常量。"""
        from src.ui import export_gate
        import inspect
        source = inspect.getsource(export_gate)
        assert "state_keys" in source or "DATA_FRAME_KEY" in source
