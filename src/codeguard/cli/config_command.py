from typing import Literal

from pydantic import BaseModel
from pydantic_settings import CliPositionalArg


class ConfigCommand(BaseModel):
    setting: CliPositionalArg[Literal["review_time_limit_minutes"]]
