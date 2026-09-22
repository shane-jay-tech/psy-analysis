"""psy 导出隐私预检 PII 假阴性探针集（s922-124）。

**本件所有样本一律合成，不含任何真实个人信息**：域名只用 RFC 2606 保留的 `example.edu.cn`，
号码只用 010/021 交换局下的 1234xxxx / 65432100 一类顺子，身份证样式为 110101+19900307+551X
的教学用假号，姓名位一律留空或写"被试"。`test_every_sample_is_synthetic_by_construction`
把这条声明变成可机检断言，而不是一句 docstring。

🔴 派单前提否证（按实况扩面，未改任何检测规则）
1. 任务书说"过 `_PII_PATTERNS` 现有检测"。实测 `src/utils/guardrails.py:348` 的 `_PII_PATTERNS`
   是**列名关键词三档分级**，`detect_pii_columns` 只遍历 `df.columns`、**从不看单元格值**
   （`guardrails.py:371-391`）。所以"座机加分机／微信号／住址门牌／病历号"写在内容里时，
   `_PII_PATTERNS` 结构上不可能检出——不是漏检，是不归它管。
2. `KNOWN_ISSUES.md:150` 那句"导出前隐私预检可有假阴性"的**真实宿主**是
   `src/utils/privacy_ethics.py:59` 的 `_PATTERNS`（7 条正则）→ `scan_text_for_sensitive`
   → `export_pre_check`（`src/ui/export_gate.py:95`、`app.py:2370` 两处调用）。
   ⇒ 本单把三面都量化：S1 列名分级、S2 值级正则、S3 导出门禁 safe 判定。
3. `export_pre_check` 的 `safe` **只看 high**（`privacy_ethics.py:190`）⇒ medium（email/password）
   检出也照样放行。这属"检出但不拦"的第三类，本件单列钉桩。

基线（先命令后数字，探针件 `tmp/s922-124_pii_probe.py` 跑完即删）
```
$ PYTHONUTF8=1 PYTHONPATH=. .venv/Scripts/python.exe tmp/s922-124_pii_probe.py
### 值级 S2 scan_text_for_sensitive  检出 9 / 漏检 16  （共 25）
### 列名 S1 detect_pii_columns      检出 10 / 漏检 10  （共 20）
### 门禁 S3 有发现且仍判 safe=True 的条数：2 / 有发现总数 9
```
本件只锁下限（已检出项不许静默退化）＋登记漏检面（xfail 不阻断），**不替 owner 扩规则**。
日后 owner 补了规则，xfail 会转 XPASS（`strict=False` ⇒ 不红），那就是"覆盖面变宽"的信号；
而已检出项一旦不再被检出，本件当场红。

📌 pd01 / 20260922-1830（2026-09-22 18:2x 用户拍板后落的两处收紧，上面的历史基线读数**不回改**）
- 上面第 3 条（`safe` 只看 high ⇒ email／password 放行）**已改**：`export_pre_check` 现在
  除 high 全档外还拦 `_BLOCKING_MEDIUM_TYPES = ("email","password")`。第 3 条的桩位随之从
  "登记现状"翻成"钉住新判据"（`test_export_gate_now_blocks_email_and_password_medium`）。
- 上面第 2 条点名的"座机加分机"分机号残留**已修**（`_PATTERNS["landline"]` 的替换段吃到分机号）。
- 值级 25 / 列名 20 两组**探针条数与检测面不变**（本单没加检测规则，只动脱敏覆盖与门禁判据），
  所以 `test_probe_inventory_matches_the_recorded_baseline_counts` 与 26 条 xfail 仍逐条在册。
"""
from __future__ import annotations

import re

import pandas as pd
import pytest

from src.utils import guardrails, privacy_ethics
from src.utils.guardrails import detect_pii_columns
from src.utils.privacy_ethics import (
    export_pre_check,
    redact_sensitive_text,
    scan_text_for_sensitive,
)

# ══════════════════ S2 值级：已检出 9 条（锁下限） ══════════════════

