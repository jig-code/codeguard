---
name: pytest-factoryboy
description: "Enforce idiomatic pytest + FactoryBoy + pytest-factoryboy patterns when writing, editing, or reviewing test code (test_*.py, conftest.py, tests/factories/**). Trigger BEFORE any edit to test files. Covers factory structure, fixture wiring, and the antipatterns they replace."
---

# pytest + FactoryBoy Patterns

All test object construction MUST use one of the patterns below. Module-level helpers (`def _make_*`, `def _build_*`, `def _context`) and module-level constants (`_SPEC = ...`, `_REGISTRY = ...`) are antipatterns.

## Pattern 1: `Make*` factory registered as fixture

Factories live in `tests/factories/`, named `Make<Type>`, registered in `conftest.py`. Produces fixture `make_<type>`.

```python
# tests/factories/field_specs.py
class MakeConfiguredFieldSpec(factory.Factory):
    class Meta:
        model = ConfiguredFieldSpec
    definition = factory.SubFactory(MakeFieldSpecDefinition)

# conftest.py
register(MakeConfiguredFieldSpec)

# test
def test_something(self, make_configured_field_spec):
    spec = make_configured_field_spec(definition__field_ref=FieldRef(domain_key="profile", name="status"))
```

## Pattern 2: `Params` for transient shortcuts

```python
class MakeFieldSpecDefinition(factory.Factory):
    class Meta:
        model = FieldSpecDefinition
    class Params:
        field_name = "field"
        domain_key = "test_domain"
        reasoning_mode = ReasoningMode.SCALAR_EXTRACTION
    field_ref = factory.LazyAttribute(lambda o: FieldRef(domain_key=o.domain_key, name=o.field_name))
    behavior = factory.LazyAttribute(lambda o: FieldBehavior(reasoning_mode=o.reasoning_mode))
```

## Pattern 3a: `SelfAttribute` derives one field from another — never a fixture chain

When a factory needs a value **derived from another object it builds**, declare it with
`SelfAttribute`. Do NOT write a fixture that constructs the parts and hand-derives the
link at each call site — that duplicates the derivation once per test module and is what
a chain of `x_campaign` → `x_execution` fixtures actually is.

- **Same factory:** `campaign_id = SelfAttribute("campaign.id")` — build the object, pass
  only its id to the constructor. Pair with `Meta.exclude` so the object itself is not
  passed on.
- **Into a nested SubFactory:** `..` navigates up to the parent factory's context, so a
  SubFactory can reference a **sibling declaration**:
  `campaign = SubFactory(CampaignFactory, office=SelfAttribute("..prospect.office"))`.

This is what makes a factory both/and rather than either/or: call it bare and the whole
tree is built; pass **any one node** and every sibling derives from it.

```python
class MakeCampaignExecution(factory.Factory):
    class Meta:
        model = CampaignExecution
        exclude = ("prospect", "campaign")

    prospect = factory.SubFactory(ProspectFactory)
    campaign = factory.SubFactory(
        CampaignFactory, office=factory.SelfAttribute("..prospect.office")
    )
    campaign_id = factory.SelfAttribute("campaign.id")
    prospect_id = factory.SelfAttribute("prospect.id")

MakeCampaignExecution()                    # builds prospect + campaign
MakeCampaignExecution(prospect=prospect)   # campaign's office derives from it
```

**Tell you needed this:** the same derivation (`office=prospect.office`) written
at more than one call site, or a fixture whose only body is "construct B from A's field".

## Pattern 3b: `LazyFixture` injects a per-test value a factory cannot build

A factory declaration that needs something only pytest can provide — a client from an
async fixture, a tmp path, a running environment — uses `LazyFixture`. The callable's
parameter names are resolved as fixtures.

```python
from pytest_factoryboy import LazyFixture

client = LazyFixture(lambda campaign_environment: campaign_environment.client)
```

Requires the factory be `register()`ed. This is the answer to "my factory needs an
injected collaborator that only exists per-test" — do not fall back to a plain fixture
that calls the constructor by hand.

**`SubFactory` in a registered factory resolves to the fixture of that model's name**, not
a fresh object (`subfactory_fixture` calls `getfixturevalue(underscore(model.__name__))`).
So `SubFactory(ProspectFactory)` returns the test's existing `prospect` fixture — a factory
graph shares objects with the test exactly as a fixture chain does. Registering binds by
**model** name, so check for an existing fixture of that name before registering.

