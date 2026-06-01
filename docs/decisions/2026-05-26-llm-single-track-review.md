# LLM 单轨化 v4.6 — DeepSeek 独立审查 + 阻断级修复

**日期**：2026-05-26
**关联**：[2026-05-25-merge-llm-config-quickonly.md](./2026-05-25-merge-llm-config-quickonly.md)（v4.6 主体重构）

---

## 触发

v4.6 主体重构（11 个 LLM 调用站点迁移到 `active_config.get_active_llm_config()`）落地后，恢复 DeepSeek 独立审查（用户初次中断后又要求"继续 deepseek 独立审查"）。

DeepSeek 审完给出 **request changes**：3 个阻断级 + 若干建议级。

---

## DeepSeek 发现的问题

### 必修（阻断级 — 直接破坏 v4.6 单轨承诺）

| # | 文件:行 | 症状 |
|---|---|---|
| 1 | `src/ui/literature_review_panel.py:749` | `_get_llm_config()` 还在读 `st.session_state.llm_provider/llm_api_key/llm_model`；v4.6 这些键已不再被任何 UI 写入，结果文献综述 LLM 提取永远拿到空字符串 |
| 2 | `src/ui/upstream_panel.py:670` | 同上；上游漏斗（苏格拉底反问/构念识别/Gap 识别）所有 LLM 路径同样断 |
| 3 | `src/ui/project_panel.py:39` | 切项目时 `preserved` 列表保留旧 `llm_api_key/llm_provider/llm_model/llm_temperature`（这些已没人写了），但 **没保留** `quick_model_id`；切项目=丢失模型选择 |

### 建议级（不阻断主流程，但削弱质量）

- `active_config.py:63-66` 裸 `except Exception` 吞所有错误，`.env.local` 损坏会无声变成"未激活"
- `active_config._FORCED_TEMPERATURES` 与 `quick_models._FORCED_TEMPERATURE` 重复表（DeepSeek=0.3 在两处都写）；以后改一份漏一份就不一致
- `_q_design_pending` 模型切换时 in-flight future 没取消，可能产生 stale 响应
- `chat_with_smart_fallback` 单调用化掉了重试逻辑，瞬时网络抖动直接报错（之前 v4.5 有 2 次重试）
- `upstream_panel._has_llm()` 已删 ollama 分支，但与 `is_llm_active()` 逻辑等价

---

## 仲裁决定

**3 个阻断 → 立即修**（用户痛点是"上面选了不生效"，留这 3 个等于没改完）。

**5 个建议 → 默认不动，等用户决定**。原因：
- `except Exception` 是用户体验权衡（裸异常 vs 启动报错），现状对非技术用户更友好
- 温度表重复目前不影响功能，等真改一处的时候再合并
- in-flight future 取消是边缘情况（用户高频切模型才出问题）
- 重试逻辑和单轨化目标无关，可作为独立任务
- `_has_llm()` 是 dead-code 清理，零功能影响

---

## 改了什么（这次）

### `src/ui/literature_review_panel.py`
```python
def _get_llm_config() -> Optional[Dict[str, Any]]:
    """v4.6 单轨化：从顶部「🤖 AI 模型」激活的预设读。未激活返回 None。"""
    from src.llm_gateway.active_config import get_active_llm_config
    cfg = get_active_llm_config()
    if cfg is None:
        return None
    out = dict(cfg)
    out.setdefault("timeout", 60)
    return out
```

### `src/ui/upstream_panel.py`
```python
def _has_llm() -> bool:
    from src.llm_gateway.active_config import is_llm_active
    return is_llm_active()

def _get_llm_config() -> Optional[Dict[str, Any]]:
    from src.llm_gateway.active_config import get_active_llm_config
    cfg = get_active_llm_config()
    if cfg is None:
        return None
    out = dict(cfg)
    out.setdefault("timeout", 30)
    return out
```

### `src/ui/project_panel.py`
```python
preserved = {
    k: st.session_state[k] for k in [
        "quick_model_id",  # ← v4.6 替换 llm_api_key/llm_provider/llm_model/llm_temperature
        "privacy_accepted", "onboarding_completed",
        "startup_check_done", "env_status", "has_auto_cleaned",
        "_workspace_dismissed", "_autosave_dismissed",
    ] if k in st.session_state
}
```

---

## 验证

- AST 三个文件全部通过
- pytest **1260 passed / 4 skipped**（114.01s）— 与 v4.6 主体重构相同基线，零回归
- 调用图链验证：上游漏斗 / 文献综述 / 切项目三条路径的 LLM 入口全部最终落到 `get_active_llm_config()`

---

## 剩余风险

- `socratic_engine.ask_socratic(llm_config: Dict)` 类型签名是非 Optional 的 Dict；目前由 `is_llm_active()` gate 保护（先判活再调），但类型上是 lie。如果未来有人绕过 gate 直接调，会 None.get crash。

---

## 补丁 2（同日，处理 5 个建议级）

用户决定把建议级也一并修掉，落地：

### `src/llm_gateway/active_config.py` — 收紧 except + 合并温度表
- 删除模块级 `_FORCED_TEMPERATURES`（4 key 全表）
- API 强制温度（GPT/Kimi=1.0）改为单一引用 `quick_models.get_forced_temperature`
- 没有 API 强制的模型（DeepSeek=0.3 / Claude=0.7）放到 `_UI_DEFAULT_TEMPERATURES`
- `except Exception` 收窄到 `(OSError, KeyError, UnicodeDecodeError)`，并 `_logger.warning` 留痕
- session_state 读取 except 收窄到 `(AttributeError, KeyError)`
- streamlit 导入 except 收窄到 `ImportError`

### `src/llm_gateway/gateway.py` — chat_with_smart_fallback 重试
- `retries=2` 显式传给 `llm_chat`（总计最多 3 次尝试）
- 注释说明"业务/瞬时错误一视同仁交由 llm_chat 内部捕获"，避免在网关层引入异常分类

### `app.py` — 模型切换前取消 in-flight future
- `_qm_picked_id != _qm_current` 时遍历 `_q_design_pending` / `_exp_design_pending`
- 调 `cancel_design_request(cancel_id)` + `future.cancel()` + `pop` 状态
- 然后才设置新 `quick_model_id` + rerun

### `src/ui/upstream_panel.py` — 删 `_has_llm` wrapper
- 顶层 import `is_llm_active`
- `if not _has_llm():` → `if not is_llm_active():`
- 删 `_has_llm` 函数定义

### 验证
- 6 个文件 AST 全部通过
- pytest **1260 passed / 4 skipped**（112.81s）— 与基线一致，零回归

### Backlog 清空
原 5 个建议项全部消化：
- ~~裸 except 吞错~~ → 已收窄
- ~~温度表两份重复~~ → 已合并到 quick_models 单一源
- ~~in-flight future 没取消~~ → 切模型时已取消
- ~~重试逻辑被砍掉~~ → 已恢复 retries=2
- ~~`_has_llm` dead code~~ → 已删 wrapper
