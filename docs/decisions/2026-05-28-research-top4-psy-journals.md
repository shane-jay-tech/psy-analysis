# 中文心理学顶刊抓取可行性调研（v4.7 自学习模块前置）

**日期**：2026-05-28
**调研方**：Kimi K2.6（kimi-researcher 子代理）
**触发**：自学习模块需要确定 4 本顶刊（心理学报 / 心理科学进展 / 心理科学 / 管理世界）的可抓取路径
**注意**：Kimi 在本次执行中 Bash + WebSearch 被禁用，结论基于训练数据（截止 2025-08），关键事实需在 /implement 阶段实测验证。

---

## 决策表（4×5）

| 期刊 | 推荐路径 | 合规度 | 稳定性 | IO/HR/OB 覆盖 | 置信度 |
|---|---|---|---|---|---|
| 心理学报 | Crossref API 优先，官网 SSR 备用 | 中 | 高（SSR，结构稳定） | 低（基础心理为主） | 高 |
| 心理科学进展 | Crossref API 优先，官网 SSR 备用 | 中 | 高（同主办方，同结构） | 中（含应用/管理心理综述） | 高 |
| 心理科学 | 官网直爬（SSR），Crossref 弱 | 中 | 中（有改版历史） | 中高（含 IO/人格/组织） | 中 |
| 管理世界 | 官网直爬为主（CSR 难），Crossref 极弱 | 中低（ToS 严） | 低（CSR 疑似，反爬强） | 高（IO/HR/OB 核心来源） | 中低 |

---

## 各刊详细论据

### 1. 心理学报 (Acta Psychologica Sinica) — ISSN 0439-755X

- **官网**：`https://journal.psych.ac.cn/xlxb/CN/home`（中科院心理所维护）
- **渲染**：SSR，`requests` 直接拿，无需 JS
- **Crossref**：DOI 前缀 `10.3724`，API `https://api.crossref.org/works?filter=issn:0439-755X&sort=published&order=desc&rows=10` 直接返回 title/abstract/author/date/DOI，**完全免费，加 `mailto:` 参数进 Polite Pool**
- **HTML 模板**：华科出版社平台，class 命名规律（`.article-abstract` / `.article-keywords`）
- **合规**：robots.txt 未禁，每日 1 次属合理使用
- **推荐间隔**：3-5 秒，UA 带联系方式
- **IO 覆盖**：低（约 5%），实验 / 认知 / 神经为主
- **Semantic Scholar 覆盖率**：40-60%

### 2. 心理科学进展 (Advances in Psychological Science) — ISSN 1671-3710

- **官网**：`https://journal.psych.ac.cn/xlkxjz/CN/home`（同主办方，同模板）
- **渲染**：SSR
- **Crossref**：DOI 前缀同 `10.3724`，API 同样覆盖
- **IO 覆盖**：中（15-20%），是 4 本里**综述密度最高**的刊（含工业组织 / 管理心理 / HR 系统综述）
- **Semantic Scholar 覆盖率**：50-70%（英文摘要综述较多）
- **结论**：与心理学报共平台，可复用 fetcher 实现

### 3. 心理科学 (Journal of Psychological Science) — ISSN 1671-6981

- **官网**：`https://www.psysci.net`（中国心理学会，华东师范承办），备用 `http://jps.ecnu.edu.cn`
- **渲染**：SSR 为主，目录页有 jQuery 懒加载，但静态分页 URL 可绕过：`/CN/volumn/home?volId=XX`
- **关键点**：摘要 / 作者通常在 `<meta name="citation_abstract">` / `<meta name="citation_author">` 学术元标签中，**而不是可见正文 DOM**，需专门解析
- **Crossref 覆盖**：弱（早期论文未注册 DOI），不能依赖
- **改版历史**：2019、2022 两次大改版 → fetcher 必须加版本探针（连续 3 次失败发警告，不静默崩溃）
- **推荐间隔**：5-8 秒
- **IO 覆盖**：中高（20-25%），含人格 / 工作心理 / 组织行为

### 4. 管理世界 (Management World) — ISSN 1002-5502

- **官网**：`https://www.mzworld.com`
- **渲染**：**疑似 CSR 或混合**——首屏 SSR 但摘要 div 是空的，由异步 JS 填充，`curl` 拿不到摘要
- **Crossref**：极弱（DOI 注册滞后，2022 后改善但仍不全）
- **替代路径**：**CNKI 期刊目录页** `https://kns.cnki.net/kns8/defaultresult/index?korder=PY&PT=&cname=管理世界` 是 CNKI 核心来源期刊，需手动验证 SSR 可行性
- **合规**：官网 ToS 明确"未经授权不得批量下载"（商业性强，版权严格）；CNKI 同样有限制；个人低频摘要抓取学术界视为合理使用，但**风险最高的一本**
- **推荐间隔**：10-15 秒 + ±3s jitter
- **IO 覆盖**：高（IO/HR/OB 中文文献最核心来源，劳动经济学 / 组织管理 / HR 政策类高度集中）
- **结论**：先手动验证 CNKI 路径；不行就接受"管理世界暂不自动化，手动查"的降级方案

---

## 最小可行方案（MVP）

| 期刊 | 路径 | 请求模式 |
|---|---|---|
| 心理学报 | Crossref API | 每天 1 次，`?mailto=xxx`，rows=10 |
| 心理科学进展 | Crossref API | 同上，换 ISSN |
| 心理科学 | requests + BeautifulSoup（解析 `<meta>`） | 间隔 5s，UA + 联系方式，加版本探针 |
| 管理世界 | 待确认 CNKI SSR 可行性 | 若爬：间隔 10-15s + jitter；否则降级手动 |

---

## 仲裁结论（Opus）

1. **采纳 Kimi 的两层路径策略**：能用 Crossref 的优先 Crossref（合规零风险，结构最稳），实在不行才走防御性爬虫
2. **管理世界先做手动验证**：在 /implement 阶段开第一件事就是 `curl https://kns.cnki.net/...` 看 SSR 可抓性。如果不行，本期版本接受降级（手动每月 1 次粘贴管理世界目录链接，系统抽元数据），不卡其他三本上线
3. **fetcher 抽象层必须支持降级**：每本期刊的 fetcher 实现要独立，一本失败不影响其他三本（这点写进 /debate 待论证项）
4. **Kimi 信息时效性局限**：训练截止 2025-08，2026 年 ISSN 政策 / Crossref 中文摘要覆盖可能有变化，落地前必须实测
