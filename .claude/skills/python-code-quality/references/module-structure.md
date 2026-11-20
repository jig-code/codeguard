# Module structure, type placement and interfaces

## A well-named module can still be a bucket

`no-bucket-module-names` catches a bucket by its name. A module named after a real
concept is still a bucket when it holds a second public class, or loose functions, that
serve a different concept. List the public classes and functions of each module a change
touches; more than one concept is the defect, however good the filename.

Composition doesn't make ownership. A second public class stays in the module only when
it is `_`-private to the primary type, or part of one family a reader would look for
under the module's name (a discriminated union and its variants, an enum and the error
that carries it). "The primary type is its only caller" argues for moving it to its own
module, where the one import is the one clean coupling.

`review/judge.py` is one family: the request the judge gets (`JudgeRequest`), what it
returns (`Verdict`, `Violation`, `Confidence`, `Judgement`), how it fails (`JudgeError`
and its subclasses) and the interface (`Judge`). Adding a provider's output parser there
would add a second concept.

## The inverse bucket: one concept scattered

The mirror defect is one concept split across one-symbol files. A primary type's own
parameter and result shapes, used by nothing else, belong in its module. A `foo_params.py`
whose only importer is `foo.py` is fragmentation. A discriminated union's variants share
one module with the alias.

A shape that several peers produce or consume equally is its own concept: give it its own
module or place it with its producer.

## Every loose function has an owner

For each module-level function, ask which type would be less coherent if it became a
method. If the answer names a type, move it there:

- **Builds one type** → a `classmethod` on that type: `JudgeRequest.of_change`,
  `Binding.from_config`, `ClaudeResult.from_stream`.
- **Reads one instance's own data** → a method or property on its type:
  `Diagnostic.blocks`, `LineRange.described`, `Violation.severity`.
- **Coordinates several types** → a type named after the operation: `Reviewer` runs the
  steps, `JudgePlan` plans the calls.
- **Formats or adapts for another component** → an owner named after that target, not a
  free function in whatever module needed it.

A module-level function stays only when no type owns it, and then it is usually
`_`-private to the one module that calls it (`_relative` in `claude_result.py`). In test
files, which module-level functions are allowed is `pytest-factoryboy`'s call.

## Behavior that reads only a type's own fields lives on the type

A `@staticmethod`, a method that ignores `self`, or a free function whose body reads only
one parameter's own fields is that parameter's behavior parked on whatever host needed it
first. The test: does the body read only that parameter's fields? Then it belongs on the
parameter's type, wherever the host lives.

`JudgeProvider` owns `default_model`, `runs_a_cli` and `families`: each reads only the
provider. A change that moves `families` into `rules/judges.py` as

```python
def _families_of(provider: JudgeProvider) -> frozenset[ModelFamily]:
    return _FAMILIES[provider]
```

because `Judges` is its new caller has moved a derived mapping off the type that owns its
key. Every other caller now has to find it in `judges.py`, or derive it again. Keep it on
`JudgeProvider`, and keep it there when the caller moves.

The test applies to a mapping, a predicate, a sort key or a formatted line alike. If a
type already renders or derives something (`Diagnostic.as_json`, `LineRange.__str__`), a
second site that re-derives it inline is duplication: call the owner, and extend it if it
lacks the variant you need.

## Code that understands a foreign format lives beside its caller

A judge runs a CLI and turns its output into a `Judgement`. Understanding the CLI's output
format is a second concept with its own reason to change (the CLI's release notes). It
lives in its own module beside the judge: `claude_provider/claude_result.py` parses the
`claude` CLI's stream into `ClaudeResult`, and `claude_judge.py` calls
`ClaudeResult.from_stream`. A new provider follows the same shape: `<provider>_judge.py`
runs it, and a result module beside it parses what it prints. Putting the parser's
message models and stream walking inside the judge module makes the judge change for two
reasons.

## Validators and wiring

A model validator stays on the model when it checks the model's own fields
(`LineRange.validate_end_is_not_before_start`,
`Diagnostic._error_type_only_on_judge_errors`). Validation that needs a repository, a
ruleset, the file system or other models belongs to the code that has them (a loader, a
`Validation`). Wiring that builds collaborators belongs with the code that consumes them.

## Place a type with its producer

A type lives in the package whose code constructs it: instantiates it, returns it, raises
it or subclasses it. The number of importers never moves it; consumers import it from
the producer's package root. When two layers construct a type, it lives in the lower
one: `Verdict.diagnostics_for` in `review/` and the pattern checks in `pattern_rules/`
both build `Diagnostic`, so it lives in `review/` and `pattern_rules` imports it from
there.

- Group passive shapes by concept in their producer's package, never by the kind of
  construct they are. A `contracts` module is already banned by `no-bucket-module-names`.
- A type that many layers need sits in a low layer that imports nothing above it:
  `LineRange` in `line_range`, `Severity` in `config`. That placement, not a neutral
  bucket, is what keeps it a leaf.
- If placing a type with its producer would create a cycle or break a layer, the
  boundary is wrong: fix it, or invert the dependency with a consumer-owned `Protocol`.
  Never move the type somewhere neutral to hide the cycle.
- Behavior that reads only the type's fields is on the type (above). Behavior that
  queries or walks other types is a service with its own name.

## Interfaces must earn their existence

A `Protocol` or ABC is justified when it inverts a real dependency or has two or more
implementers that exist today. Either alone is enough.

- **Inversion, even with one implementer.** A lower layer defines a narrow `Protocol` for
  what it needs, so it never imports the higher layer that implements it. `Judge` in
  `review/` is the case: `review` sits below the provider packages, and `ClaudeJudge`,
  `CodexJudge`, `ApiJudge` and `CachedJudge` implement it. `Step` and `Check` in `review/`
  are the same shape.
- **Neither.** A single-implementer interface in the same layer as its implementation, or
  in a layer that could import the implementation, is a hand-synced copy of one type's
  shape. Delete it and type consumers against the concrete class. The decisive test:
  would typing the consumers against the concrete type create a cycle or a layer
  violation? No → delete the interface.
- **A planned implementer doesn't count.** Add the interface in the change that adds the
  second implementer, when two real cases show its shape.
- **Design it from the consumer's needs.** A `Protocol` whose members are just the
  attributes a consumer happens to read off one wide object couples the consumer to that
  object by coincidence. Decide what the consumer needs and pass exactly that.
- The interface lives with the consumer that depends on it.

A `dict[str, Callable]` handed in for dispatch is `typed-dispatch-registries`.
