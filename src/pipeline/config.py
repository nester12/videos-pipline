from pathlib import Path
import yaml


def load_config(path: str = 'config/pipeline.yaml') -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    if not isinstance(data, dict):
        raise ValueError('Pipeline config must be a YAML mapping')
    return data
