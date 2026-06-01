"""PsychoPy 实验程序生成器

根据实验设计参数自动生成 PsychoPy 可运行的 Python 脚本。
不依赖 PsychoPy 运行时——仅生成脚本文件，可在安装了 PsychoPy 的计算机上运行。

支持：
- 标准 Stroop / Flanker / 情绪图片 / 记忆再认 等实验范式
- 拉丁方平衡
- 试次随机化
- 指导语自动生成
- 数据自动记录（CSV 格式）
"""

import json
import random
import textwrap
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PsychoPyExperiment:
    """PsychoPy 实验配置"""
    title: str = "心理实验"
    paradigm: str = "stroop"  # stroop / flanker / emotion / memory / custom
    n_blocks: int = 2
    n_trials_per_block: int = 36
    n_practice_trials: int = 10
    conditions: List[str] = field(default_factory=lambda: ["一致", "不一致"])
    stimuli_text: List[str] = field(default_factory=list)
    stimuli_images: List[str] = field(default_factory=list)
    iti_min: float = 0.5  # 试次间间隔最小值(s)
    iti_max: float = 1.5  # 试次间间隔最大值(s)
    feedback_duration: float = 0.5
    use_latin_square: bool = True
    show_feedback: bool = True
    response_keys: List[str] = field(default_factory=lambda: ["f", "j"])
    instructions: str = ""
    data_dir: str = "data"
    fullscreen: bool = False


# ============================================================
# 核心 API
# ============================================================


def generate_psychopy_script(
    experiment: PsychoPyExperiment,
    output_path: Optional[str] = None,
) -> str:
    """
    生成可独立运行的 PsychoPy Python 实验脚本。

    不依赖 PsychoPy 模块即可生成（生成期不 import），
    但生成的脚本在运行时需要 PsychoPy 环境。

    参数：
        experiment: PsychoPyExperiment 实验配置
        output_path: 输出文件路径（可选），不指定则返回脚本字符串

    返回：
        完整的 Python 脚本字符串
    """
    script = _build_script(experiment)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script, encoding="utf-8")

    return script


def generate_standard_paradigm(
    paradigm: str = "stroop",
    n_trials_per_condition: int = 24,
    n_subjects: int = None,
) -> PsychoPyExperiment:
    """
    快速生成标准范式的实验配置。

    参数：
        paradigm: "stroop" | "flanker" | "emotion" | "memory"
        n_trials_per_condition: 每种条件的试次数
        n_subjects: 被试总数（用于拉丁方，None 则默认 30）

    返回：
        PsychoPyExperiment 配置对象
    """
    paradigm_configs = {
        "stroop": PsychoPyExperiment(
            title="Stroop 任务",
            paradigm="stroop",
            conditions=["一致", "不一致", "中性"],
            stimuli_text=["红", "绿", "蓝", "黄"],
            instructions="请根据呈现文字的颜色（而非文字含义）尽快做出反应。\n"
                         "红色→按F键  绿色→按J键",
            response_keys=["f", "j"],
            n_blocks=3,
            n_trials_per_block=n_trials_per_condition * 3,
            n_practice_trials=12,
        ),
        "flanker": PsychoPyExperiment(
            title="Flanker 任务",
            paradigm="flanker",
            conditions=["一致", "不一致"],
            stimuli_text=["<<<<<", ">><>>", ">>>>>", "<<><<"],
            instructions="请根据中央箭头的方向尽快做出反应。\n"
                         "向左→按F键  向右→按J键",
            response_keys=["f", "j"],
            n_blocks=2,
            n_trials_per_block=n_trials_per_condition * 2,
            n_practice_trials=10,
        ),
        "emotion": PsychoPyExperiment(
            title="情绪图片评定",
            paradigm="emotion",
            conditions=["正性", "负性", "中性"],
            instructions="请认真观看图片后，对图片的情绪效价进行评定。\n"
                         "1=非常不愉快  5=中性  9=非常愉快",
            response_keys=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            n_blocks=1,
            n_trials_per_block=n_trials_per_condition * 3,
            n_practice_trials=4,
            show_feedback=False,
        ),
        "memory": PsychoPyExperiment(
            title="记忆再认任务",
            paradigm="memory",
            conditions=["旧项目", "新项目"],
            instructions="请判断当前呈现的词语是否在学习阶段出现过。\n"
                         "出现过（旧）→按F键  未出现过（新）→按J键",
            response_keys=["f", "j"],
            n_blocks=2,
            n_trials_per_block=n_trials_per_condition * 2,
            n_practice_trials=6,
            show_feedback=True,
            feedback_duration=0.8,
        ),
    }

    config = paradigm_configs.get(paradigm)
    if config is None:
        raise ValueError(
            f"未知范式 '{paradigm}'。支持的范式：{list(paradigm_configs.keys())}"
        )

    return config


