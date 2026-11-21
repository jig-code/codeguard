def without_retired_keys(data: object, retired: frozenset[str]) -> object:
    if not isinstance(data, dict):
        return data
    return {key: value for key, value in data.items() if key not in retired}
