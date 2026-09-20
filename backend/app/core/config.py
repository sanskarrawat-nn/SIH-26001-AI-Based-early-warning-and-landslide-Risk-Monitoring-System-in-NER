import os
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "AI-Based early warning and landslide Risk Monitoring System in NER"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DESCRIPTION: str = "AI-Based early warning and landslide Risk Monitoring System in NER"

    SMS_ENABLED: bool = False
    TWILIO_SMS_FROM: str = ''
    TWILIO_SMS_MESSAGING_SERVICE_SID: str = ''
    TWILIO_TEST_CONTENT_SID: str = ''

    WHATSAPP_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ''
    TWILIO_AUTH_TOKEN: str = ''
    TWILIO_WHATSAPP_FROM: str = ''
    TWILIO_CONTENT_SID: str = ''
    TWILIO_CONTENT_SIDS: str = '{}'  # JSON mapping of language code to approved Content SID
    OPERATIONS_API_KEY: str = ''

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'landslide_system.db')}"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Environmental Data Provider
    WEATHER_PROVIDER: str = "hybrid"  # "openmeteo", "simulated", "hybrid"
    OPEN_METEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_CACHE_TTL_SECONDS: int = 600

    # Landslide Risk Thresholds (0 - 100)
    DEFAULT_THRESHOLD_LOW: float = 25.0
    DEFAULT_THRESHOLD_MODERATE: float = 50.0
    DEFAULT_THRESHOLD_HIGH: float = 75.0

    # Model Settings
    MODEL_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "artifacts")
    MODEL_FILE_NAME: str = "landslide_model_v1.joblib"

    # Static frontend serving
    SERVE_STATIC_FRONTEND: bool = True
    FRONTEND_DIST_DIR: str = os.getenv(
        "FRONTEND_DIST_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "frontend",
            "dist"
        )
    )


settings = Settings()
