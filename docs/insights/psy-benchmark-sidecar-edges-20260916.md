# psy benchmark side-car 补评落盘契约补测扩展（n916x-32）

**结论：既有 side-car 测试（3a07b8e，3 用例）追加 4 边界用例全绿——`python -m pytest -k sidecar -q` → 7 passed。并发隔离／源缺失明确失败／目录不存在现状锁定／字节不变守卫负例全部在册，零真实模型调用、零生产实现改动。**

## 一、命令与数字

```
$ python -m pytest -k sidecar -q  → 7 passed（既有 3＋追加 4）
```

## 二、追加用例与「原 JSON 字节不变」断言实现

| 用例 | 断言 | 说明 |
|---|---|---|
| 并发两次补评不互相覆盖 | 双线程各自 apply 到不同 side-car 路径 → 两产物均 30 条完整结构、返回 payload 正常 | 并发形态取「并发实例、独立目标」确定性口径；同路径并发＝.bak 机制 last-writer-wins（既有实现语义，未测） |
| 补评源缺失明确失败 | bench 缺失 → `pytest.raises(FileNotFoundError)` 且 **side-car 不得留下半成品** | 静默失败防线 |
| 目录不存在（契约↔实现差异记录） | side-car 落 nested 目录 → 现状抛 FileNotFoundError、nested 不建 | **实现无 makedirs＝任务书期望「创建目录后成功」不成立**——按「不改生产实现」锁定现状，差异留日间拍板（补 makedirs 属行为增强） |
| 字节不变守卫负例 | apply 进行中改动 bench → 内置守卫 AssertionError「原始基准 JSON 发生了变化」 | 触发方式＝monkeypatch mod.json.dumps（守卫的 sha 计算与复读之间的打点位；source_sha256 于 build_sidecar 后才计算，故打点不在 build 期） |

「原 JSON 字节不变」断言实现方式：实现内建 sha256 前后比对（backfill-draft.py apply_sidecar 内 `assert after == payload["source_sha256"]`），用例以「apply 进行中改动文件→断言守卫触发（pytest.raises + match）」证明其有效；既有 test_original_json_untouched 另以整文件 sha 前后相等兜底。

## 三、验收情况

- ✅ `-k sidecar` 7 passed（新增 ≥4，命令与数字同段）；✅ 字节不变断言实现方式同段；✅ 全程离线零 LLM 调用；✅ 生产实现零改动；测试精确路径 git add，未 push。

## 遗留问题

无阻塞。①同路径并发语义（.bak last-writer-wins）与 ②目录不存在自动创建，两项均为日间拍板候选。