## Pattern 3: SubFactory `__` forwarding

Use `__` (double-underscore) to pass values through to a nested SubFactory at the call site. This is the idiomatic way to customize nested objects without introducing wrapper helpers or Params shortcuts — the factory's SubFactory declaration already defines the relationship, and `__` lets callers reach any depth.

**When to use:** A test needs to override one or more fields on a nested SubFactory. Instead of writing a helper that wraps the factory call with pre-filled nested kwargs, pass them directly with `__` notation.

**Why:** Eliminates module-level helpers like `_make_runtime(collection_steps=[...])` that exist only to forward arguments to a nested factory. The `__` syntax is FactoryBoy's built-in mechanism for this — a wrapper adds zero value.

```python
# Factory definition — config is a SubFactory
class MakeCollectionRuntime(factory.Factory):
    class Meta:
        model = Runtime
    class Params:
        config = factory.SubFactory(MakeCollectionWorkflowConfig)
    context = factory.LazyAttribute(lambda o: build_context(o.config))

# Call site — forward collection_steps to the nested config SubFactory
runtime = MakeCollectionRuntime(config__collection_steps=[step_0, step_1])

# Multi-level forwarding works too
make_configured_field_spec(
    definition__field_ref=FieldRef(domain_key="profile", name="marital_status"),
    definition__presentation=FieldPresentation(description="Marital status"),
)
```

**Anti-pattern this replaces:**
```python
# WRONG — wrapper that just forwards to nested factory kwargs
def _make_runtime(collection_steps=None):
    steps = collection_steps or [default_step]
    return MakeCollectionRuntime(
        config=MakeCollectionWorkflowConfig(collection_steps=steps, field_specs=FieldSpecIndex())
    )
```

## Pattern 4: `factory.Trait` for same-model variants

Use a Trait when usage patterns differ by one/few param values. Do NOT create a separate factory class.

```python
class MakeFieldCaptureContext(factory.Factory):
    class Meta:
        model = FieldCaptureContext
    operation = UieOperation.EXTRACT
    class Params:
        update = factory.Trait(operation=UieOperation.UPDATE)

# Usage:
make_field_capture_context(update=True, state_models={"care_plan": GoalsState})
```

## Pattern 5: Construct through the production builder

When production constructs a type through a builder API, the test MUST go through that **same** builder — never reimplement its assembly (hand-rolling the fields the builder derives) in a factory's declarations or a helper. Which mechanism depends on how the object is used:

- **One-off, unparameterized instance** (e.g. a single merged `field_specs`) → call the builder directly in a fixture; do NOT wrap it in a factory.
- **Reusable / parameterized / composed-as-a-`SubFactory` type** (e.g. a `DomainDefinition` built per `domain_key` and nested in `collection_steps`) → register a `Make*` factory whose `_create` delegates to the builder — see Pattern 10.

```python
@pytest.fixture
def field_specs():
    registry = build_field_definition_registry({"domain": DomainState})
    return (
        ConfiguredFieldSpecIndexBuilder(registry)
        .add_option_source("status_options", ConfiguredOptionSourceFactory(options=[...]))
        .build()
    )
```

## Pattern 6: Separate state definition from construction

State models are test inputs — define them as classes (the data), then use a separate fixture for construction (the builder call). Do NOT conflate both in one fixture.

```python
class _DomainState(BaseModel):
    status: Annotated[str | None, FieldConfig(
        option_source=OptionSourceRef("status_options"),
    )] = None

@pytest.fixture
def field_specs():
    registry = build_field_definition_registry({"domain": _DomainState})
    return (
        ConfiguredFieldSpecIndexBuilder(registry)
        .add_option_source("status_options", ConfiguredOptionSourceFactory(options=[...]))
        .build()
    )
```

## Pattern 7: Derived fixtures for sub-values

```python
@pytest.fixture
def auto_select_spec(field_specs):
    spec = field_specs.get_by_ref(FieldRef(domain_key="domain", name="status"))
    assert spec is not None
    return spec
```

### When a zero-argument fixture earns its place