DETECTED_VALUE_PROBES = [
    ("身份证18位无分隔", "被试 11010119900307551X 已完成", "id_card", "被试 [REDACTED_ID_CARD] 已完成"),
    ("手机11位裸写", "联系 13800138000", "phone", "联系 [REDACTED_PHONE]"),
    ("座机带标签", "电话：010-12345678", "landline", "[REDACTED_LANDLINE]"),
    ("座机加分机", "座机：010-12345678 转 802", "landline", "[REDACTED_LANDLINE]"),
    ("邮箱", "邮箱 student.sample01@example.edu.cn", "email", "邮箱 [REDACTED_EMAIL]"),
    ("微信带中文标签", "微信：liulab_2023", "messenger", "[REDACTED_MESSENGER]"),
    ("QQ号", "QQ：123456789", "messenger", "[REDACTED_MESSENGER]"),
    ("api_key样式sk", "key sk-abcdefghijklmnopqrstuvwx", "api_key", "key [REDACTED_API_KEY]"),
    ("password赋值样式", "pwd=abc12345", "password", "[REDACTED_PASSWORD]"),
]

# ══════════════════ S2 值级：当前漏检 16 条（登记，不扩规则） ══════════════════

MISSED_VALUE_PROBES = [
    # label, sample, 为什么算敏感面
    ("身份证18位空格分组", "证件 110101 19900307 551X", "分组书写即可绕开 (?<!\\d)\\d{17}[\\dXx]"),
    ("身份证15位旧式", "证件 110101900307551", "位数固定 18，15 位老号不在面内"),
    ("手机带+86前缀", "联系 +8613800138000", "前一位是数字 6 ⇒ (?<!\\d) 直接把整串否掉"),
    ("手机分段加连字符", "联系 138-0013-8000", "只认连续 11 位"),
    ("座机无标签裸号", "办公 021-65432100", "landline 要求「电话/座机/tel」前缀（防误伤的既有设计）"),
    ("座机空格分组", "座机：010 1234 5678", "只认 0xx-xxxxxxxx 与 0xxx-xxxxxxxx 两种连字符形态"),
    ("WeChat英文标签隔词", "WeChat ID: liulab_2023", "标签与号之间夹了 ID ⇒ 中间词切断匹配"),
    ("vx黑话", "vx: liulab_2023", "'vx' 不在 (微信|wechat|qq) 词表"),
    ("住址到门牌", "家住 海淀区中关村大街5号院3号楼2单元501", "值级根本没有地址类规则"),
    ("学号纯数字", "学号 20231234567", "11 位且以 2 开头，phone 要求 1[3-9] ⇒ 两头不靠"),
    ("学号字母前缀", "S2023001234", "无学籍号样式规则"),
    ("工号字母数字", "工号 E20230042", "工号只在 S1 列名面，值面不认"),
    ("病历号样式", "病历号 MRN-2023-0042", "MRN 样式零覆盖（合成假号，非真实病历）"),
    ("被试编号P001", "被试编号 P001", "弱标识：现状不拦也许可接受，先登记"),
    ("出生日期", "出生日期 1990-03-07", "准直接标识符，值面无规则"),
    ("银行卡19位", "卡号 6222021234567890123", "长数字串不被任何规则认领"),
]

# ══════════════════ S1 列名面：已检出 10 / 漏检 10 ══════════════════

DETECTED_COLUMN_PROBES = [
    ("手机号", "high"), ("家庭住址", "high"), ("微信", "high"), ("身份证", "high"),
    ("邮箱", "high"), ("姓名", "medium"), ("学号", "medium"), ("工号", "medium"),
    ("员工号", "medium"), ("subject_id", "low"),
]

