"""实验设计系统 — 自动生成符合心理学标准的完整实验设计方案"""

from .design_engine import ExperimentDesignEngine, ExperimentDesign
from .power_analysis import (
    calculate_sample_size, format_power_report, PowerResult,
    quick_sample_size,
)
from .procedure_builder import (
    build_full_procedure, generate_latin_square,
    generate_randomization, generate_instructions,
    ExperimentProcedure,
)
from .experiment_templates import (
    DesignTemplate, get_template, list_templates,
    recommend_template, TEMPLATES,
)
from .jspsych_data_importer import (
    JsPsychData,
    parse_jspsych_csv,
    parse_jspsych_json,
    to_wide_format,
    extract_condition_variables,
    get_summary_stats,
    get_trial_timeline,
)
from .preregistration import (
    PreregistrationDoc,
    generate_preregistration,
    generate_preregistration_from_analysis,
    validate_preregistration,
)
from .psychopy_generator import (
    PsychoPyExperiment,
    generate_psychopy_script,
    generate_standard_paradigm,
    generate_latin_square_psychopy,
)
from .single_subject import (
    SingleSubjectDesign, SingleSubjectResult,
    create_ab_design, create_multiple_baseline_design,
    analyze_single_subject, analyze_multiple_behaviors,
    format_single_subject_report,
)
from .llm_engine import (
    design_experiment_llm,
    design_experiment_llm_async,
    cancel_design_request,
    CancelledLLMError,
    LLMEngineError,
)

__all__ = [
    "ExperimentDesignEngine", "ExperimentDesign",
    "calculate_sample_size", "format_power_report", "PowerResult",
    "quick_sample_size",
    "build_full_procedure", "generate_latin_square",
    "generate_randomization", "generate_instructions",
    "ExperimentProcedure",
    "DesignTemplate", "get_template", "list_templates",
    "recommend_template", "TEMPLATES",
    "JsPsychData", "parse_jspsych_csv", "parse_jspsych_json",
    "to_wide_format", "extract_condition_variables",
    "get_summary_stats", "get_trial_timeline",
    "PreregistrationDoc", "generate_preregistration",
    "generate_preregistration_from_analysis",
    "validate_preregistration",
    "PsychoPyExperiment", "generate_psychopy_script",
    "generate_standard_paradigm",
    "generate_latin_square_psychopy",
    "SingleSubjectDesign", "SingleSubjectResult",
    "create_ab_design", "create_multiple_baseline_design",
    "analyze_single_subject", "analyze_multiple_behaviors",
    "format_single_subject_report",
    "design_experiment_llm", "design_experiment_llm_async",
    "cancel_design_request", "CancelledLLMError", "LLMEngineError",
]
