# Fixtures and test data (gates 9, 15)

## One object per fixture

A fixture returns one object, never a tuple (`return judge, store, repo`). Write one
fixture per concept (`repo`, `store`, `judge`), depending on each other, so each test's
signature names what it uses.

A fixture that returns data (a repo, a request, a model) doesn't also set up environment
(environment variables, the fake CLIs' config, telemetry). That is a separate setup-only
fixture, such as `fake_cli_config`, `no_telemetry` or `committed_config`, which may
return `None`. What a setup fixture may do is `test-quality` gate 17.

## Test data through fixtures

A constructed value two or more tests use (a model, a tuple of domain objects, a config
dict) is a fixture, not a module-level constant, so each test's signature declares it and
a test can override it. A bare scalar that names an external token (a prompt string, a
regex, a URL template, `MODEL`) may be a module constant, unless a test asserts on it as
an identity (below).

## Identities

A test that asserts on a runtime identity (an id, a session or correlation key, passed in
and asserted) owns it: it creates the value in its body and passes it through setup, so the
assertion shows the value flowed through the SUT. A shared constant used in both setup and
an `assert` passes even when the SUT substitutes its own value.

A factory's identity fields default to a fresh value, not a shared constant, so tests
built from it aren't coupled.

Give a test an id only when the SUT correlates on it and the object it names exists or is
asserted. When an id is needed only because a wide constructor requires it, narrow the
setup to the real inputs instead.

Parent-owned children are seeded through the parent's creator:
[reuse-and-helper-existence.md](reuse-and-helper-existence.md).
