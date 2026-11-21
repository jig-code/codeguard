def without_retired_keys(data: object, retired: frozenset[str]) -> object:
    """Drop the keys a config written for an older codeguard still sets, so it loads."""
    if not isinstance(data, dict):
        return data
    return {key: value for key, value in data.items() if key not in retired}
