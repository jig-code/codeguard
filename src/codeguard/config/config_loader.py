import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from codeguard.config.config import Config
from codeguard.config.config_error import ConfigError

CONFIG_DIR = ".codeguard"
CONFIG_FILE = f"{CONFIG_DIR}/config.yaml"
CONFIG_ENV_VAR = "CODEGUARD_CONFIG"


@dataclass(frozen=True)
class ConfigLoader:
    root: Path

    def load(self) -> Config:
        config_file = self.root / os.environ.get(CONFIG_ENV_VAR, CONFIG_FILE)
        settings = yaml.safe_load(config_file.read_text()) if config_file.is_file() else {}
        if not isinstance(settings, dict):
            raise ConfigError(
                f"{self.root / CONFIG_DIR} is invalid:\n  {config_file.name} holds no settings"
            )
        try:
            return Config(**settings)
        except ValidationError as error:
            raise ConfigError.invalid(self.root / CONFIG_DIR, error) from error