MISSED_COLUMN_PROBES = [
    ("学籍号", "medium", "'学号' 不匹配 '学籍号'（子串方向反了）"),
    ("证件号", "high", "词表只有 身份证/身份号/id_card，'证件号' 不在内"),
    ("家庭地址", "high", "词表有 '住址'/'address'，'家庭地址' 两头都不含"),
    ("通讯方式", "high", "无'通讯'类词"),
    ("联系方式", "high", "同上，中文交付表里极常见"),
    ("病历号", "medium", "无医疗标识符词表（合成假样，仅测样式）"),
    ("student_number", "medium", "英文侧只有 student_id，'number' 不匹配"),
    ("sno", "medium", "常见缩写，未收录"),
    ("job_no", "medium", "英文侧只有 employee_id"),
    ("备注", "medium", "自由文本列名不认——PII 常藏这里（值面靠 S2，但 S2 只认 7 类）"),
]

ALL_VALUE_LABELS = [label for label, *_ in DETECTED_VALUE_PROBES] + \
                   [label for label, _, _ in MISSED_VALUE_PROBES]


def _column_bucket(col: str) -> str | None:
    result = detect_pii_columns(pd.DataFrame({col: ["x"], "得分": [1.0]}))
    return next((s for s in ("high", "medium", "low") if col in result[s]), None)


# ══════════════════ 一、基线台账（数字与探针命令逐位对齐） ══════════════════


def test_probe_inventory_matches_the_recorded_baseline_counts():
    """判据 3 落进代码：25=9+16（值级）、20=10+10（列名），标签不得重复或缺项。"""
    assert len(ALL_VALUE_LABELS) == 25, len(ALL_VALUE_LABELS)
    assert len(set(ALL_VALUE_LABELS)) == 25, "标签重名会让 parametrize 覆盖"
    assert (len(DETECTED_VALUE_PROBES), len(MISSED_VALUE_PROBES)) == (9, 16)
    assert (len(DETECTED_COLUMN_PROBES), len(MISSED_COLUMN_PROBES)) == (10, 10)


# ══════════════════ 二、S2 值级：已检出项锁下限 ══════════════════


@pytest.mark.parametrize(
    "label,sample,pattern,redacted_expectation",
    DETECTED_VALUE_PROBES,
    ids=[p[0] for p in DETECTED_VALUE_PROBES],
)
def test_detected_value_probes_still_fire_and_are_actually_redacted(label, sample, pattern,
                                                                    redacted_expectation):
    """检出 ⇒ ① 命中类型正确 ② 真脱敏（原样从文本消失）③ 门禁 severity 对得上。"""
    findings = scan_text_for_sensitive(sample, source="probe")

    assert {f.pattern_type for f in findings} == {pattern}, f"{label} 的认领类型变了：{findings}"
    assert all(f.severity in ("high", "medium") for f in findings)
    text, counts = redact_sensitive_text(sample)
    assert text == redacted_expectation, f"{label} 脱敏产物漂移：{text!r}"
    assert counts == {pattern: 1}
    raw_digits = re.sub(r"\D", "", sample)
    if len(raw_digits) >= 6:                     # api_key 那类纯字母样本没有数字面可比
        assert raw_digits[:6] not in text, f"{label} 脱敏后仍留着前 6 位数字：{text!r}"


#: pd01 前这条叫 `test_landline_extension_survives_redaction_registered_leak`（登记式现状钉桩：
#: 断言 "转 802" **留在**脱敏文本里）。判据已按 2026-09-22 18:2x 拍板收紧，桩位随之翻正为真断言。
LANDLINE_EXTENSION_FORMS = [
    "座机：010-12345678 转 802",
    "座机：010-12345678 转802",
    "座机：010-12345678 分机 802",
    "座机：010-12345678（分机号 802）",
    "电话：010-12345678 ext. 802",
    "电话：010-12345678#802",
    "Telephone: 010-12345678 extension 802",
]


@pytest.mark.parametrize("sample", LANDLINE_EXTENSION_FORMS,
                         ids=[f"e{i}" for i in range(len(LANDLINE_EXTENSION_FORMS))])
