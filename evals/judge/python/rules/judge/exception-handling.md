---
name: exception-handling
description: Never discard an exception.
---

# Exception handling

Never discard an exception. The violation is a handler, such as an `except` block,
that does none of these with the exception it catches: re-raise it, return an error to
its caller, or log it with its traceback.

Ask of each handler: does it re-raise the exception, return an error, or log the
exception with its traceback? If none, the handler is the violation. The code its `try`
block guards is not.
