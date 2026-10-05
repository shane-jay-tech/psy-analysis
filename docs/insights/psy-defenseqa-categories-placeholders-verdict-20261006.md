# defense_qa REQUIRED_CATEGORIES 4→6 与 placeholders 双口径裁决材料（s1002-41，只读）

- 承 s924-56 遗留 1/2 ＋ s924-57 遗留 5。

## 一、现值快照（python 直读）

| 面 | 现值 |
|---|---|
| REQUIRED_CATEGORIES（src/paper_writer/defense_qa.py:20） | `('method', 'data', 'effect', 'infer')` —— 4 类 |
| CATEGORY_FALLBACK_QA（defense_qa_kb.py:66）键集 | assumption/data/effect/infer/limit/method —— **6 键**（assumption/limit 两条兜底模板在册但引擎不取） |
| placeholders 声明面 | kb dataclass 字段（:44），逐模板声明；**执行面 `_safe_format` 按正文 `{}` 取键，声明零消费** |

## 二、案一：REQUIRED_CATEGORIES 4→6（纳入 assumption/limit）

- **行为影响面**：`_ensure_required_categories` 对每份手册按必备族补全 ⇒ 扩 6 类后**每份手册多出 assumption/limit 两节**（现状：仅当选题策略/数据面恰好触达才有）。清单分布变化＝全量手册 +2 节；纸面长度 +2 问。
- **红名单**：tests/test_defense_qa.py 的手册结构断言（节数/键集快照类，预估 1-3 例翻红需同批）；test_defense_qa_paper_aware.py 若钉「仅四节」同理。kb_data 件不受影响（:213-232 断言 placeholders 形状与表结构，与必备族无涉）。
- **前置**：assumption/limit 两条模板**措辞属人工域**（s924-56 遗留 2 明载：`n={n}` 与「分层随机抽样/纵向追踪」表述待复核）——**纳入必备族前须先过人工措辞复核**，否则把待定文案强制推进每份手册。
- **迁移顺序**：①人工复核两条文案（可留修订注）→ ②改 REQUIRED_CATEGORIES 一行 → ③同批改红名单断言 → ④paper_aware 件回归。

## 三、案二：placeholders 双口径统一（声明零消费 vs `_safe_format` 正文推导）

| 方向 | 做法 | 收益 | 代价 |
|---|---|---|---|
| **A 按声明校验注入** | `_safe_format` 渲染前比对「正文 {} 键集 ⊆ 声明 placeholders」，越界即 warn/error | 声明面从死文档变活闸：模板笔误（正文引用未声明键）在入库测试即炸（:350 `test_entry_declared_placeholders_are_substitutable` 已是半个校验——它正向验声明可代入，缺「正文⊆声明」反向） | 老模板正文/声明漂移会当场翻：红名单＝:350 族需要补反向断言，且 70 条含 placeholders 的模板可能有漂移历史（先跑一次全量对账再定 warn/error 档位） |
| **B 删声明留正文推导** | 删 placeholders 字段（:44/:76/:90/... 70 条逐条删） | 消灭双口径，单一事实源=正文 | 红名单大：:213-214/:228/:232/:346 四族断言全翻；且声明面有自文档价值（kb 浏览器/手册结构可读性）；70 条删除＝大 diff 低收益 |
- **建议 A**：先以 warn 档跑全量对账（只报告不拒载），漂移清单清零后升 error——红名单最小化且声明面活化为真闸。

## 四、零码改自证

python 读 defense_qa 两模块（只读 import）＋rg/读码；src/ 零触碰。
