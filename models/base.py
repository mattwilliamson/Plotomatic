from pydantic import BaseModel
from unidecode import unidecode
from json_repair import repair_json
from typing import Any

class BaseModel(BaseModel):
    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, *, strict: bool | None = None, context: Any | None = None) -> "BaseModel":
        """Parse JSON into a StoryModel instance, removing non-ASCII characters."""
        json_data = json_data.strip()
        json_data = unidecode(json_data)
        json_data = repair_json(json_data)
        return super().model_validate_json(json_data, strict=strict, context=context)
