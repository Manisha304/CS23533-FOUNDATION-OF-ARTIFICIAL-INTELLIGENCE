import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./stadium_twin.db")
    TOMTOM_API_KEY: str | None = os.getenv("TOMTOM_API_KEY")
    SATELLITE_TILE_URL: str = os.getenv("SATELLITE_TILE_URL", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")

    AREA_PER_PERSON_COMFORTABLE: float = 2.0
    AREA_PER_PERSON_DENSE: float = 4.0
    AREA_PER_PERSON_DANGER: float = 5.0
    EXIT_THROUGHPUT: float = 1.5

    RISK_STAIRS_WEIGHT: int = 20
    RISK_NARROW_WEIGHT: int = 15
    RISK_ARTICULATION_WEIGHT: int = 30
    RISK_CENTRALITY_WEIGHT: int = 15
    RISK_THROUGHPUT_WEIGHT: int = 20
    NARROW_WIDTH_THRESHOLD: float = 2.0
    CENTRALITY_TOP_PERCENT: float = 0.10
    DEFAULT_HIGHWAY_WIDTHS: dict = {
        "footway": 2.0,
        "path": 1.2,
        "service": 3.0,
        "steps": 1.5,
        "pedestrian": 3.0,
        "primary": 5.0,
        "secondary": 5.0,
        "tertiary": 4.0,
        "residential": 3.5,
        "unclassified": 3.0
    }
    RISK_ROUTE_PENALTY_MULTIPLIER: float = 5.0

    class Config:
        env_file = ".env"

settings = Settings()
