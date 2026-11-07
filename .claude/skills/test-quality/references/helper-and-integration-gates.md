# Helper Gates (10, 11) and Integration-Level Guidance

(Construction-helper *parameter* rules — the former gate 12 — now live in the `pytest-factoryboy` skill.)

## Gate 10 — A test helper may set up, never perform the act under test

A test helper's legitimate job is to *reduce setup boilerplate*: assemble a real object graph, write files to a `GitRepo`, build Factory Boy objects, build the inputs and collaborators the SUT takes (the SUT itself is constructed in the test body — gate 17). Its job is **not** to absorb the *act* the test exists to verify. When a helper does, it relocates the behavior under test out of the visible test body and into opaque setup: the reader can no longer see what is exercised, with what arguments, or tell the SUT's output apart from fixture data. The general tell is a helper that not only *constructs* a collaborator but also *returns the result of exercising it*. This manifests in two species.

### Factory, fixture, or helper

Use this decision rule before adding shared test setup (how to *build* the factory/fixture itself is governed by the `pytest-factoryboy` skill):

- **Factory/builder:** constructs one object type and returns that object. It may call constructors, Factory Boy, or builder-chain methods as part of construction, but its return value is the constructed object.
- **Setup fixture:** provides one named setup object or establishes one setup condition. If it returns a value, that value is the concept named by the fixture; it must not also hide environment setup or terminal projections.
- **Helper:** reduces repeated setup mechanics. It earns existence only when it does non-trivial setup across call sites and still leaves the act and assertions visible.

Do not use any of the three to wrap another factory/builder's default construction or to rename a constructor call. A fixture whose body is only `loader = RulesetLoader.local(repo.root); return Bindings.from_rulesets([loader.load()])`, or only `return EditReviewTask(binding=binding, judges=judges, confidence_threshold=threshold, scanner=scanner)`, is a low-value wrapper: it hides the production construction direction while adding no test-specific configuration. Inline it at the test seam unless the wrapper applies meaningful, non-default configuration, constructs an object through Factory Boy, or resolves a real typing seam.

Do not use any of the three to return a filtered/projection result from methods called on objects just built inside the helper. A fixture named `python_triggered_bindings` that loads a ruleset, builds its `Bindings`, calls `binding.files(...)`, then filters by `binding.is_triggered(...)` is not a factory for `Binding`; it is hiding the selection logic needed by the test's scripted verdict. Fix by making the projection call visible in the test body, or by moving the projection into production/shared code that genuinely owns that domain concept.

### Species (a) — computing a value production already computes

A helper that *re-derives a value production code already computes* (an allocated id, generated key, hash, ordering). The moment a helper imports the same builder/allocator/factory the production path uses and runs it to predict an output, it has stopped setting up and started shadowing the SUT — it clones production logic into the suite, drifts out of sync the instant that logic changes (scope, ordering, an added field), and yields an opaque value the test author cannot eyeball for correctness.

- **Right scope:** "build the real thing the test needs as input." If the production code computes a derived value, get it *from the production path* — call the real function/build the real object and read the value off it — rather than re-implementing the derivation in test code. Better yet, reuse an existing production or shared-test utility that already exposes the mapping.
- **Wrong scope:** a helper that re-runs a production computation, *especially* one narrowed to a single scenario (e.g. a helper that hardcodes a single domain/category key). Pinning the scope bakes in an assumption — widen the scenario and the helper silently returns the wrong answer while the test still "passes." Naming a helper after one domain/case is the tell that it has absorbed logic that belongs to production.
- **Why this keeps happening:** you mocked *below* a transform. Production assigns the value upstream (e.g. `JudgeRequest.of_change` renders line numbers into the prompt) and the real component reads it back; swap a fake in below that seam and the test is forced to guess the value the running system will assign. The fix is almost always to **mock at a higher seam** — above the transform — or not at all, so the test never has to speak the internal encoding. If the value genuinely must appear in the mock, build it explicitly in the test body with the production builder and bind it to a named variable, so the assignment is visible *in the test*, not hidden behind a scenario-named helper.

