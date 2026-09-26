from pathlib import Path

from src.pipeline.graph import build_analysis_graph, build_flowchart_graph


class Cleaner:
    def clean_code(self, source, output):
        output.write_text("CLEAN", encoding="utf-8")
        return ["CLEAN"]


class LogicBlocks:
    def generate_logic_blocks(self, source, output):
        output.write_text("BLOCKS", encoding="utf-8")
        return {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}


class DataPoints:
    def generate_data_points(self, code, blocks, output):
        output.write_text("DATA", encoding="utf-8")
        return {"prompt_tokens": 2, "completion_tokens": 0, "total_tokens": 2}


class FailingLogicDoc:
    def generate_logic_doc(self, blocks, code, output):
        raise RuntimeError("document failed")


class LogicDoc:
    def generate_logic_doc(self, blocks, code, output):
        output.write_text("DOC", encoding="utf-8")
        return {"prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1}


class Flow:
    max_regenerate = 1
    max_retries = 2

    def __init__(self):
        self.render_calls = 0
        self.repair_calls = 0

    def _generate_dot_code(self, **kwargs):
        kwargs["output_file_path"].write_text("digraph {}", encoding="utf-8")
        return {
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 1,
                "total_tokens": 4,
            }
        }

    def _dot_to_pdf(self, code_path, pdf_path):
        self.render_calls += 1
        pdf_path.write_bytes(b"PDF")
        return ""

    def _retry_with_error_info(self, code_path, error):
        self.repair_calls += 1
        return {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1}


class Sequence:
    max_regenerate = 1
    max_retries = 2

    def _generate_mermaid_code(self, **kwargs):
        kwargs["output_file_path"].write_text(
            "sequenceDiagram", encoding="utf-8"
        )
        return {
            "usage": {
                "prompt_tokens": 4,
                "completion_tokens": 1,
                "total_tokens": 5,
            }
        }

    def _mermaid_to_chart(self, code_path, pdf_path):
        pdf_path.write_bytes(b"PDF")
        return ""

    def _retry_with_error_info(self, code_path, error):
        return {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1}


def test_analysis_graph_parallel_branches_aggregate_and_degrade(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.ppcl"
    source.write_text("PPCL", encoding="utf-8")
    monkeypatch.setattr(
        "src.pipeline.graph.shutil.which", lambda command: f"/usr/bin/{command}"
    )
    graph = build_analysis_graph(
        cleaner=Cleaner(),
        logic_blocks=LogicBlocks(),
        data_points=DataPoints(),
        logic_doc=FailingLogicDoc(),
        flowchart=Flow(),
        sequence_chart=Sequence(),
    )

    result = graph.invoke(
        {
            "input_file": source,
            "output_dir": tmp_path,
            "usages": [],
            "warnings": [],
        }
    )

    assert result["data_points"] == tmp_path / "data_points.md"
    assert result["logic_doc"] is None
    assert result["flowchart"].exists()
    assert result["sequence_chart"].exists()
    assert result["total_tokens"] == 13
    assert result["warnings"] == ["logic_doc: document failed"]


def test_flowchart_subgraph_repairs_then_renders(tmp_path, monkeypatch):
    class RepairingFlow(Flow):
        def _dot_to_pdf(self, code_path, pdf_path):
            self.render_calls += 1
            if self.render_calls == 1:
                return "syntax error"
            pdf_path.write_bytes(b"PDF")
            return ""

    generator = RepairingFlow()
    monkeypatch.setattr("src.pipeline.graph.shutil.which", lambda _: "/usr/bin/dot")
    graph = build_flowchart_graph(generator)
    source = tmp_path / "source.ppcl"
    blocks = tmp_path / "blocks.md"
    source.write_text("PPCL", encoding="utf-8")
    blocks.write_text("BLOCKS", encoding="utf-8")

    result = graph.invoke(
        {
            "cleaned_code": source,
            "logic_blocks": blocks,
            "code_path": tmp_path / "flow.dot",
            "pdf_path": tmp_path / "flow.pdf",
            "generation_attempts": 0,
            "repair_attempts": 0,
            "usages": [],
        }
    )

    assert result["success"] is True
    assert generator.repair_calls == 1
    assert generator.render_calls == 2
    assert sum(item["total_tokens"] for item in result["usages"]) == 5


def test_flowchart_subgraph_preserves_usage_when_repair_fails(
    tmp_path, monkeypatch
):
    class FailedRepairFlow(Flow):
        def _dot_to_pdf(self, code_path, pdf_path):
            return "syntax error"

        def _retry_with_error_info(self, code_path, error):
            raise RuntimeError("repair model unavailable")

    generator = FailedRepairFlow()
    monkeypatch.setattr("src.pipeline.graph.shutil.which", lambda _: "/usr/bin/dot")
    graph = build_flowchart_graph(generator)
    source = tmp_path / "source.ppcl"
    blocks = tmp_path / "blocks.md"
    source.write_text("PPCL", encoding="utf-8")
    blocks.write_text("BLOCKS", encoding="utf-8")

    result = graph.invoke(
        {
            "cleaned_code": source,
            "logic_blocks": blocks,
            "code_path": tmp_path / "flow.dot",
            "pdf_path": tmp_path / "flow.pdf",
            "generation_attempts": 0,
            "repair_attempts": 0,
            "usages": [],
        }
    )

    assert result["fatal_error"] == "repair failed: repair model unavailable"
    assert sum(item["total_tokens"] for item in result["usages"]) == 4


def test_missing_server_renderers_are_not_user_warnings(tmp_path, monkeypatch):
    source = tmp_path / "source.ppcl"
    source.write_text("PPCL", encoding="utf-8")
    monkeypatch.setattr("src.pipeline.graph.shutil.which", lambda _: None)
    graph = build_analysis_graph(
        cleaner=Cleaner(),
        logic_blocks=LogicBlocks(),
        data_points=DataPoints(),
        logic_doc=LogicDoc(),
        flowchart=Flow(),
        sequence_chart=Sequence(),
    )

    result = graph.invoke(
        {
            "input_file": source,
            "output_dir": tmp_path,
            "usages": [],
            "warnings": [],
        }
    )

    assert result["warnings"] == []
    assert result["flowchart"] is None
    assert result["sequence_chart"] is None
    assert result["flowchart_code"].exists()
    assert result["sequence_chart_code"].exists()
