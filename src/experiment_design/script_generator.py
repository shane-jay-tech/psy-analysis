"""jsPsych v7 脚本生成器：将实验设计模板转换为可运行的 Web 实验脚本

支持的模板：
  - between_subjects_single: 单因素被试间设计
  - within_subjects_single:  单因素被试内设计
  - survey: 问卷调查研究
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class JsPsychScript:
    """jsPsych 实验脚本"""
    experiment_id: str
    template_name: str
    html_content: str
    js_content: str
    preview_url: str = ""  # 本地预览URL
    warning: str = ""


# ═══════════════════════════════════════════════════════════════
# 题名转义（台账 #69 案 A：堵「experiment_title 未转义即注入」）
#
# ⚠️ 两类上下文的规则**不同**，合一写法必错：
#   1) JS 字符串上下文（内联 <script> 里的 "..."／'...'／`...`）：
#      危险字符是「定界符 + 转义符 + 模板插值」⇒ 转义 \ " ' ` ${ 与控制字符；
#      另外整段串活在 <script> 元素内，HTML 分词器只按字面 "</script" 终结脚本块，
#      它**不看 JS 语法** ⇒ 单引号/反斜杠转义救不了 `</script>`，必须把 `<` 变成
#      \u003c 这类 Unicode 转义（JS 侧解析回来仍是 `<`，HTML 侧却凑不出 "</script"）。
#   2) HTML 文本上下文（<title> 元素、jsPsych 用 innerHTML 渲染的 stimulus）：
#      危险字符是「标签定界符 + 实体前缀」⇒ 转义 & < >（`&` 必须**最先**，
#      否则会把 &lt; 二次转成 &amp;lt;）；引号在此不是定界符，但一并转成实体，
#      同一函数放进属性值里也安全。
#   混合上下文（模板字符串里的 HTML 片段）＝ **先 HTML 再 JS**（外层上下文最后转），
#   顺序反了会让 JS 转义产生的 \" 被 HTML 转义改写成 \&quot; 而失去 JS 语义。
# ═══════════════════════════════════════════════════════════════

_JS_STRING_SUBS = (
    ("\\", "\\\\"),        # 必须最先：后续每一项都会引入新的反斜杠
    ('"', '\\"'),
    ("'", "\\'"),
    ("`", "\\`"),          # 模板字符串定界符
    ("${", "\\${"),       # 模板字符串插值
    ("\r", "\\r"),
    ("\n", "\\n"),
    ("\t", "\\t"),
    ("\u2028", "\\u2028"),  # JS 行终止符，未转义会截断字符串字面量
    ("\u2029", "\\u2029"),
    ("<", "\\u003c"),      # 断 "</script>" / "<!--" 的破出
    (">", "\\u003e"),
)

_HTML_TEXT_SUBS = (
    ("<", "&lt;"),
    (">", "&gt;"),
    ('"', "&quot;"),
    ("'", "&#39;"),
)


def _as_text(value) -> str:
    """把题名/文本入参统一成 str（None → ""，与 f-string 现状一致，不改语义）。"""
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def escape_js_string(value) -> str:
    """上下文 1：JS 字符串字面量内安全（"..."／'...'／`...` 三种定界符通用）。"""
    text = _as_text(value)
    for needle, replacement in _JS_STRING_SUBS:
        text = text.replace(needle, replacement)
    return text


def escape_html_text(value) -> str:
    """上下文 2：HTML 文本节点／RCDATA（<title>）／属性值内安全。"""
    text = _as_text(value).replace("&", "&amp;")  # & 最先
    for needle, replacement in _HTML_TEXT_SUBS:
        text = text.replace(needle, replacement)
    return text


def escape_html_comment(value) -> str:
    """上下文 3：HTML 注释内安全。

    注释里唯一的破出是提前收尾序列 `-->`／`--!>` 与非法嵌套 `<!--`，
    把 < > 实体化即断根（注释内容不做实体解码，故只做最小破坏性替换）。
    """
    return _as_text(value).replace("<", "&lt;").replace(">", "&gt;")


def escape_html_in_js(value) -> str:
    """混合上下文：JS 模板字符串里的 HTML 片段（先 HTML 后 JS）。"""
    return escape_js_string(escape_html_text(value))


def generate_jspsych_script(
    design_template: Dict,
    conditions: List[str] = None,
    procedure: Dict = None,
    experiment_title: str = "心理学实验",
    fullscreen: bool = True,
    show_progress: bool = True,
    timeline_variables: List[Dict] = None,
) -> JsPsychScript:
    """
    根据实验设计生成完整的 jsPsych v7 实验脚本。

    参数：
        design_template: 设计模板（来自实验设计引擎）
        conditions: 实验条件列表
        procedure: 实验程序（来自 procedure_builder）
        experiment_title: 实验标题
        fullscreen: 是否全屏模式
        show_progress: 是否显示进度条
        timeline_variables: 自定义试次变量列表（可选，用于更复杂的实验逻辑）

    返回：
        JsPsychScript 包含独立的 HTML 和 JS 代码
    """
    design_type = design_template.get("design_type", "between_subjects")

    if design_type == "between_subjects":
        return _gen_between_subjects(
            design_template, conditions, procedure, experiment_title,
            fullscreen, show_progress, timeline_variables,
        )
    elif design_type == "within_subjects":
        return _gen_within_subjects(
            design_template, conditions, procedure, experiment_title,
            fullscreen, show_progress, timeline_variables,
        )
    elif design_type in ("survey", "questionnaire"):
        return _gen_survey(
            design_template, conditions, procedure, experiment_title,
            fullscreen, show_progress, timeline_variables,
        )
    else:
        return _gen_generic(
            design_template, conditions, procedure, experiment_title,
            fullscreen, show_progress, timeline_variables,
        )


# ═══════════════════════════════════════════════════════════════
# 单因素被试间设计
# ═══════════════════════════════════════════════════════════════

def _gen_between_subjects(
    design: Dict,
    conditions: List[str],
    procedure: Dict,
    title: str,
    fullscreen: bool,
    show_progress: bool,
    timeline_vars: List[Dict],
) -> JsPsychScript:
    """生成单因素被试间设计的 jsPsych 脚本"""
    cond_list = conditions or ["条件A", "条件B"]
    n_conditions = len(cond_list)
    cond_json = [
        {"id": i, "name": cond_list[i], "label": f"condition_{i}"}
        for i in range(n_conditions)
    ]

    conditions_js_array = ", ".join(
        f'{{id: {c["id"]}, name: "{c["name"]}", label: "{c["label"]}"}}'
        for c in cond_json
    )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_html_text(title)}</title>
  <!-- jsPsych v7 -->
  <script src="https://unpkg.com/jspsych@7.3.4"></script>
  <script src="https://unpkg.com/@jspsych/plugin-html-keyboard-response@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-html-button-response@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-survey-likert@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-survey-text@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-instructions@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-fullscreen@1.1.2"></script>
  <link href="https://unpkg.com/jspsych@7.3.4/css/jspsych.css" rel="stylesheet">
  <style>
    body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f0f2f6; }}
    .jspsych-content {{ max-width: 900px; margin: 40px auto; }}
    .jspsych-display-element {{ background: white; padding: 32px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .cond-badge {{ display: inline-block; padding: 4px 14px; margin: 4px; border-radius: 20px; font-size: 14px; }}
    .cond-active {{ background: #1890ff; color: white; }}
    .cond-inactive {{ background: #f0f0f0; color: #999; }}
    .progress-bar {{ width: 100%; height: 6px; background: #f0f0f0; border-radius: 3px; margin-bottom: 20px; }}
    .progress-fill {{ height: 100%; background: #1890ff; border-radius: 3px; transition: width 0.3s; }}
  </style>
</head>
<body>
  <script>
    // ═════════════════════════════════════════════════════════
    // 实验配置 (由 PsyAnalysis 2.0 自动生成)
    // ═════════════════════════════════════════════════════════
    const EXPERIMENT_CONFIG = {{
      title: "{escape_js_string(title)}",
      designType: "between_subjects",
      conditions: [{conditions_js_array}],
      participantId: jsPsych.randomization.randomID(8),
      startTime: new Date().toISOString(),
    }};

    // 随机分配被试到条件 (简单随机分配)
    const assignedCondition = jsPsych.randomization.sampleWithoutReplacement(
      EXPERIMENT_CONFIG.conditions, 1
    )[0];

    console.log(
      `[PsyAnalysis] 被试 ${{EXPERIMENT_CONFIG.participantId}} → 条件: ${{assignedCondition.name}}`
    );

    // ═════════════════════════════════════════════════════════
    // 时间线构建
    // ═════════════════════════════════════════════════════════
    const timeline = [];

    // 阶段 1: 全屏请求
    {'if (fullscreen) {'}
    timeline.push({{
      type: jsPsychFullscreen,
      fullscreen_mode: true,
    }});
    {'}'}

    // 阶段 2: 欢迎页面
    timeline.push({{
      type: jsPsychHtmlButtonResponse,
      stimulus: `
        <h2>{escape_html_in_js(title)}</h2>
        <hr style="margin: 20px 0;">
        <p style="font-size: 16px; line-height: 1.8;">
          感谢您参加本次心理学实验！<br><br>
          在接下来的实验中，我们将请您完成一系列任务。<br><br>
          <strong>注意事项：</strong><br>
          1. 请认真阅读每一屏的指导语<br>
          2. 没有时间限制，请凭第一反应作答<br>
          3. 答案没有对错之分<br>
          4. 您的所有信息将严格保密，仅用于学术研究
        </p>
      `,
      choices: ["开始实验"],
      data: {{ phase: "welcome" }},
    }});

    // 阶段 3: 实验任务 (条件特定)
    // 每个试次根据分配的条件显示对应的刺激
    // 各条件的试次定义（请根据实验需求修改）
    const trialStimuli = {{
      {', '.join(f'"{c["label"]}": []' for c in cond_json)}
    }};

    // 默认试次：如果模板未提供具体刺激，使用通用试次
    const practiceTrials = {{
      type: jsPsychHtmlKeyboardResponse,
      stimulus: `<div style="text-align:center;">
        <h3>练习阶段</h3>
        <p style="margin-top: 30px;">屏幕中央将出现刺激，请尽快做出反应。</p>
        <p style="color: #999;">按 <strong>空格键</strong> 开始练习</p>
      </div>`,
      choices: [" "],
      data: {{ phase: "practice" }},
    }};

    const mainTrials = {{
      timeline: [
        {{
          type: jsPsychHtmlKeyboardResponse,
          stimulus: `<div style="text-align:center;">
            <p style="color: #666; margin-bottom: 20px;">当前条件：${{assignedCondition.name}}</p>
            <div style="padding: 40px; border: 2px dashed #d9d9d9; border-radius: 8px; font-size: 24px;">
              请根据指导语完成判断任务
            </div>
          </div>`,
          choices: ["f", "j"],
          data: {{
            phase: "trial",
            condition: assignedCondition.label,
            conditionName: assignedCondition.name,
          }},
          on_finish: function(data) {{
            data.rt = data.rt;
            data.correct = data.response === "f";
          }},
        }}
      ],
      timeline_variables: Array.from({{ length: 20 }}, (_, i) => ({{
        trial_index: i + 1,
        stimulus_id: `trial_${{i + 1}}`,
      }})),
    }};

    timeline.push(practiceTrials);
    timeline.push(mainTrials);

    // 阶段 4: 操作检验
    timeline.push({{
      type: jsPsychSurveyLikert,
      questions: [
        {{
          prompt: `请评价您在实验中感受到的「${{assignedCondition.name}}」程度`,
          labels: ["非常弱", "较弱", "中等", "较强", "非常强"],
          name: "manipulation_check",
          required: true,
        }},
      ],
      data: {{ phase: "manipulation_check", condition: assignedCondition.label }},
    }});

    // 阶段 5: 结束页面
    timeline.push({{
      type: jsPsychHtmlButtonResponse,
      stimulus: `
        <h2>实验完成</h2>
        <hr style="margin: 20px 0;">
        <p style="font-size: 16px; line-height: 1.8;">
          感谢您的参与！<br><br>
          您的实验编号：<strong>${{EXPERIMENT_CONFIG.participantId}}</strong><br>
          实验条件：<strong>${{assignedCondition.name}}</strong><br><br>
          如有任何疑问，请联系实验人员。
        </p>
      `,
      choices: ["结束"],
      data: {{ phase: "debrief" }},
    }});

    // ═════════════════════════════════════════════════════════
    // 启动实验
    // ═════════════════════════════════════════════════════════
    jsPsych.init({{
      timeline: timeline,
      on_finish: function() {{
        // 下载数据
        const data = jsPsych.data.get().csv();
        const blob = new Blob([data], {{ type: "text/csv" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${{EXPERIMENT_CONFIG.participantId}}_${{assignedCondition.label}}_${{Date.now()}}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        console.log("[PsyAnalysis] 实验完成，数据已下载。");
        console.log(jsPsych.data.get().json());
      }},
      on_trial_finish: function() {{
        {'if (show_progress) {'}
        const progress = jsPsych.progress();
        const pct = Math.round(progress.proportion_completed * 100);
        const bar = document.querySelector(".progress-fill");
        if (bar) bar.style.width = pct + "%";
        {'}'}
      }},
    }});
  </script>
</body>
</html>'''

    return JsPsychScript(
        experiment_id="exp_" + design.get("id", "unnamed"),
        template_name=design.get("name", "未命名模板"),
        html_content=html,
        js_content="",
        warning=(
            "生成的 jsPsych 脚本中实验试次为通用占位符。"
            "请根据具体实验需求替换 stimulus 内容和试次变量。"
        ),
    )


# ═══════════════════════════════════════════════════════════════
# 单因素被试内设计
# ═══════════════════════════════════════════════════════════════

def _gen_within_subjects(
    design: Dict,
    conditions: List[str],
    procedure: Dict,
    title: str,
    fullscreen: bool,
    show_progress: bool,
    timeline_vars: List[Dict],
) -> JsPsychScript:
    """生成单因素被试内设计的 jsPsych 脚本（含拉丁方平衡）"""
    cond_list = conditions or ["条件A", "条件B", "条件C"]
    n_conditions = len(cond_list)
    cond_json = [
        {"id": i, "name": cond_list[i], "label": f"condition_{i}"}
        for i in range(n_conditions)
    ]

    # 生成平衡拉丁方用于顺序分配
    from .procedure_builder import generate_balanced_latin_square
    square = generate_balanced_latin_square(n_conditions)
    orders_json = ", ".join(
        "[{}]".format(", ".join(f'"{cond_list[j-1]}"' for j in row))
        for row in square
    )
    all_orders = f"[{orders_json}]"

    conditions_js_array = ", ".join(
        f'{{id: {c["id"]}, name: "{c["name"]}", label: "{c["label"]}"}}'
        for c in cond_json
    )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_html_text(title)}</title>
  <script src="https://unpkg.com/jspsych@7.3.4"></script>
  <script src="https://unpkg.com/@jspsych/plugin-html-keyboard-response@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-html-button-response@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-survey-likert@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-instructions@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-fullscreen@1.1.2"></script>
  <link href="https://unpkg.com/jspsych@7.3.4/css/jspsych.css" rel="stylesheet">
  <style>
    body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f0f2f6; }}
    .jspsych-content {{ max-width: 900px; margin: 40px auto; }}
    .jspsych-display-element {{ background: white; padding: 32px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .progress-bar {{ width: 100%; height: 6px; background: #f0f0f0; border-radius: 3px; margin-bottom: 20px; }}
    .progress-fill {{ height: 100%; background: #52c41a; border-radius: 3px; transition: width 0.3s; }}
  </style>
</head>
<body>
  <script>
    const EXPERIMENT_CONFIG = {{
      title: "{escape_js_string(title)}",
      designType: "within_subjects",
      conditions: [{conditions_js_array}],
      counterbalanceOrders: {all_orders},
      participantId: jsPsych.randomization.randomID(8),
    }};

    // 随机分配顺序（从拉丁方中随机选取一行）
    const orderIndex = Math.floor(Math.random() * EXPERIMENT_CONFIG.counterbalanceOrders.length);
    const assignedOrder = EXPERIMENT_CONFIG.counterbalanceOrders[orderIndex];

    console.log(
      `[PsyAnalysis] 被试 ${{EXPERIMENT_CONFIG.participantId}} → 顺序: [%c${{assignedOrder.join(", ")}}%c]`,
      "color: #52c41a;", ""
    );

    const timeline = [];

    // 全屏
    {'if (fullscreen) {'}
    timeline.push({{ type: jsPsychFullscreen, fullscreen_mode: true }});
    {'}'}

    // 欢迎页面
    timeline.push({{
      type: jsPsychHtmlButtonResponse,
      stimulus: `
        <h2>{escape_html_in_js(title)}</h2>
        <hr style="margin: 20px 0;">
        <p style="font-size: 16px; line-height: 1.8;">
          感谢您参加本次实验！您将依次完成所有实验条件。<br>
          每个条件之间有短暂休息。<br><br>
          <strong>注意事项：</strong>请认真阅读每一屏的指导语，凭第一反应作答。
        </p>
      `,
      choices: ["开始实验"],
      data: {{ phase: "welcome" }},
    }});

    // 为每个条件生成 block（按拉丁方顺序）
    assignedOrder.forEach(function(conditionName, blockIndex) {{
      const cond = EXPERIMENT_CONFIG.conditions.find(c => c.name === conditionName);

      // Block 指导语
      timeline.push({{
        type: jsPsychHtmlButtonResponse,
        stimulus: `
          <h3>第 ${{blockIndex + 1}} 部分 / 共 ${{assignedOrder.length}} 部分</h3>
          <hr>
          <p style="font-size: 18px; margin-top: 30px;">当前条件：<strong>${{conditionName}}</strong></p>
          <p style="color: #999;">请仔细阅读以下指导语，准备好后按按钮开始。</p>
        `,
        choices: ["开始"],
        data: {{ phase: "block_instruction", block: blockIndex, condition: cond.label }},
      }});

      // 该条件下的试次
      timeline.push({{
        timeline: [
          {{
            type: jsPsychHtmlKeyboardResponse,
            stimulus: `<div style="text-align:center;">
              <p style="color: #666;">条件：${{conditionName}}</p>
              <div style="padding: 40px; border: 2px dashed #d9d9d9; border-radius: 8px; font-size: 24px;">
                请根据指导语完成判断任务
              </div>
            </div>`,
            choices: ["f", "j"],
            data: {{
              phase: "trial",
              block: blockIndex,
              condition: cond.label,
              conditionName: conditionName,
            }},
            on_finish: function(data) {{
              data.conditionOrder = blockIndex + 1;
            }},
          }}
        ],
        timeline_variables: Array.from({{ length: 15 }}, (_, i) => ({{
          trial_index: i + 1,
        }})),
      }});

      // Block 间休息（非最后一个）
      if (blockIndex < assignedOrder.length - 1) {{
        timeline.push({{
          type: jsPsychHtmlButtonResponse,
          stimulus: `
            <h3>休息</h3>
            <p style="margin-top: 30px;">请稍作休息，准备好后继续。</p>
          `,
          choices: ["继续"],
          data: {{ phase: "rest", after_block: blockIndex }},
        }});
      }}
    }});

    // 结束页面
    timeline.push({{
      type: jsPsychHtmlButtonResponse,
      stimulus: `
        <h2>实验完成</h2>
        <hr style="margin: 20px 0;">
        <p>您的实验编号：<strong>${{EXPERIMENT_CONFIG.participantId}}</strong></p>
        <p>感谢您的参与！</p>
      `,
      choices: ["结束"],
      data: {{ phase: "debrief" }},
    }});

    // 启动
    jsPsych.init({{
      timeline: timeline,
      on_finish: function() {{
        const data = jsPsych.data.get().csv();
        const blob = new Blob([data], {{ type: "text/csv" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${{EXPERIMENT_CONFIG.participantId}}_within_${{Date.now()}}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }},
      on_trial_finish: function() {{
        {'if (show_progress) {'}
        const p = jsPsych.progress();
        const bar = document.querySelector(".progress-fill");
        if (bar) bar.style.width = Math.round(p.proportion_completed * 100) + "%";
        {'}'}
      }},
    }});
  </script>
</body>
</html>'''

    return JsPsychScript(
        experiment_id="exp_" + design.get("id", "unnamed"),
        template_name=design.get("name", "未命名模板"),
        html_content=html,
        js_content="",
        warning=(
            "生成的被试内设计脚本中使用了平衡拉丁方（Balanced Latin Square）分配顺序。"
            "请根据具体实验需求替换试次内容和刺激呈现参数。"
        ),
    )


# ═══════════════════════════════════════════════════════════════
# 问卷调查研究
# ═══════════════════════════════════════════════════════════════

def _gen_survey(
    design: Dict,
    conditions: List[str],
    procedure: Dict,
    title: str,
    fullscreen: bool,
    show_progress: bool,
    timeline_vars: List[Dict],
) -> JsPsychScript:
    """生成问卷调查研究脚本"""
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_html_text(title)}</title>
  <script src="https://unpkg.com/jspsych@7.3.4"></script>
  <script src="https://unpkg.com/@jspsych/plugin-survey-likert@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-survey-text@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-survey-multi-choice@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-html-button-response@1.1.3"></script>
  <script src="https://unpkg.com/@jspsych/plugin-instructions@1.1.3"></script>
  <link href="https://unpkg.com/jspsych@7.3.4/css/jspsych.css" rel="stylesheet">
  <style>
    body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f0f2f6; }}
    .jspsych-content {{ max-width: 800px; margin: 40px auto; }}
    .jspsych-display-element {{ background: white; padding: 32px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .progress-bar {{ width: 100%; height: 6px; background: #f0f0f0; border-radius: 3px; margin-bottom: 20px; }}
    .progress-fill {{ height: 100%; background: #722ed1; border-radius: 3px; transition: width 0.3s; }}
  </style>
</head>
<body>
  <script>
    const EXPERIMENT_CONFIG = {{
      title: "{escape_js_string(title)}",
      participantId: jsPsych.randomization.randomID(8),
    }};

    const timeline = [];

    // 指导语
    timeline.push({{
      type: jsPsychHtmlButtonResponse,
      stimulus: `
        <h2>{escape_html_in_js(title)}</h2>
        <hr style="margin: 20px 0;">
        <p style="font-size: 16px; line-height: 1.8;">
          尊敬的参与者：<br><br>
          本问卷旨在了解相关心理特征。请仔细阅读每个题目，根据您的<br>
          实际感受选择最符合的选项。<br><br>
          答案没有对错之分，请按真实情况作答。<br>
          本问卷采用匿名方式，您的回答将严格保密，仅用于学术研究。
        </p>
      `,
      choices: ["开始作答"],
      data: {{ phase: "instructions" }},
    }});

    // 示例 Likert 量表题（实际题目由问卷设计引擎生成后替换）
    timeline.push({{
      type: jsPsychSurveyLikert,
      questions: [
        {{ prompt: "示例题目1：请根据您的真实感受选择。", labels: ["完全不同意", "不同意", "不确定", "同意", "完全同意"], name: "Q1", required: true }},
        {{ prompt: "示例题目2：请根据您的真实感受选择。", labels: ["完全不同意", "不同意", "不确定", "同意", "完全同意"], name: "Q2", required: true }},
      ],
      preamble: "<h3>第一部分</h3><p>请仔细阅读每个题目，选择最符合您实际情况的选项。</p>",
      data: {{ phase: "survey_block", block: 1 }},
    }});

    // 结束
    timeline.push({{
      type: jsPsychHtmlButtonResponse,
      stimulus: `
        <h2>问卷完成</h2>
        <hr style="margin: 20px 0;">
        <p style="font-size: 16px;">感谢您的参与！您的编号：<strong>${{EXPERIMENT_CONFIG.participantId}}</strong></p>
      `,
      choices: ["提交"],
      data: {{ phase: "debrief" }},
    }});

    jsPsych.init({{
      timeline: timeline,
      on_finish: function() {{
        const data = jsPsych.data.get().csv();
        const blob = new Blob([data], {{ type: "text/csv" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${{EXPERIMENT_CONFIG.participantId}}_survey_${{Date.now()}}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }},
    }});
  </script>
</body>
</html>'''

    return JsPsychScript(
        experiment_id="exp_" + design.get("id", "unnamed"),
        template_name=design.get("name", "未命名模板"),
        html_content=html,
        js_content="",
        warning=(
            "问卷题目为通用占位符。请使用问卷设计引擎生成的题目替换 survey block 中的 questions 数组。"
        ),
    )


# ═══════════════════════════════════════════════════════════════
# 通用降级
# ═══════════════════════════════════════════════════════════════

def _gen_generic(
    design: Dict,
    conditions: List[str],
    procedure: Dict,
    title: str,
    fullscreen: bool,
    show_progress: bool,
    timeline_vars: List[Dict],
) -> JsPsychScript:
    """通用降级生成器"""
    return JsPsychScript(
        experiment_id="exp_" + design.get("id", "unnamed"),
        template_name=design.get("name", "未命名模板"),
        html_content=f"<!-- jsPsych script for {escape_html_comment(title)} -->\n<!-- Generic template - please customize -->",
        js_content="",
        warning=(
            f"设计类型「{design.get('design_type', 'unknown')}」暂无专用 jsPsych 模板。"
            "请使用 between_subjects 或 within_subjects 模板。"
        ),
    )


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def convert_items_to_jspsych_likert(items: List[Dict]) -> str:
    """
    将问卷设计引擎生成的题目列表转换为 jsPsych survey-likert 插件的 questions 数组。
    """
    questions = []
    for item in items:
        q = f'{{prompt: "{item.get("text", "")}", labels: ["完全不同意", "不同意", "不确定", "同意", "完全同意"], name: "Q{item.get("index", 0)}", required: true}}'
        questions.append(q)
    return "[\n    " + ",\n    ".join(questions) + "\n]"


def convert_instructions_to_jspsych(instructions: List[Dict]) -> str:
    """将指导语列表转换为 jsPsych instructions 插件的 pages 数组"""
    pages = []
    for inst in instructions:
        text = inst.get("text", "").replace("\n", "\\n").replace('"', '\\"')
        pages.append(f'"{text}"')
    return "[\n    " + ",\n    ".join(pages) + "\n]"