**Legitimate exception — asserting a delegated, deterministic *output* field whose inputs are also asserted.** Calling the production function inside the *expected value* is **not** shadowing when all three hold: (1) the value appears in the SUT's **output** and is a deterministic function of other fields **asserted in the same expected object** (so it can only diverge when an already-pinned input also diverges); (2) the SUT **delegates** the computation to a collaborator rather than owning it — the SUT's own logic is elsewhere (selection, routing, filtering), and it merely passes inputs to the collaborator that stamps the value; and (3) that collaborator's function is **independently pinned by its own test via a different construction path** — reconstructing the value from primitives, not by calling the same function. When all three hold the recompute asserts a genuine *consistency* relationship ("this id was derived from *these* refs, not a stale or arbitrary one"), and reusing the production function is correct reuse, not a clone of SUT logic. **Discriminator:** *if this assertion went red, could it reveal a bug the SUT owns — or only one the collaborator's own test already guards?* If only the latter, and the value's inputs are asserted right beside it, it is consistency-checking, not shadowing. The hazard species (a) targets is the SUT **re-deriving its own output** so a bug in *its* logic stays invisible; a value the SUT delegates and that is covered at its own layer carries no such hazard. (Worked case: a step that selects items and hands them to a batcher, which stamps a content-hash `batch_id`. The step's test asserts the whole `BatchPlan` — `items`, `mode`, and `batch_id=build_batch_id(mode, items)`. The `batch_id` is a pure function of the two fields already pinned, the step delegates id-generation to the batcher, and the hash scheme is pinned independently in the batcher's own suite by hashing primitives directly. Reusing `build_batch_id` is correct here, not a gate-10 violation.)

### Species (b) — ending by calling a method instead of returning the constructed object

A construction helper must **return the constructed type**, never the *result of calling a method on it*. The tell is purely structural and does **not** depend on whether the method is the one under test: if the last thing a `_make_*`/`_build_*` helper does is `return collaborator.some_method(...)` rather than `return collaborator`, the helper has folded invocation into construction. This is wrong even when the method is incidental (a getter, a `.build()`, a `.resolve()`, a render call) — the moment a helper's return value is a method's output, the constructed object is gone, the call's arguments are buried in setup, and the call site can't tell construction from behavior (`x = make_thing(...)` looks identical either way).

A helper may legitimately call methods *while building* — chaining a builder (`Configurator(reg).add_source(...).configure()`), calling Factory Boy, invoking a constructor. The line is what it **returns**: the assembled object (allowed) versus the output of a terminal method call layered on top of an already-complete object (flag). If you can split the body into "build the object" then "call a method on it and return that," the second half does not belong in this helper.

- **Right scope:** the helper returns the *constructed* type. The test body (or a second, dedicated helper) makes the call. The method name and its arguments stay visible next to the assertion they feed.
- **Wrong scope:** a helper whose return value *is* a method's output. `return build_x(...).resolve(input)`, `return Mapper(specs).map(captured)`, `return make_judge_request(...).prompt` — all end by reaching past the constructed object to a method/attribute result.
- **The fix — two helpers, not one.** Keep the construction helper, returning the built object (`make_mapper() -> Mapper`). If invoking the method is itself shared across tests, write a *separate* helper that does only that and is named for the action (`map_captured(mapper, captured) -> Result`), or just inline the one-line call into each test. Never let a single helper both construct and invoke.

### Species (c) — an action-wrapper that drives the SUT *and* asserts

The most damaging form takes `(judge, request, result)`, asserts on the `result` it was handed, performs the next step (`judge.judge(...)`), and returns the new `result`. It is named for the *action* it performs (`rejudge_after_edit`, `advance_past_retry`), not for a component it builds. This is species (b) compounded with hidden assertions: a reader of the test sees `judgement = rejudge_after_edit(judge, repo, request, judgement)` and can see neither what is asserted nor what is driven. Multi-step tests attract this because the same "change the input, then run again" dance repeats every step — and the instinct is to DRY it into one helper. That instinct is wrong here: the repetition *is* the test honestly showing it steps the SUT through each change.

```python
# BAD — helper asserts the previous judgement, reads the cache, edits the file, judges again
def rejudge_after_edit(judge, repo, request, judgement) -> Judgement:
    assert judgement.verdict.violations == ()  # spec assertion, invisible to the test
    assert len(list(judge.store)) == 1  # reaches around the boundary
    repo.write(request.file, "print(2)\n")
    return judge.judge(request)  # the act, hidden


# at 14 call sites — the reader sees neither the assertions nor the judge call:
judgement = rejudge_after_edit(judge, repo, request, judgement)
```

