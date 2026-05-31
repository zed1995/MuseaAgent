from typing import Literal

from pydantic import BaseModel


class IntentClassificationSchema(BaseModel):
    mode: Literal["wallpaper", "reference", "photographer", "auto"]
    topic_action: Literal["new", "refine", "reset"]
