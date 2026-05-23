from pydantic import BaseModel


class InternalSinglePhotoRequest(BaseModel):
    payload: dict


class InternalBatchIngestionRequest(BaseModel):
    payloads: list[dict]
