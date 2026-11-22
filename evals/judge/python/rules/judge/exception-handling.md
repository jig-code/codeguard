# Exception handling

An exception handler never discards the exception it catches.

## Why

A discarded exception hides the failure: the program carries on as if the call
succeeded, and nobody can tell that it failed or why.
