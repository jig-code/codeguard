# Pytest Guidelines

These guidelines apply when writing or reviewing pytest test code.

## Test Style

### Group tests in a class; put class-wide marks on the class

Two requirements, both mandatory:

1. **Every test lives in a `Test<SUT>` class** named after the system under test (`TestCachedJudge` for `CachedJudge`, `TestBindings` for `Bindings`). No module-level `def test_*` functions.
2. **Apply a class-wide mark (`@pytest.mark.usefixtures("fake_cli_config")`, `@pytest.mark.llm`) as a decorator on that class**, never as a module-level `pytestmark = pytest.mark.usefixtures("fake_cli_config")`. The decorator keeps the mark attached to the tests it governs, so a reader looking at the class sees what it needs; a module-level `pytestmark` hides that at the top of the file, detached from the class, and silently applies to anything later added to the module.

```python
# AVOID - module-level function and/or module-level pytestmark
pytestmark = pytest.mark.usefixtures("fake_cli_config")

def test_stores_the_judgement():
    ...

# PREFERRED - class named after the SUT, mark on the class
@pytest.mark.usefixtures("fake_cli_config")
class TestCachedJudge:
    def test_stores_the_judgement(self):
        ...
```

Other class-wide marks follow the same rule — decorate the class (`@pytest.mark.llm`, etc.), don't hoist them to a module `pytestmark`.

Fixture, factory, and test-object construction — module-level constants, module-level helper functions, fixture-returning-callables, and keeping one construction path per type across a file — is governed by the `pytest-factoryboy` skill. Load it before writing fixtures or factories.

### Don't Mix unittest.TestCase with pytest Fixtures

Mixing `unittest.TestCase` classes with pytest fixtures creates confusion about which setup and cleanup mechanism is in effect and can leave unexpected state behind.

```python
# AVOID - Mixed patterns
class JudgeTests(unittest.TestCase):
    def setUp(self):  # unittest pattern
        ...

    def test_judges(self, tmp_path):  # pytest pattern (the fixture is never injected)
        ...

# PREFERRED - Standardize on pytest style
class TestJudge:
    @pytest.fixture(autouse=True)
    def setup(self):
        ...

    def test_judges(self, tmp_path):
        ...
```

## Fixture Best Practices

### Proper Fixture Scoping

Match fixture scope to cleanup requirements. Review `autouse=True` fixtures to ensure they run at the appropriate scope.

```python
# Ensure scope matches actual cleanup needs
@pytest.fixture(autouse=True, scope="function")  # Per-test cleanup
def reset_state():
    yield
    # cleanup here runs after each test

@pytest.fixture(scope="session")  # Only for truly immutable resources
def shared_resource():
    ...
```

### Remove Placeholder Fixtures

Empty or placeholder fixtures add confusion. Remove unused fixtures or document why they're kept.

```python
# AVOID - Empty placeholder
@pytest.fixture(autouse=True)
def reset_cached_agents():
    """Reset cached agents for test isolation."""
    pass  # No longer needed

# PREFERRED - Remove entirely or implement properly
```

### Session-Scoped Fixtures Must Be Immutable

Session-scoped resources should be truly immutable. Tests that modify shared state can affect subsequent tests.

## Async Testing

### Use Async Coordination Primitives Over `asyncio.sleep()`

While less problematic than `time.sleep()`, using `asyncio.sleep()` for coordination is still timing-based and can be flaky.

```python
# AVOID - Timing-based coordination
await asyncio.sleep(0.1)

# PREFERRED - Use proper async primitives
await event.wait()
async with condition:
    await condition.wait_for(predicate)
```

## Test Isolation

### Avoid Class-Level Mutable State

Class attributes shared across test methods can leave state in a bad condition for subsequent methods.

```python
# AVOID - Shared mutable state
class TestSuite:
    worker_process = None  # Class-level, shared

# PREFERRED - Test-level isolation or robust health checking
class TestSuite:
    @pytest.fixture(autouse=True)
    def worker(self):
        # Per-test worker or health check
        ...
```

## Prefer Decorators Over Fixture Mutation

When temporarily changing test behavior (settings, feature flags, environment), prefer declarative decorators over imperatively modifying fixtures. Decorators make the test's preconditions visible at a glance and ensure proper cleanup.

```python
# AVOID - Imperatively mutating fixtures
def test_reads_the_config(self, monkeypatch, tmp_path):
    monkeypatch.setenv("CODEGUARD_CONFIG", str(tmp_path / "config.yaml"))
    # test code...

# PREFERRED - Declarative decorator
@mock.patch.dict(os.environ, {"CODEGUARD_CONFIG": "config.yaml"})
def test_reads_the_config(self):
    # test code...
```

This pattern applies to environment variables (`@mock.patch.dict(os.environ, ...)`), settings objects (`@mock.patch.object(...)`), and other test context managers that have decorator equivalents.
