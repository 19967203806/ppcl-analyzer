from pathlib import Path
import shutil

from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from ..utils.model_factory import create_chat_model, invoke_text
import re
import subprocess
from ..utils.eng_prompts import sequencechart_system_prompt as eng_sequence_system_prompt, sequencechart_user_prompt as eng_sequence_user_prompt
from ..utils.eng_prompts import fix_sequencechart_system_prompt as eng_fix_sequencechart_system_prompt, fix_sequencechart_user_prompt as eng_fix_sequencechart_user_prompt
from ..utils.mermaid_utils import normalize_sequence_mermaid

class SequenceChart:
    def __init__(self, language: str = "en", max_regenerate: int = 3, max_retries: int = 20, model: BaseChatModel | None = None):
        self.language = language
        self.logger = logger
        self.model = model or create_chat_model()
        self.max_regenerate = max_regenerate
        self.max_retries = max_retries
        # For now only English prompts are available; keep logic identical
        self.sequence_system_prompt = eng_sequence_system_prompt
        self.sequence_user_prompt = eng_sequence_user_prompt
        # Use existing flowchart fix prompts for generic Mermaid repair
        self.fix_system_prompt = eng_fix_sequencechart_system_prompt
        self.fix_user_prompt_tmpl = eng_fix_sequencechart_user_prompt

    def _strip_mermaid_fences(self, mermaid_code: str) -> str:
        mermaid_code = re.sub(r"```mermaid", "", mermaid_code)
        mermaid_code = re.sub(r"```", "", mermaid_code)
        return mermaid_code.strip()

    def _generate_mermaid_code(self, logic_blocks_file_path: Path, ppcl_code_file_path: Path, output_file_path: Path) -> dict:
        with open(logic_blocks_file_path, "r", encoding="utf-8") as file:
            logic_blocks = file.readlines()
        with open(ppcl_code_file_path, "r", encoding="utf-8") as file:
            ppcl_code = file.readlines()
        system_prompt = self.sequence_system_prompt
        user_prompt = self.sequence_user_prompt.format(logic_blocks="\n".join(logic_blocks), ppcl_code="\n".join(ppcl_code))
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        mermaid_code = result["content"]
        usage = result.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        mermaid_code = normalize_sequence_mermaid(self._strip_mermaid_fences(mermaid_code))
        if not output_file_path.parent.exists():
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(mermaid_code)
        return {"mermaid_code": mermaid_code, "usage": usage}
    
    def _mermaid_to_chart(self, mermaid_code_path: Path, output_file_path: Path) -> None:
        cmd = ["mmdc", "-i", mermaid_code_path, "-o", output_file_path, "-p", "puppeteer-config.json","--pdfFit"]
        try:
            result = subprocess.run(cmd, check=False, capture_output=True)
            if result.returncode != 0:
                return result.stderr
            return ""
        except Exception as e:
            return str(e)

    def _retry_with_error_info(self, mermaid_code_path: Path, error_info: str) -> dict:
        self.logger.info("开始修复mermaid代码（Sequence Chart）")
        self.logger.info(f"错误信息: {error_info}")
        with open(mermaid_code_path, "r", encoding="utf-8") as file:
            mermaid_code = file.read()
        system_prompt = self.fix_system_prompt
        user_prompt = self.fix_user_prompt_tmpl.format(flowchart=mermaid_code, error_info=error_info)
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        fixed_code = result["content"]
        usage = result.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        fixed_code = normalize_sequence_mermaid(self._strip_mermaid_fences(fixed_code))
        with open(mermaid_code_path, "w", encoding="utf-8") as file:
            file.write(fixed_code)
        return usage

    def generate_mermaid_code(self, cleaned_code_path: Path, logic_blocks_path: Path, output_mermaid_path: Path, output_pdf_path: Path) -> dict:
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for _ in range(self.max_regenerate):
            gen_result = self._generate_mermaid_code(logic_blocks_file_path=logic_blocks_path,ppcl_code_file_path=cleaned_code_path,output_file_path=output_mermaid_path)
            for k in total_usage:
                total_usage[k] += gen_result["usage"].get(k, 0)
            if shutil.which("mmdc") is None:
                self.logger.warning("Mermaid CLI 'mmdc' is not installed; skipping sequence chart PDF rendering")
                return {"success": False, "usage": total_usage}
            for _ in range(self.max_retries):
                error_info = self._mermaid_to_chart(mermaid_code_path=output_mermaid_path,output_file_path=output_pdf_path)
                if error_info == "":
                    return {"success": True, "usage": total_usage}
                fix_usage = self._retry_with_error_info(mermaid_code_path=output_mermaid_path, error_info=error_info)
                for k in total_usage:
                    total_usage[k] += fix_usage.get(k, 0)
        return {"success": False, "usage": total_usage}

if __name__ == "__main__":
    seq = SequenceChart()
    output_file_dir = Path("output/abc")
    seq.generate_mermaid_code(cleaned_code_path=Path("output/1/a1/original_code.ppcl"), logic_blocks_path=Path("output/1/a1/logic_blocks.md"), output_mermaid_path=Path("output/abc/sequence_chart.mmd"), output_pdf_path=Path("output/abc/sequence_chart.pdf"))
    sequence_pdf_path = output_file_dir / "sequence_chart.pdf"
    if sequence_pdf_path.exists():
        logger.info(f"sequence chart generated: {sequence_pdf_path}")
    else:
        logger.error(f"sequence chart not generated: {sequence_pdf_path}")
