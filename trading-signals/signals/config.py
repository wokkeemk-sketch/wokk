"""Config loading, shared by the interactive CLI and the scheduled digest."""

import yaml


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)
