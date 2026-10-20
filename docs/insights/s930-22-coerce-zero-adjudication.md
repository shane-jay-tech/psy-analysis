# models.py 六处裸强转静默回退 0 裁决材料

> 产出单：s930-22（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-29 遗留（C 案红线：六处裸强转静默回退 0 属改数据统计口径，未实现）。
> **零码改动**。六处现点：models.py:69（year）/73（citation_count）/78（relevance_score）/89（from_crawled year）/93（from_crawled citation_count）/201（confidence）。

## 一、六处行为解剖（关键：`or 0` 的两段行为）

形状 `int(data.get("year") or 0)` 实际是**两段语义**：
1. **falsy 回退**（None/''/0/[] ⇒ or 短路取 0）＝「静默回退 0」本尊——缺失与真 0 在数据上不可区分；
2. **truthy 非数字抛错**（year="约 2019" ⇒ int() ValueError）＝**已被 s930-02 容错层捕获跳行**（本班落地）——即「C 案之外的脏值面」已有出口，C 案剩余裁决面收窄为**第 1 段**。

## 二、三案对比（含消费点实证）

| 案 | 行为 | 消费点影响（实测） | 评 |
|---|---|---|---|
| **甲 维持现状** | falsy ⇒ 0（缺失＝0） | `search.py:220` `cite_bonus = citation_count/1000`：缺失条目 bonus=0（不加分＝保守，方向可）；`:199` `tkey=(title, year)` 去重键：缺 year 的多条目若 title 亦近会互并（边角）；completeness :80 同款 or-0 形态自洽 | 零成本；「缺失与真 0 不可区分」的统计口径瑕疵保留 |
| **乙 缺失＝None**（字段可空+下游感知） | year/citation_count/confidence ⇒ None | **全部消费点需 None 感知**：cite_bonus 会 `None/1000` TypeError、sorted(None 比较) TypeError、completeness float(None) TypeError——**改动面=全部算术/排序消费点**（≥4 文件） | 统计口径最诚实，工程成本最高；C 案红线正是指此 |
| **丙 缺失哨兵＋数据状态标记** | 值保持 0，但对象加 `missing_fields: set`（from_dict 时登记 "year"/"citation_count"…） | 消费点零改动（0 值不变）；统计面可按 missing_fields 区分「真 0 vs 缺失」；UI 可标「年份未知」 | 新增字段＝schema 扩展（to_dict/from_dict 往返+golden 面随动），成本中 |

## 三、建议（不签口径）

1. **丙案是 C 案意图的最小实现**——「区分缺失与真 0」不必动数值语义（乙案），一个 missing_fields 集合即可让统计面按需感知；建议随下次 literature 模型版本（_version）一并走；
2. 甲案在「文献管理」域内可辩护（年份未知记 0 是 Zotero 等工具惯例），若主班认可现状，C 案销案的依据即本档 §一第 1 段（truthy 脏值已由 s930-02 出口，剩余面=纯缺失语义，惯例可依）；
3. `from_crawled`（:89/:93）的 getattr 面（:89/:93）与 from_dict 同构——任何改案须两函数同笔（六处一次改齐，勿分批制造第七种形态）。
