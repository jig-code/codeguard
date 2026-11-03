from pydantic import JsonValue, TypeAdapter

from codeguard.review import Verdict, output_schema


def verdict_schema() -> dict[str, JsonValue]:
    """Inline references for Codex's strict schema validator, retaining field descriptions."""
    schema = TypeAdapter(dict[str, JsonValue]).validate_python(output_schema(Verdict))
    definitions = schema.pop("$defs", {})
    if not isinstance(definitions, dict):
        raise ValueError("Verdict schema definitions must be objects")
    return {key: _inline(value, definitions) for key, value in schema.items()}


def _inline(value: JsonValue, definitions: dict[str, JsonValue]) -> JsonValue:
    if isinstance(value, list):
        return [_inline(item, definitions) for item in value]
    if not isinstance(value, dict):
        return value
    reference = value.get("$ref")
    if isinstance(reference, str):
        definition = definitions[reference.removeprefix("#/$defs/")]
        if not isinstance(definition, dict):
            raise ValueError("Verdict schema references must name objects")
        value = {**definition, **{key: item for key, item in value.items() if key != "$ref"}}
    return {key: _inline(item, definitions) for key, item in value.items()}
