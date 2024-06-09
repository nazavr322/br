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
            'model_name': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Model',
                params={'options': self.models},
            ),
            'width': GenerationParam(
                type=GenerationParamType.INT_NUMBER,
                display_name='Illustration Width',
                params={
                    'min_value': 256, 'max_value': 2048, 'init_value': 1024
                },
            ),
            'height': GenerationParam(
                type=GenerationParamType.INT_NUMBER,
                display_name='Illustration Height',
                params={
                    'min_value': 256, 'max_value': 2048, 'init_value': 1024
                },
            ),
            'steps': GenerationParam(
                type=GenerationParamType.INT_NUMBER,
                display_name='Steps',
                params={'min_value': 1, 'max_value': 100, 'init_value': 30},
            ),
            'sampler': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Sampler',
                params={'options': self.samplers},
            ),
            'scheduler': GenerationParam(
                type=GenerationParamType.COMBO_BOX,
                display_name='Scheduler',
                params={'options': self.schedulers},
            ),
        }

    def _get_dim_range(self, dim: str) -> range:
        try:
            dim_params = self._generation_params[dim]['params']
        except:
            raise ValueError(f'Unknown Dimension Name: {dim}')
        return range(dim_params['min_value'], dim_params['max_value'] + 1)

    def _is_valid_img_dims(self, width: int | str, height: int | str) -> bool:
        try:
            w_in_range = int(width) in self._get_dim_range('width')
            h_in_range = int(height) in self._get_dim_range('height')
        except:
            return False
        return w_in_range and h_in_range

    @property
    def host(self) -> str:
        return self._host
    
    @property
    def port(self) -> int:
        return self._port

    @property
    def generation_params(self) -> dict[str, GenerationParam]:
        return self._generation_params

    @property
    def samplers(self) -> list[str]:
        r = requests.get(f'{self._base_endpoint}/samplers').json()
        return [sampler['name'] for sampler in r]

    @property
    def schedulers(self) -> list[str]:
        r = requests.get(f'{self._base_endpoint}/schedulers').json()
        return [scheduler['label'] for scheduler in r]

    @property
    def models(self) -> list[str]:
        r = requests.get(f'{self._base_endpoint}/sd-models').json()
        return [model['model_name'] for model in r]

    def generate_image(
        self,
        model_name: str,
        pos_prompt: str,
        width: int | str = 1024,
        height: int | str = 1024,
        neg_prompt: str | None = None,
        steps: int | None = 30,
        sampler: str | None = None,
        scheduler: str | None = 'Karras',
        **kwargs,
    ) -> str:
        if model_name not in self.models:
            raise ValueError(f'Unknown Model: {model_name}')
        if not self._is_valid_img_dims(width, height):
            raise ValueError(f'Invalid image dimensions: {width=}; {height=}')
        payload = {
            **kwargs,
            'prompt': pos_prompt,
            'width': int(width),
            'height': int(height),
            'override_settings': {'sd_model_checkpoint': model_name},
        }
        if neg_prompt:
            payload['negative_prompt'] = neg_prompt
        if steps in self._get_dim_range('steps'):
            payload['steps'] = steps
        if sampler in self.samplers:
            payload['sampler_name'] = sampler
        if scheduler in self.schedulers:
            payload['scheduler'] = scheduler
        r = requests.post(f'{self._base_endpoint}/txt2img', json=payload).json()
        return r['images'][0]
    
