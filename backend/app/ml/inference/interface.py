from typing import Protocol

from backend.app.schemas.investigation import ModelResult


class TextInference(Protocol):
    def predict(self, content: str) -> ModelResult: ...
