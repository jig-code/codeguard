# Module structure, ownership, placement and interfaces

## A well-named module can still be a bucket

A module is a bucket when it holds a second public class, or loose functions, that serve
another concept, however good its name. List the public names in each touched module.

A second public class stays only when it is `_`-private to the primary type, or part of
one family a reader would look for under the module's name (a union and its variants, a
type and the errors it raises). Being built only by the primary type doesn't make it
part of that type's module; it argues for its own module.

The mirror defect is one concept scattered across one-symbol files. A type's own
parameter and result shapes, used by nothing else, belong in its module, and a union's
variants share one module with its alias.

## Every loose function has an owner

Ask which type would be less coherent if the function became its method:

- builds one type → a `classmethod` on that type;
- reads one instance's own data → a method or property on that type;
- coordinates several types → a type named after the operation;
- adapts data for another component → an owner named after that target.

A function stays module-level only when no type owns it, and is then usually private to
the module that calls it. In tests, `pytest-factoryboy` decides which module-level
functions are allowed.

## Own-field behavior lives on its type

A `@staticmethod`, a method that ignores `self`, or a free function whose body reads only
one parameter's own fields belongs on that parameter's type: a derived mapping, a
predicate, a sort key, a formatted line. It stays there when a change adds or moves a
caller; moving it next to its newest caller strands every other caller. A second site
that re-derives what a type already derives is duplication: call the owner, and extend
it if a variant is missing.

## Outside formats get their own module

Running an external tool and understanding its output format change for different
reasons. The parser (the message models and the classmethod that builds the result)
lives in its own module beside the code that runs the tool, never inside it.

## Validators and wiring

A model validator stays on the model when it checks only the model's own fields.
Validation that needs the file system, a repository, configuration or other models
belongs to the code that has them. Wiring that builds collaborators belongs with the
code that consumes them.

## Place a type with its producer

A type lives in the package whose code constructs it (instantiates, returns, raises or
subclasses it); the number of importers never moves it. When code in two layers
constructs it, it lives in the lower one.

- Group passive shapes by concept in the producer's package, never by kind of construct.
- A type many layers need sits in a low layer that imports nothing above it.
- If placing a type with its producer creates a cycle or breaks a layer, fix the
  boundary or invert the dependency with a consumer-owned `Protocol`; never move the
  type somewhere neutral to hide the cycle.
- Behavior that queries or walks other types is a named service, not a method on a data
  shape.

## Interfaces must earn their existence

A `Protocol` or ABC is justified when it inverts a dependency or has two or more
implementers today. Either alone is enough.

- A lower layer's narrow `Protocol` for what it needs from a higher layer is correct,
  even with one implementer.
- Otherwise a single-implementer interface is a hand-synced copy: delete it. Decisive
  test: would typing consumers against the concrete type create a cycle or a layer
  violation?
- A planned implementer doesn't count; add the interface with the second implementer.
- Design it from the consumer's needs, not as the list of attributes one consumer happens
  to read off a wide object.
- The interface lives with the consumer that depends on it.
