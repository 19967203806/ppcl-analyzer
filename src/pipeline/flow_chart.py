from pathlib import Path
import shutil

from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from ..utils.prompts import flowchart_system_prompt, flowchart_user_prompt
from ..utils.prompts import fix_flowchart_system_prompt, fix_flowchart_user_prompt
from ..utils.model_factory import create_chat_model, invoke_text
from ..utils.graphviz_utils import is_probably_dot, normalize_dot_for_display
import re
from ..utils.eng_prompts import flowchart_system_prompt as eng_flowchart_system_prompt, flowchart_user_prompt as eng_flowchart_user_prompt
from ..utils.eng_prompts import fix_flowchart_system_prompt as eng_fix_flowchart_system_prompt, fix_flowchart_user_prompt as eng_fix_sequencechart_user_prompt

class FlowChart:
    def __init__(self, language: str = "en", max_regenerate: int = 3, max_retries: int = 20, model: BaseChatModel | None = None):
        self.language = language
        self.logger = logger
        self.model = model or create_chat_model()
        self.max_regenerate = max_regenerate
        self.max_retries = max_retries
        if self.language == "en":
            self.flowchart_system_prompt = eng_flowchart_system_prompt
            self.flowchart_user_prompt = eng_flowchart_user_prompt
            self.fix_flowchart_system_prompt = eng_fix_flowchart_system_prompt
            self.fix_flowchart_user_prompt = eng_fix_sequencechart_user_prompt
        else:
            self.flowchart_system_prompt = flowchart_system_prompt
            self.flowchart_user_prompt = flowchart_user_prompt
            self.fix_flowchart_system_prompt = fix_flowchart_system_prompt
            self.fix_flowchart_user_prompt = fix_flowchart_user_prompt

    def _strip_code_fences(self, code: str) -> str:
        code = re.sub(r"```(mermaid|dot|graphviz)", "", code)
        code = re.sub(r"```", "", code)
        return code.strip()

    def _generate_dot_code(self, logic_blocks_file_path: Path, ppcl_code_file_path: Path, output_file_path: Path) -> dict:
        with open(logic_blocks_file_path, "r", encoding="utf-8") as file:
            logic_blocks = file.readlines()
        with open(ppcl_code_file_path, "r", encoding="utf-8") as file:
            ppcl_code = file.readlines()
        system_prompt = self.flowchart_system_prompt
        user_prompt = self.flowchart_user_prompt.format(logic_blocks="\n".join(logic_blocks), ppcl_code="\n".join(ppcl_code))
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        dot_code = result["content"]
        usage = result.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        dot_code = self._strip_code_fences(dot_code)
        if not is_probably_dot(dot_code):
            raise ValueError("model returned non-DOT flowchart content")
        dot_code = normalize_dot_for_display(dot_code)
        if not output_file_path.parent.exists():
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(dot_code)
        return {"dot_code": dot_code, "usage": usage}

    def _retry_with_error_info(self, code_path: Path, error_info: str) -> dict:
        self.logger.info("开始修复flowchart代码")
        self.logger.info(f"错误信息: {error_info}")
        with open(code_path, "r", encoding="utf-8") as file:
            current_code = file.read()
        system_prompt = self.fix_flowchart_system_prompt
        user_prompt = self.fix_flowchart_user_prompt.format(flowchart=current_code, error_info=error_info)
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        flowchart = result["content"]
        usage = result.get("usage")
        flowchart = self._strip_code_fences(flowchart)
        with open(code_path, "w", encoding="utf-8") as file:
            file.write(flowchart)
        return usage

    def _dot_to_pdf(self, dot_code_path: Path, output_pdf_path: Path) -> str:
        """Render DOT to PDF using Graphviz. Returns empty string on success, stderr/error text otherwise."""
        import subprocess
        cmd = ["dot", "-Tpdf", str(dot_code_path), "-o", str(output_pdf_path)]
        try:
            result = subprocess.run(cmd, check=False, capture_output=True)
            if result.returncode != 0:
                return result.stderr.decode("utf-8", errors="replace")
            return ""
        except Exception as e:
            return str(e)

    def generate_dot_code(self, cleaned_code_path: Path, logic_blocks_path: Path, output_dot_path: Path, output_pdf_path: Path | None = None) -> dict:
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for _ in range(self.max_regenerate):
            gen_result = self._generate_dot_code(logic_blocks_file_path=logic_blocks_path, ppcl_code_file_path=cleaned_code_path, output_file_path=output_dot_path)
            for k in total_usage:
                total_usage[k] += gen_result["usage"].get(k, 0)
            # Optional: validate by rendering to PDF if a path is provided
            if output_pdf_path is None:
                return {"success": True, "usage": total_usage}
            if shutil.which("dot") is None:
                self.logger.warning("Graphviz 'dot' is not installed; skipping flowchart PDF rendering")
                return {"success": False, "usage": total_usage}
            for _ in range(self.max_retries):
                error_info = self._dot_to_pdf(dot_code_path=output_dot_path, output_pdf_path=output_pdf_path)
                if error_info == "":
                    return {"success": True, "usage": total_usage}
                fix_usage = self._retry_with_error_info(code_path=output_dot_path, error_info=error_info)
                for k in total_usage:
                    total_usage[k] += fix_usage.get(k, 0)
        return {"success": False, "usage": total_usage}

if __name__ == "__main__":
    flowchart = FlowChart()
    output_file_dir = Path("output/abc")
    flowchart.generate_dot_code(
        cleaned_code_path=Path("output/1/a1/original_code.ppcl"),
        logic_blocks_path=Path("output/1/a1/logic_blocks.md"),
        output_dot_path=Path("output/abc/flowchart.dot"),
        output_pdf_path=Path("output/abc/flowchart.pdf"),
    )
    flowchart_dot_path = output_file_dir / "flowchart.dot"
    if flowchart_dot_path.exists():
        logger.info(f"flowchart generated: {flowchart_dot_path}")
    else:
        logger.error(f"flowchart not generated: {flowchart_dot_path}")
