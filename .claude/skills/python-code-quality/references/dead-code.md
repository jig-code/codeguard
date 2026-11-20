# Dead code and orphans

Every production symbol has a production reference.

## The five orphan shapes

- **Unreferenced**: delete it.
- **Used only by tests**: delete it and its tests, unless it is a missing wire (built and
  tested but never connected); then connect it. Don't leave it tested but unused.
- **Re-exported only** from a package `__init__.py`: remove both.
- **A dead method on a live type**: remove the method.
- **An empty package** (only an empty `__init__.py`): delete the directory. An empty
  `__init__.py` beside real modules is a correct package marker.

## Verify before deleting

Search the whole repository for the name, and rule out dynamic reach:

- registration by reference: CLI subcommand handlers, pytest hooks and fixtures,
  registered factories, Pydantic validators, framework callbacks;
- names in strings or config: `pyproject.toml` entry points, hook and plugin manifests,
  import-linter contracts, `getattr` by name;
- use within its own module;
- work in progress wired only in tests: ask before deleting.
