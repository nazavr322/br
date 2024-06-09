from typing import NamedTuple, Sequence, Literal
from itertools import chain

from openai import OpenAI

from br.imagen.backends.base import (
    GenerationParam, GenerationParamType, ImagenBackend
)


class OpenAIImagenModel(NamedTuple):
    sup_dims: Sequence[str]
    max_prompt_length: int


class OpenAIBackend(ImagenBackend):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._client = OpenAI(*args, **kwargs)
        self._models = {
            'dall-e-2': OpenAIImagenModel(('256', '512', '1024'), 1000),
            'dall-e-3': OpenAIImagenModel(('1024', '1792'), 4000),
        }
        self._quality_opts = ('standard', 'hd')
        self._style_opts = ('vivid', 'natural')
        all_dims = list(
            dict.fromkeys(
                chain.from_iterable(m.sup_dims for m in self._models.values())
            )
        )
        self._generation_params = {
            'model_name': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Model',
                params={'options': self._models.keys()},
            ),
            'width': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Illustration Width',
                params={'options': all_dims},
            ),
            'height': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Illustration Height',
                params={'options': all_dims},
            ),
            'quality': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Quality',
                params={'options': self._quality_opts},
            ),
            'style': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Style',
                params={'options': self._style_opts},
            ),
        }

    def _is_valid_img_dims(
        self, model_name: str, width: int | str, height: int | str
    ) -> bool:
        try:
            sup_dims = self._models[model_name].sup_dims
        except KeyError:
            raise ValueError(f'Unknown Model: {model_name}')
        if model_name == 'dall-e-2':
            return width in sup_dims and height == width
        else:
            if width not in sup_dims or height not in sup_dims:
                return False
            if width == '1792' and height == '1792':
                return False
            return True

    @property
    def generation_params(self) -> dict[str, GenerationParam]:
        return self._generation_params

    @property
    def models(self) -> list[str]:
        return list(self._models)

    @property
    def supports_neg_prompt(self) -> bool:
        return False

    def generate_image(
        self,
        model_name: str,
        pos_prompt: str,
        width: int | str = '1024',
        height: int | str = '1024',
        neg_prompt: str | None = None,
        quality: Literal['standard', 'hd'] = 'standard',
        style: Literal['vivid', 'natural'] = 'vivid',
    ) -> str:
        try:
            model = self._models[model_name]
        except KeyError:
            raise ValueError(f'Unknown Model: {model_name}')
        if not self._is_valid_img_dims(model_name, width, height):
            raise ValueError(f'Invalid Image Dimensions: {width=}; {height=}')
        payload = {
            'prompt': pos_prompt[:model.max_prompt_length],
            'model': model_name,
            'response_format': 'b64_json',
            'size': f'{width}x{height}',
        }
        if quality in self._quality_opts:
            payload['quality'] = quality
        if style in self._style_opts:
            payload['style'] = style
        image = self._client.images.generate(**payload).data[0]
        if image.revised_prompt is not None:
            print('Revised Prompt:', image.revised_prompt)
        return image.b64_json

