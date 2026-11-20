# Single responsibility

A type or module has one reason to change. Two unrelated reasons is already a violation.

- **Group by reason to change, never count.** Name the change that would force each
  method to change and cluster by it. One cluster: keep. Two or more unrelated clusters:
  split, naming each extracted type after its concern.
- **Size is not the test.** A long type serving one concept is fine; a two-method type
  serving two is not.
- **A frozen value type is not a god object.** A god object holds collaborators or
  mutable state and answers unrelated questions about it. A frozen type with no
  collaborators, whose methods read only its own fields, changes for one reason: its
  shape. Splitting it leaves a bag of fields and services that reach into it.
- **Oversized entry methods.** A long entry method, or the same `isinstance` branching
  repeated across siblings, hides an orchestrator or per-shape handlers. Extract named
  steps.
- **A multi-responsibility function is a type in disguise.** Signs: a name joined by
  "and", a long list of unrelated collaborators, or sibling functions taking the same
  arguments. Those arguments are a type's fields; make the type and check it again.