def test_landline_extension_is_redacted_together_with_the_number(sample):
    """收紧面①：座机后挂的分机号不许活到导出文本里（旧行为只摘主体号，留 "转 802"）。"""
    text, counts = redact_sensitive_text(sample)

    assert counts == {"landline": 1}, f"分机形态 {sample!r} 改变了认领类型或条数"
    assert "802" not in text, f"分机号残留：{text!r}"
    assert "010-12345678" not in text                              # 主体照旧被摘
    assert text.strip() == "[REDACTED_LANDLINE]"


@pytest.mark.parametrize("sample, keep", [
    ("办公 021-65432100 8023", "8023"),          # 无「转/分机/ext」关键词 ⇒ 后挂数字**不许**被顺手吞掉
    ("座机：010-12345678 备注 20231234567", "20231234567"),   # 同理：非分机词不吞
])
def test_landline_extension_group_does_not_swallow_unrelated_trailing_digits(sample, keep):
    """收紧面②的反向护栏：只多盖"确实写了转/分机/ext"的那一段，别把整句尾巴都吃掉
    （否则 `test_detected_value_probes...` 那类"锁脱敏产物逐字"的探针会失去判别力）。"""
    text, _counts = redact_sensitive_text(sample)

    assert keep in text, f"{keep} 被误吞：{text!r}"


def test_landline_fix_did_not_loosen_any_registered_miss():
    """只许收紧不许放宽的可机检面：两条已登记的座机漏检（无标签裸号／空格分组）**必须仍然漏**——
    若哪天有人把正则放宽到认领它们，这条会红，逼一次"这是不是又把误伤面放大了"的复核。"""
    landline_misses = [p for p in MISSED_VALUE_PROBES if p[0].startswith("座机")]

    assert len(landline_misses) == 2, [p[0] for p in landline_misses]
    for label, sample, _why in landline_misses:
        assert not scan_text_for_sensitive(sample, source="probe"), (
            f"{label} 现在被认成 landline：放宽了匹配面，请复核误伤风险后再改本桩"
        )


# ══════════════════ 三、S2 值级：漏检项（xfail 登记，防静默退化） ══════════════════


@pytest.mark.xfail(strict=False, reason="KNOWN_ISSUES.md:150 假阴性面，owner 扩规则前不阻断")
@pytest.mark.parametrize(
    "label,sample,why",
    MISSED_VALUE_PROBES,
    ids=[p[0] for p in MISSED_VALUE_PROBES],
)
def test_missed_value_probes_should_be_detected_one_day(label, sample, why):
    """今天必红（xfail）：现状不检出。owner 补规则后转 XPASS＝覆盖面变宽的信号。"""
    findings = scan_text_for_sensitive(sample, source="probe")

    assert findings, f"（{why}）仍无人认领：{sample!r}"


@pytest.mark.parametrize(
    "label,sample,why",
    MISSED_VALUE_PROBES,
    ids=[p[0] for p in MISSED_VALUE_PROBES],
)
def test_missed_value_probes_are_reported_by_gate_as_clean(label, sample, why):
    """现状可断言的一面：漏检项过导出预检 ⇒ safe=True（假阴性的端到端后果）。"""
    verdict = export_pre_check(sample, source="probe")

    assert verdict["safe"] is True, f"{label} 现状其实会被拦，登记表要更正：{verdict}"
    assert verdict["total_count"] == 0


# ══════════════════ 四、S1 列名面 ══════════════════


@pytest.mark.parametrize("col,bucket", DETECTED_COLUMN_PROBES, ids=[p[0] for p in DETECTED_COLUMN_PROBES])
def test_detected_column_probes_keep_their_severity_bucket(col, bucket):
    assert _column_bucket(col) == bucket, f"列名 {col} 的档位从 {bucket} 变了"


@pytest.mark.xfail(strict=False, reason="列名关键词面未覆盖（S1 假阴性），只登记不扩词表")
@pytest.mark.parametrize("col,expected_bucket,why", MISSED_COLUMN_PROBES,
                         ids=[p[0] for p in MISSED_COLUMN_PROBES])
def test_missed_column_probes_are_unclassified_today(col, expected_bucket, why):
    assert _column_bucket(col) == expected_bucket, f"{col}：{why}"


