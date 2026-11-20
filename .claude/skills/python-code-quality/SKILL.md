---
name: python-code-quality
description: "Applies codeguard's design standards for Python: names that match their bodies, an owner for every function and type, cohesive modules and packages, single responsibility, parsing outside data once, one owner per shared mapping, typing, enums, Pydantic, imports, and types with overlapping responsibility. Use before writing, editing, refactoring or reviewing any .py file in codeguard, tests included, and whenever a change adds, moves, renames or deletes a function, class, constant or module."
---

# Python code quality

Applies to every `.py` file, tests included. The `test-quality` and `pytest-factoryboy`
skills decide every test-specific question. Code in an eval case or fixture that holds a
defect on purpose keeps it.

## References

Read each reference whose topic the change touches; for a review, read them all.

- **Naming** (types, functions, constants, modules): [references/naming.md](references/naming.md)
- **Module structure** (what a module holds, who owns each function, where a type lives,
  when an interface is justified): [references/module-structure.md](references/module-structure.md)
- **Package cohesion** (adding, moving or splitting packages):
  [references/package-cohesion.md](references/package-cohesion.md)
- **Single responsibility** (a type or module that may do two jobs):
  [references/single-responsibility.md](references/single-responsibility.md)
- **Domain modeling** (new types, outside data, mappings between models):
  [references/domain-modeling.md](references/domain-modeling.md)
- **Dead code** (adding, removing or deleting symbols): [references/dead-code.md](references/dead-code.md)
- **Overlapping responsibility** (a new type with a role name, or a caller assembling a
  pipeline): [references/overlapping-responsibility.md](references/overlapping-responsibility.md)
- **Function design** (signatures, return values, helpers, Ruff's limits):
  [references/function-design.md](references/function-design.md)
- **Types and values** (annotations, unions, enums, guards, defaults, Pydantic):
  [references/types-and-values.md](references/types-and-values.md)

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

## Review workflow

Copy this checklist and check off each step for every touched module. A step counts as
done only when you can say why the code passes; on a failure, fix the code and repeat
the step.

```
Python review:
- [ ] Run uv run ruff check, uv run basedpyright and uv run lint-imports
- [ ] Naming
- [ ] Module structure
- [ ] Package cohesion
- [ ] Single responsibility
- [ ] Domain modeling
- [ ] Dead code
- [ ] Overlapping responsibility
- [ ] Function design
- [ ] Types and values
- [ ] Comments and docstrings
- [ ] Imports and dependencies
```