def generate_latin_square_psychopy(
    conditions: List[str],
    n_subjects: int = 30,
) -> List[List[str]]:
    """
    为 PsychoPy 实验生成拉丁方平衡列表。
    每个被试按分配顺序执行条件。
    """
    k = len(conditions)
    if k < 2:
        return [conditions.copy() for _ in range(n_subjects)]

    # 构建基本方阵
    square = []
    for i in range(k):
        row = []
        for j in range(k):
            row.append(conditions[(i + j) % k])
        square.append(row)

    # 扩展至被试数
    result = []
    for subj in range(n_subjects):
        result.append(list(square[subj % k]))
        # 奇数被试顺序反转以增强平衡
        if subj % k == 0 and subj > 0:
            random.shuffle(square)

    return result


# ============================================================
# 脚本生成器内部逻辑
# ============================================================


def _build_script(exp: PsychoPyExperiment) -> str:
    """组装完整的 PsychoPy Python 脚本"""
    parts = []
    parts.append(_script_header(exp))
    parts.append(_script_imports())
    parts.append(_script_window_setup(exp))
    parts.append(_script_stimuli_setup(exp))
    parts.append(_script_trial_list(exp))
    parts.append(_script_routine_defs(exp))
    parts.append(_script_main_loop(exp))
    return "\n\n".join(parts)


def _script_header(exp: PsychoPyExperiment) -> str:
    return textwrap.dedent(f"""\
    #!/usr/bin/env python
    # -*- coding: utf-8 -*-
    \"\"\"
    {exp.title} — PsychoPy 实验程序
    范式：{exp.paradigm}
    条件：{', '.join(exp.conditions)}
    区组：{exp.n_blocks} × {exp.n_trials_per_block} 试次
    自动生成于 PsychoPy 实验生成器
    \"\"\"
    """)


def _script_imports() -> str:
    return textwrap.dedent("""\
    from psychopy import visual, core, event, gui, data
    from psychopy.hardware import keyboard
    import numpy as np
    import random
    import csv
    import os
    from datetime import datetime
    from pathlib import Path
    """)


def _script_window_setup(exp: PsychoPyExperiment) -> str:
    fs = "True" if exp.fullscreen else "False"
    return textwrap.dedent(f"""\
    # ========== 窗口与计时器设置 ==========
    win = visual.Window(
        size=[1024, 768],
        fullscr={fs},
        units="pix",
        color=(0, 0, 0),
        colorSpace="rgb",
    )
    globalClock = core.Clock()
    kb = keyboard.Keyboard()
    """)


def _script_stimuli_setup(exp: PsychoPyExperiment) -> str:
    lines = ["# ========== 刺激材料 =========="]
    lines.append("# 注视点")
    lines.append(
        "fixation = visual.TextStim(win, text='+', color='white', "
        "height=32, pos=(0, 0))"
    )
    lines.append("# 指导语")
    lines.append(
        "instruction_text = visual.TextStim(win, text=" +
        json.dumps(exp.instructions) +
        ", color='white', height=24, wrapWidth=800)"
    )
    lines.append("# 试次刺激（运行时更新）")
    lines.append(
        "trial_stim = visual.TextStim(win, text='', color='white', "
        "height=48, pos=(0, 0))"
    )
    lines.append("# 反馈文本")
    lines.append(
        "feedback = visual.TextStim(win, text='', color='green', "
        "height=28, pos=(0, -80))"
    )
    return "\n".join(lines)


