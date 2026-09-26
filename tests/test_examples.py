from pathlib import Path

import pytest

from src.pipeline.remove_comment import CodeCleaner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    PROJECT_ROOT / "examples" / "minimal_demo.ppcl",
    PROJECT_ROOT / "examples" / "synthetic_chiller_plant_demo.ppcl",
]


@pytest.mark.parametrize("example_path", EXAMPLES)
def test_synthetic_examples_are_cleanable(example_path, tmp_path):
    source = example_path.read_text(encoding="utf-8")
    assert "SYNTHETIC" in source

    destination = tmp_path / example_path.name
    cleaned_lines = CodeCleaner(output_base_dir=str(tmp_path)).clean_code(
        example_path, destination
    )

    assert cleaned_lines
    assert destination.read_text(encoding="utf-8").strip()
