"""s1004-31：docx/delivery 逐图失败可观测化（0e66 遗留：debug 静默→warning＋清单可见）。

两处统一改法＝案 2（零契约变更）：debug→warning＋点名＋M/N 计数出口；
docx 侧经日志汇总、delivery 侧经 inventory 行（README.txt 用户可见）。
单图炸 ⇒ 失败可见且其余图继续（两路径各一例）。
"""
import io
import logging
import zipfile
from unittest.mock import patch

from src.output.delivery_package import DeliverySpec, build_delivery_package
from src.output.docx_exporter import plotly_figs_to_figure_items


def test_docx_single_figure_failure_visible_and_others_continue(caplog):
    """单图炸 ⇒ WARNING 点名＋M/N 汇总，其余 2 张继续进 items。"""
    specs = [("图A", object()), ("图B", object()), ("图C", object())]
    calls = {"n": 0}

    def flaky(fig, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom-s1004-31")
        return b"png"

    with caplog.at_level(logging.WARNING):
        with patch("src.visualization.paper_export.to_paper_png", side_effect=flaky):
            items = plotly_figs_to_figure_items(specs)

    assert len(items) == 2  # 其余图继续
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "图B" in joined  # 失败点名可见
    assert "2/3" in joined  # M/N 计数出口（0e66 指出 docx 路径原缺此口）


def test_delivery_single_figure_failure_visible_in_inventory(monkeypatch, caplog):
    """单图炸 ⇒ inventory 行含失败清单（README 可见），其余图继续计数。"""
    import src.output.delivery_package as dp

    calls = {"n": 0}

    def flaky(fig, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom-s1004-31")
        return b"png"

    # delivery 内两依赖均为调用期懒导入（取 paper_export 现值）⇒ patch 源模块
    monkeypatch.setattr("src.visualization.paper_export._kaleido_available", lambda: True)
    monkeypatch.setattr("src.visualization.paper_export.to_paper_png", flaky)
    spec = DeliverySpec(figures=[
        {"fig": object(), "test_name_zh": "t检验", "chart_type": "箱线图"},
        {"fig": object(), "test_name_zh": "ANOVA", "chart_type": "柱状图"},
        {"fig": object(), "test_name_zh": "相关", "chart_type": "散点图"},
    ])
    with caplog.at_level(logging.WARNING):
        data = build_delivery_package(spec)

    zf = zipfile.ZipFile(io.BytesIO(data))
    readme = zf.read("README.txt").decode("utf-8-sig")
    line = [ln for ln in readme.splitlines() if "图表集/" in ln and "共" in ln and "论文版" in ln][0]
    assert "共 2 张" in line        # 其余图继续计数
    assert "1 张失败跳过" in line   # 失败清单可见（0e66：原来只有 fig_count）
    assert "ANOVA" in line          # 失败图点名
    assert any("图表导出失败已跳过" in r.getMessage() for r in caplog.records)
