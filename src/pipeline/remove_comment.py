from typing import List
from pathlib import Path
from loguru import logger

class CodeCleaner:
    def __init__(self, output_base_dir: str = "output"):
        self.output_dir = Path(output_base_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
    
    def _is_filter_comment(self, line: str) -> bool:
        if len(line) > 6 and line[6].upper() == "C":
            return True
        return False
    
    def _is_filter_empty(self, line: str) -> bool:
        if line.strip() == "":
            return True
        return False

    def clean_code(self, input_file_path: Path, output_file_path: Path) -> List[str]:
        cleaned_lines = []
        with open(input_file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        for line in lines:
            if self._is_filter_comment(line):
                continue
            if self._is_filter_empty(line):
                continue

            cleaned_lines.append(line)
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.writelines(cleaned_lines)
        return cleaned_lines

if __name__ == "__main__":
    cleaner = CodeCleaner()
    cleaner.clean_code(Path("data/a.ppcl"), Path("output/a/cleaned_code.ppcl"))
