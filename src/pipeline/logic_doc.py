from pathlib import Path
import re
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from ..utils.prompts import logic_doc_system_prompt, logic_doc_user_prompt
from ..utils.eng_prompts import logic_doc_system_prompt as eng_logic_doc_system_prompt, logic_doc_user_prompt as eng_logic_doc_user_prompt
from ..utils.model_factory import create_chat_model, invoke_text

class LogicDoc:
    def __init__(self, language: str = "en", model: BaseChatModel | None = None):
        self.language = language
        self.logger = logger
        self.model = model or create_chat_model()
        if self.language == "en":
            self.logic_doc_system_prompt = eng_logic_doc_system_prompt
            self.logic_doc_user_prompt = eng_logic_doc_user_prompt
        else:
            self.logic_doc_system_prompt = logic_doc_system_prompt
            self.logic_doc_user_prompt = logic_doc_user_prompt
    
    def generate_logic_doc(self, logic_blocks_file_path: Path, ppcl_code_file_path: Path, output_file_path: Path) -> None:
        with open(logic_blocks_file_path, "r", encoding="utf-8") as file:
            logic_blocks = file.readlines()
        with open(ppcl_code_file_path, "r", encoding="utf-8") as file:
            ppcl_code = file.readlines()
        system_prompt = self.logic_doc_system_prompt
        user_prompt = self.logic_doc_user_prompt.format(logic_blocks="\n".join(logic_blocks), ppcl_code="\n".join(ppcl_code))
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        logic_doc = result["content"]
        usage = result.get("usage")
        logic_doc = re.sub(r'(^```markdown\s*)|(\s*```$)', '', logic_doc)
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(logic_doc)
        return usage

if __name__ == "__main__":
    logic_doc = LogicDoc()
    logic_doc.generate_logic_doc(logic_blocks_file_path=Path("output/a/logic_blocks.md"), ppcl_code_file_path=Path("output/a/cleaned_code.ppcl"), output_file_path=Path("output/a/logic_doc.md"))
