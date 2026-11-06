# Playwright Testing Guidelines

These guidelines apply when writing or reviewing Playwright browser tests.

## Fullstack System Test Philosophy

Fullstack tests behave exactly like a user: drive the UI, wait for visible outcomes, assert on what the user sees. They are NOT integration tests that happen to use a browser.

### Assert only on user-visible outcomes

The test observes what the user observes — rendered text, element visibility, element count, navigation state. Never poll the database, query internal models, or assert on server-side state.

```python
# WRONG - Database polling is not the user experience
from chat.models import ChatMessage
wait_for_database_condition(lambda: ChatMessage.objects.filter(chat=chat).count() == 2)

# RIGHT - Wait for the UI outcome the user sees
assistant_article = page.get_by_role("article").filter(has_text=ASSISTANT_MESSAGE)
expect(assistant_article).to_be_visible()
```

### Mock setup should be minimal

Register the simplest data that lets the pipeline complete. The mock registry returns whatever you give it without schema validation — consuming agents will parse responses into their expected Pydantic types, so the shape must be correct, but you don't need fully populated domain objects.

```python
# WRONG - Over-specified: builds real domain objects the pipeline won't validate
field_specs = WellSkyCarePlanWorkflowBuilder(ChatService()).field_specs()
phrase_outputs = [PhraseOutput(text=OFFICE_PHRASE, reason="office selection")]
assignment = EvidenceCategoryAssignmentFactory(
    category_specs=field_specs.get_by_refs([OFFICE_REF]),
    ...
)

# RIGHT - Minimal stubs that satisfy the pipeline shape
registry.register_response(
    "evidence_category_assignment_agent",
    [[{"phrase_id": 0, "category_ids": [0], "confidence": 0.9}]],
)
```

### No test-specific infrastructure (v2 tests)

v2 fullstack tests (marked `fullstack_v2`) exercise production code paths with mocked model responses, requiring no gated handlers, custom consumers, or special settings. The older v1 tests (e.g., `test_file_processing_interrupt_resume`) use timing-gated infrastructure via `settings/fullstack_gated.py` when explicit control over cross-process timing is needed.

### No internal state imports for assertions

Importing domain models to create test data (e.g., `ChatFactory` to seed history) is fine. Importing them to assert on server-side state after a UI action is not — that's a unit test concern.

## Anti-Patterns to Avoid

### Never Use `time.sleep()`

**Critical**: Playwright docs explicitly warn that `time.sleep()` leads to outdated state because it prevents async operations from being processed correctly.

```python
# BAD - Never do this
import time
time.sleep(2)

# GOOD - Use Playwright waits
page.wait_for_selector("#element")
expect(page.locator("#element")).to_be_visible()
```

### Minimize `wait_for_timeout()`

Playwright documentation states that `wait_for_timeout()` is "strongly discouraged" for production use as it leads to flaky tests. Prefer Playwright's auto-waiting mechanisms.

```python
# AVOID - Only use when absolutely necessary
page.wait_for_timeout(500)

# PREFERRED - Use specific waits
locator.wait_for(state="visible")
expect(locator).to_be_visible()
page.wait_for_load_state("networkidle")
```

**Acceptable alternatives:**
- `locator.wait_for()` with specific states (`visible`, `attached`, `hidden`)
- `expect()` assertions which auto-wait
- `page.wait_for_selector()` for specific element conditions
- `page.wait_for_load_state()` for navigation

### Prefer Role/TestID Locators Over CSS Selectors

Direct DOM selectors are fragile. Playwright recommends user-visible locators.

```python
# AVOID - Fragile CSS selectors
profile_section = page.locator("#personal_info")
button = page.locator("div.container > button.submit")

# PREFERRED - Accessibility-based locators
profile_section = page.get_by_role("region", name="Personal Information")
button = page.get_by_role("button", name="Submit")
name_input = page.get_by_label("Name")
element = page.get_by_test_id("submit-button")
```

### Avoid `force=True` Unless Documented

Using `force=True` bypasses Playwright's actionability checks which exist to ensure elements are actually interactable. This can hide real UI issues.

```python
# AVOID - Bypasses safety checks
element.click(force=True)
element.fill(value, force=True)

# PREFERRED - Fix the root cause
# If element isn't actionable, investigate why and fix the UI issue
element.click()
element.fill(value)
```

Only use `force=True` as a last resort with documented justification explaining why the element isn't naturally actionable.

### Don't Override Default Timeouts

Never override Playwright's default timeouts in tests that use mocked or stubbed backend responses. The default 5-second auto-retry timeout is the performance contract: if the async pipeline (queue → worker → mock LLM → websocket → UI render) cannot complete within it, that is a production bug to fix — not a testing gap to paper over with a longer timeout.

```python
# NEVER - Custom timeouts when backend responses are mocked
expect(element).to_be_visible(timeout=30000)
RESPONSE_TIMEOUT = 30_000  # Don't define timeout constants

# CORRECT - Default timeout is the performance contract
expect(element).to_be_visible()
```

Custom timeouts are only appropriate when the test exercises genuinely slow real-world operations (large dataset pagination against a live database, real file uploads to cloud storage). Mocked/stubbed responses eliminate real latency — if the pipeline still exceeds the default timeout, the system is broken for users too.

```python
# AVOID - Global timeout changes
expect.set_options(timeout=30000)
page.set_default_timeout(60000)
```
