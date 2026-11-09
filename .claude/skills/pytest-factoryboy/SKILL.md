---
name: pytest-factoryboy
description: "Covers how codeguard tests construct their objects: FactoryBoy Make* factories registered with pytest-factoryboy, fixtures, inline construction and construction helpers. Use when writing, editing or reviewing a factory, fixture, conftest.py, a file under tests/factories/, or any test code that builds test data."
---

# Constructing test objects

This skill owns every object-construction decision in codeguard's tests;
`test-quality` gates 5, 9, 11, 13, 14, 15 and 16 point here.

Construct test objects with the patterns below. A module-level function in a test file
or conftest is allowed when it is a callback the SUT or a framework hook takes
(`def _no_answer(messages, info): raise AssertionError` for `FunctionModel`) or one of the
three `# factory-exempt` shapes in
[reuse-and-helper-existence.md](references/reuse-and-helper-existence.md). A fixture
never returns a callable defined inside it.

## Patterns

1. **`Make*` factory registered as a fixture.** Use for a reusable type with configurable
   fields: `Make<Type>` in `tests/factories/`, `register()`ed in `tests/conftest.py`,
   used through its `make_<type>` fixture.
2. **`Params`.** Use for a transient input that shapes fields but isn't one.
3. **`SubFactory` `__` forwarding.** Use to set a nested object's field at the call site
   instead of a wrapper.
4. **`SelfAttribute`.** Use when a field derives from another object the factory builds,
   instead of a chain of fixtures that hand-derive the link.
5. **`LazyFixture`.** Use when a declaration needs a per-test value only pytest has (a
   repo root, a store).
6. **`Trait`.** Use for a variant of the same model that differs in one or a few fields.
7. **Production builder in a fixture.** Use for a one-off, unparameterized object that
   production builds through a builder, and for a type passed as an argument.
8. **Input model apart from construction.** Use when a test needs its own input model:
   a class for the data, a fixture for the builder call.
9. **Derived fixture.** Use for a sub-value of another fixture, and for a zero-argument
   fixture that is an override seam or a value two places must agree on.
10. **Inline.** Use for a bare constructor call, and for a configured construction of a
    type with no registered factory.
11. **Subclass a registered factory.** Use for a fixed structural specialization with a
    few varying knobs.
12. **Factory delegating to a builder in `_create`.** Use for a reusable, parameterized
    or nested type that production builds through a builder.
13. **Abstract base factory.** Use for distinct model classes whose factories share
    declarations.

### Inline or factory

Inline a bare constructor call or literal, however many tests repeat it and including a
stateful double you assert on (`wrapped = RecordingJudge()`), unless it is an override
seam or a value two places must agree on (pattern 9); otherwise a fixture only hides the
arrange (`test-quality` gate 17). Inline a configured construction of a type with no
registered factory; when the same construction recurs across files and the suite has no
inline idiom for it, register a factory (pattern 1). When a factory is registered, tests
and fixtures build the type through its `make_<type>` fixture, inside other constructors
included.

When production builds a type through a builder (`Bindings.from_rulesets`,
`JudgeRequest.of_change`), go through that builder (pattern 7 or 12); re-implementing its
derivations drifts when it changes.

## Which pattern

| You need | Pattern |
|---|---|
| A reusable object with configurable fields | 1 |
| A transient input to a factory | 2 |
| A nested field set at one call site | 3 |
| A field derived from another built object | 4 |
| A per-test value inside a factory | 5 |
| A variant differing in a few fields | 6 |
| A registered factory with fixed structure and a few knobs | 11 |
| A builder's output, once | 7 |
| A builder's output, reusable or nested | 12 |
| A test-only input model | 8 |
| A sub-value of a fixture | 9 |
| A bare constructor or literal | 10 |
| Factories for related model classes | 13 |
| A mutation or action, not construction | A named class or function in a test utility module, returned by a fixture |

When nothing fits, stop and ask the user which pattern applies, saying what you are
building and what makes it hard to place. Don't invent a new shape or fall back to a
module-level helper.

## References

- [patterns.md](references/patterns.md): code for each pattern and the antipatterns they
  replace. Read when writing a factory or fixture.
- [fixture-and-data-design.md](references/fixture-and-data-design.md): one object per
  fixture, setup fixtures, test data and identities through fixtures (gates 9, 15).
- [reuse-and-helper-existence.md](references/reuse-and-helper-existence.md): reusing
  shared builders and fakes, seeding children through their parent, the
  `# factory-exempt` shapes, and when a helper is a shim (gates 5, 14, 16).
- [construction-helper-parameters.md](references/construction-helper-parameters.md):
  helper signatures and where a test gets its values (gates 11, 13).
