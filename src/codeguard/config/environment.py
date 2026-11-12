ENV_PREFIX = "CODEGUARD_"
ENV_NESTED_DELIMITER = "__"


def environment_variable(*field_path: str) -> str:
    """The environment variable that sets the config field at `field_path`."""
    return ENV_PREFIX + ENV_NESTED_DELIMITER.join(field_path).upper()
