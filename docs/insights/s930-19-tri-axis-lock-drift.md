# lock/venv/HEAD 三向依赖漂移对账与重建方案材料

> 产出单：s930-19（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-21 遗留 R5（lock/实装 numpy 三向不一致，golden 逐字节钉「第一天起红」预警）。
> requirements-lock.txt 为**在途 M 件只读**；测试零改动。

## 一、三向对账表（六主包实测）

| 包 | HEAD lock | 在途 lock（M，工作树） | venv 实装 | 三向态 |
|---|---|---|---|---|
| numpy | 2.4.4 | **2.3.5** | **2.3.5** | HEAD 独旧 |
| scipy | 1.17.1 | **1.18.0** | **1.18.0** | HEAD 独旧 |
| streamlit | 1.57.0 | **1.58.0** | **1.58.0** | HEAD 独旧 |
| plotly | 6.7.0 | **6.8.0** | **6.8.0** | HEAD 独旧 |
| openai | 2.36.0 | **2.44.0** | **2.44.0** | HEAD 独旧 |
| pandas | 3.0.3 | 3.0.3 | 3.0.3 | 三向一致 |
| python | — | — | 3.12.9（.venv 与系统同版） | — |

**对账结论：「三向不一致」已被在途 requirements-lock.txt 的 diff 缓解为「两向收敛」**——在途 lock（M）＝实装 venv 逐键相等；唯一落后向＝HEAD lock（未提交的旧态）。矿源 R5 描述的 lock/实装 numpy 不一致（2.4.4 vs 2.3.5）正是这条在途 diff 所修的内容。

## 二、R5 风险实测：逐字节钉没有红

`test_cfa_sem_golden.py::test_generated_content_equals_committed_fixture`（「沙箱产物与入库夹具逐字节同（含 numpy/pandas 版本流）」的最强钉）在**当前实装（numpy 2.3.5）下 1 passed**（-k equals_committed 实测）——R5 预言「沿用逐字节钉会第一天起红」**未发生**：夹具的 RNG 产物在 numpy 2.4.4→2.3.5 间未漂（或夹具生成不踩漂移面）。golden 钉无需重建/重录。

## 三、重建方案材料（不实施）

| 步骤 | 动作 | 面 |
|---|---|---|
| 1（唯一必需） | **提交在途 requirements-lock.txt**（+scipy 1.18/streamlit 1.58/plotly 6.8/openai 2.44/numpy 2.3.5 六包对齐）——HEAD 拉平到收敛态，三向归两向 | 根仓/psy 在途 M 面的既有内容，非新改动 |
| 2 | 提交后复核逐字节钉（一条命令 `-k equals_committed`）——预期仍绿 | 只读 |
| 3 | **不做**夹具重录：R5 风险实测未发生＋钉通过＝夹具有效 | —— |
| 4 | 未来 lock 变更纪律：改 lock 必须同日跑 `-k equals_committed`（与钉 docstring「版本漂移请查 numpy/pandas，勿手改夹具」衔接） | 纪律面 |

## 四、建议

提交在途 lock（步骤 1）是**零成本关闭 R5** 的动作——它已在工作树里完成了对齐，只差 commit；任何一天的延迟都是「HEAD lock 误导新班」的窗口（新班按 HEAD 装环境会装出 2.4.4≠实装 2.3.5 的旧不一致）。
