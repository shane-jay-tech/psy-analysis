# usage_logger 字体诊断兜底裁决材料

> 产出单：s930-23（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-38 遗留（usage_logger.py:249-255 只兜 ImportError；字体侧抛未列出异常 ⇒ 隐私导出当场炸，「让 bug 冒泡」的 intended 后果落在隐私导出路径，是否补兜底属行为改动）。
> 零改动；两调用点只读（app.py:634 面为在途邻域只读）。

## 一、现状实况

- `usage_logger.py:249-255`（导出包内 Environment diagnosis 段）：`try: from …environment_diagnosis import run_full_diagnosis; diag = run_full_diagnosis(); write(…json) except ImportError: pass`——**只兜 import 失败**；
- `environment_diagnosis.py` 自身兜底密度：**7 处 except**（每项子检查各自 ImportError 兜底，:68/:76/:83/:90…）——**组件内部的「单项失败」已被广泛兜住**；run_full_diagnosis 主体（平台版本段 :50-62）为无守卫直读代码；
- 另一调用点 `app.py:634`（侧栏诊断按钮）：**无任何 try**——诊断异常直接打到 Streamlit 页面（用户可见报错）＝冒泡哲学的另一形态；
- 失败面实算：run_full_diagnosis 内非兜底可抛点＝platform/python 版本段（几乎不可抛）＋各子项的**非 ImportError** 异常（如 `streamlit.__version__` 属性面、文件系统扫描面）——概率低但非零。

## 二、三案对比

| 案 | 行为 | 隐私导出路径影响 | 评 |
|---|---|---|---|
| **A 维持现状**（只兜 ImportError，让其余冒泡） | 诊断组件非 ImportError 异常 ⇒ 导出整体炸 | 导出失败=用户拿不到反馈包（数据无恙，重试可能同样炸） | 「让 bug 冒泡」纯度最高；但冒泡的**代价**落在最不该炸的隐私导出上 |
| **B 扩兜底**（except Exception ⇒ 写 `environment_diagnosis.json` 为 `{"error": …}` 占位＋导出继续） | 导出永不因诊断面炸；错误进包内可取证 | **反馈包反而更有用**（诊断失败的现场被抓进包里带回）——匿名包本来就是取证件 | 兜底会吞「让 bug 冒泡」的信号？——**不会**：错误内容原样进 error 字段，开发侧取证链完整 |
| **C 拆调用**（诊断移出导出函数，由调用方可选附加） | 重构面（导出签名/调用方两处） | 干净但工程面大 | 超出「补一层兜底」的最小问域 |

## 三、建议（不签口径）

1. **推荐 B 案**（最小问域内的行为改动）：`except ImportError: pass` 扩为 `except Exception as exc: (output_dir / "environment_diagnosis.json").write_text(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, …))`——**冒泡哲学与导出健壮性可以两全**：错误不吞（进包取证）、导出不炸；与矿源「让 bug 冒泡」的本意（可见、可归因）兼容——冒泡的终点从「炸掉导出」改为「进包可见」；
2. app.py:634 侧栏调用点维持无兜底（UI 面用户直视报错=合理冒泡终点），两调用点形态分化有据；
3. 实施时同笔补一例「诊断抛非 ImportError ⇒ 导出仍成功且 error 字段落盘」的看守（先红后绿同构）。
