import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_value(name: str, default: str = "") -> str:
    return os.getenv(f"DOVIET_AGENT_{name}", os.getenv(f"ANIMAL_AGENT_{name}", default))


DB_PATH = BASE_DIR / env_value("DB_PATH", "data/agent.db")
OUTPUT_DIR = BASE_DIR / env_value("OUTPUT_DIR", "assets")
RAW_DIR = OUTPUT_DIR / "raw"
FINAL_DIR = OUTPUT_DIR / "final"
LOG_DIR = BASE_DIR / "logs"

for path in [DB_PATH.parent, OUTPUT_DIR, RAW_DIR, FINAL_DIR, LOG_DIR]:
    path.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = env_value("GEMINI_API_KEY", "").strip()
GEMINI_TEXT_MODEL = env_value("GEMINI_TEXT_MODEL", "gemini-2.5-flash").strip()
GEMINI_IMAGE_MODEL = env_value("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()
IMAGE_FALLBACK_ON_ERROR = env_value("IMAGE_FALLBACK_ON_ERROR", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
IMAGE_ASPECT_RATIO = env_value("IMAGE_ASPECT_RATIO", "4:5").strip()

FB_PAGE_ID = env_value("FB_PAGE_ID", "").strip()
FB_PAGE_TOKEN = env_value("FB_PAGE_TOKEN", "").strip()
FB_GRAPH_VERSION = env_value("FB_GRAPH_VERSION", "v21.0").strip()
TIMEZONE = env_value("TIMEZONE", "Asia/Ho_Chi_Minh").strip()

FONT_BOLD = env_value("FONT_BOLD", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf").strip()

FONT_REGULAR = env_value("FONT_REGULAR", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf").strip()

WEB_HOST = env_value("WEB_HOST", "127.0.0.1").strip()
WEB_PORT = int(env_value("WEB_PORT", "8000"))
WEB_SECRET_KEY = env_value("WEB_SECRET_KEY", "change-me-local-dashboard")

MIN_FUTURE_POSTS = int(env_value("MIN_FUTURE_POSTS", "6"))
TARGET_FUTURE_POSTS = int(env_value("TARGET_FUTURE_POSTS", "14"))
DIRECT_IMAGE_BOOTSTRAP_DAYS = int(
    env_value("DIRECT_IMAGE_BOOTSTRAP_DAYS", env_value("DIRECT_IMAGE_DAYS", "0"))
)
DIRECT_IMAGE_BOOTSTRAP_UNTIL = env_value("DIRECT_IMAGE_BOOTSTRAP_UNTIL", "").strip()
