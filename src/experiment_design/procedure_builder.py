"""实验设计系统 — 实验程序构建器

生成详细的实验流程、时间线、随机化方案和平衡设计。
"""

import random
import itertools
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ExperimentProcedure:
    """实验程序"""
    phases: List[Dict]                     # 各阶段详细步骤
    timeline: List[Dict]                   # 时间线
    randomization: Dict                    # 随机化方案
    counterbalancing: Optional[Dict]       # 平衡方案
    instructions: List[Dict]               # 指导语
    total_duration_min: int = 0            # 总时长（分钟）


def _generate_phases(design_type: str, n_conditions: int, materials: List[Dict]) -> List[Dict]:
    """根据设计类型生成实验阶段"""
    phases = []

    # 阶段1: 准备阶段
    phases.append({
        "phase": 1,
        "name": "实验准备",
        "duration_min": 5,
        "description": "实验者提前到达实验室，检查实验设备（电脑、问卷平台等），确保实验材料准备齐全。线上实验需确认问卷链接可正常访问。",
        "checklist": [
            "检查实验设备运行正常",
            "准备知情同意书（纸质或电子版）",
            "确认实验材料/量表可用",
            "线上实验：测试问卷链接",
        ],
    })

    # 阶段2: 被试接待与知情同意
    phases.append({
        "phase": 2,
        "name": "被试接待与知情同意",
        "duration_min": 5,
        "description": "被试到达后，实验者简要介绍实验内容和流程（但不透露具体假设），请被试阅读并签署知情同意书。强调被试有权在任何时候退出实验。",
        "checklist": [
            "问候被试，引导入座",
            "简要介绍实验流程（不透露研究假设）",
            "请被试阅读知情同意书",
            "回答被试疑问",
            "签署知情同意书",
        ],
    })

    # 阶段3: 人口学信息与指导语
    phases.append({
        "phase": 3,
        "name": "人口学信息与实验指导语",
        "duration_min": 5,
        "description": "被试填写基本人口学信息（性别、年龄、年级等）。然后呈现实验指导语，说明实验任务的要求和注意事项。如涉及按键反应，说明按键对应关系。",
        "checklist": [
            "收集人口学信息",
            "呈现标准化的实验指导语",
            "确认被试理解实验要求",
            "告知被试实验总时长",
        ],
    })

    # 阶段4: 练习/预试（如果需要）
    if design_type in ("within_subjects", "mixed", "cognitive"):
        phases.append({
            "phase": 4,
            "name": "练习阶段",
            "duration_min": 5,
            "description": "被试完成若干练习试次，以熟悉实验任务。练习阶段的刺激材料与正式实验不同。确保被试正确率达到预设标准（如≥80%）后方可进入正式实验。必要时可重复练习。",
            "checklist": [
                "呈现练习试次（与正式实验不同的材料）",
                "提供正误反馈",
                "检查正确率是否达标（≥80%）",
                "未达标则重复练习",
            ],
        })

    # 阶段5: 正式实验
    phase_num = len(phases) + 1
    main_duration = _estimate_main_duration(design_type, n_conditions, materials)
    phase_desc = _build_main_task_desc(design_type, n_conditions)
    phases.append({
        "phase": phase_num,
        "name": "正式实验",
        "duration_min": main_duration,
        "description": phase_desc,
        "checklist": [
            "按预设顺序呈现实验刺激/问卷",
            "记录被试反应（反应时/正确率/量表得分）",
            "确保实验环境安静无干扰",
            "如为线上实验，设置注意力检查题",
        ],
    })

    # 阶段6: 结束
    phases.append({
        "phase": phase_num + 1,
        "name": "实验结束与事后说明",
        "duration_min": 5,
        "description": "实验任务完成后，感谢被试的参与。进行事后说明（debriefing），解释研究的真实目的和假设。询问被试是否有疑问，并请被试对研究目的保密。发放被试费或学分。",
        "checklist": [
            "感谢被试参与",
            "事后说明（揭示研究目的）",
            "回答被试疑问",
            "请被试保密",
            "发放被试费/学分",
        ],
    })

    return phases


