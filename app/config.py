from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    app_name: str = "Sigma Intelligence"
    app_description: str = (
        "Прототип программного продукта для анализа видео, который автоматически "
        "обнаруживает опасные или значимые события, определяет время их возникновения "
        "и формирует список хайлайтов для просмотра и последующей нарезки. "
        "Система поддерживает несколько доменов (ДТП, производство, драки) "
        "и работает без специализированного обучения — на основе self-hosted VLM/LLM."
    )
    api_prefix: str = "/api"
    api_v1_prefix: str = f"{api_prefix}/v1"

    db_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/sigma.db"
    db_echo: bool = False

    media_dir: Path = BASE_DIR / "media"

    model_version: str = "stub-v1.0"
    prompt_version: str = "v1.0"

    window_duration_sec: float = 5.0

    llm_api_url: str = "http://45.80.129.209:9011"
    llm_window_sec: float = 1.5
    llm_target_fps: int = 10
    llm_frames_per_window: int = 5
    llm_max_highlights: int = 10

    model_config = {"env_file": ".env"}


settings = Settings()
settings.media_dir.mkdir(parents=True, exist_ok=True)
(settings.media_dir / "videos").mkdir(exist_ok=True)
