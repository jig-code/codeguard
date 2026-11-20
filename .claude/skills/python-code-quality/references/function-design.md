# Function design

## Getting under Ruff's limits

The thresholds are in `pyproject.toml`, or Ruff's defaults when it sets none. When a
function nears one, work down this list:

1. Replace branching that maps inputs to outputs with data: a mapping keyed by an enum,
   or a property on the enum member.
2. Split responsibilities into functions named after each, on the type that owns each
   concept. This holds at any length: passing the limits never excuses two
   responsibilities.
3. Group parameters into a type only when you would store, pass on or test the group as
   a unit; a parameter object built at one call and unpacked at once is indirection.
4. If the complexity is inherent, add a targeted `# noqa` rather than splitting into
   pieces that model nothing.

## Inputs

- **Configuration belongs in the constructor.** Collaborators every call passes (a root,
  a store, a deadline) are fields; methods take only what varies per call.
- **Pass a collaborator what it uses,** not a wide object it reads a few fields of.
- **Don't pass a value beside its source.** When a variable is an argument and also
  inside the expression computing a sibling argument, the callee should take the source
  and derive the value itself.

## Outputs and helpers

- A `tuple` of unrelated answers is two responsibilities: return a named type, or let
  callers ask each question. To save a second fetch, cache the fetch.
- A helper that only packs its arguments into a `dict` or `tuple` literal is
  indirection: inline the literal, or make it a type if the shape recurs and means
  something.
- A single-call wrapper whose body is only a comprehension over an already-named
  per-item function is `map` with a name: inline it. Keep it when several callers share
  it or it filters, sorts, deduplicates or reports errors.

## Anti-patterns

- A helper that is an arbitrary chunk of the original with no identity of its own.
- `**kwargs` used to cut the argument count without cutting complexity.
- An options object that is a bag of the same parameters, there only to satisfy the
  argument limit.
- A thin wrapper forwarding all its parameters to an underlying API.
