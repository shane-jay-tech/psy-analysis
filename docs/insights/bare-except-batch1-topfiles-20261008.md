# 批#1 Top 热点件裸 except 判定（s1007-61，含两在途件只读判定）

- 日期：2026-10-08 ｜ 全量清点 CSV＝bare-except-census-571-20261008.csv（现值 569，锚 571−2 为期内同目录并发编辑漂移，复现命令同锚）

## src/ui/undergrad_wizard.py（porcelain M 在途，只读判定零改动，26 处）

- :128 [broad/可观测] `except Exception as exc:`
- :215 [broad/可观测] `except Exception as exc:`
- :284 [broad/可观测] `except Exception as exc:`
- :455 [broad/可观测] `except Exception as e:`
- :590 [broad/无声] `except Exception:`
- :603 [typed/可观测] `except TutorAPIError as e:`
- :606 [broad/可观测] `except Exception as e:`
- :853 [broad/可观测] `except Exception as e:`
- :982 [broad/可观测] `except Exception as exc:`
- :1086 [typed/可观测] `except ValueError as exc:`
- :1088 [broad/可观测] `except Exception as exc:`
- :1148 [broad/可观测] `except Exception as exc:`
- :1399 [broad/可观测] `except Exception as e:`
- :1514 [typed/可观测] `except ValueError as ve:`
- :1538 [broad/可观测] `except Exception as e:`
- :1658 [broad/可观测] `except Exception as e:`
- :1725 [typed/-] `except KaleidoMissingError:`
- :1728 [broad/无声] `except Exception:`
- :2060 [broad/可观测] `except Exception as exc:`
- :2101 [pass形/无声] `except Exception:`
- :2614 [broad/可观测] `except Exception as e:`
- :3041 [pass形/无声] `except Exception:`
- :3210 [broad/可观测] `except Exception as e:`
- :3278 [broad/可观测] `except Exception as exc:`
- :3571 [broad/可观测] `except Exception as e:`
- :3636 [broad/无声] `except Exception as exc:`

## src/ui/literature_review_panel.py（porcelain M 在途，只读判定零改动，14 处）

- :112 [broad/可观测] `except Exception as exc:`
- :129 [broad/可观测] `except Exception as exc:`
- :138 [broad/可观测] `except Exception as exc:`
- :161 [broad/可观测] `except Exception as exc:`
- :166 [broad/可观测] `except Exception as exc:`
- :171 [broad/可观测] `except Exception as exc:`
- :243 [pass形/无声] `except Exception:`
- :251 [broad/可观测] `except Exception as exc:  # s921-09：降级不再对用户隐身，补一条带 exc 摘要的提示`
- :326 [broad/可观测] `except Exception as exc:`
- :715 [broad/可观测] `except Exception as exc:`
- :770 [pass形/无声] `except Exception:`
- :786 [typed/可观测] `except (ValueError, TypeError) as exc:  # 只兜脏数字；非 dict 等编程错误照旧抛`
- :863 [broad/可观测] `except Exception as exc:`
- :940 [broad/可观测] `except Exception as exc:  # noqa: BLE001`

## project_panel.py（已收敛）

- 12 处：typed 6＋可观测 broad 2 注记不动；无声 4 处补 logger.debug（新增 logging），commit 见 result。
