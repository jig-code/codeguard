# VCR Testing Guidelines

VCR tests record real HTTP interactions as YAML cassettes and replay them in CI. Use them for vendor API integrations where you need to validate against actual response shapes and payloads.

## When to Use VCR vs `requests_mock`

| Approach | Use When |
|---|---|
| **VCR (`@pytest.mark.vcr`)** | Testing the full request/response cycle against a real vendor API — validating transformers produce correct payloads and the client correctly parses real responses |
| **`requests_mock`** | Unit-testing specific error paths, status codes, or edge cases where you control the response shape |

Both can coexist in the same test file (WellSky does this — `requests_mock.mock(real_http=True)` passes requests through to VCR while still capturing `request_history`).

## Project Setup

The project uses **pytest-recording** (a pytest wrapper around vcrpy). It's already in `backend/pyproject.toml` as a dependency.

## Cassette Location Convention

Cassettes live alongside their test files:

```
services/vendors/<vendor>/tests/
├── cassettes/
│   └── <test_module_name>/
│       ├── TestClassName.test_method_name.yaml
│       └── ...
├── test_prod_<vendor>_client_vcr.py
└── ...
```

pytest-recording auto-generates the directory structure based on test module and class names.

## Writing a VCR Test

### 1. Define `vcr_config` Fixture

Every VCR test module needs a `vcr_config` fixture. At minimum, filter auth headers and set match criteria:

```python
@pytest.fixture(scope="module")
def vcr_config(self):
    return {
        "filter_headers": ["authorization"],
        "match_on": ["method", "scheme", "path", "query"],
        "decode_compressed_response": True,
    }
```

### 2. Mark Tests with `@pytest.mark.vcr`

```python
@pytest.mark.vcr
def test_provider_create(self):
    result = self.client.provider_create(transformed_data)
    assert result.get("id") is not None
```

### 3. Record and Verify Cassettes

Always pass `-n0` to disable parallel execution during recording — VCR records sequentially.

**Record all cassettes** (requires real credentials):

```bash
task backend:test_unit -- services/vendors/<vendor>/tests/test_prod_<vendor>_client_vcr.py -v --record-mode=all -m <vendor> -n0
```

**Record a single new or updated cassette** using `--record-mode=new_episodes` to only hit the API for tests missing cassettes (existing cassettes replay as-is):

```bash
task backend:test_unit -- services/vendors/<vendor>/tests/test_prod_<vendor>_client_vcr.py::TestClassName::test_method_name -v --record-mode=new_episodes -m <vendor> -n0
```

**After recording, always verify all cassettes replay correctly** by running the full test file without `--record-mode`:

```bash
task backend:test_unit -- services/vendors/<vendor>/tests/test_prod_<vendor>_client_vcr.py -v -m <vendor> -n0
```

This confirms existing cassettes weren't broken by the change.

## Sensitive Data Scrubbing

**Always filter credentials before committing cassettes.**

### Request-side filtering (vcr_config)

```python
"filter_headers": ["authorization"],
"filter_post_data_parameters": ["client_id", "client_secret"],
```

### Response-side filtering (before_record_response)

For credentials that appear in response bodies, use a `before_record_response` callback:

```python
def before_record_response(self, response):
    body = response["body"]["string"].decode()
    body = body.replace(real_secret, "REDACTED")
    response["body"]["string"] = bytes(body, "utf-8")
    return response
```

Then reference it in `vcr_config`:

```python
"before_record_response": self.before_record_response,
```

See `services/vendors/wellsky/tests/test_prod_wellsky_client.py` for a complete example.

## Cassette Maintenance

- **Re-record when the vendor API changes** — if a vendor updates response formats, delete the affected cassettes and re-record with `--record-mode=all`
- **Review cassettes in PRs** — YAML cassettes are human-readable; check that no secrets leaked through
- **Don't hand-edit cassettes** — re-record instead; hand edits are fragile and hard to verify

## Finding Existing VCR Tests

To find all VCR test files and cassettes in the codebase:

```bash
# Test files using VCR
grep -rl "pytest.mark.vcr" backend/

# Cassette directories
find backend/ -type d -name cassettes
```
