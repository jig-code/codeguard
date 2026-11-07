# Construction-Helper Parameters and Sourcing Values

Rules for the *signature* of any construction helper/fixture/factory, and for where a test gets the values it feeds in.

## Construction helpers declare their own parameters

A test/conftest construction helper's `**kwargs`/`**overrides` is allowed *only* as transparent pass-through: the bag flows **untouched** into a single typed sink (a Pydantic model, a Factory Boy factory, a dataclass) whose schema already declares and validates the keys. The moment the body `.pop()`s named keys out of the bag to apply per-key logic, route them to different destinations, or mutate them onto an object after construction, those keys are real parameters and must appear in the signature — typed, keyword-only, with defaults. **Why:** a helper's signature is its contract. A destructured bag empties that contract: the available parameters become invisible at the call site, and a misspelled kwarg (`reporterr=spy`) silently falls through to a default instead of raising, so the test runs green against a configuration the author never intended — the worst outcome for a *test* helper, because it manufactures false confidence. Explicit parameters turn that typo into an interpreter `TypeError` at the call site and restore type-checking, autocomplete, and safe rename. **The distinguishing test is mechanical: does the body splat the bag whole into one constructor (forward — allowed), or does it `.pop()` named keys out (destructure — flag)?** A `.pop("x", default)` call, or a hand-rolled `raise TypeError("unexpected ...")`, is the tell.

**Alternative-input branching is the related function-design defect.** A helper that offers two paths to the same input reconciled by a runtime guard (`if bindings is None and rulesets: ...`), or that **derives one constructor input from another** (builds `bindings` from `rulesets`, a registry from steps), breaks "one canonical input form — no alternative-input branching": a function takes each input in exactly one form, and the caller converts to it. It is especially corrosive in a **test** construction helper: the derivation shadows the very production logic the test should be exercising, and the call site can't tell which form is live — manufacturing the same false confidence as a destructured `**kwargs` bag. Fix the same way: take the lowest abstraction (the already-assembled value — a `Binding`, a `JudgeRequest`) directly, and move the derivation to the call site. Make the assembled object the only path.

**The trivial-wrap variant is the one that slips through review — flag it anyway.** The derivation that gets caught is usually compute-heavy (a registry built from steps); the one that survives is a **one-line convenience param that lifts a value into the field's real type** — most often wrapping into **one member of a discriminated union**. The tell: the helper exposes a param (`git_url=...`) whose name is *not* a field of the constructed model, and the body wraps it into the model's actual field (`packages=(GitPackageConfig(git=git_url, ref="main"),)`), picking one union variant. It reads as harmless because the wrap is one line — but it is the same defect at full strength: the call site can't see *which variant* is live, and the convenience alias hides the union the production code switches on. The cheapness is the trap, not an excuse. **Fix: delete the convenience param; callers pass the canonical field with the variant spelled out.** Do **not** relocate the wrap into a Factory `LazyAttribute`/`Params` that picks the variant from an optional param — that is the same branch moved inside the factory.

**Do not invent production-sounding names for test-only structural inputs.** A local alias/dataclass/TypedDict whose shape exists only to make a helper call shorter must not reuse or approximate production vocabulary. `CaseVerdict = tuple[str, Outcome]` is not the app's `EditReview`; it is a test-friendly pair that later gets converted into the real result. Naming the tuple like a domain model creates synonym drift, hides that the helper is translating test data into production shape, and sends reviewers looking for a nonexistent app concept. Keep simple structural inputs explicit in the helper signature (`*verdicts: tuple[str, Outcome]`), use the production type directly when that is the real contract, or choose an obviously test-data name only after the helper earns a shared abstraction.

```python
# ALLOWED — transparent forwarding: the bag flows whole into one typed sink that
# validates every key. A typo raises from the constructor; the keys ARE its fields.
def make_state(**overrides) -> SomeState:
    defaults = {"status": "pending", "items": []}
    defaults.update(overrides)
    return SomeState(**defaults)


# FLAG — destructure-and-dispatch: named keys are popped out and routed to different
# destinations, so no single sink can validate the key set — which is exactly why it
# must hand-roll the TypeError. Every popped key is a real parameter in hiding.
def make_runtime(*, resources=None, **overrides):
    formatter = overrides.pop("formatter", default_formatter)  # -> into config
    on_complete = overrides.pop("on_complete", None)  # -> into config
    service = overrides.pop("service", RealService())  # -> into factory
    ctx = Factory(formatter=formatter, on_complete=on_complete, service=service).build()
    reporter = overrides.pop("reporter", None)
    if reporter is not None:
        ctx.reporter = reporter  # -> mutated post-build
    if overrides:
        raise TypeError(f"unexpected: {', '.join(overrides)}")  # rebuilds a language feature
    return Runtime(context=ctx)


# FIXED — the popped keys become the signature. Typos error at the call site; the
# second sink is routed by name, no bag needed.
def make_runtime(
    *,
    formatter: Formatter = default_formatter,
    on_complete: OnComplete | None = None,
    service: Service | None = None,
    reporter: Reporter | None = None,
) -> Runtime: ...
```

## Trace values to their source, don't extract from assembled results

When a test needs a value (an id, a ref, a key) for setup or assertions, trace it back to the production type that *originally produces* it — don't write a helper that digs it out of a downstream composite. If you find yourself writing a loop, filter, `find_by_*`, or scanning helper to extract data from a type the test already built, you are looking at the wrong level: go back one more factory/constructor to find where that value was a named, direct input. Keep tracing until you reach the source. **Tell:** any local helper whose job is "get X out of Y" where Y was built from X in the first place. The test built the graph — it knows the inputs; reading them back out of an assembled result is needless indirection that obscures what the test actually depends on.