A fixture whose body is a bare constructor call (`return Thing()`) or a literal
(`return timedelta(days=1)`) is pure indirection unless one of these holds:

1. **It is an override seam** — a test or class substitutes it via pytest fixture
   overriding. Nothing else provides that mechanism, so it must be a fixture.
2. **Two places must agree on one value** — a delay a factory sets and a test sleeps for;
   inlining the literal twice lets them drift silently.

Otherwise inline the call (Pattern 8) — including a stateful double you assert on
(`spy = SpyChatGroupManager()`): construct it and assert on it in the test body, no matter
how many tests do the same. Being observed is not a reason to hoist it, and neither is the
test count; a `return Thing()` fixture only hides that arrange (`test-quality` gate 17).
`test-quality` gate 5 defers to this rule.

## Pattern 8: Inline for trivial single-constructor (2-3 sites)

For types that have NO registered `Make*` factory, inline construction is fine when only 2-3 call sites exist.

**If a `Make*` factory is registered in conftest, always use the fixture form (`make_<type>`)** — even when building instances inline as arguments to other constructors. Consistency matters: one construction path per type, no mixing `MakeX(...)` class calls with `make_x(...)` fixture calls across the suite.

```python
state = UserInputEvaluationState(
    uie_request=UserInputEvaluationRequestFactory(operation=UieOperation.UPDATE),
    domain_states={"test_domain": _FakeState()},
    update_resolution=result,
)
```

## Pattern 9: Specialize a registered factory by subclassing it

When a would-be helper wraps a registered `Make*` with a **fixed config plus a few varying knobs**, subclass that factory and override its `Params` defaults. Reuse beats a helper, and a named subclass is fine — the "separate factory for same model" antipattern targets duplicate *parallel* factories, not a subclass reusing its parent. Trait (Pattern 4) is for one/few differing params; a substantial fixed-config specialization is a subclass.

When two constructed fields must share a **derived intermediate** (e.g. `collection_steps` and `field_specs` built from one registry), put it on `Params` as a `LazyFunction`/`LazyAttribute` and have each field read `o.<name>` — the same value a helper held in a local variable. **Concrete case — one `FieldSpecIndex` per config:** production builds a single merged index and threads that same object into `config.field_specs` **and** every domain it contains. So the factory must share one index too: put it on `Params`, read it into `field_specs`, and pass it into each domain's factory rather than letting the domain build its own — never a private per-domain index. A per-domain index alongside an option-sourced config index is the **drift smell** (test-quality).

**Subclass only for *structural/behavioral* specialization, never for *data*.** If the "specializations" differ merely by which state classes, which option sources, or which context keys they use, that is differ-by-**data** — use `Params`/`Trait`/`__` forwarding, or a fixture that supplies the data (the shared-intermediate above). A tree of per-scenario subclasses each hard-coding a specific domain graph + option-source payload is inheritance used where parameters belong.

```python
class MakeIdentityRuntime(MakeCollectionRuntime):          # reuses the parent's `context` builder
    class Params:
        field_registry = factory.LazyFunction(_identity_field_registry)   # shared intermediate
        summary_formatter = None
        config = factory.LazyAttribute(lambda o: MakeCollectionWorkflowConfig(
            collection_steps=[CollectionStep(domains=[identity_definition(o.field_registry)])],
            field_specs=o.field_registry,                  # both fields read one registry
            summary_formatter=o.summary_formatter))

# conftest:  register(MakeIdentityRuntime)   →   make_identity_runtime(chat_id=..., summary_formatter=...)
```

Subclassing to specialize is FactoryBoy's own recommended mechanism (a subclass inherits every parent declaration and overrides only what it names): https://factoryboy.readthedocs.io/en/stable/introduction.html#inheritance

## Pattern 10: Factory over a production `Builder` — delegate in `_create`

When a **reusable** type is produced in production by a `Builder` (`XBuilder(...).build()`) and the suite needs many parameterized instances of it (varying by a key) or composes it inside other factories, register a `Make*` factory whose `_create` delegates to that builder. This keeps ONE construction path (the production builder) while giving the factory its parameterization and `SubFactory` composition. `_create` is FactoryBoy's sanctioned extension point for "build via a builder/manager method, not by calling the class" ([recipes: custom `_create`](https://factoryboy.readthedocs.io/en/stable/recipes.html#custom-manager-methods)).

