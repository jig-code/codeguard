# Exception handling

A handler never discards the exception it catches: it re-raises it, returns an error to
its caller, or logs it with its traceback.

## Why

A discarded exception hides the failure, so the program carries on in a bad state and
nobody can find what went wrong.
