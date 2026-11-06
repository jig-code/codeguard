# Pytest Guidelines

These guidelines apply when writing or reviewing pytest test code.

## Test Style

### Group tests in a class; mark `django_db` on the class

Two requirements, both mandatory:

1. **Every test lives in a `Test<SUT>` class** named after the system under test (`TestBuildResponse` for `BuildResponse`, `TestResolveFieldOptionsSelection` for that node). No module-level `def test_*` functions.
2. **Apply `@pytest.mark.django_db` as a decorator on that class**, never as a module-level `pytestmark = pytest.mark.django_db`. The decorator keeps the mark attached to the tests it governs, so a reader looking at the class sees it needs the database; a module-level `pytestmark` hides that at the top of the file, detached from the class, and silently applies to anything later added to the module.

```python
# AVOID - module-level function and/or module-level pytestmark
pytestmark = pytest.mark.django_db

def test_renders_option_section():
    ...

# PREFERRED - class named after the SUT, mark on the class
@pytest.mark.django_db
class TestRenderOptionsAnswer:
    def test_renders_option_section(self):
        ...
```

Other class-wide marks follow the same rule — decorate the class (`@pytest.mark.django_db(transaction=True)`, etc.), don't hoist them to a module `pytestmark`.

Fixture, factory, and test-object construction — module-level constants, module-level helper functions, fixture-returning-callables, and keeping one construction path per type across a file — is governed by the `pytest-factoryboy` skill. Load it before writing fixtures or factories.

### Don't Mix Django TestCase with pytest Fixtures

Mixing Django's `TestCase`/`TransactionTestCase` classes with pytest fixtures creates confusion about which cleanup mechanism is in effect and can cause unexpected database state.

```python
# AVOID - Mixed patterns
class WebSocketTests(TransactionTestCase):
    def setUp(self):  # Django pattern
        ...

    @pytest.mark.asyncio  # pytest pattern
    async def test_connection(self):
        ...

# PREFERRED - Standardize on pytest style
@pytest.mark.django_db(transaction=True)
class TestWebSocket:
    @pytest.fixture(autouse=True)
    def setup(self):
        ...

    @pytest.mark.asyncio
    async def test_connection(self):
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

### Standardize asyncio_mode Configuration

Use `strict` mode and explicitly mark async tests to avoid behavior differences between test configurations.

```ini
# pytest.ini
[pytest]
asyncio_mode = strict
```

```python
# Explicitly mark async tests
@pytest.mark.asyncio
async def test_async_operation():
    ...
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
def test_error_handling(self, settings):
    settings.RAISE_ON_ERROR = False
    # test code...

# PREFERRED - Declarative decorator
from django.test import override_settings

@override_settings(RAISE_ON_ERROR=False)
def test_error_handling(self):
    # test code...
```

This pattern applies to Django settings (`@override_settings`), environment variables (`@mock.patch.dict(os.environ, ...)`), and other test context managers that have decorator equivalents.
