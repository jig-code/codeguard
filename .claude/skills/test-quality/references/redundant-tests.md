# Signal (gate 1)

- The deciding question
- Defect 1: tautology
- Defect 2: framework behavior
- Defect 3: already verified elsewhere
- Integration tests earn their level

Ask of every test: what change to my own code would make this fail? Match a test on the
defect below, not its surface shape. A test without signal is deleted, or not written.

## The deciding question

For an assertion against a declared value (a default, a bound, a config field): if it went
red, would you fix the code or the test? When the value answers to something outside the
declaration (a confidence is between 0 and 1, a line number is positive), you'd fix the
code: keep the test. When it answers only to itself (a label, a message string, a default
someone chose), you'd update the test: it's a tautology.

## Defect 1: tautology

The expected value restates the SUT's own source, so only an edit to the declaration turns
it red. Check: could you regenerate the expected value by reading the source?

- Asserting a model's declared config equals a hand-typed copy of it (the severity a
  binding's config declares, an enum's member values).
- Plugging a concrete type into tested generic machinery to read back the config it was
  given.
- `isinstance` or protocol-conformance checks, which any test that uses the object
  already proves.

Keep such a test when it reaches logic of yours that the generic path doesn't cover: a
custom validator, an override, a computed default.

## Defect 2: framework behavior

Pydantic, the stdlib or a library guarantees the behavior; no decision of yours is under
test. Check: whose code fails if this goes red?

A declared constraint is your decision even though Pydantic enforces it: a test that
`Diagnostic(confidence=1.5, ...)` is rejected under `Field(le=1)` has signal. These don't:

- A default equals the literal it was declared with (a computed default has signal).
- A field with no validator accepts any value of its type.
- `model_validate(model.model_dump()) == model` for a model with no custom serializer.
- Each member of an enum or `Literal` is accepted.

## Defect 3: already verified elsewhere

Check: if this test were deleted, would any behavior go unverified?

- A subclass that adds no logic, already covered by the base class's tests.
- LLM call plumbing: scripting the model and asserting its output passes through
  unchanged. Unit-test an LLM caller for its own branching (prompt construction, result
  mapping, routing); the LLM tests cover the judge itself.
- A domain-variant replay, below.

## Integration tests earn their level

An integration test is justified by a wiring bug between components that no unit test on
either side can catch: a key both sides must agree on, a ref one side must register, an
order the pipeline must keep. Name that bug, or the test is redundant.

The usual redundant form runs a real type through a generic mechanism (a registry walk, a
mapper) whose generic half is tested with a synthetic type and whose type-specific half is
tested in its own suite. It only shows the generic code runs for one more type. Needing
result normalization (gate 12) to strip framework noise is a second tell.

To review one, trace each step to the unit test covering it. When every step is covered,
delete the test; if the seam itself has no generic test, add one synthetic case to the
mechanism's suite, and assert a lone config invariant (the type registered the field the
mapper needs) directly.
