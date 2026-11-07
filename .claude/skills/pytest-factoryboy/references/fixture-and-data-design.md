# Fixture and Test-Data Design

Rules for how fixtures return values, how test data reaches the test, and how parent/child objects are seeded. These extend the patterns in `SKILL.md`.

## One fixture per concept, never tuples

Fixtures return a single object. Never return a tuple to bundle multiple objects (`return judge, store, repo`) — this forces positional destructuring, hides what each test actually needs, and couples unrelated concerns. Instead, define separate named fixtures (`repo`, `store`, `judge`) that depend on each other via pytest's fixture dependency graph. Each test then declares exactly the fixtures it needs in its signature.

**Keep setup fixtures separate from object/data fixtures.** A fixture that returns a repo, request, model instance, or other data object must not also hide environment setup such as environment variables, fake CLI config, telemetry, registries, or external service state. Use explicit setup-only fixtures for those dependencies (`fake_cli_config`, `no_telemetry`, `committed_config`) and request the object/data fixtures directly in the test signature. A setup-only fixture may return `None`/`pass`; its purpose is the dependency edge, not a bundled value.

## Test data flows through fixtures, not module constants

A module-level `SCREAMING_SNAKE` constant for test input data (values passed to the SUT) or expected output bypasses pytest's fixture dependency-injection graph. The test signature no longer declares what data it needs — a reader must scan the body to discover hidden dependencies. Fixtures are pytest's mechanism for making test data dependencies explicit, composable, and overridable.

**Rule:** any constructed value (a model instance, a tuple/list of domain objects, a configuration dict) that two or more tests consume must be a `@pytest.fixture`, not a module constant. A test that needs the value declares it in its signature — visible, overridable per-test via parametrize, and composable with other fixtures.

**The narrow exception — true constants that are names for opaque tokens.** A bare scalar that names a well-known identifier and carries no construction logic (`MODEL = "gemini-3.1-pro-preview"`, a regex pattern, a URL template) may stay module-level because it has no dependencies to compose and no lifecycle to manage. The discriminator: does the value *construct* domain objects (models, dataclasses, tuples of typed things) or is it a *bare scalar/string naming an external concept*? Construction → fixture; naming → constant is acceptable.

**The exemption does NOT extend to a runtime identity a test asserts on.** A bare scalar naming an *opaque external token* (a prompt string, regex, URL template) may stay module-level. But a shared constant standing in for a *runtime identity* — `user_id`, `session_id`, `job_id`, a correlation UUID — that any test passes as input **and then asserts on** is not exempt, even though it's a bare scalar. The asserting test must **own** the value: construct it inline (`user_id = str(uuid4())`) and thread it through setup, so the assertion proves the value *flowed through the SUT* rather than proving two references to the same module constant are trivially equal. A shared `FIXED_ID = "0000…0001"` asserted via `assert result.user_id == FIXED_ID` is a tautology dressed as a check — it passes regardless of whether the SUT propagated the value or substituted its own. **Mechanical tell:** a `SCREAMING_SNAKE` id constant that appears both in a factory/setup call *and* in an `assert` → flag; the test owns it inline instead.

**Corollary for shared factories:** a factory's identity fields default to *fresh* values (`factory.LazyFunction(lambda: str(uuid4()))`), never a shared constant — a fixed identity default silently couples every test built from it and lets non-owning assertions pass.

Parent-owned children are seeded through the parent creator — see [reuse-and-helper-existence.md](reuse-and-helper-existence.md).
