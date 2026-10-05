# AppTest download_button 载荷断言口设计（s1002-25，2026-10-06）

- 承 s921-12 / s924-01 遗留：AppTest 层闭环下载载荷的可行性验证。
- 环境：streamlit **1.58.0**（本仓 .venv 实测）。

## 一、判定：**不可行**（当前版本结构性缺口）

原型链逐侧门实测（脚本见证据）：

| 侧门 | 读数 |
|---|---|
| `at.download_button` 公开元素 | **不存在**（AppTest 无该属性；element_tree 源码 `rg download_button` → 0 命中，v1.58 根本未收录该元素） |
| `at._tree` / `at.main` 子树递归（找 UnknownElement 兜底 proto） | 树只含 int id；button 可见（at.button==1）而 download_button 零暴露 ⇒ **专缺而非树空** |
| `streamlit.runtime.media_manager` 模块 | v1.58 已改名：`media_file_manager`/`memory_media_file_storage`；且 AppTest 裸模式 **Runtime 单例未创建**（`Runtime.instance()` raise "Runtime hasn't been created!"）⇒ deferred_file_id 反查的入口账本在 AppTest 形态下根本不存在 |

结论：`deferred_file_id` 反查 media manager 的路线**双重断**：①proto 层面 download_button 元素未进 AppTest 树（拿不到 id）；②AppTest 无 Runtime/media 账本（有 id 也没处查）。

## 二、替代断言口评估（三案）

### 案 A：读 blob 变量（生产码把载荷写 session_state）——**推荐**

生产码每处 `st.download_button(..., data=X)` 前加一行 `st.session_state["_dl_<key>"] = X`。
- 优点：断言口稳定（`at.session_state["_dl_…"]` 逐字节比对）；AppTest 天然支持；改动机械化（约 N 行 × N 处）。
- 代价：生产码为测试让路（session_state 增键）；需在 conftest 登记消费件。
- 适配面：qimport/交付包族（_render_results 下载口、实验协议 Word 口）。

### 案 B：桩型面守载荷（维持现状＋补桩强度）

既有主流（s921-15 族）：FakeSt 记 download_button 调用参数（label/data/mime）。
- 优点：零生产码改动、参数级断言已闭环「屏上日志=载荷」等式的桩侧。
- 缺点：真运行时面（AppTest）仍无覆盖——双轨永不合龙。

### 案 C：升级 streamlit（等官方补 download_button 元素）

上游 v1.58 未收录；新版是否补齐需另查（联网面，本单未验）。
- 若未来补齐：deferred 路线仍需 Runtime 账本在 AppTest 形态可用（不确定）。
- 建议：被动等待＋本案归档，案 A 不被它阻塞。

## 三、推荐

**案 A**（session_state 载荷镜像）——唯一不依赖上游版本、双层（桩＋AppTest）都能断言的口；实施可拆「逐面板小单」。
