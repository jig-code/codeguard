# Exception handling

A handler that catches an exception re-raises it, returns an error to its caller, or logs it with its traceback.

## Why

A discarded exception hides a failure, so the program carries on in a state its author never intended.
