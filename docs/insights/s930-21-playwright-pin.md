# playwright 钉法与浏览器族 36 例现状材料

> 产出单：s930-21（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-27 遗留（playwright 不在 lock ⇒ 36 例结论无版本依据；门禁化先裁钉法）。
> 零改动；实测含真浏览器跑。

## 一、现状实测（三向＋浏览器口径）

| 面 | 实测 | 备注 |
|---|---|---|
| playwright 版本（系统侧实装） | **1.62.0**（importlib.metadata） | 与矿源时点同版 |
| requirements-lock.txt | **ABSENT**（grep 零命中）——未钉实锤 | 与矿源一致 |
| pytest-playwright 插件 | ABSENT——e2e 件用**原生 `sync_playwright()`**（非 fixture 驱动） | 钉法只需考虑 playwright 本体 |
| 浏览器二进制 | `D:\ms-playwright\chromium-1234\chrome-win64\chrome.exe`（**PLAYWRIGHT_BROWSERS_PATH 自定义位置**，非默认 LOCALAPPDATA） | 浏览器安装口径＝环境变量+手工目录 |
| 收集/执行 | `--collect-only` **11 例**；**真跑 11 passed in 53.51s**（浏览器真起，健康） | 「36 例」为矿源时点的浏览器族总数——现盘 e2e 件 collect=11，族面已漂（漂移留痕，10 例差或为 s927-27 后的用例精简） |
| 与 s930-07 钉的关系 | 11 例只在**系统侧**可收集（playwright 只装系统侧）——collect-gap 钉已守「差集=11 全 e2e」 | 本单补「版本依据」面 |

## 二、钉法三案

| 案 | 内容 | 利 | 弊 |
|---|---|---|---|
| **案 1 进 lock** | requirements-lock.txt 加 `playwright==1.62.0` | 版本依据进主锁；三向对账自动覆盖 | .venv 装上后 **collect-gap 钉（s930-07）翻红**（差集 11→0）——钉的「环境形态变化」语义触发，届时把 e2e 件纳入正式收集面（删/改钉）；lock 体积+playwright 依赖链（greenlet 等） |
| **案 2 独立 e2e 锁**（requirements-e2e.txt 或 e2e 件头部 pins 注释＋测试内版本断言） | e2e 件自钉 `playwright==1.62.0`（importorskip 后 assert version）——版本漂移时 **skip 而非 silent 版本漂移** | 主 lock 干净；版本依据显式在 e2e 面 | 双锁文件面；assert version 形态要维护 |
| **案 3 不钉，维持 collect-gap 钉** | 版本无依据现状继续；只靠 s930-07 钉守「差集=11」 | 零动作 | 「结论无版本依据」持续——矿源点名的原病不治 |

## 三、浏览器安装口径（现状记录＋门禁化前置）

现口径＝`PLAYWRIGHT_BROWSERS_PATH=D:\ms-playwright`＋chromium-1234（版本随 playwright 1.62 的 revision）。门禁化前需人工定：①浏览器目录是否入运维文档（换机重建步骤）；②chromium revision 与 playwright 版本的绑定是否随案 1/2 的钉走（`playwright install` 会自动配对）。

## 四、建议

**案 2（e2e 面自钉）优先**：不动主 lock/不触发 s930-07 翻红链，版本依据显式化成本最低；实现＝e2e 件 importorskip 后加两行（`assert version('playwright') == '1.62.0'` 形态或宽松下限）；若主班偏好案 1，须同时裁 s930-07 钉的翻面（差集 11→0 的预期形态）——两案各自带一条连带面，**不建议案 3 维持**（原病不治）。
