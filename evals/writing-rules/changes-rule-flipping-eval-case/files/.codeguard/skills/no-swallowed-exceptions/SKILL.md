---
name: no-swallowed-exceptions
description: Flags except blocks that swallow errors.
---

# No swallowed exceptions

Flag an `except` clause that handles an exception in a way one of the forms below names.

Forms:

- `pass` as the whole body.
- Logging the error without re-raising it.
- Returning `None` or a default value.
- Catching `Exception` or a bare `except`.