**Never reimplement the builder's derivations as factory declarations** (hand-rolling whatever the builder computes internally). That is a parallel construction path that drifts when the builder changes — test-quality gate 10.

Shape: declare the builder's *inputs* as factory attributes, then have `_create` read them off `**kwargs` (read the bag, not a positional signature — that survives adding declarations) and call the builder.

```python
class MakeThing(factory.Factory):   # production: ThingBuilder(a, b).build()
    class Meta:
        model = Thing
    a = ...            # the builder's inputs, as ordinary declarations/Params/LazyAttribute
    b = ...

    @classmethod
    def _create(cls, model_class, **kwargs):
        return ThingBuilder(kwargs["a"], kwargs["b"]).build()
```

`_create` is the create-strategy hook (the default; nothing here is built or stubbed, so no `_build`). Canonical instance in this repo: `MakeDomainDefinition` → `DomainDefinitionBuilder`.

**Fixture (Pattern 5) vs. factory `_create` (Pattern 10):** a *one-off* builder output → fixture; a *reusable/parameterized/nested* builder output → factory delegating in `_create`. The banned shape is reimplementing the builder inside the factory, not delegating to it.

## Pattern 11: Abstract base factory for distinct models that share construction

`Meta.model` binds **one** model class per factory — `Trait` and call-time kwargs vary field *values*, never the model *class*. So a discriminated union / family of **distinct model classes** (each with different required fields) needs **one factory per model**; there is no idiomatic "one factory, pick the class by a param." When those per-model factories share construction logic (a common Param, a derived id, a default), hoist the shared declarations into an **abstract base factory** (`class Meta: abstract = True`) and subclass it — each subclass sets its own `Meta.model` and adds only its own fields. This is FactoryBoy's documented inheritance idiom ([abstract factories](https://factoryboy.readthedocs.io/en/stable/reference.html#factory.FactoryOptions.abstract)); it removes the duplication without collapsing distinct models.

```python
class MakeMessage(factory.Factory):        # never instantiated directly
    class Meta:
        abstract = True
    class Params:
        parent = None
    parent_id = factory.LazyAttribute(lambda o: o.parent.id if o.parent else uuid4())

class MakeCommandMessage(MakeMessage):
    class Meta:
        model = CommandMessage
    command = "run"

class MakeStatusMessage(MakeMessage):
    class Meta:
        model = StatusMessage
    code = 200
```

Register each concrete subclass (not the abstract base) in conftest → `make_command_message` / `make_status_message`. **Do NOT** point `Meta.model` at a dispatch callable to fake a single param-switched factory: that declares every variant's fields on one factory, silently accepts wrong-variant fields, and erases the per-model type — fighting the framework.

---

# Antipatterns (NEVER correct)

