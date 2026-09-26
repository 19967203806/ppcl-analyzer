import operator
import shutil
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from loguru import logger

from .data_point import DataPoint
from .flow_chart import FlowChart
from .logic_block import Logicblock
from .logic_doc import LogicDoc
from .remove_comment import CodeCleaner
from .sequence_chart import SequenceChart


Usage = dict[str, int]


class AnalysisState(TypedDict, total=False):
    input_file: Path
    output_dir: Path
    original_code: Path
    cleaned_code: Path
    logic_blocks: Path
    data_points: Path | None
    logic_doc: Path | None
    flowchart: Path | None
    flowchart_code: Path | None
    sequence_chart: Path | None
    sequence_chart_code: Path | None
    usages: Annotated[list[Usage], operator.add]
    warnings: Annotated[list[str], operator.add]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class RenderState(TypedDict, total=False):
    cleaned_code: Path
    logic_blocks: Path
    code_path: Path
    pdf_path: Path
    generation_attempts: int
    repair_attempts: int
    render_error: str
    fatal_error: str
    renderer_missing: bool
    success: bool
    usages: Annotated[list[Usage], operator.add]


def _zero_usage() -> Usage:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _usage(value: Usage | None) -> Usage:
    result = _zero_usage()
    for key in result:
        result[key] = int((value or {}).get(key, 0) or 0)
    return result


def build_flowchart_graph(generator: FlowChart):
    def generate(state: RenderState) -> dict[str, Any]:
        try:
            result = generator._generate_dot_code(
                logic_blocks_file_path=state["logic_blocks"],
                ppcl_code_file_path=state["cleaned_code"],
                output_file_path=state["code_path"],
            )
        except Exception as exc:
            return {
                "fatal_error": f"generation failed: {exc}",
                "success": False,
            }
        return {
            "generation_attempts": state.get("generation_attempts", 0) + 1,
            "repair_attempts": 0,
            "render_error": "",
            "fatal_error": "",
            "renderer_missing": False,
            "success": False,
            "usages": [_usage(result.get("usage"))],
        }

    def render(state: RenderState) -> dict[str, Any]:
        if shutil.which("dot") is None:
            return {
                "renderer_missing": True,
                "render_error": "Graphviz 'dot' is not installed",
                "success": False,
            }
        error = generator._dot_to_pdf(state["code_path"], state["pdf_path"])
        return {"render_error": error, "success": error == ""}

    def repair(state: RenderState) -> dict[str, Any]:
        try:
            usage = generator._retry_with_error_info(
                state["code_path"], state["render_error"]
            )
        except Exception as exc:
            return {
                "fatal_error": f"repair failed: {exc}",
                "success": False,
            }
        return {
            "repair_attempts": state.get("repair_attempts", 0) + 1,
            "fatal_error": "",
            "usages": [_usage(usage)],
        }

    def route_after_work(state: RenderState) -> Literal["render", "__end__"]:
        return END if state.get("fatal_error") else "render"

    def route(state: RenderState) -> Literal["repair", "generate", "__end__"]:
        if state.get("success") or state.get("renderer_missing"):
            return END
        if state.get("repair_attempts", 0) < generator.max_retries:
            return "repair"
        if state.get("generation_attempts", 0) < generator.max_regenerate:
            return "generate"
        return END

    builder = StateGraph(RenderState)
    builder.add_node("generate", generate)
    builder.add_node("render", render)
    builder.add_node("repair", repair)
    builder.add_edge(START, "generate")
    builder.add_conditional_edges("generate", route_after_work)
    builder.add_conditional_edges("render", route)
    builder.add_conditional_edges("repair", route_after_work)
    return builder.compile()