```python
# GOOD — the edit and the judge call (the act) are visible; the out-of-band judge is read
#        through its boundary fake; redundant plumbing assertions dropped (owned by unit tests).
repo.write(request.file, "print(2)\n")
judgement = judge.judge(request)
assert wrapped.received == [request, request]
```

- **The buried assertions are usually also redundant (gate 1).** Before relocating them into the test body, check whether a unit test already owns them — the empty verdict is asserted by the judge's own test, the cache write by `CachedJudge`'s test. If so, *drop* them rather than repeating them 14×; re-checking the same plumbing fact every step adds no signal.
- **Simulate out-of-band actors through the boundary, not a query of internal state.** The production judge is a CLI subprocess or a model API, so the faithful stand-in is the boundary fake (the fake CLI, `RecordingJudge`, `ScriptedGemini`) and what it received — the test does not reach around the boundary into the cache's store to recover a value the SUT produced. Reading the seam the production actor reads keeps the simulation honest (gate 2).
- **The `repo` fixture stays.** It returns a component (a `GitRepo`) and has other callers — that is exactly the setup-only helper gate 10 endorses. Only the edit→judge *sequence* is inlined.

## Gate 11 — Do not normalize the result before asserting

Assert against the result the SUT actually returns. Do not rebuild it with `dataclasses.replace`, `model_copy(update=...)`, `model_dump(exclude=...)`, or a comprehension that strips/rewrites fields before the `==`. **Why:** every field you edit out of the result is a field the test no longer guards — the normalization silently downgrades a full-object assertion (gate 4) to a partial one, and the discarded fields are usually the noisy, hard-to-predict ones that carry the most regression risk. **The smell:** the test constructs the expected object *and* post-processes the actual object to make them match. That post-processing is the tell that the result contains something the author couldn't predict. **What to do instead:** if one field of a result object is non-deterministic or carries framework-shaped noise (e.g. a Pydantic enum-validation `ctx` that enumerates every member), don't reshape the whole result — navigate to that one field and assert its meaningful part directly (`assert issue.context["input"] == "high"`, `assert issue.message.startswith("Input should be ")`), and assert the surrounding object's stable fields normally. If you find yourself normalizing the result to control noise, that is also a signal the test may be exercising too wide a seam — a narrower unit test asserting the same field would have no noise to strip.

## Construction-helper parameters

Moved to the `pytest-factoryboy` skill — see its `references/construction-helper-parameters.md` (helpers declare typed params; `**kwargs` only as untouched pass-through; no alternative-input branching; no production-sounding aliases; no test-only bundle or post-build injection; no fabricated runtime identity for static data).


## Integration tests must earn their level

An integration test is justified only when it catches a **wiring** bug that no unit test on either side of the seam can — a mismatch *between* components, not behavior *within* one. Before keeping (or writing) one, name the specific defect it alone catches: a key that two components must agree on, a ref one side must have registered for the other to resolve, an ordering the pipeline must preserve. If you can name that bug, the test has signal at this level. If you cannot — if the honest answer is "it re-runs generic behavior with a real type plugged in" — it is a **domain-variant replay** and fails the redundancy gate (Defect 3 in [redundant-tests.md](redundant-tests.md)).

**The recurring trap.** A seam between a generic mechanism (an evaluator, a mapper, a registry walk) and a concrete domain type tempts a per-domain integration test: "feed the *real* `FooDomain` state through the generic evaluator and assert the real clarification comes out." But the seam already has coverage on both sides — the generic half is tested once with a synthetic domain in the mechanism's own suite, and the domain-specific half (the validation, the projection, the config) is tested in the domain's own unit suite. Running the real domain through the generic path proves only that generic code runs the same way for one more type, which the generic suite already guarantees. The lone sliver of unique signal (e.g. "this domain registered the field the mapper needs") is a config invariant — assert it directly and generically, don't dress it up as a full end-to-end flow.

**How to flag it in review.** Trace each step of the integration test's chain to the unit test that already covers it. If every step is covered and the only thing new is the *combination of a real type with generic plumbing*, flag as redundant and point to (a) the domain unit test covering the domain-specific half and (b) the generic mechanism test covering the seam. The remedy is usually: delete the per-domain integration test, and if the seam itself lacks a generic test, add one synthetic-domain case to the mechanism's suite. A secondary tell that the level is wrong: the test needs result-normalization (gate 11) to tame framework noise that a narrower unit test would never surface.