def test_column_surface_never_looks_at_cell_values_by_design():
    """🔴 前提否证 1 的证据面：值里塞满手机号，只要列名中性，S1 依旧报"无 PII"。

    这就是任务书把"座机/微信/门牌"交给 `_PII_PATTERNS` 检不出的结构性原因（不归它管）。
    """
    df = pd.DataFrame({"备注": ["手机 13800138000，微信：liulab_2023", "普通说明"]})

    assert detect_pii_columns(df)["any"] is False
    # 同一张表的值级面（S2）能认两条 ⇒ 两面的分工不是笔误
    assert len(scan_text_for_sensitive(df["备注"].iloc[0], source="probe")) == 2


# ══════════════════ 五、S3 门禁 severity 语义 ══════════════════


def test_export_gate_now_blocks_email_and_password_medium():
    """pd01 判据（20260922-18:2x 拍板）：`safe` 从"只看 high"扩到含 email／password 档。

    改前这条叫 `test_export_gate_passes_medium_severity_findings`，断言的是
    `total_count==1 / high_count==0 / safe is True`（即"检出了但照样放行"）——
    本条把它整个翻正，并顺带钉住新增的两个计数键。
    """
    email = export_pre_check("邮箱 student.sample01@example.edu.cn", source="probe")
    password = export_pre_check("pwd=abc12345", source="probe")

    for verdict, ptype in ((email, "email"), (password, "password")):
        assert verdict["total_count"] == 1 and verdict["high_count"] == 0    # 档位本身没动（仍是 medium）
        assert verdict["medium_count"] == 1                                  # 此前该键根本不返回
        assert verdict["blocking_count"] == 1
        assert verdict["safe"] is False, f"{ptype} 仍被放行，扩判据没生效：{verdict}"
        assert [f.pattern_type for f in verdict["findings"]] == [ptype]


def test_export_gate_return_shape_is_the_six_keys_consumers_read():
    """`app.py:2370` 与 `zip_exporter.py:252-253` 是按键名 `.get(...)` 读的（读不到就静默取 0），
    所以键集合必须钉住：少一个键不会报错，只会把交付摘要里的中风险数写成 0。"""
    verdict = export_pre_check("联系 13800138000 邮箱 a.b@example.edu.cn", source="probe")

    assert set(verdict) == {"safe", "findings", "high_count", "medium_count",
                            "blocking_count", "total_count"}
    assert (verdict["high_count"], verdict["medium_count"], verdict["blocking_count"],
            verdict["total_count"], verdict["safe"]) == (1, 1, 2, 2, False)


def test_export_gate_tightening_is_monotone_never_looser():
    """「只许收紧」的可机检形式：任取样本，旧判据（只看 high）判拦的，新判据必须也判拦。

    pd01 续作修正（psy5）：psy3 原版把蕴含方向写反了——它断言的是
    `old_safe is False or safe is False`，即"每个样本至少被一版判拦"，于是任何一条
    **两版都放行**的漏检探针（如"证件 110101 19900307 551X"）都会让它当场红。
    真判据是 `old_safe or not new_safe`（旧拦 ⇒ 新必拦），另补一条"确实变严了"的判别面，
    免得这条退化成"门禁永远放行"的假绿。
    """
    samples = [p[1] for p in DETECTED_VALUE_PROBES] + [p[1] for p in MISSED_VALUE_PROBES]
    newly_blocked = []

    for sample in samples:
        verdict = export_pre_check(sample, source="probe")
        old_safe = verdict["high_count"] == 0
        assert old_safe or verdict["safe"] is False, (
            f"判据放宽了：{sample!r} 旧拦新放"
        )
        if old_safe and verdict["safe"] is False:
            newly_blocked.append(sample)

    assert newly_blocked == ["邮箱 student.sample01@example.edu.cn", "pwd=abc12345"], (
        f"扩判据应恰好把 email／password 两档从放行转为拦下，实得 {newly_blocked}"
    )


