from pathlib import Path
import re
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from ..utils.prompts import logic_block_system_prompt, logic_block_user_prompt
from ..utils.eng_prompts import logic_block_system_prompt as eng_logic_block_system_prompt, logic_block_user_prompt as eng_logic_block_user_prompt
from ..utils.model_factory import create_chat_model, invoke_text

class Logicblock:
    def __init__(self, language: str = "en", model: BaseChatModel | None = None):
        self.language = language
        if self.language == "en":
            self.system_prompt = eng_logic_block_system_prompt
            self.user_prompt = eng_logic_block_user_prompt
        else:
            self.system_prompt = logic_block_system_prompt
            self.user_prompt = logic_block_user_prompt
        self.logger = logger
        self.model = model or create_chat_model()
    
    def generate_logic_blocks(self, cleaned_code_file_path: Path, output_file_path: Path) -> None:
        if not cleaned_code_file_path.exists():
            self.logger.error(f"File {cleaned_code_file_path} not found")
            raise FileNotFoundError(f"File {cleaned_code_file_path} not found")
        
        with open(cleaned_code_file_path, "r", encoding="utf-8") as file:
            source_code = file.readlines()
        system_prompt = self.system_prompt
        user_prompt = self.user_prompt.format(source_code="\n".join(source_code))
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        logic_blocks = result["content"]
        usage = result.get("usage")
        logic_blocks = re.sub(r'(^```markdown\s*)|(\s*```$)', '', logic_blocks)
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(logic_blocks)
        return usage

if __name__ == "__main__":
    logic_block = Logicblock(language="en")
    logic_block.generate_logic_blocks(Path("output/a/cleaned_code.ppcl"), Path("output/a/logic_blocks.md"))
