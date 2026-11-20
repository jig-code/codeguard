# Function design

## Ruff's limits

`pyproject.toml` selects `C90` (McCabe complexity), `PLR0913` (too many arguments) and
`PLR0915` (too many statements) and sets no thresholds, so Ruff's defaults apply:
complexity 10, 5 arguments, 50 statements. `uv run ruff check` enforces them. When a
function nears a limit, work down this list:

1. **Is it a data problem written as logic?** Replace branching that maps inputs to
   outputs with data: a dict keyed by an enum (`_DEFAULT_MODELS[provider]`), a tuple to
   iterate, a property on the enum member.
2. **Does it have more than one responsibility?** Split it into functions named after
   each, on the type that owns each concept. This rule holds whatever the length: a short
   function that fetches *and* decides still breaks it, and passing the limits never
   excuses two responsibilities.
3. **Are some parameters a missing concept?** Group them into a dataclass or model when
   the group means something you would store, pass on or test as a unit.
4. **Is the complexity inherent?** Then a targeted `# noqa` is more honest than a split
   into pieces that model nothing.

A parameter object built at one call site and unpacked at once is indirection, not a
concept: prefer the `# noqa`.

**Configuration goes in the constructor.** When every call to a method passes the same
collaborators (a store, a deadline, a root), they describe what the object is. Make them
fields, as `ClaudeJudge` holds `root`, `model` and `deadline`, so `judge(request)` takes
only what varies per call.

## Pass a collaborator what it uses

Don't hand a wide object to a collaborator that reads a few of its fields. Pass the
fields, or a narrow type built at the call, so the signature says what it depends on and
a test can call it without the wide object. `PatternRuleCheck(root, ruleset, ast_grep)`
takes a root, not the `WorkingTree` or the whole `Rules`.

## Don't pass a value beside its source

A call passes each input at one level of abstraction. When the same variable is an
argument and also inside the expression computing a sibling argument,
`f(lines=judged(binding, file), binding=binding)`, every caller repeats the derivation
and the callee sits at the wrong level. Let the callee take `binding` and derive `lines`
itself. Passing two independent values is fine. `one-form-per-input` covers the
function-side twin: a function that takes a value or what it is derived from.

## Unnamed structure

- **A tuple of unrelated answers is two responsibilities.** A method returning
  `tuple[Verdict, bool]` (the verdict and whether it came from the cache) computed two
  answers and bundled them. Return a named type (`Judgement` names the verdict and the
  files the judge loaded), or let callers ask each question separately. Saving a second
  fetch is valid; cache the fetch, don't bundle the answers.
- **A helper that only packs its arguments into a literal is not an abstraction.** When
  the parameter names and the returned dict's keys are the same words, either inline the
  literal or, if the shape recurs and means something, make it a type with its own
  constructor. `Diagnostic.as_json` earns its place: it adds the derived `id` and
  converts `lines`.
- **A single-call wrapper whose whole body is `[f(x) for x in xs]` over a named `f`** is
  `map` with a name. Inline the comprehension. Keep the wrapper when several call sites
  share it, or when it filters, sorts, deduplicates or reports errors.

## Loops

A loop that branches to compute each item's result and appends it in every branch mixes
mapping one item with iterating: `no-append-in-every-branch` enforces this in production
code, and the same fix applies in tests. A loop that only filters, or that keeps state
across items, is not a per-item map: leave it, or use a comprehension's `if`.

## Anti-patterns

- A helper that is an arbitrary chunk of the original function with no identity of its
  own (`_review_part_two`).
- `**kwargs` used to cut the argument count without cutting complexity. In tests,
  `no-manual-kwargs-check` and `no-pop-from-kwargs` cover the forms they detect, and
  `pytest-factoryboy` owns construction-helper signatures.
- A config or options object that is a bag of the same parameters, there only to satisfy
  `PLR0913`.
- A thin wrapper that forwards all its parameters to an underlying API: call the API.
