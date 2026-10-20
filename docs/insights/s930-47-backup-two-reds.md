# test_backup_user_data 两枚红归因材料

> 产出单：s930-47（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-68 遗留（两枚未归因红：DatabaseError at backup_user_data.py:57；归因线索＝r5 A1 改 _snapshot_sqlite 走 sqlite3.backup()，夹具是否同步未查）。
> **零码改动（不改夹具不改实现）**。

## 一、复现（traceback 逐字）

`$ python -m pytest tests/test_backup_user_data.py -q` → `2 failed, 8 passed`：
- `::test_create_backup_packs_projects_tree_and_feed_db` ＋ `::test_verify_accepts_archive_right_after_create`
- 都在 `scripts/backup_user_data.py:57` `con.backup(out)` 抛 `sqlite3.DatabaseError: file is not a database`。

## 二、归因链（commit 号实证）

| 时点 | 事件 | 证据 |
|---|---|---|
| s918-11~35（90b4d60） | 测试件与夹具同批入库：`feed.write_bytes(b"fake-sqlite")`——**夹具喂 11 字节假串**（当时 _snapshot_sqlite 的旧实现是 `zf.write(FEED_DB)` 纯打包，不 parse 内容 ⇒ 假串无碍） | `git log --all -S "fake-sqlite" -- tests/…` → 90b4d60 |
| **r5 A1（6fb6b16，09-27 00:43）** | `_snapshot_sqlite` 改 `sqlite3.backup()`（修「WAL 未折叠整批丢失」——真缺陷修复）＋ 新增 `_live_article_count`；**该笔 git show 未动 tests/test_backup_user_data.py**（夹具未同步） | `git show 6fb6b16 --stat`（tests 件不在名单）；`git log -1 -- tests/test_backup_user_data.py` → 90b4d60（其后零改动） |
| 现 | `con.backup(out)` 对假串执行 ⇒ sqlite3 判「file is not a database」⇒ 两红 | traceback |

**归因定谳＝夹具喂了非库字节**（`b"fake-sqlite"` 11 字节假串）：实现改走真 sqlite 协议（backup API 必须打开真库）后，假串夹具不再被容忍。**不是「实现不容忍」的缺陷**——backup API 对非库文件报错是 sqlite 正确行为；分叉引入笔＝**6fb6b16（r5 A1）**，且属于「修真缺陷时夹具未随语义升级」的常规欠账。

## 三、两案对比

| 案 | 内容 | 评 |
|---|---|---|
| **改夹具喂真库**（推荐） | 夹具用 `sqlite3.connect(...)` 建真库＋建 `articles` 表灌 1-2 行（借 :57-60 的 `_live_article_count` 断言面） | 与生产语义对齐（A1 修复要的正是「真库语义」——WAL 折叠/行数读数）；两红翻绿；**注意** create 断言可能需同步（zip 内 feed 行为变化） |
| 实现容忍非库字节 | `_snapshot_sqlite` 对 backup 失败退回 `zf.write` 打包原字节 | ❌ 退回恰是 A1 要修的缺陷形态（非库文件丢 WAL 语义无从谈起）——**不建议** |

## 四、建议

改夹具（案 1）随下次 backup 域单走；实施时两红同笔翻＋`_live_article_count` 断言面顺手加值（现夹具喂假串时该函数返回 None 的分支也没被测试覆盖——真库夹具一并激活）。
