import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CHROME_BOT_PROFILE_DIR: str
    AI_PRO_FLOW_URL: str = "https://labs.google/fx/tools/flow"
    OLLAMA_MODEL: str = "llama3.1:8b"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    IMAP_HOST: str = "imap.gmail.com"
    EMAIL_USER: str = "placeholder@gmail.com"
    EMAIL_APP_PASSWORD: str = "placeholder_pass"
    NOTIFICATION_RECIPIENT: str = "placeholder@gmail.com"

    STORAGE_RAW_DIR: str = "storage/raw_video"
    STORAGE_AUDIO_DIR: str = "storage/audio"
    STORAGE_OUTPUT_DIR: str = "storage/final_output"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

for folder in [
    settings.STORAGE_RAW_DIR,
    settings.STORAGE_AUDIO_DIR,
    settings.STORAGE_OUTPUT_DIR,
    settings.CHROME_BOT_PROFILE_DIR
]:
    os.makedirs(folder, exist_ok=True)