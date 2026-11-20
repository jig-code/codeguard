---
name: python-code-quality
description: "Covers the design standards for codeguard's Python: naming, where a function or type lives, responsibilities, typing, enums, Pydantic, imports and duplication, and which codeguard rules already enforce part of them. Use before writing, editing or reviewing any .py file in codeguard, tests included, and whenever a change adds, moves, renames or deletes a function, class or module."
---

# Python code quality

## Scope

These standards apply to every `.py` file: `src/`, `tests/` and `hooks/`. A test file is
held to them as well. Code in an eval case or fixture that holds a defect on purpose
(`evals/`, `evals-pending/`) keeps the defect its case is about.

The `test-quality` and `pytest-factoryboy` skills add the test-specific gates (signal,
mocking, assertions, fixtures, factories, helpers and where a test's values come from)
and decide every question they cover. A test that only re-checks Pydantic, the standard
library or another framework has no signal: `test-quality` gate 1.

codeguard reviews itself with the `general` and `python` rulesets of
jig-code/codeguard-rules, pinned in [`.codeguard/config.yaml`](../../../.codeguard/config.yaml).
Where a rule enforces a requirement, its section below names the rule instead of
restating it: read the rule's message and note, and follow them. A rule bound only to
production code still describes good test code; the test skills say where it differs.
When a rule lands that covers guidance below, delete that guidance and name the rule.

Ruff, basedpyright and import-linter, configured in [`pyproject.toml`](../../../pyproject.toml),
enforce the rest of what is mechanical: `uv run ruff check`, `uv run basedpyright` and
`uv run lint-imports`.

## Naming

State in one sentence what the symbol does, read from its body. The sentence's verb and
nouns appear in the name, and every word of the name is borne out by the body. A
misleading name is worse than a vague one: `process` under-informs, while
`merge_diagnostics` on a function that only filters them misinforms. A constant's name is
its contract: reuse a constant only for what its name says, and give a different purpose
its own name. Keep one verb per concept across collaborating types.

[references/naming.md](references/naming.md)

## Module structure and ownership

- **One concept per module.** Bucket names are banned by `no-bucket-module-names`. A
  well-named module is still a bucket when it holds a second unrelated public class or
  loose functions that serve another concept.
- **Every loose function has an owner.** A function that builds one type is a
  `classmethod` on it; one that reads one instance's own data is a method or property on
  that instance's type; one that coordinates several types belongs to a type named after
  the operation. Keep it module-level only when no type would be less coherent without it.
- **Behavior that reads only a type's own fields lives on that type**, wherever its first
  caller sits: a derived mapping, a sort key, a formatted line, a predicate. Keep it there
  when a change moves its caller.
- **Code that understands a foreign format lives beside the code that calls it, not inside
  it.** The `claude` CLI's stream is parsed in `claude_result.py`, beside
  `claude_judge.py`, not in the judge.
- `__all__` only in a package's `__init__.py`: `all-only-in-init`.

[references/module-structure.md](references/module-structure.md)

## Package cohesion

Modules that serve one flow or feature share one package, and a reader can predict a
concept's package from its responsibility. Flag a flow split across sibling packages, a
package that only re-exports another, a module that sits outside the package owning its
concept, and a package of unrelated modules.

[references/package-cohesion.md](references/package-cohesion.md)

## Single responsibility

A type or module has one reason to change. Two unrelated reasons is a violation however
small the type is, and size alone never justifies a split. A frozen value type whose
methods read only its own fields has one reason to change, its shape. A function whose
name needs "and", or several functions that all take the same arguments, is a type in
disguise.

[references/single-responsibility.md](references/single-responsibility.md)

## Domain modeling and boundary data

A type models a concept, not a step or a wrapper around one identity, and nothing keeps
a copy of a value another object owns. Data that enters from outside (a CLI's JSON, a
YAML file, a git object, a model's reply) is parsed once, at the seam, into a named type;
code past the seam never indexes, slices or `isinstance`-dispatches the raw shape.

[references/domain-modeling.md](references/domain-modeling.md)

## Model-to-model mapping

Map one model to another field by field. The dict round-trip is banned by
`no-dict-round-trip-between-models`. When one source type maps into several targets,
one mapper type owns that mapping and each target calls it.

[references/domain-modeling.md](references/domain-modeling.md#model-to-model-mapping)

## Dead code and orphans

Every production symbol has a production caller. Delete an unreferenced symbol, a
symbol only tests use (unless it is a missing wire), a re-export nothing imports, a dead
method on a live type, and an empty package. Grep the whole repository, and rule out
dynamic reach, before deleting.

[references/dead-code.md](references/dead-code.md)

## Duplication, overlapping responsibility and re-implemented orchestration

The `dry` judge rule reviews production code for repeated steps, a process's stages run
outside the process, a collection that relists another set, and a second type for the
same outside thing. Its binding leaves tests out: hold test code to its text too, with
`pytest-factoryboy` deciding reuse of builders and fakes. This skill adds what `dry`
doesn't judge: two types that both answer "who owns X?", and a caller that rebuilds the
inputs of a pipeline such as `Rules.review` instead of calling it.

[references/duplication.md](references/duplication.md)

## Function design

Stay within Ruff's limits: `C901` (complexity 10), `PLR0913` (5 arguments) and `PLR0915`
(50 statements). `pyproject.toml` selects them and sets no thresholds, so Ruff's
defaults apply. To get under a limit: turn branching into data, split responsibilities,
group parameters that form a concept, and only then add a targeted `# noqa`.

- One responsibility per function, whatever its length.
- A `tuple` or `dict` literal of unrelated answers, and a helper that only packs its
  arguments into a literal, are unnamed concepts.
- Pass a collaborator the values it uses, not a wide object, and don't pass a value
  beside the input it was derived from.
- Already enforced: `one-form-per-input`, `no-append-in-every-branch`, and in tests
  `no-manual-kwargs-check` and `no-pop-from-kwargs`.

[references/function-design.md](references/function-design.md)

## Comments and docstrings

Treat a comment as a sign the code is unclear, and fix the name or design first. Keep a
comment only for a why that no name or structure can hold, such as an outside constraint.
A docstring meets the same test. Document what code does, never what it used to do.
Comments in tests: `no-comments-in-tests`.

## Imports

Imports go at the top of the module (`PLC0415`), except for a measured import cost,
with a targeted `# noqa` and a comment saying why; never to dodge a cycle. `TYPE_CHECKING` imports are banned (`TID251`). Use direct attribute access; `getattr` only for a name that is truly dynamic.
Package layering and facades: [references/imports.md](references/imports.md).

## Type annotations

No explicit `Any` in `src/` (basedpyright's `reportExplicitAny`); use `JsonValue` or a
model for JSON. Use `StrEnum` when code branches on the value or keys a mapping with it,
`Literal["x"] = "x"` as a union variant's tag, and `Literal["a", "b"]` for a constrained
value nothing branches on. Tag a union's variants and keep them together with the alias.

[references/types-and-values.md](references/types-and-values.md)

## Trusting established invariants

Don't re-check a fact that dispatch, an enclosing branch or a collaborator's return
contract already guarantees. Narrow the type at the contract instead. basedpyright's
`reportUnnecessaryIsInstance` and `reportUnnecessaryComparison` catch the cases the type
checker can see. Validating input the code received is not a re-check.

[references/types-and-values.md](references/types-and-values.md#trusting-established-invariants)

## Enum usage

Never call `.value` on a `StrEnum` or `IntEnum` member. Wherever a parameter, field or
key is typed as an enum, pass the member (`Severity.ERROR`), never its string, in
production and tests alike.

## Value provenance

A default lives once, on the type that owns the field; callers omit it. A fallback
written as `x or default` in a consumer is a default in the wrong place. A supplied
value's form states its role: omitted when irrelevant, a literal when asserted or
branched on, and taken from its owner when the code correlates on it. Test values:
`pytest-factoryboy`.

[references/types-and-values.md](references/types-and-values.md#value-provenance)

## Pydantic configuration and validation

Set `arbitrary_types_allowed` only on a model whose own field annotation needs it; a
nested model never makes its container need it. Keep validators on the model for its own
invariants, and extract one only when several models share it. Validation that needs
anything beyond the model's fields belongs to the code that has it.

[references/types-and-values.md](references/types-and-values.md#pydantic)

## Type ownership and placement

A type lives in the package that constructs it, in a module named after the concept,
however many packages import it. `no-bucket-module-names` already bans a `contracts`
module. A type that many packages need sits in a low layer that imports nothing above it
(`line_range`, `config`).

[references/module-structure.md](references/module-structure.md#place-a-type-with-its-producer)

## Interfaces must earn their existence

A `Protocol` or ABC earns its place when it inverts a dependency between layers or has
two implementers today; a planned implementer doesn't count. The consumer defines it from
its own needs. `Judge` in `review/` earns its place on both counts. A dict of handlers is
`typed-dispatch-registries`.

[references/module-structure.md](references/module-structure.md#interfaces-must-earn-their-existence)

## Circular dependencies and package interfaces

`lint-imports` enforces the layers in `pyproject.toml`'s import-linter contracts: a
package imports only from layers below it. Import another package through its root
`__init__.py`, and a module of your own package by its full submodule path. Fix a cycle
or a layer violation in the design; if you can't, stop and ask.

[references/imports.md](references/imports.md)

## Review checklist

Before finishing, walk [references/review-checklist.md](references/review-checklist.md),
one line per section. A line counts as checked only when you can say why it passes.