| Shape | Why it's wrong | Use instead |
|-------|---------------|-------------|
| Module-level helper function (any name) that constructs test objects | Each concern has a dedicated home — construction in factories/fixtures, act+assert+projection in the test body | Pattern 1/4/8 (construction) or inline in test body (act/assert/projection) |
| Plain function in conftest imported by module path | conftest provides fixtures (auto-discovered), not importable helpers; if it takes params and constructs objects, it's a factory | Pattern 1 (register as factory) or convert to fixture |
| Module-level constant (`_X = ...`, `X = SomeType(...)`) | Test data belongs in fixtures | Pattern 7 if it meets an earner; otherwise inline the literal (Pattern 8) — a cheap value like `A_DAY = timedelta(days=1)` is an alias, not test data, and a fixture wrapping it is the same indirection in a new place |
| Chain of fixtures that build parts and hand-derive the link (`b_fixture(a)` returning `B(company=a.office.company)`, then `c_fixture(b, a)` returning `C(b.id, a.id)`) | That is a factory's object graph written by hand; the derivation is copied per module | Pattern 3a (`SelfAttribute`, `..` for siblings) + Pattern 3b (`LazyFixture`) |
| `class TestX: def _helper(self, ...)` | Not how pytest/FactoryBoy work | Pattern 1 |
| `@pytest.fixture` returning inner callable | See "No exemptions" below | Pattern 1/5/action fixture |
| Duplicate *parallel* factory for same model | Trait for one/few params; a fixed-config specialization is a *subclass*, not a duplicate | Pattern 4 / Pattern 9 |
| Module-level helper wrapping a registered `Make*` with fixed config + a few varying knobs | It's a factory specialization, not a helper | Pattern 9 (subclass it) |
| `*Factory` naming for test builders | Convention is `Make*` | Pattern 1 |
| `Meta.exclude` for transient fields | Use `Params` block | Pattern 2 |
| Hand-assembled specs with synthetic attrs | Build from real state models | Pattern 5 + 6 |
| Factory reimplementing a production `Builder`'s field derivations in its declarations | Parallel construction path; drifts when the builder changes (test-quality gate 10) | Pattern 10 (delegate in `_create`) |
| FactoryBoy `_create` wrapping a builder for a *one-off, unparameterized* value | A fixture is simpler; `_create` earns its place only for a reusable/parameterized/nested type | Pattern 5 (fixture) |
| Per-scenario factory subclass hard-coding a specific domain graph / option-source payload (differ-by-data) | Inheritance used where params belong; scenarios differ by data, not structure | Pattern 4/9 (Params/Trait/`__`) or a fixture supplying the data |
| Domain built with its own private `FieldSpecIndex` beside an option-sourced `config.field_specs` | Two indices for one config = drift; production shares one object | Pattern 9 (shared intermediate) + Pattern 10 |
| Distinct model classes' factories repeating the same Param/derivation/default | Duplicated construction across a model family; `Meta.model` is one class per factory | Pattern 11 (abstract base factory) |
| One factory whose `Meta.model` dispatches on a param to emit different model classes | Fights the framework: all variants' fields on one factory, wrong-variant fields silently accepted, per-model type erased | Pattern 11 (one subclass per model) |
| Fixture defining state model AND calling builder | Conflates input data with construction | Pattern 6 (separate them) |
| Overriding a model-generated pk or any `UUIDField` with a faker/string value (`id = LazyAttribute(lambda _: fake.uuid4())`) | faker's `uuid4()` returns a `str`; Django never coerces in-memory assignments, so factory-built instances carry `str` pks while DB-refetched rows carry `uuid.UUID` - model `__eq__` (pk comparison) silently fails and every consumer ends up hand-coercing with `str(...)` casts, `uuid.UUID(...)` wraps, or refetch fixtures | Omit the field entirely (the model's `default=uuid4` generates a real `uuid.UUID`); if an explicit value is genuinely needed, assign a `uuid.UUID`, never a string |

## No exemptions — fixture-returning-callable is always convertible

There is no `# factory-exempt` annotation. Every fixture-returning-callable maps to a FactoryBoy feature or a simpler fixture shape. The common "but it needs…" justifications each have a direct answer:

| Justification | FactoryBoy mechanism |
|---------------|---------------------|
| "Needs arguments" | Factory kwargs or `Params` (Pattern 2) |
| "Does DB seeding / creates multiple related objects" | `SubFactory` chain — one factory per layer, root factory composes them |
| "Wires M2M / FK relationships after creation" | `@factory.post_generation` or `RelatedFactory` |
| "Uses test doubles / injected collaborators" | Factory kwargs with defaults (the caller overrides when needed) |
| "Takes a dynamic type arg (generic over model)" | Pattern 5 — call the production builder in a fixture that takes the type as a param; FactoryBoy is the wrong tool when the *type* varies, but a plain fixture returning the result (not a callable) is correct |
| "Performs a mutation / action (not construction)" | This is not construction — use a plain fixture returning a helper object (dataclass or named function), not a fixture-returning-anonymous-callable |

**Decomposition principle:** "It does multiple things" is the signal to use SubFactory composition, not a reason to bypass FactoryBoy. A fixture that creates Company → Office → User → Chat → Workflow is five `SubFactory` declarations in a `MakeWorkflow` factory.

**Action fixtures:** A fixture whose purpose is to perform a *mutation* (e.g., aging a timestamp, signing a token, running a side-effect) is not object construction and does not need FactoryBoy — but it still must not be a fixture-returning-anonymous-callable. Use a named helper (dataclass with a method, or a top-level function in a test utility module) and expose it via a plain fixture that returns the instance.

