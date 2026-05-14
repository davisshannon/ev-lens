from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Security
    secret_key: str
    encryption_key: str
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    first_run_admin_password: str = ""

    # Tesla Fleet API
    tesla_client_id: str = ""
    tesla_client_secret: str = ""
    oauth_bridge_url: str = "https://auth.ev-lens.com"
    # Public URL of this instance — sent to the bridge so it knows where to redirect back.
    # For local installs: http://localhost:8000
    # For exposed installs: https://evlens.yourdomain.com
    app_public_url: str = "http://localhost:8000"

    # App
    log_level: str = "info"
    app_version: str = "0.1.0"


settings = Settings()  # type: ignore[call-arg]
