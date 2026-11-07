# Redundant Test Anti-Patterns

The governing question for every test: **what change to my own code would make this fail?** A test earns its place only when a plausible bug in *your* logic turns it red. If the only way to break it is to edit the declaration it mirrors, or to break framework/generic code that is already tested elsewhere, it has no independent signal — delete it.

The patterns below are recurring instances of three underlying defects. Match on the defect, not the surface shape: a novel form of the same defect still fails the gate. When in doubt, apply the defect's diagnostic question.

**Tautology vs. real constraint — the deciding question.** When a test asserts against a declared value (a default, a numeric bound, a config field), ask: *if this assertion went red, would I fix the code or fix the test?* If the declared value answers to an authority **outside** the declaration — a confidence is a 0–100 percentage, a count can't be negative, an age can't exceed 150 — then a red test means the code drifted from a real-world invariant, so you'd fix the code. **That test has signal; keep it.** If the value is arbitrary, answerable only to itself — a label string, a question key, a priority that could be any number — then a red test just means someone edited the declaration, and you'd mechanically update the test to match. **That's a tautology; delete it.** A `Field(le=100)` bound-rejection test is the keep case; a `label == "Frequency"` echo is the delete case. The distinction is not the assertion mechanics — it is whether the expected value is governed by something the code must obey.

## Defect 1 — The test transcribes the thing it claims to test (tautology)

The expected value is a restatement of the system-under-test's own source: its field declarations, its config annotations, the literal it was constructed from. Such a test cannot catch a bug, because the only edit that turns it red is changing the declaration — which forces changing the test in lockstep. The two move together forever and verify nothing in between.

**Diagnostic:** *Could I regenerate the entire expected value by mechanically reading the source?* If yes, it's a tautology.

Instances:
- **Config-mirroring** — extracting a model's declarative config and asserting it equals a hand-written copy of those same annotations (e.g. `{member.name: float(member) for member in Confidence} == {"CERTAIN": 1.0, "HIGHLY_PROBABLE": 0.9, ...}`, or asserting a binding carries the severity its config declares). The expected dict just re-types the declaration.
- **Smoke tests for declarative config / domain-variant replay** — plugging a concrete model into already-tested generic infrastructure (a registry, a definition builder) to read back the config it was handed. The generic machinery is tested once with a synthetic model; repeating it per real domain type proves nothing new.
- **`isinstance`/protocol conformance checks** — restate the type declaration; already proven by any test that exercises the object.

Keep such a test only when it reaches domain-specific logic — a custom validator, an override, a computed default — that the generic/declarative path does not already cover.

## Defect 2 — The test exercises the framework, not your logic

The behavior under test is guaranteed by the framework (Pydantic, the stdlib, a library), not written by you. No change to your code could break it without the framework itself breaking.

**Diagnostic:** *Whose code fails if this assertion goes red — mine, or the framework's?* If it's the framework's, delete it.

**Separate the decision from the mechanism.** A declared constraint like `Field(le=100)` is **your** decision; Pydantic is only the mechanism that enforces it. A test that the bound rejects out-of-range input (`Config(confidence_threshold=1.5)` raises against its `le=1`) verifies *your* decision and has signal — apply the deciding question above; do **not** dismiss it as framework behavior just because Pydantic does the raising. Framework behavior is when *no decision of yours* is under test: that a field accepts its own declared type, that assignment round-trips, that a default takes its declared value.

Instances:
- **Default-value echoes** — asserting a field defaults to `None`, or that a configured default equals the literal it was declared with. The default value is a tunable knob, not an invariant: if it changed you'd update the test, not the code. (A *computed* default produced by your own logic is different — that has signal.)
- **Absence-of-validation tests** — asserting a field with no custom validator accepts arbitrary values of its declared type (e.g. that a plain `str` field accepts any string, or that two records with the same flag are both allowed). Asserting the *absence* of a constraint proves nothing a regression could break.
- **Round-trip serialization** of a model with no custom serializers — `model_validate(model_dump()) == original` is Pydantic's contract, not yours.
- **Exhaustive enum/Literal iteration** confirming each member is accepted — framework validation, not business logic.

Test a default, validator, serializer, or constraint only when it encodes a decision your code must obey, and then assert the behavior of that decision — not the framework plumbing around it.

## Defect 3 — The behavior is already verified elsewhere

The assertion is real signal, but an existing test already covers it. The duplicate adds maintenance cost and no protection.

**Diagnostic:** *If I deleted this test, would any behavior go unverified by the remaining suite?* If no, delete it.

Instances:
- **Pass-through subclass tests** — a subclass that adds no custom logic is already covered by the base class tests.
- **LLM call plumbing tests** — mocking the model and asserting the mocked output passes through unchanged verifies wiring, not behavior. If a function's only logic is `call agent -> return result`, eval tests already prove the agent works. Only unit-test LLM callers with real branching logic (prompt construction, result mapping, conditional routing).
- **Domain-variant integration replay** — an integration test that runs a *real* domain type through a *generic* mechanism (evaluator, mapper, registry walk) and asserts an end-to-end result, when the seam is already covered on both sides: the generic mechanism is tested once with a synthetic domain in its own suite, and the domain-specific half (validation, projection, field config) is tested in the domain's own unit suite. Running the real type through the generic path proves only that generic code runs the same way for one more type — which the generic suite already guarantees. **Diagnostic for this instance:** *name the wiring bug between the two components that this test alone catches.* A real such bug — a key two sides must agree on, a ref the domain must register for the mapper to resolve, a pipeline ordering — is genuine integration signal; keep a *generic* test for it. "It exercises the real type end-to-end" is not a bug, it's a replay. A frequent companion tell: the test needs `replace`/`model_copy` result-normalization to strip framework noise (e.g. an enum-validation `ctx`) that a narrower unit test on the same field would never surface. The remedy is to delete the per-domain integration test and, if the seam lacks generic coverage, add one synthetic-domain case to the mechanism's suite. See "Integration tests must earn their level" in SKILL.md.
