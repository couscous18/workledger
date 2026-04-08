import importlib.util
from pathlib import Path
from types import ModuleType


def _load_hf_runtime() -> ModuleType:
    runtime_path = Path("hf/software-capex-review/runtime.py")
    spec = importlib.util.spec_from_file_location("workledger_hf_runtime", runtime_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hf_runtime_helpers_smoke() -> None:
    runtime = _load_hf_runtime()

    cases = runtime.load_cases(runtime.DEFAULT_DATASET_PATH)
    assert len(cases) >= 1

    result = runtime.evaluate_cases(cases[:2])
    markdown = runtime.render_markdown(result)

    assert result["per_case"]
    assert result["classifications"]
    assert "Software capex review bundle" in markdown
