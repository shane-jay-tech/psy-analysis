# psy 大快照超阈值方案 A 增量资产化设计稿（s918-03）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读设计稿，零改码。

## 现状链路（file:line 图，grep 实测）
```
src/utils/autosave_bg.py
:40  SNAPSHOT_WORKER_CSV_MB_THRESHOLD = 10.0        # 阈值常量（CSV 口径 10MB）
:41  SNAPSHOT_WORKER_B64_BYTES_THRESHOLD = …*4/3     # base64 折算阈值 ≈ 13.98MB
:56  _worker_loop: 取 _pending → _busy=True          # 单 worker 串行
:62-64  mod.st.session_state = job['refs']            # workspace 私有副本灌入引用
       ws = mod.build_workspace_snapshot()            # 全量序列化（df → base64）
:84  df_mb = len(b64)*3/4/1MB                         # 体积折算
:85  if len(b64) > B64_THRESHOLD:                     # 超阈值分支（当前仅日志告警）
:87      logger.warning('快照 df 序列化体量超换案阈值…')  # 无降级行为，大快照仍整包入库
```
调用方（app.py/会话侧）→ `_pending = {'project_id', 'refs'}` → worker 全量序列化 → 整包 b64 存快照。

## 痛点
超过 10MB 的 DataFrame 整包 base64 序列化：单次 ~2s、内存峰值 ~52MB（:38 实测注释），且快照体积随数据线性膨胀——目前只告警不治理。

## 方案 A：增量资产化设计
**核心思想**：把「全量 df 序列化」改为「基线资产 + 增量差异」——首次超阈值时把当前 df 落为独立资产文件（CSV/Parquet），后续快照只存引用指纹 + 变更增量。

### 数据结构（草案）
```json
{
  "snapshot": {
    "version": 2,
    "base_asset": "assets/snap/<project>/df_20260919.parquet",  // 基线资产文件引用
    "base_hash": "sha256:…",           // 基线内容指纹（一致性校验）
    "rows_total": 123456,
    "increments": [                     // 基线之后的追加/修改增量
      {"op": "append", "rows_b64": "…", "rows_n": 120},
      {"op": "patch", "index": [12, 48], "cols": ["值"], "rows_b64": "…"}
    ]
  }
}
```

### 切分边界
| 边界 | 规则 |
|---|---|
| 触发 | 序列化 b64 > B64_BYTES_THRESHOLD（:41 常量复用）时启用增量路径；未超阈值维持整包（小快照不引入复杂度） |
| 基线粒度 | 每 project 一份基线；基线生成时机＝首次超阈值或增量条数 > 50（防增量无限膨胀，到量重打基线） |
| 增量边界 | 按 DataFrame 行追加/指定行列 patch 两类操作；无行级 diff 能力的列（自由文本整列）整段归入基线重打 |
| 失败边界 | 增量序列化失败 → 回退整包路径（现状行为），并记日志——不阻塞快照主流程 |

### 失败回滚（草案）
1. 增量写失败（磁盘/格式）：丢弃 increments，回落整包 b64 路径（现状行为），日志记 `fallback_full`。
2. 基线资产写失败：同上回落；资产文件写采用「临时名+原子 rename」，防半文件。
3. 恢复读取失败（基线 hash 不符）：日志告警 + 要求整包快照重打；旧快照文件保留不删（回退=读上一份 v1 整包快照）。
4. 版本兼容：snapshot.version=2 新结构；读取端遇 version=1 走原路径——新旧并存，可灰度可回退。

### 边界条件表（方案 A）
| 条件 | 行为 |
|---|---|
| b64 ≤ 阈值 | 整包（现状），version=1 |
| b64 > 阈值且首次 | 落基线资产，snapshot=引用+空增量，version=2 |
| 增量条数 > 50 | 重打基线（增量合并进新基线） |
| 增量序列化异常 | 回落整包 + fallback_full 日志 |
| 恢复时 hash 不符 | 告警 + 触发整包重打，读取侧仍能出上一份有效快照 |

## 遗留
- 行级 diff 的实现选型（hash 行 vs 全行比对）待原型；本文档只定边界与回退。
- 落地改动点预估：autosave_bg.py worker 循环 + 快照读取端两处，均为后续批次。
