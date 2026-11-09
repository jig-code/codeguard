# Patterns

- 1–13: code for each pattern in SKILL.md
- Antipatterns
- A fixture that returns a function

## 1. `Make*` factory registered as a fixture

```python
# tests/factories/skill.py
class MakeBinding(factory.Factory):
    class Meta:
        model = Binding

    skill = factory.SubFactory(MakeSkill)


# tests/conftest.py
register(MakeBinding)


# a test
binding = make_binding(skill__name="no-print")
```

`register()` names fixtures after the model, so check no fixture of that name exists
first. A `SubFactory` in a registered factory resolves to the test's fixture for that
model (`SubFactory(MakeSkill)` returns the test's `skill`), so a factory graph shares
objects with the test as a fixture chain would.

## 2. `Params`

```python
class MakeJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    class Params:
        line = 1
        code = "print(1)"

    skill = factory.SubFactory(MakeSkill)
    file = "a.py"
    changes = factory.LazyAttribute(lambda o: f"+{o.line:>6}\t{o.code}\n")
```

## 3. `SubFactory` `__` forwarding

```python
make_binding(skill__name="no-print", skill__text="# No print\n")
```

This replaces a wrapper such as `_make_request(rule)` that only forwards to a nested
factory.

## 4. `SelfAttribute`

Call the factory bare and the whole tree is built; pass any one node and its siblings
derive from it. `Meta.exclude` keeps the `SubFactory`-built objects out of the model's
constructor.

```python
class MakeJudgedDiagnostic(MakeDiagnostic):
    class Meta:
        exclude = ("binding", "request")

    binding = factory.SubFactory(MakeBinding)
    request = factory.SubFactory(MakeJudgeRequest, skill=factory.SelfAttribute("..binding.skill"))
    rule = factory.SelfAttribute("binding.rule")
    file = factory.SelfAttribute("request.file")
```

The tell you need it: the same derivation (`skill=binding.skill`) at more than one call
site, or a fixture whose body is "build B from A's field".

## 5. `LazyFixture`

```python
root = LazyFixture(lambda repo: repo.root)
```

The lambda's parameter names resolve as fixtures. The factory must be `register()`ed.

## 6. `Trait`

```python
class MakeDiagnostic(factory.Factory):
    class Meta:
        model = Diagnostic

    class Params:
        warning = factory.Trait(severity=Severity.WARNING, note=None)


make_diagnostic(warning=True, file="b.py")
```

## 7. Production builder in a fixture

```python
@pytest.fixture
def bindings(tmp_path):
    loader = RulesetLoader(repo=tmp_path, root=tmp_path / "python", name="example/python")
    return Bindings.from_rulesets([loader.load()])
```

For a type passed as an argument, the fixture receives the type and returns the built
value.

## 8. Input model apart from construction

```python
class _Answer(BaseModel):
    reason: str
    level: Literal["low", "high"] | None = None


@pytest.fixture
def answer_schema():
    return output_schema(_Answer)
```

## 9. Derived fixture

```python
@pytest.fixture
def no_print_binding(bindings):
    [binding] = [b for b in bindings if b.rule == "no-print"]
    return binding
```

A zero-argument fixture (`return Thing()`, a literal) earns its place in two cases: it is
an override seam a test or class replaces through pytest's fixture overriding, or it holds
one value two places must agree on (a delay a factory sets and a test waits for).
Otherwise inline it (pattern 10).

## 10. Inline

```python
verdict = Verdict(reason="print bypasses logging.", violations=(make_violation(line=2),))
```

## 11. Subclass a registered factory

Subclass when a would-be helper wraps a registered factory with a fixed configuration and
a few varying knobs. Scenarios that differ only by data use `Params`, `Trait`, `__`
forwarding or a fixture, not a subclass per scenario.

```python
class MakeGeminiBinding(MakeBinding):
    class Params:
        model_name = JudgeProvider.GEMINI.default_model

    model = factory.LazyAttribute(
        lambda o: JudgeModel(provider=JudgeProvider.GEMINI, name=o.model_name)
    )
```

When fields share a derived intermediate, put it on `Params` (`LazyAttribute`) and have
each field read it. When production threads one object into an aggregate and each of its
children, the factory shares one too: build it on `Params` and pass it to each child's
factory, never a copy per child.

## 12. Factory delegating to a builder in `_create`

Declare the builder's inputs as fields; `_create` reads them from `kwargs` and calls the
builder.

```python
class MakeChangedJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    binding = factory.SubFactory(MakeBinding)
    root = LazyFixture(lambda repo: repo.root)
    file = "a.py"
    scope = factory.LazyAttribute(lambda o: AllLines((o.file,)))

    @classmethod
    def _create(cls, model_class, **kwargs):
        return JudgeRequest.of_change(
            kwargs["binding"], kwargs["root"], kwargs["file"], kwargs["scope"]
        )
```

## 13. Abstract base factory

`Meta.model` is one class per factory, so distinct model classes get one factory each;
shared declarations go on an abstract base. Register each concrete subclass.

```python
class MakePackageConfig(factory.Factory):
    class Meta:
        abstract = True

    rulesets = factory.LazyFunction(lambda: {"python": RulesetConfig()})


class MakeGitPackageConfig(MakePackageConfig):
    class Meta:
        model = GitPackageConfig

    git = "https://github.com/example/rules.git"
    ref = "main"


class MakePathPackageConfig(MakePackageConfig):
    class Meta:
        model = PathPackageConfig

    path = LazyFixture(lambda tmp_path: tmp_path)
```

## Antipatterns

| Shape | Use instead |
|---|---|
| Module-level function, or `def _helper(self)` on a test class, that constructs test objects and is none of the `# factory-exempt` shapes | A pattern above |
| Plain function in `conftest.py` imported by module path | Pattern 1, or a fixture |
| Module-level constant built from domain objects | Pattern 9 if it earns a fixture, otherwise inline (pattern 10) |
| Chain of fixtures that build parts and hand-derive the link | Patterns 4 and 5 |
| A parallel second factory for the same model | Pattern 6 or 11 |
| `*Factory` naming | `Make*` |
| `Meta.exclude` for a transient input | `Params` (pattern 2); `exclude` is for `SubFactory`-built objects kept out of the constructor (pattern 4) |
| Factory declarations re-implementing a builder's derivations | Pattern 12 |
| `_create` wrapping a builder for a one-off value | Pattern 7 |
| A subclass per scenario hard-coding its data | Pattern 6 or 11's `Params`, or a fixture supplying the data |
| A child built with its own copy of an object its aggregate holds | Pattern 11's shared intermediate |
| One factory whose `Meta.model` dispatches on a param | Pattern 13 |
| A fixture that defines an input model and calls the builder | Pattern 8 |
| A generated `uuid.UUID` field set from a faker string | Omit the field so its `default_factory` makes a real `UUID`; when a value is needed, assign a `UUID` |

## A fixture that returns a function

A fixture never returns a callable defined inside it. Each reason for one maps to a FactoryBoy feature or a plain fixture:

| "It needs to…" | Use |
|---|---|
| take arguments | Factory kwargs or `Params` |
| create several related objects | A `SubFactory` per layer, composed by a root factory |
| wire objects after creation | `@factory.post_generation` or `RelatedFactory` |
| take a test double | A factory kwarg with a default the caller overrides |
| vary by a type argument | Pattern 7 |
| perform a mutation or action | A named class or function in a test utility module, returned by a plain fixture |
