# Single responsibility

A type or module has one responsibility: one reason to change. Two unrelated reasons is
already a violation, however small the type. This and the one-responsibility rule for
functions in [function-design.md](function-design.md) are the same principle at two
scales.

## Group by reason to change, never count

For each method, name the change that would force it to change. Cluster the methods by
that reason. One cluster: keep. Two or more unrelated clusters: split, and name each
extracted type after its concern. The original delegates, or its callers take the new
types directly.

Suppose `ClaudeJudge` gained a method that prints its telemetry as a table for the CLI.
Running the `claude` CLI changes when the CLI's flags change; the table changes when the
CLI's output design does. Two reasons, so the table belongs to the CLI's output code,
which reads `ClaudeResult.telemetry`.

## Size is not the test

A long type whose methods all serve one concept is fine; don't split it for size. A
two-method type whose methods change for unrelated reasons must be split; its size
doesn't save it.

## A frozen value type is not a god object

A god object has two halves: held collaborators or mutable state, and methods answering
questions from unrelated domains about that state. A frozen value type with no
collaborators fails the first half. Methods that read only its own fields are intrinsic
behavior and change for one reason, the value's shape, even when they fall into several
topics.

`Diagnostic` has `id`, `blocks`, `as_warning`, `as_json` and a validator: identity,
blocking, conversion and serialization. Splitting those into "focused services" would
leave a bag of fields and services that reach into it. Keep it whole. Check the first
half before flagging a many-method type: does it hold collaborators or mutable state?

## Oversized entry methods

A long `run()` or `review()`, or the same `isinstance` branching repeated across sibling
methods, is an orchestrator or per-shape handlers waiting to be extracted. Extract named
steps so the entry method reads as a short sequence. `Rules.review` reads as steps
because pattern checks, classification and judge checks each have their own owner.

## A multi-responsibility function is a type in disguise

The signs: a name joined by "and" (`load_and_validate`), a long list of unrelated
collaborators, or several sibling functions that all take the same arguments. When three
functions all take `(working_tree, bindings, classification)`, those arguments are a
type's fields and the functions are its methods. Make the type, then check it again for
more than one reason to change.
