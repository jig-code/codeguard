# Imports, layers and package interfaces

## What the tools enforce

- **Ruff `PLC0415`**: imports at the top of the module. The one exception is a measured
  import cost on a path that rarely needs the module: `cli.py`'s `_eval` imports
  `judge_evals` inside the function with `# noqa: PLC0415` and a comment saying why,
  because pydantic-evals is slow to import. Never use an inline import to break a cycle:
  fix the cycle (below).
- **Ruff `TID251`**: `typing.TYPE_CHECKING` is banned. Its message: fix the import cycle.
- **import-linter** (`uv run lint-imports`), with the contracts in `pyproject.toml`:
  - *codeguard packages depend one way*: a layers contract over every package in
    `codeguard`. A package may import only from layers below it; packages in the same
    layer (`claude_provider | codex_provider | api_provider | judge_evals`, `review |
    packages`, `config | repository | file_lock`) may not import each other.
  - *the repository package depends one way*: the same inside `codeguard.repository`.
  - *only the repository package runs git*, *only the libgit2 module runs libgit2* and
    *only judge_evals runs pydantic-evals*: those dependencies stay behind their one
    owner.

Because the layers contract is `exhaustive`, a new package must be added to a layer; put
it in the layer its imports and importers imply, not in a new top layer for convenience.

## Package interfaces

A package's `__init__.py` imports the names other packages use and lists them in
`__all__`. That list is the package's public interface; its submodules are its own.

- **Import another package through its root**: `from codeguard.review import Diagnostic,
  Verdict`, not `from codeguard.review.diagnostic import Diagnostic`.
- **Import a module of your own package by its full submodule path**:
  `from codeguard.review.binding import Binding` inside `review/`. Importing your own
  package's root from inside it runs its `__init__.py` before the importing module has
  loaded, which is a cycle. codeguard doesn't use relative imports.
- A name another package needs is added to the owner's `__init__.py`, not reached by a
  deep import. A deep import of a module the owner doesn't export is a sign the name
  should be exported, or that the code needing it belongs in the owning package.
- Keep `__init__.py` to imports and `__all__`, so importing the root costs nothing more
  than its names.

import-linter checks layers, not facades: no contract fails a deep import of another
package's submodule. Hold to the facade by review.

## Cycles and layer violations

When an import would close a cycle or point up a layer, the boundary is wrong. Fix it in
the design, in this order:

1. Move the shared type to the lowest package that produces it
   ([module-structure.md](module-structure.md#place-a-type-with-its-producer)).
2. Invert the dependency: the lower package defines a `Protocol` for what it needs and
   the higher package implements it, as `review` defines `Judge` for the providers.
3. Merge modules that are one concept split in two.
4. Restructure the dependency graph.

Never loosen an import-linter contract to let an import through, and never hide the
cycle with an inline import or by moving a type somewhere neutral. If none of these
resolves it, stop and ask.