**Arrange/act/assert belong in the test body, not a fixture.** "A fixture is a thing, not an action" also bans a fixture that *returns a real object* but **performs the test's arrange actions to produce it** — starting a workflow/job, advancing a simulated clock (`sleep`/skip/`freeze_time`), issuing the calls that drive the SUT into its precondition. Returning a genuine object (a workflow handle, a model row) does not launder the hidden action: the tell is *what the fixture does to build it*, not *what it returns*. When a single test consumes it, inline those steps into that test's body so arrange, act, and assert stay visible (this is `test-quality` gate 17). A setup fixture earns its place only when shared by more than one test **and** setting up genuinely *ambient environment* (workers, queues, flags, registries). And if the arrange is too large to sit in the body, that is a missing production seam/collaborator — or an over-responsible SUT (SRP) — to fix, never a reason to hide the setup in a fixture.

---

# Decision Tree

1. Not construction (mutation, signing, side-effect)? -> Named helper class/function in test utility, exposed via plain fixture
1a. Would the fixture *itself* perform the test's arrange/act (start a workflow, advance a clock, drive the SUT to a precondition) rather than return a reusable mutation helper — and is it single-use? -> Inline it in the test body; AAA stays in the test (test-quality gate 17)
2. Production builds this type via a `Builder`, one-off / unparameterized? -> Pattern 5 (call the builder in a fixture)
2b. Production builds this type via a `Builder`, but reusable / parameterized by a key / nested as a `SubFactory`? -> Pattern 10 (`Make*` factory delegating to the builder in `_create`)
3. Dynamic type arg (generic over model)? -> Pattern 5 (fixture takes the type param, calls production builder, returns result directly — no inner callable)
4. Same-model variant (differs by one/few params)? -> Pattern 4 (Trait)
5. Wraps a registered `Make*` with a fixed config + a few varying knobs (structural, not just data)? -> Pattern 9 (subclass it)
5b. A family of *distinct model classes* (discriminated union) whose factories share a Param/derivation/default? -> Pattern 11 (abstract base factory, one concrete subclass per model)
6. Need test-specific state models as input? -> Pattern 6 (class for state, fixture for construction)
7. Extracting sub-value from parent? -> Pattern 7 (derived fixture)
7a. Value derived from another object the factory builds (an id, a company off a prospect)? -> Pattern 3a (`SelfAttribute`, `..` for a sibling) — never a fixture chain that hand-derives it
7b. Value only pytest can supply (client from an async fixture, tmp path)? -> Pattern 3b (`LazyFixture`)
8. Zero-arg / fixed value? -> Fixture only if it is an override seam or a value two places must agree on (Pattern 7's earners); a stateful double you assert on inlines like the rest; otherwise inline it (Pattern 8)
9. Thin pass-through, 2-3 sites? -> Pattern 8 (inline)
10. Reusable object with configurable attrs? -> Pattern 1 (`Make*` factory)

**If none of the above fit clearly, STOP and ask the user.** There is always a correct, idiomatic pattern — never invent a novel shape, shoe-horn into a poor-fit pattern, or fall back to a module-level helper "just to make it work." Difficulty mapping to a pattern is a skill gap signal, not a creativity opportunity. State what you're trying to construct, what makes it hard to categorize, and ask which pattern applies.

---

# Further rules (references)

These extend the patterns above; read the matching file when the situation applies.

- **Fixture and test-data design** — one object per fixture (never a tuple), setup-only fixtures kept apart from data fixtures, test data through fixtures not module constants, a test owns any identity it asserts on, and parent-owned children seeded through the parent: [references/fixture-and-data-design.md](references/fixture-and-data-design.md).
- **Reuse and helper existence** — reuse a shared builder/fake before writing a local one, the factory-convergence rule and the narrow `# factory-exempt` shapes, and deleting thin-wrapper shims (single call site, dead params/defaults, projections, re-passed defaults, one-constructor pass-throughs, closure fixtures, and the load-bearing-annotation carve-out): [references/reuse-and-helper-existence.md](references/reuse-and-helper-existence.md).
- **Construction-helper parameters and sourcing values** — helpers/factories declare their own typed params (a `**kwargs` bag only as untouched pass-through; no test-only bundle, post-build injection, or fabricated identity; no alternative-input branching), and trace a needed value to the factory input that first produced it: [references/construction-helper-parameters.md](references/construction-helper-parameters.md).
