from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/musea_agent"
    echo: bool = False
