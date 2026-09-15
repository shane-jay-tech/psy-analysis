# psy 测试目录结构与命名规范审计（s916-02，2026-09-16，只读）

- 口径：`tests/` 递归 `*.py`、排除 `__pycache__`；规范＝pytest.ini 钉死的 `testpaths = tests`＋`python_files = test_*.py`＋`python_functions = test_*`。

## 一、全量清单与计数（文件数附命令）

```
$ python -c "import pathlib; print(len([p for p in pathlib.Path('tests').rglob('*.py') if '__pycache__' not in p.parts]))"
186
```

- 总计 **186** 个 .py：**184 个 `test_*.py`** ＋ 2 个标准基础设施（`__init__.py`、`conftest.py`）。
- 目录形态：扁平单层（`tests/` 直下，无子目录测试模块）；`tests/fixtures/` 为数据夹具目录（golden_delivery/golden_stats 等数据文件），不含测试模块，不入计数口径。

## 二、非规范命名命中：**0 条**

```
$ python -c "...非 test_ 前缀且非 __init__/conftest 的 .py 清单..."
nonstd: []
```

## 三、跨目录重复命名：**0 条**

- 扁平结构下重复基名不可能跨目录出现；脚本核对 `dup basenames: []`（含同目录同名即文件系统本身禁止）。

## 四、疑似归类错误排查

- **autosave 家族**（任务书点名）：`test_autosave.py`／`test_autosave_acceptance_h912_06.py`／`test_autosave_bg.py`／`test_autosave_throttle.py` —— 4 件全部在 `tests/` 扁平根，与全仓其余测试同层，**无归类错误**；s914-39 归位对象 `tests/test_autosave_throttle.py` 在册（该单 2cbd750 已核「归位彻底」：桥测试目录 psy 真实导入精确匹配零命中）。
- 其余按名分类抽查（literature_review 9 件、llm 6 件、docx/export 家族 10+ 件、upstream 6 件、golden/e2e 家族）前缀语义一致，扁平结构下无「放错子目录」问题面。
- 仓内 `tests/` 之外无项目测试散落（`test_*.py` 仅存在于 `.venv/Lib/site-packages/` 第三方包内，被 `testpaths = tests` 天然排除）。

## 五、建议（不改文件的只读建议）

1. 维持现状：扁平＋`test_*.py`＋严格 markers（--strict-markers）结构健康，无需整改。
2. 可选（非必须）：若未来 tests 数量继续增长，可按家族（literature/llm/export/e2e）引入子目录＋同名 `__init__.py`；当前 186 件规模暂无必要。
3. `tests/fixtures/` 数据目录与测试模块分离的现行做法建议保持。

## 六、声明

未改名/移动任何测试文件；未改任何配置；不 push。审计为纯只读。
