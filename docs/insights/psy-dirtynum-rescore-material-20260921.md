# psy 脏数字整页红 ＋ rescore 无 try：复现与最小防御草案（s922-05 材料单，2026-09-21）

> 只读材料单。来源：`s920-13 遗留②/③`（经 `outbox/s921-09-psy-hidden-degrade-warn.result.md` 转登记）。
> **不落生产码、不改任何统计数值/文献打分结论**；本档只给：现状复现命令 + 期望行为 + 触发面量化 + 可执行补丁草案。
> 施工与否属数据口径与主干改动，按 s920-13 原口径交日间拍板。
> 行号取工作树版；`app.py` 带他人在途 ` M`，本档涉及的 `src/literature_review/models.py`、`src/ui/literature_review_panel.py` **均为 tracked-clean**（不在在途清单里）。

## 一、两处病灶现状（复核结论：锚点全部有效，仅 1 处行号漂 1）

| # | 位置 | 事实 |
|---|---|---|
| ② | `src/literature_review/models.py:69 / :73 / :78`（`LiteratureItem.from_dict`）、`:89 / :93`（`from_crawled`）、`:201`（`GapAnalysis.from_dict`） | 6 处**裸强转** `int(...)` / `float(...)`，脏值即抛 `ValueError` |
| ②′ | `src/ui/literature_review_panel.py:757`（`_materialize_items`） | 列表推导，**一条坏数据使整表 0 条产出**（好条目一起被弃） |
| ②″ | `src/ui/literature_review_panel.py:126` | 主入口 `render_literature_review` 调 `:757`，**整个函数 0 个 `try`**（AST 实测）⇒ 页面起不来 |
| ③ | `src/ui/literature_review_panel.py:121-123` | `if st.session_state.get("_lr_pending_rescore"):` → `:122 _do_relevance_rescore(...)` → `:123 置 False`，**调用无 `try`**；`_do_relevance_rescore`（`:198-210`）内部也无 `try` |

**订正 s920-13 遗留 3 的失败形态**（原文：「开关已准备被置回 False……一次失败永久静默该次 rescore」）：
实测 `:123` 在 `:122` 抛出时**根本不会执行**（同一 `if` 块的下一行），故开关**留在 True** ⇒ 每次 rerun 都**重新调用打分器**，既每帧再抛一次（页面持续红），又每帧再烧一次 LLM 调用/积分。
「永久静默」应为「永久重试」。这条改变修复优先级：必须用 `finally` 落开关，而不是只加 `try`。

## 二、复现命令与期望

```bash
cd /d/code/psy-analysis
export PYTHONIOENCODING=utf-8

# ── ② 脏数字：逐字段直触 from_dict（现状实测）
python - <<'PY'
from src.literature_review.models import LiteratureItem
for probe in ['约 2019', '2019年', 'n/a', '', None, '12']:
    try:    print('year=%-8r -> OK  %r' % (probe, LiteratureItem.from_dict({'year': probe}).year))
    except Exception as e: print('year=%-8r -> %s: %s' % (probe, type(e).__name__, e))
for probe in ['约 12', '1,234', None, '7']:
    try:    print('citation=%-8r -> OK %r' % (probe, LiteratureItem.from_dict({'citation_count': probe}).citation_count))
    except Exception as e: print('citation=%-8r -> %s' % (type(e).__name__,))
for probe in ['约 0.75', '0.75 左右', None, '0.9']:
    try:    print('relevance=%-10r -> OK %r' % (probe, LiteratureItem.from_dict({'relevance_score': probe}).relevance_score))
    except Exception as e: print('relevance=%-10r -> %s' % (probe, type(e).__name__))
PY
```
现状输出（已跑，逐字）：`'约 2019'`/`'2019年'`/`'n/a'` → `ValueError: invalid literal for int() with base 10: ...`；
`''`/`None` → OK（`or 0` 兜住了空值，**只有非空脏串漏网**）；`'12'` → OK 12（数字串按原设计强转）；
`'1,234'` → `ValueError`；`'约 0.75'`/`'0.75 左右'` → `ValueError: could not convert string to float`。

