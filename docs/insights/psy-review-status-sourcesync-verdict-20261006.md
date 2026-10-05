# review 状态表 × 决策白名单同源化裁决材料（s1002-34，2026-10-06，只读）

- 承 s920-03 遗留 1/2。**现值实况比矿源多一张表**：同源化裁决实际是「三表一硬码」收敛。

## 一、现值键集快照（rg 现取）

| 表 | 位置 | 形态 | 键集 |
|---|---|---|---|
| REVIEW_STATUSES | review_queue_ui.py:15-22 | 运行期可变 dict（图标,标签） | pending/approved/rejected/deferred/merged |
| ReviewAction.validate 硬码元组 | review_queue_ui.py:139 | 字面量 tuple | approved/rejected/deferred/merged（**无 pending**＝pending 非决策，语义正确） |
| VALID_STATUSES | review_service.py:35 | set | 五键全量（:54 `not in or == "pending"` 二次排除 pending——同语义第三写法） |

外部消费：tests/test_review_queue_ui.py:172-174 键集快照＋values 形状断言（monkeypatch/迭代 REVIEW_STATUSES 本体）。

## 二、两案对照（含迁移顺序与红名单）

### 案 A：REVIEW_STATUSES 打 is_decision 标记并派生决策白名单

```python
REVIEW_STATUSES: dict[str, tuple[str, str, bool]] = {   # 第三位 = is_decision
    "pending":  ("🔵", "待审核", False),
    "approved": ("✅", "已纳入", True),
    ...
}
DECISIONS = tuple(k for k, (_, _, d) in REVIEW_STATUSES.items() if d)   # 派生白名单
```
- **diff 面**：review_queue_ui.py 3 处（表体/status_label/status_icon 解包改 `[0]`/`[1]` + validate :139 改 `in DECISIONS`）；review_service.py :35 改 `set(DECISIONS)` 导入同源（可选第二步）。
- **红名单**：test_review_queue_ui.py:173 `len(v)==2` 形状断言翻红（同批改 3→2 值解包）；:174 解包循环同翻。**迁移顺序**：①表体加位＋UI 三 getter 改下标取 ②validate 换 DECISIONS ③测试件 :173-174 同批 ④review_service 收编（独立小步，可后置）。
- **收益**：新增状态只改一处表；validate 与展示永远同步。

### 案 B：MappingProxyType 防篡改＋白名单独立收紧

```python
REVIEW_STATUSES = MappingProxyType({...原 dict...})
_DECISIONS = frozenset(("approved", "rejected", "deferred", "merged"))
# validate: self.decision not in _DECISIONS
```
- **diff 面**：review_queue_ui.py 2 处（import+表体包裹；:139 换 frozenset 名）；**零解包改动**（getter 不动）。
- **红名单**：无——:172-174 只读不写；monkeypatch 路线（若有）会红，现测面无此形态。防「运行期篡改」但**不解决两表漂移**（白名单仍是人记的）。
- **收益**：类型层防篡改；改动最小。

### 组合建议

**B 先 A 后**：B 是零红一行级卫生（先落）；A 解决真问题（漂移）但动解包面（排批）。A 落地后 VALID_STATUSES（第三表）可顺势收编成 `frozenset(REVIEW_STATUSES)`（review_service 独立跟进单）。

## 三、零码改自证

本单命令面＝rg/sed 读码＋本档撰写；`git diff --numstat src/` 本班净 0。
