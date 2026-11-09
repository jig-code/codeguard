# Helpers, results and test phases (gates 10, 12, 17)

- Gate 10: a helper sets up, it doesn't perform the act
- Gate 12: no normalizing the result
- Gate 17: arrange, act and assert in the test body

Which construction shape to use (factory, fixture, inline) is `pytest-factoryboy`'s
decision; these gates cover what a helper or fixture may do once it exists.

## Gate 10: a helper sets up, it doesn't perform the act

A helper assembles collaborators and inputs: writes files to a `GitRepo`, builds objects
with factories. It doesn't absorb the act the test verifies. Three shapes cross the line.

**(a) It computes a value production computes** (an id, a key, an ordering, the line
numbers `JudgeRequest.of_change` renders) by running the same builder. It clones SUT
logic and drifts with it; a helper named after one scenario is the tell. Get the value
from the production path instead, or mock above the transform that assigns it. When the
value must appear in a mock, compute it in the test body with the production builder,
bound to a named variable.

Calling the production function in the expected value is fine when all three hold: the
value is a deterministic output field computed from inputs asserted in the same expected
object; the SUT delegates the computation to a collaborator; and that collaborator's own
test pins the function from primitives. That assertion checks consistency, not SUT logic.

**(b) It returns a method's result instead of the object it built:**
`return make_judge_request(...).prompt`, even when the method isn't the one under test.
A helper may call methods while building (constructors, builder chains, factories); what
it returns is the built object. Split it: one helper returns the object, and the test body
(or a separate helper named for the action) makes the call.

**(c) It drives the SUT and asserts.** A helper named for an action takes the last result,
asserts on it, runs the next step and returns the new result:

```python
judgement = rejudge_after_edit(judge, repo, request, judgement)  # what ran? what was checked?
```

Write the step in the test body instead:

```python
repo.write(request.file, "print(2)\n")
judgement = judge.judge(request)
assert wrapped.received == [request, request]
```

Drop repeated assertions a unit test already owns (gate 1) rather than moving them into a
helper. Simulate an out-of-band actor (the judge CLI) through its boundary fake and what
it received, not by reading the SUT's internal state such as the cache's store.

## Gate 12: no normalizing the result

Assert the result the SUT returns. Rebuilding it before `==` with `replace`,
`model_copy(update=...)`, `model_dump(exclude=...)` or a stripping comprehension unguards
every field removed. When one field is noisy, assert that field's meaningful part
directly and the rest of the object normally:

```python
assert diagnostic.note.startswith("claude exited with ")
```

Needing normalization also suggests the seam is too wide; a narrower test has no noise to
strip.

## Gate 17: arrange, act and assert in the test body

Construct the SUT in the test body (`judge = CachedJudge(wrapped=wrapped, ...)` beside
`judge.judge(request)`); a `make_*` call in the body counts. Fixtures and helpers supply
collaborators and inputs. A test parameter that is the object the test acts on is the
tell.

A fixture supplies a thing. It doesn't perform arrange actions (start a process, advance
a clock, dispatch the calls that put the SUT in its precondition), the act or assertions,
even when what it returns is a real object. A time advance is the scenario, so it is a
visible line in the body.

A setup fixture is for ambient environment (environment variables, the fake CLIs'
config, telemetry, registries) shared by more than one test. Inline one that a single test
uses.

When the arrange is too large to read in the body, fix the production code (add the
seam, inject the collaborator, split the responsibility) rather than hiding the arrange.
