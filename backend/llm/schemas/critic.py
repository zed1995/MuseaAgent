from pydantic import BaseModel


class CriticAdviceSchema(BaseModel):
    summary: str
