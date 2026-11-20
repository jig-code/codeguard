# Review checklist

One line per section of the skill, in its order. List the public classes and functions in
each touched module, then check each line. A line counts as checked only when you can say
why it passes. In test files, run the `test-quality` checklist as well.

- **Naming**: does each name share its verb and nouns with a one-sentence summary of its
  body, both ways, with nothing misleading, and is each constant used only for what its
  name says?
- **Module structure and ownership**: does each module hold one concept, does each loose
  function have the owner it builds, reads or coordinates, does behavior that reads only
  one type's fields live on that type, and does a foreign format's parser sit beside its
  caller rather than inside it (`no-bucket-module-names`, `all-only-in-init`)?
- **Package cohesion**: could a reader predict each module's package from its
  responsibility, with no split flow, wrapper package, misplaced module or bucket
  package?
- **Single responsibility**: does each type and module have one reason to change,
  judged by grouping methods by reason, not by size?
- **Domain modeling and boundary data**: does each new type model a concept rather than
  a step, a bare identity or a copy of another object's value, and is outside data
  parsed once into a named type at the seam?
- **Model-to-model mapping**: is each mapping explicit field by field, with one mapper
  when one source feeds several targets (`no-dict-round-trip-between-models`)?
- **Dead code and orphans**: does every new or touched production symbol have a
  production caller, checked by a repository-wide grep and the dynamic-reach list?
- **Duplication**: does the change pass `dry`, test code included, with no second type
  answering "who owns X?" and no caller rebuilding a pipeline such as `Rules.review`?
- **Function design**: is each function within Ruff's limits for the right reason, with
  one responsibility, no unnamed tuple or dict of answers, no wide object or pre-derived
  argument (`one-form-per-input`, `no-append-in-every-branch`, and in tests
  `no-manual-kwargs-check`, `no-pop-from-kwargs`)?
- **Comments and docstrings**: does each comment or docstring hold a why that no name or
  structure could, and nothing about past behavior (`no-comments-in-tests`)?
- **Imports**: are imports at the top, with no `TYPE_CHECKING`, no `getattr` on a static
  name, cross-package imports through the package root and no new layer violation?
- **Type annotations**: no `Any`, `StrEnum` where code branches or keys, `Literal` for a
  tag or an unbranched constraint, and explicit, contiguous discriminated unions?
- **Trusting established invariants**: does any guard re-check what dispatch, an
  enclosing branch or a collaborator's return contract already guarantees?
- **Enum usage**: no `.value` on a `StrEnum` or `IntEnum`, and the member, never its
  string, wherever an enum is expected, tests included?
- **Value provenance**: is each default declared once on its owner with no coalescing
  fallback elsewhere, and does each supplied value's form match its role?
- **Pydantic configuration and validation**: is `arbitrary_types_allowed` only where a
  field's own annotation needs it, and is each validator on the model whose invariant it
  checks?
- **Type ownership and placement**: does each type live in the lowest package that
  constructs it, in a module named after its concept?
- **Interfaces must earn their existence**: does each `Protocol` or ABC invert a layer
  dependency or have two implementers today, designed from the consumer's needs
  (`typed-dispatch-registries` for handler dicts)?
- **Circular dependencies and package interfaces**: does `uv run lint-imports` pass with
  no contract loosened, and is every cycle fixed in the design rather than hidden?
