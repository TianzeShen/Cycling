from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent.parent
AI_DIR = BASE_DIR / "RideSmart AI"


def load_ai_module(module_name: str) -> ModuleType:
    module_path = AI_DIR / f"{module_name}.py"
    spec = spec_from_file_location(f"ridesmart_ai_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load AI module: {module_name}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_ai_function(module_name: str, function_name: str) -> Callable[..., Any]:
    module = load_ai_module(module_name)
    function = getattr(module, function_name, None)
    if function is None:
        raise AttributeError(f"{function_name} not found in {module_name}.py")
    return function


compute_feasibility_score = load_ai_function(
    "scoring_model",
    "compute_feasibility_score",
)
compute_safety_score = load_ai_function(
    "safety_scorer",
    "compute_safety_score",
)
generate_explanations = load_ai_function(
    "explanations",
    "generate_explanations",
)
detect_route_risk = load_ai_function(
    "risk_detection",
    "detect_route_risk",
)
