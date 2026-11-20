# Dead code and orphans

Every production symbol has a production reference. Check that a symbol is reachable
before adding or keeping it, and that it is unreachable before deleting it. Both checks
have false positives, so the verification below is required.

## The five orphan shapes

- **Unreferenced.** Its only occurrence is its definition. Delete it.
- **Used only by tests.** A symbol in `src/` that only `tests/` or `evals/` reference is
  an orphan. Delete it and its tests, unless it is a missing wire: behavior built and
  tested but never connected to the code that should call it. Then connect it. Decide
  which; don't leave it tested but unused.
- **Re-exported only.** A symbol whose only reference is its package's `__init__.py`
  re-export is dead behind the facade. Remove both. (The package form is the thin wrapper
  package in [package-cohesion.md](package-cohesion.md).)
- **A dead method on a live type.** One unused method, property or named constructor on a
  class that is otherwise used. Remove the method.
- **An empty package.** A directory whose only file is an empty `__init__.py`. Delete the
  directory. An empty `__init__.py` beside real modules is a correct package marker, not
  a smell.

## Verify before deleting

A text search misses symbols Python reaches dynamically. Before deleting, rule out:

- **Registration by reference.** argparse `set_defaults` handlers, pytest hooks and fixtures,
  `register()`ed factories, Pydantic validators, callbacks a framework takes (a
  `FunctionModel` function).
- **Names in strings or config.** `[project.scripts]` entry points in `pyproject.toml`,
  the hook commands in `hooks/` and the plugin manifests, import-linter contracts,
  `getattr` by name.
- **Use in its own module.** A private helper called in its own file is live.
- **Work in progress.** Something deliberately wired only in tests mid-feature. Ask
  rather than delete it.

Grep the whole repository for the name before deleting. "I didn't see a caller in this
file" is not verification; "the only hits are the definition and its test" is.
