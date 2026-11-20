---
name: python-code-quality
description: "Applies codeguard's design standards for Python: names that match their bodies, an owner for every function and type, cohesive modules and packages, single responsibility, parsing outside data once, one owner per shared mapping, typing, enums, Pydantic, imports, and types with overlapping responsibility. Use before writing, editing, refactoring or reviewing any .py file in codeguard, tests included, and whenever a change adds, moves, renames or deletes a function, class, constant or module."
---

# Python code quality

## Scope

Every `.py` file, tests included. The `test-quality` and `pytest-factoryboy` skills add
the test-specific gates and decide every question they cover: signal (a test that only
re-checks a framework has none), mocking, assertions, fixtures, factories, helpers and
where a test's values come from. Code in an eval case or fixture that holds a defect on
purpose keeps it.

## Naming

A name states what its body does: summarize the body in one sentence; its verb and nouns
appear in the name, and every word of the name is borne out by the body. A misleading
name is worse than a vague one. A constant's name is its contract: reuse it only for what
the name says. [references/naming.md](references/naming.md)

## Module structure and ownership

One concept per module, judged by its contents, not its name. Every loose function has
an owner: the type it builds, the type whose data it reads, or a type named after the
operation it coordinates. Behavior that reads only one type's own fields lives on that
type and stays there when its caller moves. Code that understands an outside format
lives in its own module beside the code that calls it. A type lives with the code that
constructs it. A `Protocol` or ABC earns its place by inverting a dependency or having
two implementers today.
[references/module-structure.md](references/module-structure.md)

## Package cohesion

A reader can predict a concept's package from its responsibility. Flag a flow split
across sibling packages, a package that only re-exports another, a module outside the
package that owns its concept, and a package of unrelated modules.
[references/package-cohesion.md](references/package-cohesion.md)

## Single responsibility

A type or module has one reason to change. Two unrelated reasons is a violation however
small the type; size alone never justifies a split. A frozen value type whose methods
read only its own fields has one reason to change.
[references/single-responsibility.md](references/single-responsibility.md)

## Domain modeling, boundary data and mapping

A type models a concept, not a step or a wrapper around one identity, and no object
keeps a copy of a value another owns. Outside data is parsed once, where it enters, into
a named type; code past that point never indexes or slices the raw shape. A mapping from
one model into several targets has one owner.
[references/domain-modeling.md](references/domain-modeling.md)

## Dead code

Every production symbol has a production caller. Verify with a repository-wide search,
and rule out dynamic reach, before deleting anything.
[references/dead-code.md](references/dead-code.md)

## Overlapping responsibility

Two types that both answer "who owns X?" are one responsibility split in two: pick one
owner. A caller that needs a pipeline's work calls the component that runs it, never
rebuilding its inputs or wiring. [references/overlapping-responsibility.md](references/overlapping-responsibility.md)

## Function design

One responsibility per function, whatever its length. Pass a collaborator the values it
uses, not a wide object, and never a value beside the input it was derived from. No
`tuple` or `dict` literal of unrelated answers. To get under a Ruff limit: data before
branching, split responsibilities, group parameters that form a concept, then a targeted
`# noqa`. [references/function-design.md](references/function-design.md)

## Comments and docstrings

A comment signals unclear code: fix the name or design first. Keep a comment or
docstring only for a why that no name or structure can hold. Never document what the code
used to do.

## Imports and dependencies

- Import another package through its root `__init__.py`; import a module of your own
  package by its full submodule path. import-linter checks layers, not this.
- An inline import needs a measured reason, such as import cost, a targeted `# noqa` and
  a comment saying why. Never use one to dodge a cycle.
- Fix a cycle or layer violation in the design: move the shared type to the lowest
  package that constructs it, invert the dependency with a consumer-owned `Protocol`,
  merge modules that are one concept, or restructure. Never loosen a contract. If none
  works, stop and ask.
- `getattr` only for a name that is truly dynamic.

## Types, enums, values and Pydantic

- `StrEnum` when code branches on the value or keys a mapping with it; `Literal` for a
  union variant's tag or a constraint nothing branches on. Tag discriminated unions
  explicitly and keep the variants together with the alias.
- Don't re-check what dispatch, an enclosing branch or a collaborator's return contract
  already guarantees; narrow the type at the contract.
- Never `.value` on a `StrEnum` or `IntEnum`. Where an enum is expected, pass the member,
  never its string, in tests too.
- A default lives once, on the type that owns the field; `x or default` in a consumer is
  a default in the wrong place. A supplied value's form states its role.
- `arbitrary_types_allowed` only where a field's own annotation needs it. Validators sit
  on the model whose own fields they check.

[references/types-and-values.md](references/types-and-values.md)

## Review workflow

Before finishing a change, run `uv run ruff check`, `uv run basedpyright` and
`uv run lint-imports`, then copy this checklist and check each touched module against
it. A line counts as checked only when you can say why it passes; on a failure, fix the
code and check the line again.

```
Python review:
- [ ] Naming: each name matches its body both ways; no constant reused against its name
- [ ] Ownership: each loose function has its owner; own-field behavior is on its type
- [ ] Modules: one concept each; outside-format parsing in its own module beside the caller
- [ ] Packages: each concept's package is predictable from its responsibility
- [ ] Responsibility: one reason to change per type, module and function
- [ ] Modeling: types model concepts; outside data parsed once; one owner per shared mapping
- [ ] Dead code: every new or touched symbol has a production caller
- [ ] Overlap: one owner per responsibility; no rebuilt pipeline wiring
- [ ] Functions: narrow inputs; no pre-derived arguments; no unnamed tuple or dict answers
- [ ] Comments: only a why that structure can't hold
- [ ] Imports: package roots across packages; no cycle dodged
- [ ] Types: no Any; StrEnum vs Literal; explicit unions; no re-checked invariants
- [ ] Enums and values: members not strings; one home per default
- [ ] Pydantic: no needless arbitrary_types_allowed; validators on their model
- [ ] Placement: each type with the code that constructs it; each interface earned
```
