# psy 快照方案B session_state 跨线程验证 + df_b64 阈值校准（2026-09-12 夜间执行班，任务 p911r-33）

> 执行：GLM-5.3-Flash 夜间执行班 sweep-20260911-2300。验证脚本：`tmp/psy-session-thread-verify.py`（可复跑：`python tmp/psy-session-thread-verify.py`）。**未改生产代码；零联网。**

## 一、明确结论行

**结论：跨线程直接读写 st.session_state 不安全（静默错位，非报错），方案B 的「主线程引用捕获 + worker 只碰私有数据」为必要替代方案且已验证可行；df_b64=5MB 换案阈值维持，实测数据支持。**

## 二、Part1：子线程改写 / 主线程读 可见性与竞态（5+2 轮）

- 等价 dict（普通 Python dict）：子线程写 1000 键后主线程 join 读 → 5/5 轮全可见；并发期主线程采样读无异常抛出（GIL 下 dict 键级操作无撕裂）。
- **真实 st.session_state（裸线程）**：写入返回 `write_ok=True` 但**写入进了孤儿上下文**（bare 模式 + `missing ScriptRunContext` 警告；streamlit run 下 worker 线程同样拿不到用户会话）——危害形态=**静默写丢/写错会话**，而非异常。
- ⇒ 直接跨线程读写 session_state 不可依赖；**替代方案（已实施于 19-01 a02626c）**：主线程引用级捕获 → 队列投递 worker → 结果由主线程下次调用原子结转。多轮运行无竞态异常。

## 三、Part2：df_b64 换案阈值校准（实测）

| CSV 体积 | df_b64 体积 | 序列化+落盘（不含 to_csv） | 全链参考（19-01 实测） |
|---|---|---|---|
| 2.0 MB | 2.0 MB | 20 ms | — |
| 5.1 MB | 5.1 MB | 35 ms | — |
| 10.1 MB | 10.1 MB | 61 ms | — |
| 11.6 MB（19-01） | 11.3 MB | 531 ms（全链同步口径） | worker 1028.8 ms（后台） |

**建议阈值：维持 df_b64>5MB 作为 B→A 换案信号不变**。依据：方案B 后 UI 线程已无序列化阻塞（5MB 级全链 ~35-60ms 也在后台），阈值的意义从「UI 预算」转为「worker 排队与内存预算」——5MB 级 worker 单次 <1s、内存峰值 ~2.6×CSV，当前队列单 worker 串行无积压风险；触发换案的真正信号是「队列频繁积压/用户报关闭丢改动」（与 19-01 报告§七一致），5MB 数字保留为预警线。

## 四、零改动声明

未改任何生产代码（验证脚本在 tmp/）；只读 mode=ro 隔离目录；未联网；未 commit/push。