def build_sequence_graph(generator: SequenceChart):
    def generate(state: RenderState) -> dict[str, Any]:
        try:
            result = generator._generate_mermaid_code(
                logic_blocks_file_path=state["logic_blocks"],
                ppcl_code_file_path=state["cleaned_code"],
                output_file_path=state["code_path"],
            )
        except Exception as exc:
            return {
                "fatal_error": f"generation failed: {exc}",
                "success": False,
            }
        return {
            "generation_attempts": state.get("generation_attempts", 0) + 1,
            "repair_attempts": 0,
            "render_error": "",
            "fatal_error": "",
            "renderer_missing": False,
            "success": False,
            "usages": [_usage(result.get("usage"))],
        }

    def render(state: RenderState) -> dict[str, Any]:
        if shutil.which("mmdc") is None:
            return {
                "renderer_missing": True,
                "render_error": "Mermaid CLI 'mmdc' is not installed",
                "success": False,
            }
        error = generator._mermaid_to_chart(state["code_path"], state["pdf_path"])
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        return {"render_error": str(error), "success": error == ""}

    def repair(state: RenderState) -> dict[str, Any]:
        try:
            usage = generator._retry_with_error_info(
                state["code_path"], state["render_error"]
            )
        except Exception as exc:
            return {
                "fatal_error": f"repair failed: {exc}",
                "success": False,
            }
        return {
            "repair_attempts": state.get("repair_attempts", 0) + 1,
            "fatal_error": "",
            "usages": [_usage(usage)],
        }

    def route_after_work(state: RenderState) -> Literal["render", "__end__"]:
        return END if state.get("fatal_error") else "render"

    def route(state: RenderState) -> Literal["repair", "generate", "__end__"]:
        if state.get("success") or state.get("renderer_missing"):
            return END
        if state.get("repair_attempts", 0) < generator.max_retries:
            return "repair"
        if state.get("generation_attempts", 0) < generator.max_regenerate:
            return "generate"
        return END

    builder = StateGraph(RenderState)
    builder.add_node("generate", generate)
    builder.add_node("render", render)
    builder.add_node("repair", repair)
    builder.add_edge(START, "generate")
    builder.add_conditional_edges("generate", route_after_work)
    builder.add_conditional_edges("render", route)
    builder.add_conditional_edges("repair", route_after_work)
    return builder.compile()


