# # app/core/config.py
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from pathlib import Path
# from typing import Optional

# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_ignore_empty=True,
#         # Very important: allow extra env vars without crashing
#         extra='ignore'           # ← this line fixes your error
#         # Alternative (more strict but still works): extra='allow'
#     )

#     AWS_REGION: str = "ap-south-1"
#     S3_BUCKET: str
#     SQS_QUEUE_URL: str
#     USE_SQS: bool = True
#     MODEL_PATH: str = "best_el_model.pth"
#     CONFIDENCE_THRESHOLD_DEFAULT: float = 0.7
#     MAX_IMAGE_SIZE_MB: int = 15
#     MAX_FILES_PER_REQUEST: int = 20

#     # Add these if you really want to read keys from .env (not recommended for prod)
#     AWS_ACCESS_KEY_ID: Optional[str] = None
#     AWS_SECRET_ACCESS_KEY: Optional[str] = None

#     @property
#     def model_full_path(self) -> Path:
#         return Path(self.MODEL_PATH)

# settings = Settings()







# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import os

# Explicitly load .env file
env_path = Path(".env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✅ Loaded .env from: {env_path.absolute()}")
else:
    print(f"⚠ .env file not found at: {env_path.absolute()}")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        env_ignore_empty=True,
        extra='ignore'
    )

    AWS_REGION: str = "ap-south-1"
    S3_BUCKET: str
    SQS_QUEUE_URL: str
    USE_SQS: bool = False
    MODEL_PATH: str = "best_el_model.pth"
    CONFIDENCE_THRESHOLD_DEFAULT: float = 0.7
    MAX_IMAGE_SIZE_MB: int = 15
    MAX_FILES_PER_REQUEST: int = 20

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    @property
    def model_full_path(self) -> Path:
        return Path(self.MODEL_PATH)

settings = Settings()

# Debug: Print credential status (remove in production)
print(f"AWS_ACCESS_KEY_ID loaded: {'✅' if settings.AWS_ACCESS_KEY_ID else '❌'}")
print(f"AWS_SECRET_ACCESS_KEY loaded: {'✅' if settings.AWS_SECRET_ACCESS_KEY else '❌'}")
print(f"USE_SQS: {settings.USE_SQS}")