def _script_trial_list(exp: PsychoPyExperiment) -> str:
    """生成试次列表（含条件和随机化）"""
    lines = ["# ========== 试次列表 =========="]

    if exp.stimuli_text:
        stim_str = "[" + ", ".join(f"'{s}'" for s in exp.stimuli_text) + "]"
        lines.append(f"stimuli = {stim_str}")
    else:
        lines.append("stimuli = ['刺激A', '刺激B', '刺激C', '刺激D']")

    cond_str = "[" + ", ".join(f"'{c}'" for c in exp.conditions) + "]"
    lines.append(f"conditions = {cond_str}")

    lines.append("")
    lines.append("practice_trials = []")
    lines.append(f"for i in range({exp.n_practice_trials}):")
    lines.append("    practice_trials.append({")
    lines.append("        'stimulus': random.choice(stimuli),")
    lines.append("        'condition': random.choice(conditions),")
    lines.append("        'is_practice': True,")
    lines.append("    })")
    lines.append("")
    lines.append("experimental_trials = []")
    lines.append(f"for block in range({exp.n_blocks}):")
    for ci, cond in enumerate(exp.conditions):
        lines.append(
            f"    for _ in range({exp.n_trials_per_block // len(exp.conditions)}):"
        )
        lines.append("        experimental_trials.append({")
        lines.append("            'stimulus': random.choice(stimuli),")
        lines.append(f"            'condition': '{cond}',")
        lines.append("            'is_practice': False,")
        lines.append("            'block': block,")
        lines.append("        })")
    lines.append("random.shuffle(experimental_trials)")
    lines.append("")
    lines.append("all_trials = practice_trials + experimental_trials")
    lines.append(f"n_trials = len(all_trials)")

    return "\n".join(lines)


def _script_routine_defs(exp: PsychoPyExperiment) -> str:
    """定义试次呈现流程"""
    feedback_lines = ""
    if exp.show_feedback:
        feedback_lines = textwrap.dedent(f"""\
            # 反馈
            if trial.get('is_practice'):
                if correct:
                    feedback.text = '正确！'
                    feedback.color = 'green'
                else:
                    feedback.text = '错误'
                    feedback.color = 'red'
                feedback.draw()
                win.flip()
                core.wait({exp.feedback_duration})
        """)

    keys_str = "[" + ", ".join(f"'{k}'" for k in exp.response_keys) + "]"

    # Determine correct response mapping per paradigm
    correct_logic = _correct_response_logic(exp)

    return textwrap.dedent(f"""\
    # ========== 试次呈现例程 ==========
    def run_trial(trial, trial_num):
        \"\"\"运行单个试次\"\"\"
        # 注视点
        fixation.draw()
        win.flip()
        core.wait(random.uniform({exp.iti_min}, {exp.iti_max}))

        # 呈现刺激
        trial_stim.text = trial['stimulus']
        trial_stim.draw()
        win.flip()

        # 记录反应
        kb.clearEvents()
        timer = core.Clock()
        response = None
        rt = None
        keys = {keys_str}
        correct = None

        while timer.getTime() < 2.5:
            key_events = kb.getKeys(keys, waitRelease=False)
            if key_events:
                response = key_events[0].name
                rt = timer.getTime()
                break
            core.wait(0.001)

        # 判断正确性
        {correct_logic}

        {feedback_lines}

        # 试次间间隔
        fixation.draw()
        win.flip()
        core.wait(random.uniform({exp.iti_min}, {exp.iti_max}))

        return {{
            'trial_num': trial_num,
            'stimulus': trial['stimulus'],
            'condition': trial['condition'],
            'block': trial.get('block', -1),
            'is_practice': trial['is_practice'],
            'response': response,
            'rt': round(rt * 1000, 1) if rt else None,
            'correct': correct,
            'timestamp': datetime.now().isoformat(),
        }}
    """)


