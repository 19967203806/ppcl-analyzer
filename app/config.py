import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Backend URL
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Streamlit config
STREAMLIT_CONFIG = {
    "page_title": "PPCL Code Analysis System",
    "page_icon": "🧭",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# API timeouts (in seconds)
API_TIMEOUTS = {
    "default": 60,
    "upload": 3000,
    "download": 120,
    "preview": 120
}

# supported file types
SUPPORTED_FILE_TYPES = ["ppcl", "txt", "pcl"]

# output types
OUTPUT_TYPES = [
    ("logic_blocks", "Logic Blocks (.md)"),
    ("data_points", "Data Points (.md)"),
    ("logic_doc", "Logic Doc (.md)"),
    ("flowchart", "Flowchart PDF"),
]

# language config
LANGUAGES = {
    "en": "English",
    "zh": "中文"
}
