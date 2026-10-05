# merged 回显目标标题：FeedStore get_title_by_kb_id 接口裁决材料（s1002-35，只读）

- 承 s920-04 遗留 1/3。

## 一、调用面清单（rg 现取）

| 位置 | 形态 | 现口径 |
|---|---|---|
| review_queue_ui.py:118 | \`review_success_message\` merged 支 | \`已合并《{name}》→ 目标 {target_kb_id}\`——**{name} 是本条目自己**的标题，目标只有裸 ID（s920-04 遗留 1 的回退形态） |
| review_queue_ui.py:202-212 | \`format_review_event\` | 六列（时间/审核人/操作/原状态/原因/备注）——**不带任何对象标题**（遗留 3 的未并轨口径） |
| review_queue_ui.py:169-172 | 合并入口 | \`st.text_input("合并目标 ID")\` 人工手输 ID ⇒ 拼写错误静默通过（validate 只查非空） |
| review_service.py:49-60/:74-80 | 落库面 | target_kb_id 原样入 decisions/events 两表，零标题解析 |

## 二、关键实体澄清（接口设计的地基）

**kb_id 不是 FeedStore.articles 的键**。盘点：articles 表主键是 \`article_id\`（int 自增）；\`target_kb_id\`（TEXT，migrations.py:65/:88）指向的"目标文献"实为**文献综述工作台的 LiteratureItem.key**（uuid，src/literature_review/models.py:43；merge 语义=把候选拢入综述库某条已有文献）。FeedStore 里没有 kb 库表——kb 条目活在 lr_state（session/快照）域，与 feed.sqlite 不同存储。

⇒ **get_title_by_kb_id 不该挂 FeedStore**（矿源命名误导：FeedStore 无此数据）。真身应在文献综述域：\`LiteratureReviewStore.get_title_by_key(key)\` 或经 \`get_literature_review_state\` 读 lr_state 的 \`literature_items\` 索引。

## 三、接口设计（真身版）

```python
def get_title_by_kb_id(lr_state: dict, kb_id: str) -> str | None:
    # O(n) 线性扫 literature_items；找不到/形状脏返回 None（调用方回退 ID）
```
- **两处消费并轨**：
  ① review_success_message：merged 支改为 \`目标 《{target_title or target_kb_id}》\`——拿到标题用《》、拿不到回退裸 ID（失败形态即矿源要求的回退，**零新增分支风险**）；
  ② format_review_event：加「目标」列 \`target_title or target_kb_id or "—"\`——历史事件带对象，与回显口径并轨。
- **缓存/索引影响**：O(n) 扫 lr_state 在个人库量级（<10⁴）无感；若未来建索引，lr_state 已有 matrix.cells 键索引可复用——**无需新表**。跨存储（feed.sqlite 事件表 ↔ lr_state）是既有架构事实，本接口是唯一需要的桥。

## 四、失败形态

| 形态 | 行为 |
|---|---|
| kb_id 无对应条目（手输错/条目已删） | 返回 None → 回显回退裸 ID（现状形态，不劣化） |
| lr_state 缺失/脏（四入口矩阵已钉） | 返回 None → 同上 |
| key 撞车（uuid 碰撞概率忽略） | 首个命中返回 |

## 五、零码改自证

rg/读码＋本档撰写；src/ 本班相关文件零触碰（git diff 名单均为他班在途件）。
