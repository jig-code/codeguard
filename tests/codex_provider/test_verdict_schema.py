import json

from codeguard.codex_provider.verdict_schema import verdict_schema
from codeguard.review import Verdict, output_schema


def test_codex_schema_inlines_references_without_losing_confidence_descriptions():
    schema = verdict_schema()
    shared = output_schema(Verdict)

    assert '"$ref"' not in json.dumps(schema)
    assert '"$defs"' not in json.dumps(schema)
    confidence = schema["properties"]["violations"]["items"]["properties"]["confidence"]
    assert confidence["anyOf"] == shared["$defs"]["Confidence"]["anyOf"]
    assert (
        confidence["description"]
        == shared["$defs"]["Violation"]["properties"]["confidence"]["description"]
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["violations"]["items"]["additionalProperties"] is False
