# Domain modeling, boundary data and model mapping

## Domain modeling

A type corresponds to a concept in codeguard's domain (a rule, a binding, a verdict, a
change, a diagnostic), not to a mechanical step or a thin wrapper.

- **Don't wrap a bare identity.** A type that only wraps an existing key, with no
  behavior or invariant of its own, adds a name and nothing else. Use the key: a rule id
  is a `str` on `Binding.rule`, not a `RuleTarget(rule: str)`.
- **Don't model a step as a type.** "Creating a binding" isn't a property of the data. A
  constructor that needs grouped arguments takes a `…Params` defined beside it, or is a
  `classmethod` that takes its sources (`Binding.from_config`).
- **Don't keep a copy of a value another object owns.** Read it from the owner. A
  `Binding` holds its `JudgeRule`; a `JudgeCheck` that also stored the rule's name beside
  its binding would hold a copy that can drift. This covers a key stored on an object
  that is already registered or looked up by that key.
- **Promote a repeatedly queried collection to a named type.** A bare `dict`, `list` or
  `set` that callers query with the same idiom at three or more sites, or that is built by
  a loop with a silent last-writer-wins policy, is a missing type that owns the lookups
  and the policy. `Bindings` is a named tuple of `Binding` with its own constructor for
  this reason. Unlike wrapping an identity, wrapping a queried collection adds behavior.

## Parse boundary data once

Data that enters codeguard from outside is parsed once, at the seam where it enters,
into a named type. Code past the seam works on that type, never on the raw shape. The
outside includes a CLI's stdout, a YAML config or binding, a git object, a model's reply,
an environment variable and a hook payload.

The defect is interpreting the raw shape in place: indexing (`parts[0]`, `line[:end]`),
slicing, positional unpacking or `isinstance` deciding what a value means, inside code
whose job is something else. That fuses understanding the format with doing the work,
and the format knowledge spreads to every method that touches it.

Signals, any one enough to look closer:

- index arithmetic on an untyped sequence or `dict[str, object]`;
- the same raw layout read in more than one function;
- `isinstance` used to decide what a raw value means, rather than to dispatch a typed
  union;
- a parameter typed as the raw shape (`dict[str, JsonValue]`, `list[str]` of lines)
  passed several calls deep.

The fix is a model or frozen dataclass whose constructor or `classmethod` takes the raw
shape and whose fields name its parts. codeguard's examples:

- `ClaudeResult.from_stream` turns the `claude` CLI's stream of JSON lines into one
  `ClaudeResult`; message and content shapes are private Pydantic models in the same
  module, discriminated by their `type`. `ClaudeJudge` reads `result.structured_output`
  and `result.loaded_files`, never a line of the stream.
- `Verdict.model_validate` turns a model's structured output into a `Verdict`, and the
  review reads `verdict.violations`.
- Config files load into `Config`, `BindingConfig` and `RulesetConfig`, so no code reads
  a YAML mapping by key.

Build the named type where the data enters, not lazily inside each consumer, and keep it
beside the code that receives the data:
[module-structure.md](module-structure.md#code-that-understands-a-foreign-format-lives-beside-its-caller).

## Model-to-model mapping

Map one typed model to another field by field. `no-dict-round-trip-between-models` bans
the round trip through a dict; follow its note. Explicit assignment makes the mapping a
checked contract: a field renamed, added or removed on either side fails the type check.

`Binding.from_config` is the shape to follow: every field of `Binding` is assigned from
`BindingConfig`, the `Ruleset` or the `JudgeChoice` by name.

When one source type is mapped into more than one target, one mapper owns that mapping
and every target calls it. Don't write the same field-by-field mapping into each target:
the copies drift. A mapping into one target stays inline in that target's constructor.

Two models with the same fields at different boundaries, such as a provider's reply and
codeguard's `Verdict`, stay separate and are mapped where they meet: see the `dry` rule's
"Not a violation" list.
