import os
from dotenv import load_dotenv

# Load only an explicitly selected file or the EPL project-root file.
project_env = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env")
)
explicit_env = os.getenv("EPL_ENV_FILE", "").strip()
env_paths = [explicit_env] if explicit_env else [project_env]

for env_p in env_paths:
    if os.path.exists(env_p):
        load_dotenv(env_p)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_GT", "")
DATABASE_MODE = os.getenv("DATABASE_MODE", "").strip().lower()
if DATABASE_MODE not in {"postgres", "sqlite"}:
    raise ValueError("DATABASE_MODE must be either 'postgres' or 'sqlite'")

raw_db_url = os.getenv("DATABASE_URL", "").split("#")[0].strip()
DATABASE_URL = raw_db_url
