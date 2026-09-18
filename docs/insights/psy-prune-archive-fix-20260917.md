# psy prune_archive docstring/实现不符收敛＋is_dir 守卫（917-33）

**结论：择一收敛＝改 docstring（实现的全条目语义为准，916p-a4-007 §四建议 4）；补 is_dir 守卫（非目录超额条目跳过并记录，绝不 rmtree）＋1 钉住用例；相关测试 7 passed 全绿（含旧特征化用例按新语义更新）。archive/ 内容零改动。**

## 一、改前差异与择一依据（复跑与原文同段）

```
$ python -m pytest tests/test_prune_archive.py -q（改前）→ 6 passed
  其中 test_non_dir_entry_in_excess_fixed_current_behaviour 钉死旧行为：
  非目录条目（00_index.json）落超额 → rmtree 抛 NotADirectoryError（无捕获）
差异：docstring（:4-8）称「timestamped snapshot dirs」，实现 :29 iterdir() 对全部条目操作
择一依据：实现的「全条目保留 20」语义是既有运行事实（archive/ 18 条含非快照件），
改实现（过滤只留目录）会改变保留行为——故改 docstring 为真实口径＋补守卫。
```

## 二、改动（scripts/prune_archive.py）

1. **docstring 收敛**：Rule 1 改述为「entries of any kind (snapshot dirs AND loose files, name-sorted)…Non-directory entries in the excess set are skipped and counted」。
2. **is_dir 守卫**：apply 删除循环内，非目录条目打印 `[skip] non-directory entry` 并 `skipped_non_dir` 计数（尾部汇总输出），`continue` 跳过——**绝不 rmtree 文件**。
3. 复跑：`pytest tests/test_prune_archive.py -q` → 7 passed（6 既有＋新增钉住用例；旧「现状固定」用例按新语义更新——守卫后文件保留、20 目录全保留）。

## 三、验收情况

- ✅ 相关测试 7 passed（≥ 改前 6+1，命令与数字同段）；✅ is_dir 守卫可用：非目录超额条目不崩溃、跳过并计数（钉住用例断言文件存活）；✅ archive/ 前后 18 条零改动；✅ 未跑生产清理、未 push；脚本与测试精确路径 git add。

## 遗留问题

无。
