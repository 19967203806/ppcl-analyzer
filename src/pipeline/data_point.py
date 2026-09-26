from pathlib import Path
import re
from langchain_core.language_models.chat_models import BaseChatModel
from ..utils.prompts import datapoints_system_prompt, datapoints_user_prompt
from ..utils.eng_prompts import datapoints_system_prompt as eng_datapoints_system_prompt, datapoints_user_prompt as eng_datapoints_user_prompt
from ..utils.model_factory import create_chat_model, invoke_text

class DataPoint:
    def __init__(self, language: str = "en", model: BaseChatModel | None = None):
        self.language = language
        self.model = model or create_chat_model()
        if self.language == "en":
            self.system_prompt = eng_datapoints_system_prompt
            self.user_prompt = eng_datapoints_user_prompt
        else:
            self.system_prompt = datapoints_system_prompt
            self.user_prompt = datapoints_user_prompt
    
    def generate_data_points(self, code_path: Path, logic_blocks_file_path: Path, output_file_path: Path) -> None:
        with open(logic_blocks_file_path, "r", encoding="utf-8") as file:
            logic_blocks = file.readlines()
        with open(code_path, "r", encoding="utf-8") as file:
            code = file.readlines()
        system_prompt = self.system_prompt
        user_prompt = self.user_prompt.format(logic_blocks="\n".join(logic_blocks), code="\n".join(code))
        result = invoke_text(self.model, system_prompt=system_prompt, user_prompt=user_prompt)
        data_points = result["content"]
        usage = result.get("usage")
        data_points = re.sub(r'(^```markdown\s*)|(\s*```$)', '', data_points)
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(data_points)
        return usage