```bash
# ── ②′ 助手层：一条坏数据拖垮整表（现状）
python - <<'PY'
import src.ui.literature_review_panel as lp
good = {'title': '好条目', 'year': 2019}
bad  = {'title': '脏条目', 'year': '约 2019'}
print(len(lp._materialize_items([good, bad, good])))
PY
```
现状：抛 `ValueError: invalid literal for int() with base 10: '约 2019'`，**3 条里 0 条产出**（前置的好条目一并被弃）。
**期望**：2 条产出 + 1 条面向用户的告警（点名是哪条、坏在哪个字段）。

```bash
# ── ③ rescore 无 try：真实调用面，桩掉打分器（零网络、零 LLM、零积分）
python - <<'PY'
import types, src.ui.literature_review_panel as lp
fake = types.SimpleNamespace(success=lambda *a, **k: None, warning=lambda *a, **k: None, error=lambda *a, **k: None)
orig_st, orig = lp.st, lp.rescore_existing_items
lp.st, lp.rescore_existing_items = fake, (lambda *a, **k: (_ for _ in ()).throw(RuntimeError('打分器炸了')))
try:
    lp._do_relevance_rescore({'research_question': 'q', 'candidate_vars': {}}, {'literature_items': [{'title': 'a'}]})
    print('NO RAISE（意外）')
except Exception as e:
    print('rescore 逃逸 ->', type(e).__name__ + ':', e)
finally:
    lp.st, lp.rescore_existing_items = orig_st, orig
print('空文献短路（零打分器调用）:',
      lp._do_relevance_rescore({}, {'literature_items': []}) is None,
      lp._do_relevance_rescore({}, {'literature_items': None}) is None)
PY
```
现状：`RuntimeError: 打分器炸了（模拟 LLM/网络失败）` 一路逃到主入口（`render_literature_review` 全函数 0 个 `try`）；
空文献路径 `:201-202` 正常 `return`，打分器一次都不调（与 s920-13 的 ⑥ 钉桩一致）。
**期望**：失败降级为一条 `st.error` + 保留原打分 + **开关必定落回 False**（`finally`），不整页红、不逐帧重烧。

```bash
# 主入口无保护（AST 实测，非人眼扫）
python - <<'PY'
import ast, pathlib
src = pathlib.Path('src/ui/literature_review_panel.py').read_text(encoding='utf-8')
fn = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == 'render_literature_review'][0]
trys = [t for t in ast.walk(fn) if isinstance(t, ast.Try)]
print('render_literature_review 内 try 块数:', len(trys))
for t in ast.walk(fn):
    if isinstance(t, ast.Call) and getattr(t.func, 'id', '') in ('_materialize_items', '_do_relevance_rescore'):
        print('  调用', t.func.id, '@', t.lineno, '被 try 包住?', any(t2.lineno <= t.lineno <= (t2.end_lineno or 0) for t2 in trys))
PY
```
现状输出：`try 块数: 0`、`调用 _do_relevance_rescore @ 122 被 try 包住? False`、`调用 _materialize_items @ 126 被 try 包住? False`。

## 三、触发面量化

| 维度 | 实测 |
|---|---|
| 裸强转点 | **6 处**（`models.py:69/73/78` `LiteratureItem.from_dict`；`:89/93` `from_crawled`；`:201` `GapAnalysis.from_dict`） |
| 「一条坏数据拖垮整表」的同构点 | **3 处**：`literature_review_panel.py:757`（本单目标）、`src/literature_review/notes.py:157`（`[ReadingNote.from_dict(d) for d in data if isinstance(d, dict)]`，同列表推导、同样无 try，它多的一层宽容只过滤非 dict）、`src/literature_review/search.py:230`（`[LiteratureItem.from_dict(d) for d in items_dict]`，爬虫/检索结果的直转面） |
| 脏值入口面（谁会喂进非数字串） | ①`src/literature_review/search.py:230` 爬虫/检索结果直转；②工作区恢复 `src/utils/workspace.py:373`（快照读回，历史版本或用户手改 JSON 均可带脏）；③批注导入 `src/literature_review/review_import.py:138-145` 写回 `literature_items`；④向导读取 `src/ui/undergrad_wizard.py:3595` 走同一列表 |
| **本仓现存数据里的脏值观测** | **0 条**。`data/` 与 `demo_projects/` 下全部 JSON 递归扫描，`literature_items` 出现 0 次（字段类型分布为空）⇒ 触发面是**外部输入面与恢复面**，不是存量数据；即「用户项目 JSON / 爬虫返回值」是唯一喂入口 |
| 影响面（一次命中后果） | 整个「文献综述」面板不可用（`:126` 在渲染主干上，非分支）；同一次会话内只要该条数据仍在 `lr_state`，**每次 rerun 都红**（无自愈路径） |
| ③ 的额外代价 | 打分器是 LLM 调用面（`rescore_existing_items`）⇒ 开关不落 ⇒ 每次 rerun 重复计费/重复网络，且用户看不到「失败」字样只看到红页 |