def _estimate_main_duration(design_type: str, n_conditions: int, materials: List[Dict]) -> int:
    """估算正式实验时长"""
    if design_type == "survey":
        # 问卷类：每量表约3-5分钟
        def _to_int(v):
            try:
                return int(v)
            except (ValueError, TypeError):
                return 10
        total_items = sum(_to_int(m.get("items", 10)) for m in materials)
        return max(5, total_items // 4)
    elif design_type in ("within_subjects", "cognitive"):
        # 认知实验：每条件约3-5分钟 + 休息
        return n_conditions * 4 + (n_conditions - 1) * 1
    elif design_type == "mixed":
        return n_conditions * 3 + 5
    else:
        # 默认
        return max(10, n_conditions * 5)


def _build_main_task_desc(design_type: str, n_conditions: int) -> str:
    """生成正式实验的主体描述"""
    if design_type == "survey":
        return f"被试依次完成各量表/问卷的作答。所有量表采用标准化指导语，明确告知被试根据自身实际情况作答。量表呈现顺序已进行随机化（如有多个量表）。作答过程中不设时间限制，但建议被试凭第一感觉作答，不要反复斟酌。"
    elif design_type == "within_subjects":
        return f"被试完成共{n_conditions}个实验条件/水平的任务。条件呈现顺序已根据拉丁方设计进行了平衡。每个条件包含若干试次。条件之间有短暂休息（30秒），被试可按空格键继续。"
    elif design_type == "mixed":
        return f"被试按随机分配进入不同的被试间条件，并在每个条件下完成全部被试内条件的任务。共{n_conditions}个实验block。"
    elif design_type == "cognitive":
        return f"被试完成{n_conditions}个block的认知任务。每个block开始前呈现简短指导语。刺激呈现顺序在每个block内随机化。记录反应时和正确率。"
    else:
        return f"被试完成实验任务。共{n_conditions}个实验条件/block。"


def build_timeline(phases: List[Dict]) -> Tuple[List[Dict], int]:
    """构建实验时间线，返回(时间线列表, 总分钟数)"""
    timeline = []
    cumulative = 0
    for phase in phases:
        start = cumulative
        cumulative += phase["duration_min"]
        timeline.append({
            "phase": phase["phase"],
            "name": phase["name"],
            "start_min": start,
            "end_min": cumulative,
            "duration_min": phase["duration_min"],
        })
    return timeline, cumulative


# ═══════════════════════════════════════════════════════════════
# 随机化与平衡
# ═══════════════════════════════════════════════════════════════

def generate_randomization(
    design_type: str,
    n_conditions: int,
    n_subjects: int,
    conditions: List[str] = None,
) -> Dict:
    """生成随机化方案。

    返回包含随机化方法和具体分配的字典。
    """
    conditions = conditions or [f"条件{i+1}" for i in range(n_conditions)]

    if design_type in ("between_subjects", "factorial"):
        # 简单随机分配
        assignments = []
        for i in range(n_subjects):
            group = i % n_conditions  # 均衡分配
            assignments.append({"subject": i + 1, "group": conditions[group]})
        random.shuffle(assignments)

        return {
            "method": "简单随机分配（均衡分组）",
            "description": f"将被试随机分配至{n_conditions}个实验条件，每组{n_subjects // n_conditions}人（剩余{n_subjects % n_conditions}人随机分配）。使用随机数生成器确保分配的无偏性。",
            "assignments": assignments,
            "seed_suggestion": "建议使用计算机生成的随机数（如Python的random.shuffle），并记录随机种子以保证可重复性。",
        }

    elif design_type == "within_subjects":
        # 拉丁方平衡
        latin = generate_latin_square(n_conditions)
        # 将数字映射到条件标签
        latin_labeled = [[conditions[j - 1] for j in row] for row in latin]

        return {
            "method": "拉丁方设计（顺序平衡）",
            "description": f"使用{n_conditions}阶拉丁方矩阵对所有实验条件的呈现顺序进行平衡。被试被随机分配至{len(latin)}种顺序之一，确保每个条件出现在每个序列位置的概率相等。",
            "latin_square": latin_labeled,
            "n_orders": len(latin),
            "note": f"每组顺序建议分配{n_subjects // len(latin)}名被试。" if n_subjects else "实际分配根据被试总数确定。",
        }

    elif design_type == "mixed":
        # 被试间随机 + 被试内拉丁方
        return {
            "method": "混合随机化",
            "description": "被试间因素的水平进行随机分配，被试内因素的顺序使用拉丁方平衡。",
            "between_randomization": "简单随机分配至被试间条件",
            "within_balancing": "拉丁方设计平衡被试内条件顺序",
            "conditions": conditions,
        }

    else:
        # 默认：简单随机
        return generate_randomization("between_subjects", n_conditions, n_subjects, conditions)


def generate_latin_square(n: int) -> List[List[int]]:
    """生成拉丁方矩阵。

    用于平衡实验条件呈现顺序。使用标准循环拉丁方（第一行: 1, 2, ..., n）。
    """
    if n < 2:
        return [[1]]

    square = []
    for i in range(n):
        row = [(j + i) % n + 1 for j in range(n)]
        square.append(row)

    return square


def generate_balanced_latin_square(n: int) -> List[List[int]]:
    """生成平衡拉丁方矩阵（Balanced Latin Square）。

    当条件数为偶数时，平衡拉丁方确保：
    1. 每个条件在每个序列位置出现恰好一次
    2. 每个条件在其他每个条件之前和之后各出现恰好一次
    3. 完全消除顺序效应中的线性趋势

    算法 (Bradley, 1958):
        第一行: 1, 2, n, 3, n-1, 4, n-2, ...
        后续行: 上一行每个数字 +1 (模n)

    当 n 为奇数时，平衡拉丁方需要两倍行数（n×(n-1)行）才能完全平衡，
    此时回退到标准拉丁方并给出警告。

    参数：
        n: 条件数（偶数时最优，奇数时降级为2倍标准方）

    返回：
        n行（奇数时2n行）× n列的拉丁方矩阵
    """
    if n < 2:
        return [[1]]

    if n % 2 == 1:
        # 奇数：使用两倍反转镜像法实现完全平衡
        # 第一半：标准拉丁方
        half1 = generate_latin_square(n)
        # 第二半：反转每行顺序（镜像对称）
        half2 = [list(reversed(row)) for row in half1]
        return half1 + half2

    # 偶数：Bradley 算法
    # 第一行: 1, 2, n, 3, n-1, 4, n-2, ...
    first_row = [1, 2]
    remaining = list(range(3, n + 1))
    left = 0
    right = len(remaining) - 1
    toggle = True  # True: 从右取, False: 从左取
    while left <= right:
        if toggle:
            first_row.append(remaining[right])
            right -= 1
        else:
            first_row.append(remaining[left])
            left += 1
        toggle = not toggle

    square = [first_row]
    for i in range(1, n):
        # 每个数字 +1 (模n, 1-based)
        row = [(x % n) + 1 for x in square[i - 1]]
        square.append(row)

    return square


def generate_full_counterbalancing(conditions: List[str]) -> List[List[str]]:
    """生成完全交叉平衡（所有可能的排列顺序）。

    警告：仅适用于条件数较少的情况（n ≤ 6）。
    """
    all_perms = list(itertools.permutations(conditions))
    return [list(p) for p in all_perms]


# ═══════════════════════════════════════════════════════════════
# 指导语生成
# ═══════════════════════════════════════════════════════════════

def generate_instructions(design_type: str, topic: str,
                          conditions: List[str] = None) -> List[Dict]:
    """生成标准化的实验指导语"""
    instructions = []

    # 通用指导语
    instructions.append({
        "type": "general",
        "title": "实验总指导语",
        "text": f"""欢迎参加本次心理学实验！

本实验旨在了解人们在日常生活中的心理过程与行为特点。在接下来的实验中，我们将请您完成一系列任务。

请注意以下事项：
1. 请认真阅读每一屏的指导语和题目
2. 没有时间限制，但请凭第一反应作答
3. 答案没有对错之分，只需如实反映您的真实情况/感受
4. 您提供的所有信息将严格保密，仅用于学术研究

如有任何疑问，请随时向实验人员提出。

按"继续"按钮开始实验。"""
    })

    # 具体任务指导语
    if design_type in ("within_subjects", "cognitive"):
        instructions.append({
            "type": "task",
            "title": "任务指导语",
            "text": f"""在接下来的任务中，屏幕中央将依次呈现一系列刺激。

您的任务是尽快且准确地对刺激做出判断。

练习阶段包含若干试次，您将获得正确/错误的反馈。
正式实验阶段没有反馈，请根据练习阶段的理解独立完成。

正式实验共包含多个任务分组，组间有短暂休息。"""
        })

    if conditions:
        for i, cond in enumerate(conditions):
            instructions.append({
                "type": "condition",
                "title": f"条件 {i+1} 指导语",
                "condition": cond,
                "text": f"接下来请您进行「{cond}」条件下的任务。请仔细阅读屏幕上的说明，确认理解后开始。"
            })

    # 结束指导语
    instructions.append({
        "type": "end",
        "title": "实验结束",
        "text": """实验任务已全部完成！

感谢您的参与和配合。您的数据对本研究非常重要。

实验人员将为您进行事后说明，解释研究的具体目的。

再次感谢！"""
    })

    return instructions


# ═══════════════════════════════════════════════════════════════
# 完整程序构建
# ═══════════════════════════════════════════════════════════════

def build_full_procedure(
    design_type: str,
    topic: str,
    n_conditions: int,
    n_subjects: int = 0,
    conditions: List[str] = None,
    conditions_labels: Dict[str, str] = None,
    materials: List[Dict] = None,
) -> ExperimentProcedure:
    """构建完整的实验程序。

    参数:
        design_type: "between_subjects" | "within_subjects" | "mixed" | "survey" | "cognitive" | "quasi_experimental"
        topic: 研究主题
        n_conditions: 实验条件数
        n_subjects: 计划被试数
        conditions: 条件标签列表
        materials: 实验材料列表 [{"name": ..., "items": ..., "alpha": ...}, ...]
    """
    materials = materials or []
    conditions = conditions or [f"条件{i+1}" for i in range(n_conditions)]

    # 1. 生成实验阶段
    phases = _generate_phases(design_type, n_conditions, materials)

    # 2. 构建时间线
    timeline, total_min = build_timeline(phases)

    # 3. 生成随机化方案
    randomization = generate_randomization(design_type, n_conditions, n_subjects, conditions)

    # 4. 生成平衡方案（仅在需要时）
    counterbalancing = None
    if design_type in ("within_subjects", "mixed"):
        counterbalancing = {
            "method": "拉丁方设计（Latin Square Design）",
            "description": f"使用{n_conditions}阶拉丁方矩阵平衡条件呈现顺序，控制顺序效应和练习效应。",
            "latin_square": [[conditions[j - 1] for j in row] for row in generate_latin_square(n_conditions)],
            "additional_recommendations": [
                "每个条件后设置短暂休息（30秒-1分钟）以减少疲劳效应",
                "若条件间可能存在延续效应（carry-over effect），建议在条件之间插入填充任务（filler task）",
                "如有必要，可增加条件间隔时间至5-10分钟（如情绪诱发实验）",
            ],
        }

    # 5. 生成指导语
    instructions = generate_instructions(design_type, topic, conditions)

    return ExperimentProcedure(
        phases=phases,
        timeline=timeline,
        randomization=randomization,
        counterbalancing=counterbalancing,
        instructions=instructions,
        total_duration_min=total_min,
    )
