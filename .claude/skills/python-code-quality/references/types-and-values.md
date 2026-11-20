# Types, enums, invariants, values and Pydantic

## `Any`

basedpyright's `reportExplicitAny` fails an explicit `Any` in `src/`. Don't work around it
with `object` plus casts: give the value a type. JSON is `JsonValue` or a model; a raw
mapping from outside is parsed into a model at the seam
([domain-modeling.md](domain-modeling.md#parse-boundary-data-once)). Test code gets no
`Any` either.

## StrEnum or Literal

- **`StrEnum`** when code branches on the value or uses it as a key: `Severity`
  (`severity is Severity.ERROR`), `JudgeProvider` (keys `_DEFAULT_MODELS`), `Category`.
  Behavior that reads only the member goes on the enum as a property
  (`JudgeProvider.runs_a_cli`).
- **`Literal["x"] = "x"`** as the fixed tag of one variant of a union:
  `GitPackageConfig.kind: Literal["git"] = "git"`.
- **`Literal["a", "b"]`** for a constrained value nothing branches on.

## Discriminated unions are explicit

Never let Pydantic infer a variant from the shape of the data: two variants that overlap
structurally parse silently into the wrong one.

- A union codeguard owns tags each variant with `kind: Literal[...]` and declares
  `Annotated[A | B, Field(discriminator="kind")]`, as `PackageConfig` does.
- A union parsing an outside format whose values codeguard doesn't control, with a
  catch-all variant for messages it ignores, uses a callable `Discriminator` with a
  `Tag` per variant, as `claude_result.py` does for the CLI's stream.

Define a union's variants together, directly above their alias, with nothing unrelated
in between, and inner unions before the outer ones that use them. The alias is the only
place membership shows, so its module is named after it and holds every variant; never
one file per variant.

## Trusting established invariants

A guard that re-checks a fact already guaranteed is dead: the path that would make it
fire can't happen, so it can't be tested, and it exists only to satisfy the type checker.
The guarantee comes from one of three places:

1. **Dispatch.** A registry or `match` already chose this handler by the value's tag, so
   the handler re-checking the tag repeats the routing decision.
2. **An enclosing branch.** An outer `if` or `isinstance` already narrowed the value.
3. **A collaborator's return contract.** A collaborator returns a value only in one case,
   so a branch gated on that value is already narrowed.

Fix it by narrowing at the contract, not in the body. Suppose `ClaudeJudge._result`
raises `JudgeNoVerdict` when `structured_output` is `None`, and `judge()` then checks
`if result.structured_output is None: raise ...` again because the returned
`ClaudeResult` still types the field as optional. The second check is dead. Return what
the contract guarantees instead: the structured output itself, or a type whose field
isn't optional. Make a handler generic over its variant so the static type carries the
guarantee inward; when heterogeneous handlers must share one mapping, the erasure lives
once at that mapping, never in each handler.

basedpyright's `reportUnnecessaryIsInstance` and `reportUnnecessaryComparison` catch the
cases it can see statically. Validating input the code received (an unknown rule id, a
malformed binding) is not a re-check; it stays and fails loud.

## Enum usage

- Never `.value` on a `StrEnum` or `IntEnum` member: it already is a `str` or `int`.
- Wherever a parameter, field, key or argument is typed as an enum, pass the member
  (`Severity.WARNING`, `JudgeProvider.GEMINI`), never the string. A literal string at an
  enum-typed boundary skips the enum's check; a typo or a renamed member fails silently.
  This holds in tests: assert `severity=Severity.ERROR`, not `severity="error"`. The one
  exception is data that enters from outside (YAML, JSON, an environment variable),
  which Pydantic parses into the member at the seam.

## Value provenance

### One home for defaults

A field's default is declared once, on the type that owns the field, and callers omit it.
`BindingConfig.severity` defaults to `Severity.ERROR`; `JudgeProvider.default_model`
holds each provider's tested model. A consumer that writes
`binding.severity or Severity.ERROR`, or `self.model or "gemini-4-argon"`, states the
default a second time in the wrong place, and the two drift. A coalescing fallback
(`x or default`, `x if x is not None else default`) is a default in disguise.

The sharpest tell is asymmetry: a type that defaults one field but leaves a sibling
required, while some consumer coalesces the sibling.

### The form of a value states its role

When a value is supplied, its form matches why:

- **omitted** when it is irrelevant here, so the type's default applies;
- **a literal** when the code asserts it or branches on it;
- **taken from its owner** when the code correlates on it. A `tool_use_id` comes from the
  stream it answers; a diagnostic's `id` from `Diagnostic.id`. A made-up value that the
  code later matches against is a lie about where it came from.

Where a test's values come from: `pytest-factoryboy`.

## Pydantic

### `arbitrary_types_allowed`

Set it only on a model whose own field annotation holds a type Pydantic can't build a
schema for. `Manifest` sets it because its `VersionRange` fields hold `packaging`'s
`SpecifierSet`. A model whose fields are models, enums, primitives and their collections
doesn't need it, and a nested model that sets it never makes its container need it: the
container reuses the child's schema. Don't copy the flag onto a new model or a split
module by habit.

### Validators

Keep validators on the model with `@field_validator` and `@model_validator`, for the
model's own invariants (`LineRange.validate_end_is_not_before_start`). Extract one to a
shared place only when several models use identical logic. Validation that needs the
file system, a ruleset or other models belongs to the code that has them.
