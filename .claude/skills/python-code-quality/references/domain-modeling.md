# Domain modeling, boundary data and mapping

## Domain modeling

- **Don't wrap a bare identity.** A type that only wraps an existing key, with no
  behavior or invariant, adds nothing. Use the key.
- **Don't model a step.** A constructor that needs grouped arguments takes a `…Params`
  beside it, or is a `classmethod` taking its sources.
- **Don't keep a copy of a value another object owns**, including a key stored on an
  object that is already registered or looked up by that key. Read it from the owner.
- **Promote a repeatedly queried collection to a named type** when callers query a bare
  `dict`, `list` or `set` with the same idiom at three or more sites, or a loop builds it
  with a silent last-writer-wins policy. The type owns the lookups and the policy.

## Parse boundary data once

Outside data (a subprocess's output, a YAML or JSON file, a model's reply, an environment
variable, a hook payload, a git object) is parsed once, where it enters, into a named
type. Code past that point never touches the raw shape.

Signals of raw data interpreted in place:

- index arithmetic or slicing on an untyped sequence or mapping;
- the same raw layout read in more than one function;
- `isinstance` deciding what a raw value means, rather than dispatching a typed union;
- a parameter typed as the raw shape passed several calls deep.

## Model-to-model mapping

Map one model to another field by field, so a field renamed, added or removed on either
side fails the type check. When one source type maps into several targets, one mapper
owns the mapping and each target calls it. Two models with the same fields at different
boundaries (a file format and the runtime type built from it) stay separate and are
mapped where they meet.
