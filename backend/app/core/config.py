from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load .env file from the project root (adjust path if needed)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

class Settings(BaseSettings):
    PROJECT_NAME: str = "EntropyOS"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str = os.getenv("DB_HOST", "db") # Use service name from docker-compose
    POSTGRES_PORT: int = int(os.getenv("DB_PORT", 5432))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "entropyos")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")

    # LLM
    LLM_PROXY_URL: str = os.getenv("LLM_PROXY_URL", "http://llm_proxy:8080")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Hatchet
    HATCHET_CLIENT_TENANT_ID: str = os.getenv("HATCHET_CLIENT_TENANT_ID", "")
    # Add other Hatchet settings if needed

    # Add other settings as needed
    # SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings() 