def _correct_response_logic(exp: PsychoPyExperiment) -> str:
    """根据范式生成正确反应判断逻辑"""
    if exp.paradigm in ("stroop", "flanker"):
        # 基于颜色/方向判断
        if exp.paradigm == "stroop":
            return textwrap.dedent("""\
        if response:
            # Stroop: 红色→f, 绿色→j
            color_to_key = {'红': 'f', '绿': 'j', '蓝': 'f', '黄': 'j'}
            expected = None
            for color, key in color_to_key.items():
                if color in trial['stimulus']:
                    expected = key
                    break
            correct = (response == expected) if expected else None""")
        else:
            return textwrap.dedent("""\
        if response:
            # Flanker: 左箭头(<<)→f, 右箭头(>>)→j
            if '<' in trial['stimulus'][2]:
                correct = (response == 'f')
            else:
                correct = (response == 'j')""")
    elif exp.paradigm == "memory":
        return textwrap.dedent("""\
        if response:
            # 记忆: 旧→f, 新→j
            expected = 'f' if trial['condition'] == '旧项目' else 'j'
            correct = (response == expected)""")
    else:
        return "        correct = None  # 无正确反应的范式"


def _script_main_loop(exp: PsychoPyExperiment) -> str:
    """主实验循环"""
    return textwrap.dedent(f"""\
    # ========== 主实验流程 ==========

    # 被试信息
    exp_info = {{
        '被试编号': '',
        '年龄': '',
        '性别': ['男', '女', '其他'],
    }}
    dlg = gui.DlgFromDict(exp_info, title='{exp.title}', fixed=['被试编号'])
    if not dlg.OK:
        core.quit()

    subj_id = exp_info['被试编号'] or 'unknown'

    # 数据目录
    Path('{exp.data_dir}').mkdir(parents=True, exist_ok=True)
    data_file = f'{exp.data_dir}/subj_{{subj_id}}_{exp.paradigm}_{{datetime.now().strftime("%Y%m%d_%H%M%S")}}.csv'

    # 指导语
    instruction_text.draw()
    win.flip()
    kb.waitKeys(keyList=['space'])

    # 练习阶段
    fixation.draw()
    win.flip()
    core.wait(0.5)
    practice_start = globalClock.getTime()

    practice_results = []
    for i, trial in enumerate(practice_trials):
        result = run_trial(trial, i + 1)
        practice_results.append(result)

    # 练习反馈
    n_correct = sum(1 for r in practice_results if r['correct'])
    feedback.text = f'练习结束：正确{{n_correct}}/{{len(practice_results)}}'
    feedback.color = 'yellow'
    feedback.draw()
    win.flip()
    core.wait(2.0)

    # 正式实验
    for block in range({exp.n_blocks}):
        # 区组开始提示
        if {exp.n_blocks} > 1:
            block_msg = visual.TextStim(
                win, text=f'第{{block + 1}}/{exp.n_blocks}区组即将开始\\\\n按空格键继续',
                color='white', height=24
            )
            block_msg.draw()
            win.flip()
            kb.waitKeys(keyList=['space'])

        block_trials = [t for t in experimental_trials if t.get('block') == block]
        for i, trial in enumerate(block_trials):
            result = run_trial(trial, block * len(block_trials) + i + 1)

            # 写入数据
            write_header = not os.path.exists(data_file)
            with open(data_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=result.keys())
                if write_header:
                    writer.writeheader()
                writer.writerow(result)

        # 区组间休息
        if block < {exp.n_blocks} - 1:
            rest_msg = visual.TextStim(
                win, text='区组结束，请休息一下。\\\\n按空格键继续下一个区组。',
                color='white', height=24
            )
            rest_msg.draw()
            win.flip()
            kb.waitKeys(keyList=['space'])

    # 结束页面
    end_msg = visual.TextStim(
        win, text='实验结束，感谢您的参与！\\\\n按空格键退出。',
        color='white', height=24
    )
    end_msg.draw()
    win.flip()
    kb.waitKeys(keyList=['space'])

    win.close()
    core.quit()
    """)