def build_analysis_graph(
    *,
    cleaner: CodeCleaner,
    logic_blocks: Logicblock,
    data_points: DataPoint,
    logic_doc: LogicDoc,
    flowchart: FlowChart,
    sequence_chart: SequenceChart,
):
    flow_graph = build_flowchart_graph(flowchart)
    sequence_graph = build_sequence_graph(sequence_chart)

    def clean_code(state: AnalysisState) -> dict[str, Any]:
        path = state["output_dir"] / "cleaned_code.ppcl"
        cleaned_lines = cleaner.clean_code(state["input_file"], path)
        if not cleaned_lines:
            raise ValueError("cleaned PPCL code is empty")
        logger.info(f"清洗代码完成: {path}")
        return {"original_code": state["input_file"], "cleaned_code": path}

    def generate_logic_blocks(state: AnalysisState) -> dict[str, Any]:
        path = state["output_dir"] / "logic_blocks.md"
        usage = logic_blocks.generate_logic_blocks(state["cleaned_code"], path)
        logger.info(f"逻辑块生成完成: {path}")
        return {"logic_blocks": path, "usages": [_usage(usage)]}

    def generate_data_points(state: AnalysisState) -> dict[str, Any]:
        path = state["output_dir"] / "data_points.md"
        try:
            usage = data_points.generate_data_points(
                state["cleaned_code"], state["logic_blocks"], path
            )
            logger.info(f"数据点生成完成: {path}")
            return {"data_points": path, "usages": [_usage(usage)]}
        except Exception as exc:
            logger.error(f"步骤 data_points 失败: {exc}")
            return {"data_points": None, "warnings": [f"data_points: {exc}"]}

    def generate_logic_doc(state: AnalysisState) -> dict[str, Any]:
        path = state["output_dir"] / "logic_doc.md"
        try:
            usage = logic_doc.generate_logic_doc(
                state["logic_blocks"], state["cleaned_code"], path
            )
            logger.info(f"逻辑文档生成完成: {path}")
            return {"logic_doc": path, "usages": [_usage(usage)]}
        except Exception as exc:
            logger.error(f"步骤 logic_doc 失败: {exc}")
            return {"logic_doc": None, "warnings": [f"logic_doc: {exc}"]}

    def generate_flowchart(state: AnalysisState) -> dict[str, Any]:
        code_path = state["output_dir"] / "flowchart.dot"
        pdf_path = state["output_dir"] / "flowchart.pdf"
        try:
            result = flow_graph.invoke(
                {
                    "cleaned_code": state["cleaned_code"],
                    "logic_blocks": state["logic_blocks"],
                    "code_path": code_path,
                    "pdf_path": pdf_path,
                    "generation_attempts": 0,
                    "repair_attempts": 0,
                    "usages": [],
                },
                {"recursion_limit": 200},
            )
            warnings: list[str] = []
            if result.get("fatal_error"):
                warnings.append(f"flowchart: {result['fatal_error']}")
            elif not result.get("renderer_missing") and not result.get("success"):
                warnings.append(
                    f"flowchart: {result.get('render_error') or 'render failed'}"
                )
            return {
                "flowchart_code": code_path if code_path.exists() else None,
                "flowchart": pdf_path if pdf_path.exists() else None,
                "usages": result.get("usages", []),
                "warnings": warnings,
            }
        except Exception as exc:
            logger.error(f"步骤 flowchart 失败: {exc}")
            return {
                "flowchart": None,
                "flowchart_code": code_path if code_path.exists() else None,
                "warnings": [f"flowchart: {exc}"],
            }

    def generate_sequence_chart(state: AnalysisState) -> dict[str, Any]:
        code_path = state["output_dir"] / "sequence_chart.mmd"
        pdf_path = state["output_dir"] / "sequence_chart.pdf"
        try:
            result = sequence_graph.invoke(
                {
                    "cleaned_code": state["cleaned_code"],
                    "logic_blocks": state["logic_blocks"],
                    "code_path": code_path,
                    "pdf_path": pdf_path,
                    "generation_attempts": 0,
                    "repair_attempts": 0,
                    "usages": [],
                },
                {"recursion_limit": 200},
            )
            warnings: list[str] = []
            if result.get("fatal_error"):
                warnings.append(f"sequence_chart: {result['fatal_error']}")
            elif not result.get("renderer_missing") and not result.get("success"):
                warnings.append(
                    f"sequence_chart: {result.get('render_error') or 'render failed'}"
                )
            return {
                "sequence_chart_code": code_path if code_path.exists() else None,
                "sequence_chart": pdf_path if pdf_path.exists() else None,
                "usages": result.get("usages", []),
                "warnings": warnings,
            }
        except Exception as exc:
            logger.error(f"步骤 sequence_chart 失败: {exc}")
            return {
                "sequence_chart": None,
                "sequence_chart_code": code_path if code_path.exists() else None,
                "warnings": [f"sequence_chart: {exc}"],
            }

    def finalize(state: AnalysisState) -> dict[str, int]:
        totals = _zero_usage()
        for usage in state.get("usages", []):
            for key in totals:
                totals[key] += int(usage.get(key, 0) or 0)
        return totals

    builder = StateGraph(AnalysisState)
    builder.add_node("clean_code", clean_code)
    builder.add_node("logic_blocks", generate_logic_blocks)
    builder.add_node("data_points", generate_data_points)
    builder.add_node("logic_doc", generate_logic_doc)
    builder.add_node("flowchart", generate_flowchart)
    builder.add_node("sequence_chart", generate_sequence_chart)
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "clean_code")
    builder.add_edge("clean_code", "logic_blocks")
    for node in ("data_points", "logic_doc", "flowchart", "sequence_chart"):
        builder.add_edge("logic_blocks", node)
    builder.add_edge(
        ["data_points", "logic_doc", "flowchart", "sequence_chart"], "finalize"
    )
    builder.add_edge("finalize", END)
    return builder.compile()
