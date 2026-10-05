# result_card Logistic 族异常静默与 table_group 路由不同源裁决材料（s1002-46，只读）

- 承 s923-43 遗留三缺陷。**时点订正与现值实测**。

## 一、① Logistic 族异常面——**时点订正：生产形状实测不抛**

- **dict 形态**（矿源 `:727` 担心点）实测：result 为 dict 时 `getattr` 全 None ⇒ 走「缺少关键统计量」warning 分支，**不抛**（本班直跑实证：apa='' + warnings=['Logistic 回归结果缺少关键统计量']）。
- **对象形态**（SimpleNamespace 全字段）实测：构建成功 APA 正常。
- 中间态（`odds_ratios` 为 DataFrame 等「真值但非预期类型」）能否触发 `:727` 族格式化异常——现值代码已用 `getattr(result, "odds_ratios", None) or …` 短路链，DataFrame 真值进入后是**渲染段**消费，异常面在 apa_tables 而非卡构建。
- **两修法对照**（若真异常形态被实锤，红名单含 test_result_card_v2_methods.py:228-233 夹具——SimpleNamespace 形状两笔一体）：
  - 导出器侧：`_build_logistic_regression` 各渲染步加 try/except 转 warnings——改动面分散（多处），但异常就地可见；
  - 吞点侧：`app.py:1463-1467` 的静默 except 改「吞但记 logger.warning＋卡面置 error 标记」——改动面一处，所有 builder 族受益（与本仓 s1002-16 project_panel 横幅化同味）。**推荐吞点侧**。

## 二、② table_group 与 apa_tables 分派不同源——**实测确认**

- method_catalog.py:70-71：`ordinal_logistic`/`multinomial_logistic` 声明 `table="logistic_regression"`（有表路由声明）；
- apa_tables.py:870 实际分派只认 `("logistic_regression", "binary_logistic")` 两名 ⇒ ordinal/multinomial **0 张表实测**（getattr 无 build_fn，分派 elif 不含其名）。
- **同源化方向**：分派白名单改为从 method_catalog 反查（`table=` 字段驱动）——声明面单源，新增方法不再双处登记；或反向在 elif 补两名（最小改动，但双源保持）。**推荐前者**（与 s922-122 同族「声明面单源」结论一致）。红名单：apa_tables 现有分派快照例（若有）＋ordinal/multinomial 首次真出表的形态例（新增正向）。

## 三、③ KNOWN_ISSUES 8 行同步锁测试形状

照 result_card_registry_snapshot 双向锁形态：
- 正向：KNOWN_ISSUES 8 行逐行解析「文件:行＋缺陷短语」→ 断言代码侧现值仍在（锚点活性）；
- 反向：代码侧修复（异常面消失/表路由同源）→ 断言 KNOWN_ISSUES 对应行被移除（防「修了不销账」）。
- 形状＝参数化两向 × 8 行，落 tests/test_knownissues_sync_lock.py（命名照 s1002-26 跨名单一致门风格）。

## 四、零码改自证

python 直跑两形态复现＋rg 读码；src/ 零触碰。