def test_export_gate_blocks_on_a_single_high_hit():
    """对照面，证明上一条不是"门禁永远放行"的假阳：high 命中必拦。"""
    verdict = export_pre_check("联系 13800138000", source="probe")

    assert verdict["safe"] is False and verdict["high_count"] == 1


# ══════════════════ 六、判别力自证（注入法，两面向） ══════════════════


@pytest.mark.parametrize("pattern", sorted({p[2] for p in DETECTED_VALUE_PROBES}))
def test_removing_a_single_value_rule_silences_exactly_its_probes(pattern, monkeypatch):
    """把某条正则从 _PATTERNS 里摘掉 ⇒ 认领它的探针必须翻红 ⇒ 证明探针真的挂在那条规则上。

    不这么做的话"检出 9 条"可能只是断言写空了。摘的是 monkeypatch 的进程内替身，
    模块真身与 src/ 一个字节都不动。
    """
    shrunken = {k: v for k, v in privacy_ethics._PATTERNS.items() if k != pattern}
    monkeypatch.setattr(privacy_ethics, "_PATTERNS", shrunken)

    owners = [p for p in DETECTED_VALUE_PROBES if p[2] == pattern]
    assert owners
    for label, sample, _pattern, _expectation in owners:
        assert scan_text_for_sensitive(sample, source="probe") == [], (
            f"摘掉 {pattern} 后探针 {label} 仍被检出 ⇒ 断言没有针对性"
        )


def test_emptying_the_column_keyword_table_silences_the_column_surface(monkeypatch):
    """注入法（S1 面）：关键词清空 ⇒ 十根探针全哑 ⇒ 说明它们各自咬住了词表项。"""
    emptied = {k: {**v, "keywords": []} for k, v in guardrails._PII_PATTERNS.items()}
    monkeypatch.setattr(guardrails, "_PII_PATTERNS", emptied)

    for col, _bucket in DETECTED_COLUMN_PROBES:
        assert _column_bucket(col) is None, f"摘掉词表后 {col} 仍被认成 PII ⇒ 用例是假绿"


def test_value_rule_count_and_names_are_pinned_so_extensions_are_visible():
    """检测面本身只有 7 条时才算得出"检出 9/漏检 16"；owner 加规则时这条先红，逼一次复核。"""
    assert sorted(privacy_ethics._PATTERNS) == [
        "api_key", "email", "id_card", "landline", "messenger", "password", "phone",
    ], "值级正则清单变了：本件的基线两数要重跑探针再记"


# ══════════════════ 七、合成性可机检（判据 2） ══════════════════


#: 本件出现过的全部"像号码"的合成串（长优先剥离，剥完还不干净就是混进了真号码）
SYNTHETIC_NUMBER_TOKENS = [
    "11010119900307551X", "6222021234567890123", "20231234567", "2023001234", "13800138000",
    "110101900307551", "123456789", "12345678", "65432100", "19900307", "110101",
    "20230042", "abc12345", "12345",
]


def test_every_sample_is_synthetic_by_construction():
    """docstring 里那句"无真实个人信息"变成断言：域名/号码/标识符都在保留段内。"""
    samples = [p[1] for p in DETECTED_VALUE_PROBES] + [p[1] for p in MISSED_VALUE_PROBES]

    domains = {m for s in samples for m in re.findall(r"@([A-Za-z0-9.-]+)", s)}
    assert domains <= {"example.edu.cn"}, f"出现了非保留域名：{domains}"

    for sample in samples:
        stripped = sample
        for token in sorted(SYNTHETIC_NUMBER_TOKENS, key=len, reverse=True):
            stripped = stripped.replace(token, "#")
        leftover = re.findall(r"\d{5,}", stripped)
        assert not leftover, f"剥掉合成白名单后仍残留 {leftover} 位以上数字串：{sample!r}"
        assert not re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", stripped), f"残留疑似手机号：{sample!r}"

    joined = "\n".join(samples)
    assert "MRN-2023-0042" in joined and "liulab_2023" in joined     # 教学假号锚点还在
    assert "example.edu.cn" in joined
