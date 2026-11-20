# Types, enums, invariants, values and Pydantic

## Annotations

- No `Any`, in tests too. JSON is `JsonValue` or a model. Don't dodge the ban with
  `object` plus casts.
- `StrEnum` when code branches on the value or keys a mapping with it; behavior that
  reads only the member is a property on the enum. `Literal["x"] = "x"` as one union
  variant's tag; `Literal["a", "b"]` for a constraint nothing branches on.
- Discriminated unions are explicit, never inferred from shape. A union the code owns
  tags each variant with `kind: Literal[...]` and uses `Field(discriminator="kind")`. An
  outside format with a catch-all variant uses a callable `Discriminator` with a `Tag`
  per variant. Define the variants together, directly above the alias, inner unions
  first, in one module named after the alias.

## Trusting established invariants

A guard that re-checks a fact already guaranteed by dispatch, an enclosing branch, or a
collaborator's return contract can never fire. Narrow at the contract instead: have the
collaborator return the narrowed type, or make the handler generic over its variant.
When heterogeneous handlers share one mapping, the type erasure lives once at that
mapping. Validating input the code received is not a re-check.

## Enum usage

- No `.value` on a `StrEnum` or `IntEnum` member.
- Where a parameter, field or key is typed as an enum, pass the member, never its
  string, in tests too. Outside data is parsed into the member where it enters.

## Value provenance

- **One home for defaults.** A field's default is declared once, on the type that owns
  it; callers omit it. A coalescing fallback in a consumer (`x or default`,
  `x if x is not None else default`) is a default in the wrong place. The sharpest tell:
  a type that defaults one field and leaves a sibling required while a consumer
  coalesces the sibling.
- **Form states role.** Omit a value when irrelevant; use a literal when the code asserts
  or branches on it; take it from its owner when the code correlates on it, never a
  made-up value. Test values: `pytest-factoryboy`.

## Pydantic

- `arbitrary_types_allowed` only on a model whose own field annotation needs it. A
  nested model that sets it never makes its container need it. Don't copy it onto a new
  or split model by habit.
- Validators sit on the model whose own fields they check; extract one only when several
  models share identical logic. Validation that needs the file system, configuration or
  other models belongs to the code that has them.
