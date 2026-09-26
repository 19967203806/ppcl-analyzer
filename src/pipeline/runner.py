from pathlib import Path
from typing import Dict
from datetime import datetime
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from .graph import build_analysis_graph
from .remove_comment import CodeCleaner
from .logic_block import Logicblock
from .data_point import DataPoint
from .logic_doc import LogicDoc
from .flow_chart import FlowChart
from .sequence_chart import SequenceChart
from ..utils.model_factory import create_chat_model

class PipelineRunner:
    def __init__(
        self,
        input_file: Path,
        output_base_dir: str = "output",
        language: str = "en",
        max_workers: int = 4,
        model: BaseChatModel | None = None,
    ):
        self.language = language
        self.model = model or create_chat_model()
        self.code_cleaner = CodeCleaner()
        self.logic_block_generator = Logicblock(language=self.language, model=self.model)
        self.data_point_generator = DataPoint(language=self.language, model=self.model)
        self.logic_doc_generator = LogicDoc(language=self.language, model=self.model)
        self.flowchart_generator = FlowChart(language=self.language, model=self.model)
        self.sequencechart_generator = SequenceChart(language=self.language, model=self.model)
        self.file_name = input_file.stem
        self.input_file = input_file
        self.output_dir = Path(output_base_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Configure a single per-run log file using Loguru with size-based rotation
        run_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{run_ts}.log"
        logger.remove()
        logger.add(
            str(log_path),
            level="INFO",
            rotation="10 MB",
            backtrace=True,
            diagnose=False,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function} | {message}"
        )
        self.logger = logger
        self.logger.info("PipelineRunner initialized")
        self.max_workers = max_workers
        self.graph = build_analysis_graph(
            cleaner=self.code_cleaner,
            logic_blocks=self.logic_block_generator,
            data_points=self.data_point_generator,
            logic_doc=self.logic_doc_generator,
            flowchart=self.flowchart_generator,
            sequence_chart=self.sequencechart_generator,
        )

    def _run_clean_code(self, input_file: Path) -> Path:
        cleaned_code_path = self.output_dir / "cleaned_code.ppcl"
        cleaned_lines = self.code_cleaner.clean_code(input_file, cleaned_code_path)
        if not cleaned_lines:
            raise ValueError("cleaned PPCL code is empty")
        self.logger.info(f"清洗代码完成: {cleaned_code_path}")
        return cleaned_code_path

    def _run_logic_blocks(self, original_code_path: Path) -> tuple[Path, dict]:
        logic_blocks_path = self.output_dir / "logic_blocks.md"
        usage = self.logic_block_generator.generate_logic_blocks(original_code_path, logic_blocks_path)
        self.logger.info(f"逻辑块生成完成: {logic_blocks_path}")
        return logic_blocks_path, usage

    def _run_data_points(self, cleaned_code_path: Path, logic_blocks_path: Path) -> tuple[Path, dict]:
        data_points_path = self.output_dir / "data_points.md"
        usage = self.data_point_generator.generate_data_points(
            code_path=cleaned_code_path,
            logic_blocks_file_path=logic_blocks_path,
            output_file_path=data_points_path,
        )
        self.logger.info(f"数据点生成完成: {data_points_path}")
        return data_points_path, usage

    def _run_logic_doc(self, cleaned_code_path: Path, logic_blocks_path: Path) -> tuple[Path, dict]:
        logic_doc_path = self.output_dir / "logic_doc.md"
        usage = self.logic_doc_generator.generate_logic_doc(
            logic_blocks_file_path=logic_blocks_path,
            ppcl_code_file_path=cleaned_code_path,
            output_file_path=logic_doc_path,
        )
        self.logger.info(f"逻辑文档生成完成: {logic_doc_path}")
        return logic_doc_path, usage

    def _run_flowchart(self, cleaned_code_path: Path, logic_blocks_path: Path) -> tuple[Path, dict]:
        flowchart_dot_path = self.output_dir / "flowchart.dot"
        flowchart_pdf_path = self.output_dir / "flowchart.pdf"
        flow_result = self.flowchart_generator.generate_dot_code(
            cleaned_code_path=cleaned_code_path,
            logic_blocks_path=logic_blocks_path,
            output_dot_path=flowchart_dot_path,
            output_pdf_path=flowchart_pdf_path,
        )
        self.logger.info(f"流程图生成完成: {flowchart_pdf_path}")
        return flowchart_pdf_path, flow_result["usage"]

    def _run_sequencechart(self, cleaned_code_path: Path, logic_blocks_path: Path) -> tuple[Path, dict]:
        seq_path = self.output_dir / "sequence_chart.mmd"
        seq_pdf_path = self.output_dir / "sequence_chart.pdf"
        seq_result = self.sequencechart_generator.generate_mermaid_code(
            cleaned_code_path=cleaned_code_path,
            logic_blocks_path=logic_blocks_path,
            output_mermaid_path=seq_path,
            output_pdf_path=seq_pdf_path,
        )
        self.logger.info(f"时序图生成完成: {seq_pdf_path}")
        return seq_pdf_path, seq_result["usage"]

    def run_sequential(self) -> Dict[str, Path | dict]:
        self.logger.info(f"运行串行流水线: {self.file_name}")
        return self._invoke_graph(max_concurrency=1)

    def run_parallel(self) -> Dict[str, Path | dict]:
        results = self._invoke_graph(max_concurrency=self.max_workers)
        self.logger.info(f"运行并行流水线完成: {self.file_name}")
        return results

    def _invoke_graph(self, max_concurrency: int) -> Dict[str, Path | dict]:
        results = self.graph.invoke(
            {
                "input_file": self.input_file,
                "output_dir": self.output_dir,
                "usages": [],
                "warnings": [],
            },
            {"max_concurrency": max_concurrency},
        )
        self.logger.info(f"token数消耗: prompt={results['prompt_tokens']}, completion={results['completion_tokens']}, total={results['total_tokens']}")
        return results
