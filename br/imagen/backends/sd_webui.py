import requests

from br.imagen.backends.base import (
    GenerationParam, GenerationParamType, ImagenBackend
)


class SdWebUIBackend(ImagenBackend):
    def __init__(self, host: str = '127.0.0.1', port: int = 7860):
        super().__init__()
        self._host = host
        self._port = port
        self._base_endpoint = f'http://{self._host}:{self._port}/sdapi/v1'
        self._generation_params = {
            'steps': GenerationParam(
                type=GenerationParamType.INT_NUMBER,
                display_name='Steps',
                params={'min_value': 1, 'max_value': 100, 'init_value': 30},
            ),
            'sampler_name': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Sampler',
                params={'options': self.list_samplers()},
            ),
            'scheduler': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Scheduler',
                params={'options': self.list_schedulers()},
            ),
        }

    @property
    def host(self) -> str:
        return self._host
    
    @property
    def port(self) -> int:
        return self._port

    @property
    def generation_params(self) -> dict[str, GenerationParam]:
        return self._generation_params

    def generate_image(
        self,
        model_name: str,
        pos_prompt: str,
        neg_prompt: str,
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> str:
        payload = {
            **kwargs,
            'prompt': pos_prompt,
            'negative_prompt': neg_prompt,
            'width': width,
            'height': height,
            'override_settings': {'sd_model_checkpoint': model_name},
        }
        r = requests.post(f'{self._base_endpoint}/txt2img', json=payload).json()
        return r['images'][0]
    
    def list_models(self) -> list[str]:
        r = requests.get(f'{self._base_endpoint}/sd-models').json()
        return [model['model_name'] for model in r]

    def list_samplers(self) -> list[str]:
        r = requests.get(f'{self._base_endpoint}/samplers').json()
        return [sampler['name'] for sampler in r]

    def list_schedulers(self) -> list[str]:
        r = requests.get(f'{self._base_endpoint}/schedulers').json()
        return [scheduler['label'] for scheduler in r]

