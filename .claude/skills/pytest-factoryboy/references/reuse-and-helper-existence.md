# Reuse and helper existence (gates 5, 14, 16)

- Reuse shared test infrastructure
- Seed children through their parent
- Import types from their defining module
- Factory convergence and `# factory-exempt`
- Helpers earn their parameters and existence

## Reuse shared test infrastructure

Before writing a helper, factory, fake or input builder, search `tests/conftest.py`,
`tests/factories/` and the test utility modules (`tests/recording_judge.py`,
`tests/git_repo.py`, `tests/fakes/`) for one that builds the same type. Grep for the
return type (`JudgeRequest`, `Diagnostic`). When a factory exists, use it and pass the
variant through its fields or traits (`make_diagnostic(judged=True)`), rather than a local
`_make_judged_diagnostic` that re-types `Diagnostic(...)` with its own defaults. When
several test files define the same helper, move it into a shared factory.

Use the idioms the suite already uses. When `None` and an empty collection mean different
things, default to `None` and guard with `if param is None:` rather than a sentinel
object.

## Seed children through their parent

When a production creator (a builder, a `from_*`/`of_*` constructor, a service method)
makes a parent and its children, test setup drives that creator and keeps its result.
A conftest loop that re-implements the creator
is `test-quality` gate 10 shadowing.

A child type's own tests may build children directly, since the child is the SUT.
Elsewhere, don't hand a child a reference to a parent that was never created (a fresh
uuid, a path to a file never written): create the parent first. A missing check that the
reference resolves is a modeling gap to fix, not to rely on. When a test needs the
parent's id or result, take it from the parent creator's result, not by navigating back
through child links. When the production operation has no
result that carries what callers need, add it to production rather than a test-only
bundle type.

## Import types from their defining module

`conftest.py` is for fixture discovery. Import a type from the module that defines it
(`from recording_judge import RecordingJudge`), never `from conftest import ...`.

## Factory convergence and `# factory-exempt`

Test data builders are `Make<Type>` factories in `tests/factories/`, registered in
`tests/conftest.py`. A top-level `def make_*`/`def build_*` that returns a construction,
or a collection of them, is a factory to write unless it is one of three shapes, each
marked `# factory-exempt: <why FactoryBoy can't build it>`:

- **Dynamic model.** It builds a model class from a `type` argument, and the model is
  setup for a different SUT. When the test checks what the model builder produces, the
  builder call is the act: inline it (`test-quality` gate 10).
- **Behavior-bearing stub or fake.** The object's point is its methods (a recording spy),
  not its data. Prefer a named top-level stub class that the function instantiates.
- **Fixed setup graph.** It assembles objects no caller parameterizes, and at least one
  has behavior or sits at a process boundary (a subprocess, a recording spy). A nested
  frozen dataclass or Pydantic model is data a `SubFactory` graph builds, and a function
  callers pass arguments to is a parameterized builder: both are factories.

These are factories, not exempt shapes:

- A function that returns a collection of constructions the suite already writes inline
  (`tuple(make_violation(line=n) for n in lines)`): inline the literal.
- Plain data FactoryBoy could build with `SubFactory`, `LazyAttribute` or `Trait`, even
  awkwardly.

Each input form gets its own branch-free factory, not one factory reconciling
alternatives (`test-quality` gate 13).

The marker is a claim to verify:

- The function still passes `test-quality` gates 10 and 14.
- A side effect given as the reason is consumed: name the value it produces (a written
  file feeds `changes`) and check the call sites. When every caller overrides or ignores
  it, the side effect is dead and the function is an ordinary factory.
- An import-linter reason names the contract in `pyproject.toml` and the forbidden module,
  and the function imports that module.

## Helpers earn their parameters and existence

For each local `_make_*`/`_build_*`, check:

1. **Call sites.** Exactly one: inline it.
2. **Parameters.** One no caller passes a non-default value to is dead: delete it. One
   every caller passes has a dead default: make it required and delete any constant that
   backed the default.
3. **Projection.** The body is one builder call read for one attribute
   (`return make_judge_request(...).prompt`): return the object, or inline.
4. **Wrapped literal.** The body wraps a builder in a literal the suite writes inline
   (`Verdict(reason=..., violations=tuple(make_violation(...)))`): use the literal.
5. **Re-passed defaults.** Every argument beyond the caller's own equals the builder's
   default (`make_binding(skill=skill, severity=Severity.ERROR, rule=skill.name)`): strip
   them, and inline the bare call that remains.
6. **One-constructor pass-through** (`return Thing(context=context)`): inline it, unless
   its return annotation is load-bearing. Inline it at one site and run basedpyright. When
   it stays green, inline everywhere. When only a `cast()` or `# type: ignore` fixes it,
   keep the wrapper as the one place the type is widened, and report the production typing
   defect.

A specialization that sets non-default configuration on a registered factory is a
subclass (pattern 11), not a helper. A new shared builder is for a construction that
recurs across files with no inline idiom; wrapping an existing inline idiom in a helper
isn't.
