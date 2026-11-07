# Signal and Mocking Gates (1–4)

The first four gates are the foundation: a test must be deterministic, exercise real objects, assert exact values, and assert whole result objects. Together they guarantee a test fails for exactly one reason — a real regression in your code — and never passes while masking one.

## Gate 1 — No-signal tests

Before writing any test, verify it adds signal. Every test must answer: *what change to my own code would make this fail?* If the only way to break it is editing the declaration it mirrors (**tautology**), breaking the framework — Pydantic/stdlib defaults, type-acceptance, serialization (**framework behavior**), or breaking already-tested generic code (**true redundancy**), it adds no signal — don't write it.

The deciding question for any assertion against a declared value: *if it went red, would I fix the code or fix the test?* Fix-the-code → real invariant, keep it. Fix-the-test → tautology/framework echo, drop it.

See [references/redundant-tests.md](redundant-tests.md) for the three defects and their concrete instances.

## Gate 2 — Real objects over mocks

`MagicMock` and `patch()` are acceptable **only at the process boundary**: HTTP calls to third-party APIs, cloud SDK calls that leave the machine (a model provider's API), or services requiring external credentials. codeguard's tests replace the judge CLIs (claude, codex, gemini) with fake CLIs at that boundary.

Git and the filesystem are **not** an external boundary — unit tests use a real temporary git repo (`GitRepo`, the `repo` fixture) and `tmp_path`. Never mock git output, file reads, services that read the working tree, or any collaborating class within the codebase.

**Never `patch()` internal functions, factories, or module-level callables.** Patching `build_my_thing()` or `my_service.get()` hides integration bugs just as much as mocking a class does. If a function builds a dependency, use dependency injection or existing test helpers that construct the real object with test-appropriate configuration.

**Before defining an inline stub class, search for identical or equivalent stubs in other test modules** — if one exists, extract it to a shared location and reuse it rather than duplicating.

The fact that a parameter is "not used" in the test is irrelevant — pass the real object anyway.

**Never substitute empty/dummy data to bypass failures in production code.** If using real data causes the test to fail, that failure is a bug — fix the production code, don't hollow out the test inputs. Empty stubs, null objects, and `make_binding(triggers=frozenset())` where real triggers belong all hide bugs by avoiding the code paths that matter. Exception: an empty value is acceptable in factory/wiring tests where the SUT provably does not exercise it.

**Seed through production's creator; never fabricate a reference to dodge creating its parent.** When production has a single creator for an object — a builder, a `from_config`/`of_change` constructor, a service method — a unit test seeds through that creator, or through a thin setup helper that drives it and returns the objects (gate 10). Re-implementing the creator's construction path inline in `conftest` — a hand-rolled loop that parallels the production builder — is gate-10 species (a) shadowing: the test exercises a creation path production never runs. **Factory Boy makes a *real* object when you genuinely need one; it is not a workaround for real data** and never licenses skipping a parent. The tell: a child is given a reference (`source_id=str(uuid4())`, `*_id=<fresh uuid>`, a path to a file never written) pointing at a parent that was never created. A missing check that the reference resolves is not permission to fabricate — it is a separate modeling gap to fix, not to exploit. Seed the parent (or drive the creator that does), then let the child reference it.

**Dependency preference hierarchy** (use the first option that works):

1. Real object (always preferred)
2. Shared stub/fake from conftest or a test utility module
3. Inline stub implementing a protocol (only for framework contract tests where the fake IS the test's domain model)
4. `patch()` / `MagicMock` (only at process boundaries — HTTP, cloud SDK, external credentials)

### A shared fake abstracts one layer — extend it by configuration, not by cross-layer subclassing

A shared fake (`RecordingJudge`, `ScriptedGemini`) exists to abstract **one seam**. `RecordingJudge` abstracts the judge: you express expectations by *configuring* it (a canned verdict, the loaded files) and *asserting on its observable in-layer state* (the requests it `received`, in order). That is the whole contract.

**Do not subclass a shared fake to override a method so the override (a) asserts internally or (b) reaches into a *different* subsystem.** Both halves are the violation:

```python
# BAD — judge fake subclassed to read the judgement cache inside judge,
# with an accumulator whose only job is to prove the override ran
@dataclass(frozen=True)
class StoreCheckingJudge(RecordingJudge):
    store: Cache | None = None
    unstored_files: list[str] = field(default_factory=list)

    def judge(self, request):
        self._assert_not_stored(request)  # assertion buried in the fake
        self.unstored_files.append(request.file)
        return super().judge(request)

    def _assert_not_stored(self, request):
        assert self.store is not None
        assert list(self.store) == []  # reaches into the cache layer


# GOOD — use the shared fake directly; assert on its in-layer state in the test body
wrapped = RecordingJudge()
...
CachedJudge(wrapped=wrapped, store=store, root=repo.root).judge(request)
assert wrapped.received == [request]
```

Why it's wrong:

- **Wrong layer.** The override punctures the abstraction the fake exists to provide — a judge fake now knows about the cache's store. Whether the store was empty is a *cache* concern; if it's worth testing, it's tested at `CachedJudge`'s seam, not by overriding `judge`.
- **Hidden assertion.** The real check lives inside the fake, where no reader looks; the test body reads as if it only checks the requests the judge received. The accumulator (`unstored_files`) is a tell — it exists solely to prove the buried override actually ran.
- **Can't be expressed by configuration.** There is no *configuration* of a judge fake that means "also check the cache's store," because that isn't a judge fact. Needing to *subclass and inject other-subsystem logic* is the signal the assertion doesn't belong on this seam.

**Tell:** `class X(RecordingJudge)` / `class X(ScriptedGemini)` whose overridden method body contains an `assert`, a read of another subsystem (the cache's store, files on disk), or an accumulator that exists only to record that the override fired. **Fix:** use the shared fake directly and assert on its observable in-layer state in the test body. A thin subclass that only *configures* the fake (a canned verdict, scripted answers) is fine — the line is overriding behavior to assert or cross layers. If a genuinely lower-layer invariant matters (e.g. a cache miss before the wrapped judge runs), give it its own test at that layer rather than mutating the judge seam.

## Gate 3 — Prefer `==` over `in`

Use exact equality assertions when values are deterministic. A containment check (`in`, `<=`) is a signal you were unsure of the full result — pin the expected value instead of weakening the assertion. (This is the determinism principle applied to a single assertion: if you can't predict the whole value, control it via fixture or an injected value, don't loosen the comparison.)

## Gate 4 — Assert on result objects, not fields

Instantiate the expected object and assert equality: `assert result == MyModel(name="Alice", age=30)`, not `assert result.name == "Alice"`.

**Why:** asserting only one field leaves every sibling field unguarded — if a future change introduces an unexpected side effect on another field, the test still passes. Object equality catches regressions when fields are added or mutated. A `len()` check without asserting the actual items is the same weakness.

When multiple tests each check one index/slice of a collection (count, first item, second item), consolidate into one structural assertion: `assert [s.key() for s in items] == ["a", "b"]` proves count, order, and content in one shot.

**When object equality is not possible** (plain classes without `__eq__`, objects with generated ids and timestamps), assert ALL observable fields — not just the one the test name mentions. This preserves the "no unexpected side effects" guarantee that object equality gives for free. Do **not** use tuple comparisons as a workaround (`assert (result.x, result.y) == ("a", "b")`) — tuples strip the field names and become unreadable when the assertion fails.
