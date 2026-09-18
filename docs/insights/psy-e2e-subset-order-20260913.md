# psy e2e 子集顺序依赖：根因定位与最小修复（2026-09-13，d913a-44 材料 + d913b-47 修复）

## 一、复现（三种运行对比）

| 运行 | 命令 | 结果 |
|---|---|---|
| 全量 | `.venv/Scripts/python.exe -m pytest -q` | 绿（exit 0；基线口径 2586 passed/60 skipped） |
| `-k "app or ui or privacy"` 子集 | 同左 | **红：tests/test_e2e_ui.py::TestDataUploadFlow::test_upload_csv_triggers_analysis FAILED（KeyError）** |
| 单用例隔离 | pytest tests/test_e2e_ui.py::TestDataUploadFlow::test_upload_csv_triggers_analysis | 红（同 KeyError，改前） |

## 二、根因（定位到行）

1. 断言点 `tests/test_e2e_ui.py:52`：`at.session_state["_workspace_last_saved"]`——在 CSV 上传后的当次 run 内立即断言自动保存标签键；
2. 该键的写入点只有两处：`app.py:558`（手动导出快照按钮分支）与 `src/utils/autosave.py:113-118 _drain_background_result`（drain 到**后台完成结果**时）；
3. 方案 B 下（`BACKGROUND_AUTOSAVE_ENABLED=True`，autosave.py:58 模块级），上传 rerun 仅**入队**（`submit` 后 return True＝受理），标签键要等下一次 trigger 的 drain 才结转；
4. **共享状态源＝`src/utils/autosave_bg.py` 模块级全局**（`_lock`:43、`_thread`:49、结果槽）——跨测试共享同一 pytest 进程。全量跑时，先前测试的入队/完成把全局结果槽「喂饱」，e2e_ui 用例首次 drain 捡到**别的测试的完成结果**，把标签键误写进本会话 → 断言侥幸通过；子集单独跑无人入队 → drain 返回 None → 键缺失 → KeyError。
5. 结论：非 app 生产码缺陷，是**测试断言违背方案 B 契约**（autosave.py:383-393 明示「True＝受理，不得据 True 断言已落盘，是否落盘以标签键为准」——但标签键本身滞后一轮 drain，断言时机天然不可靠）。

## 三、最小修复（测试侧，+15 行，b-47 实施）

- `tests/test_e2e_ui.py` TestDataUploadFlow 加 autouse fixture：`monkeypatch.setattr(autosave, "BACKGROUND_AUTOSAVE_ENABLED", False)`——走 autosave.py 文档化回滚开关的同步分支，保存与标签键在当次 run 内确定生效；对全局队列状态零依赖，双向消除顺序依赖（既不泄漏他人结果，也不等待异步）。
- 生产码零改动；不动 autosave/autosave_bg 实现。

## 四、修复后验证

- 单文件：tests/test_e2e_ui.py → 6 passed；
- 子集：`-k "app or ui or privacy"` → **456 passed, 7 skipped, 0 failed**（改前 1 failed）；
- 全量：exit 0（0 failed，基线 2586 passed/60 skipped 口径零退化）。
- git add：tests/test_e2e_ui.py（精确路径）。