## 四、最小防御草案（三块，任选组合；**本档未落任何生产码**）

```python
# A) 助手侧宽容：坏条跳过并点名（保住其余条目可渲染）—— 改 src/ui/literature_review_panel.py:755-757
def _materialize_items(items_dict_list: List[Dict[str, Any]]) -> List[LiteratureItem]:
    """从 session_state 的 dict 列表实例化 LiteratureItem；单条脏值不再拖垮整表（s920-13 遗留②）。"""
    out, bad = [], []
    for d in items_dict_list or []:
        try:
            out.append(LiteratureItem.from_dict(d))
        except (ValueError, TypeError) as exc:
            bad.append((str(d.get("title") or d.get("key") or "?"), str(exc)))
    if bad:
        st.warning(
            f"⚠️ {len(bad)} 条文献的年份/引用数/相关度字段无法解析，本已跳过：「"
            + "、".join(t for t, _ in bad[:3]) + ("…" if len(bad) > 3 else "") + "」。"
            "如需修复请在项目文件里把该字段改成纯数字。"
        )
    return out
```

```python
# B) 主入口 rescore：try + 必定落开关（:120-123）—— 关键是 finally，不是只加 try
    if st.session_state.get("_lr_pending_rescore"):
        try:
            _do_relevance_rescore(upstream, lr_state)
        except Exception as exc:                      # 打分器是外部调用面（LLM/网络）
            st.error(f"文献相关性重算失败：{exc}。已保留原有打分，可稍后再试。")
        finally:
            st.session_state["_lr_pending_rescore"] = False
```

```python
# C) 模型侧宽容（与 A 互斥的另一种口径，涉数据语义，须日间拍板）：
#    models.py 增加 _coerce_int/_coerce_float，非数字串回退默认值并把原串留在 notes 里
def _coerce_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default
# 调用点：:69 year=_coerce_int(data.get("year"))，:73、:89、:93 同；:78/:201 用 _coerce_float
```
**A 与 C 是两种语义**：A 保留「这条数据是坏的、用户看得见」，C 静默回退 0（把「约 2019」变成 0，**属于改数据统计口径**——红线域，未替 owner 决定）。
建议 A＋B 同批落（都不动数值），C 单独议。

## 五、配套测试点（施工时应先写，三条都可判真假）

1. `_materialize_items([好, 脏, 好])` → 返 2 条 + 一次 `st.warning`；改前必红（现状抛 `ValueError`），有鉴别力。
2. `_materialize_items([脏, 脏])` → 返 `[]` + 一条告警，页面走「暂无文献」空态而非红页。
3. `rescore_existing_items` 抛错时：主入口不抛、`st.error` 一次、**`_lr_pending_rescore` 必为 False**（`finally` 的证据；只加 `try` 不加 `finally` 的写法此例必红）。

## 六、口径边界（本单刻意不做）

- 不给任何文献打分/相关度/完成度数值下结论，也不修任何数值（红线）；两处复现都在内存里跑，**未写任何项目文件、未触发任何 LLM/网络**。
- 不动 `tests/test_literature_review_panel_helpers.py` 里 s920-10 系的 ④/⑥/⑦ 钉桩（现 18 例按 `tests/test_literature_review_panel_helpers.py` 原口径绿）；A/B 一旦施工，④ 那枚「只钉不改」的注释需按惯例翻正。
- `notes.py:157` 的同构列表推导本单**只登记不修**（同病灶，另有 search.py:230 共 3 处，见触发表；建议与 A 同批，否则「文献列表能容错、笔记/检索列表仍整表弃」是新的不一致）。
