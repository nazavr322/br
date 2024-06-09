from enum import Enum, auto
from typing import TypedDict, Any
from abc import ABC, abstractmethod


class GenerationParamType(Enum):
    COMBO_BOX = auto()
    INT_NUMBER = auto()


class GenerationParam(TypedDict):
    type: GenerationParamType
    display_name: str
    params: dict[str, Any]


class ImagenBackend(ABC):
    @property
    @abstractmethod
    def generation_params(self) -> dict[str, GenerationParam]: ...

    @abstractmethod
    def generate_image(
        self,
        model_name: str,
        pos_prompt: str,
        width: int | str,
        height: int | str,
        neg_prompt: str | None,
    ) -> str:
        ...

    @property
    def supports_neg_prompt(self) -> bool:
        return True

