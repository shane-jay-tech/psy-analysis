# error_type 白名单草案（s1007-31，案①未落→草案分支）

- 日期：2026-10-08 ｜ 前置态：s1004-46 案①（写侧校验）**未落**——usage_logger.log_error(:127) 现无任何校验/截断/脱敏，仅 docstring 约定；本单按任务书③分支出草案，零生产码改动

## 白名单集合（成员＋来源）

```python
# 提案常量（落点=src/utils/usage_logger.py log_error 定义前）
ERROR_TYPE_WHITELIST: frozenset[str] = frozenset({
    "data_load_failed",           # app.py:844（s1007-12 注入面清点；数据装载失败语义串）
    "template_center_load_failed",# app.py:2410（同上；模板中心加载失败）
    "export_failed",              # usage_logger.py:11 docstring 示例＋tests/test_privacy_archive_usage.py:208 现用
})
```

- 现网写点全景：app.py 两处固定语义串＋usage_hooks.py:69 透传（severity 包装层）＋docstring 例。tests 面另有 "failure"/"分析"/"数据分析"（后者属 FeedbackLogger.log_error 异签名，不入本白名单域）。
- 扩展机制提案：新增类型走「常量集合＋显式 add」（或 Enum 化），禁调用方拼串——frozenset 直比较，拒绝时 `logger.debug` 一次＋降级写 `"unclassified_error"`（保留可观测不丢事件）。

## 断言提案稿（随案①落地时照抄）

```python
def test_log_error_rejects_non_whitelisted_type(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_logger, "_log_dir", lambda: tmp_path)
    usage_logger.log_error("data_load_failed", detail="x")            # 绿：白名单内
    usage_logger.log_error("failed:条目[用户文本]")                     # 红→降级 unclassified_error
    lines = (tmp_path / f"error_events_{date.today():%Y%m%d}.jsonl").read_text(encoding="utf-8").splitlines()
    types = [json.loads(l)["error"] for l in lines]
    assert types == ["data_load_failed", "unclassified_error"]         # 动态串不入档
```

- 红源实证：s1007-12 探针场景 3——"failed:条目[USER_TEXT_███]" 拼串逐字入 errors_by_type 汇总（接口零校验坐实）。

## 落地前置

案①主班裁决（写侧校验 vs 维持约定）→ 裁准后本草案转实施（常量＋校验 4 行＋测试 1 支，≈10 分钟微单）。
