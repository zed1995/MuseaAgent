from pydantic import BaseModel


class ResponseReasonSchema(BaseModel):
    reason: str
