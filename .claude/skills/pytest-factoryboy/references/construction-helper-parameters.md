# Helper parameters and sourcing values (gates 11, 13)

## Declare parameters in the signature

A construction helper's `**overrides` bag is allowed when it flows untouched into one
typed sink (a model, a factory, a dataclass) that validates its keys. When the body
`.pop()`s keys out of the bag to route them elsewhere or set them after construction, those
keys are parameters: declare them typed and keyword-only. A popped bag turns a misspelled
argument into a silent default, so the test passes against a setup nobody wrote; a
hand-rolled `raise TypeError("unexpected ...")` is the tell.

```python
# Popped keys hide the parameters
def make_judge(**overrides):
    store = overrides.pop("store", None)
    wrapped = overrides.pop("wrapped", RecordingJudge())
    ...


# Declared
def make_judge(*, wrapped: Judge, store: Cache) -> CachedJudge: ...
```

Merging the bag into a dict of defaults before splatting it (`defaults.update(overrides)`)
is fine only when that dict goes whole into the one sink.

## One input form

A helper takes each input in one form. It doesn't accept two forms reconciled by a guard
(`if bindings is None and rulesets: ...`) or derive one constructor input from another
(bindings from rulesets): that shadows the production logic. Take the assembled value (a
`Binding`, a `JudgeRequest`) and let the caller convert.

That includes a one-line convenience parameter that is not a field of the model and lifts
a value into one variant of a union (`git_url=` wrapped into
`packages=(GitPackageConfig(git=git_url, ref="main"),)`). Delete it; callers pass the
field with the variant spelled out. A factory `Params` entry that picks the variant is the
same branch.

## No production-sounding names for test shapes

A test-only alias or structure that exists to shorten a helper call doesn't take a
production-like name (`CaseVerdict = tuple[str, Outcome]` beside the real `EditReview`).
Spell the structure in the signature (`*verdicts: tuple[str, Outcome]`) or use the
production type.

## Trace values to their source

When a test needs a value (an id, a ref, a key), take it from the input that first
produced it, not by searching a result the test built from it. A local helper whose job is
"get X out of Y", where Y was built from X, is the tell.
