# prune_archive.py 保留策略取证＋tmp 隔离安全测试（916p-a4-007，2026-09-17）

## 一、取证三条（命令与原文同段）

a. **docstring 与实现不符**：docstring（:4-8）声明「repo archive/ holds timestamped snapshot dirs」，实现 `entries = [p for p in ARCHIVE_DIR.iterdir()]`（:29）对**全部条目**操作——含文件、含非时间戳命名。
b. **`import re` 零使用**：`rg -n "re\." scripts/prune_archive.py` 无有效命中——「按时间戳正则过滤」意图未落地。
c. **无 is_dir() 守卫**：非目录条目落入超额集合时 `shutil.rmtree(p)`（:37）抛 NotADirectoryError，main() 无捕获（钉测 test_non_dir_entry_in_excess_fixed_current_behaviour 实证：`00_index.json` 名称最小必进超额 → 抛 OSError 子类）。

## 二、archive/ 现状复核（班前/班后两次计数相同）

```
班前：ls archive | wc -l → 18
班后：ls archive | wc -l → 18      （内容与条目数零变化 ✓）
```

## 三、安全测试（tests/test_prune_archive.py，tmp_path 隔离，6 用例全绿）

```
$ .venv\Scripts\python.exe -m pytest tests/test_prune_archive.py -q
6 passed in 0.10s
$ git diff --stat -- scripts/prune_archive.py → 空（脚本零改动）
```

| # | 用例 | 覆盖 |
|---|---|---|
| 1 | dry-run 超额不删（25 目录全在） | :31-37 apply=False 路径 |
| 2 | apply 只删超额，保留==ARCHIVE_KEEP | 25→20 |
| 3 | 排序口径：名称序保留最新 20、删最小 5（可控命名断言） | :32 sort |
| 4 | 非目录条目落超额 → NotADirectoryError（现状钉死） | :37 无守卫实证 |
| 5 | rule_raw 90 天过滤＋dry-run 不删 | :41-58 |
| 6 | ARCHIVE_DIR/RAW_DIR 缺失 → 空列表不抛 | :26-28/:43-45 |

## 四、修复建议（只写建议不落盘）

1. `entries = [p for p in ARCHIVE_DIR.iterdir() if p.is_dir()]`（is_dir 守卫，同时化解 c 项）;
2. 落实时间戳正则（`re.fullmatch(r"\d{8}_\d{6}_\w+", p.name)`）并移除未用的 `import re` 或启用之；
3. main 层对 rule_archive/rule_raw 包 try/except，删除失败打印并继续；
4. docstring 改为实现真实口径（含非目录条目）。

## 五、验收对照

- ✅ a/b/c 三条取证每条附命令与原文。
- ✅ 真实 archive/ 班前班后 18 条目零变化（同段）。
- ✅ 6 用例 ≥6 全绿；脚本零改动（diff 空）。
- ✅ 报告含修复建议段（未落盘）；不 push。
