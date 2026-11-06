# Signal and Mocking Gates (1–4)

The first four gates are the foundation: a test must be deterministic, exercise real objects, assert exact values, and assert whole result objects. Together they guarantee a test fails for exactly one reason — a real regression in your code — and never passes while masking one.

## Gate 1 — No-signal tests

Before writing any test, verify it adds signal. Every test must answer: *what change to my own code would make this fail?* If the only way to break it is editing the declaration it mirrors (**tautology**), breaking the framework — Pydantic/stdlib/ORM defaults, type-acceptance, serialization (**framework behavior**), or breaking already-tested generic code (**true redundancy**), it adds no signal — don't write it.

The deciding question for any assertion against a declared value: *if it went red, would I fix the code or fix the test?* Fix-the-code → real invariant, keep it. Fix-the-test → tautology/framework echo, drop it.

See [references/redundant-tests.md](redundant-tests.md) for the three defects and their concrete instances.

## Gate 2 — Real objects over mocks

`MagicMock` and `patch()` are acceptable **only at the process boundary**: HTTP calls to third-party APIs, cloud SDK calls that leave the machine (SQS, S3), or services requiring external credentials.

The database is **not** an external boundary — unit tests use a real test database. Never mock querysets, model instances, Django services that query the DB, or any collaborating class within the codebase.

**Never `patch()` internal functions, factories, or module-level callables.** Patching `build_my_thing()` or `my_service.get()` hides integration bugs just as much as mocking a class does. If a function builds a dependency, use dependency injection or existing test helpers that construct the real object with test-appropriate configuration.

**Before defining an inline stub class, search for identical or equivalent stubs in other test modules** — if one exists, extract it to a shared location and reuse it rather than duplicating.

The fact that a parameter is "not used" in the test is irrelevant — pass the real object anyway.

**Never substitute empty/dummy data to bypass failures in production code.** If using real data causes the test to fail, that failure is a bug — fix the production code, don't hollow out the test inputs. Empty stubs, null objects, and `FieldSpecs([])` where real data belongs all hide bugs by avoiding the code paths that matter. Exception: `FieldSpecs([])` is acceptable in factory/wiring tests where the SUT provably does not exercise field resolution.

**Seed through production's creator; never fabricate a record's foreign id to dodge creating its parent.** When production has a single creator for a row — a planner, a service method, a manager `create`/`upsert` — a unit test (which has a real DB) seeds through that creator, or through a thin setup helper that drives it and returns the rows (gate 10). Re-implementing the creator's insert path inline in `conftest` — a hand-rolled `create_for` + `upsert` loop that parallels the production planner — is gate-10 species (a) shadowing: the test exercises a creation path production never runs. **Factory Boy makes a *real* row when you genuinely need one; it is not a workaround for real data** and never licenses skipping a parent. The tell: a child row is given a foreign id (`source_id=str(uuid4())`, `*_id=<fresh uuid>`) pointing at a parent that was never created. A missing DB foreign-key constraint is not permission to fabricate — it is a separate modeling gap to fix, not to exploit. Seed the parent (or drive the creator that does), then let the child reference it.

**Dependency preference hierarchy** (use the first option that works):

1. Real object (always preferred)
2. Shared stub/fake from conftest or a test utility module
3. Inline stub implementing a protocol (only for framework contract tests where the fake IS the test's domain model)
4. `patch()` / `MagicMock` (only at process boundaries — HTTP, cloud SDK, external credentials)

### A shared fake abstracts one layer — extend it by configuration, not by cross-layer subclassing

A shared fake (`MockQueueManager`, `RecordingTestModel`) exists to abstract **one seam**. `MockQueueManager` abstracts the queue: you express expectations by *configuring* it (create the queue, enqueue) and *asserting on its observable in-layer state* (dequeue the messages, check their bodies and order). That is the whole contract.

**Do not subclass a shared fake to override a method so the override (a) asserts internally or (b) reaches into a *different* subsystem.** Both halves are the violation:

```python
# BAD — queue fake subclassed to run SQL against a DB table inside enqueue,
# with an accumulator whose only job is to prove the override ran
class TaskVisibilityCheckingQueueManager(MockQueueManager):
    def __init__(self):
        super().__init__()
        self.visible_task_ids: list[str] = []

    def enqueue(self, queue, message, group_id=None):
        task_id = self._task_id(queue, message)
        if task_id is not None:
            self._assert_task_visible(task_id)        # assertion buried in the fake
            self.visible_task_ids.append(task_id)
        return super().enqueue(queue, message, group_id)

    def _assert_task_visible(self, task_id):
        connection = connections["default"].copy()    # reaches below the queue layer
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from ..._extraction_task where id = %s", [task_id])
            assert cursor.fetchone() == (1,)

# GOOD — use the shared fake directly; assert on its in-layer state in the test body
manager = MockQueueManager()
...
processor.process(message)
messages = list(manager.dequeue(Queue.EVIDENCE_EXTRACTION, max_number_of_messages=10))
assert [m.body for m in messages] == [expected_body]
```

Why it's wrong:

- **Wrong layer.** The override punctures the abstraction the fake exists to provide — a queue fake now knows about a DB table. Commit-vs-visibility is a *persistence* concern; if it's worth testing, it's tested at the persistence seam, not by overriding `enqueue`.
- **Hidden assertion.** The real check lives inside the fake, where no reader looks; the test body reads as if it only checks queue contents. The accumulator (`visible_task_ids`) is a tell — it exists solely to prove the buried override actually ran.
- **Can't be expressed by configuration.** There is no *configuration* of a queue fake that means "also check a DB row on a second connection," because that isn't a queue fact. Needing to *subclass and inject other-subsystem logic* is the signal the assertion doesn't belong on this seam.

**Tell:** `class X(MockQueueManager)` / `class X(RecordingTestModel)` whose overridden method body contains an `assert`, a `cursor.execute` (or any query against another subsystem), or an accumulator that exists only to record that the override fired. **Fix:** use the shared fake directly and assert on its observable in-layer state in the test body. A thin subclass that only *configures* the fake (sets up queues, canned responses) is fine — the line is overriding behavior to assert or cross layers. If a genuinely lower-layer invariant matters (e.g. commit-before-enqueue), give it its own test at that layer rather than mutating the queue seam.

## Gate 3 — Prefer `==` over `in`

Use exact equality assertions when values are deterministic. A containment check (`in`, `<=`) is a signal you were unsure of the full result — pin the expected value instead of weakening the assertion. (This is the determinism principle applied to a single assertion: if you can't predict the whole value, control it via fixture/freeze, don't loosen the comparison.)

## Gate 4 — Assert on result objects, not fields

Instantiate the expected object and assert equality: `assert result == MyModel(name="Alice", age=30)`, not `assert result.name == "Alice"`.

**Why:** asserting only one field leaves every sibling field unguarded — if a future change introduces an unexpected side effect on another field, the test still passes. Object equality catches regressions when fields are added or mutated. A `len()` check without asserting the actual items is the same weakness.

When multiple tests each check one index/slice of a collection (count, first item, second item), consolidate into one structural assertion: `assert [s.key() for s in items] == ["a", "b"]` proves count, order, and content in one shot.

**When object equality is not possible** (plain classes without `__eq__`, Django models with auto-generated PKs and timestamps), assert ALL observable fields — not just the one the test name mentions. This preserves the "no unexpected side effects" guarantee that object equality gives for free. Do **not** use tuple comparisons as a workaround (`assert (result.x, result.y) == ("a", "b")`) — tuples strip the field names and become unreadable when the assertion fails.
