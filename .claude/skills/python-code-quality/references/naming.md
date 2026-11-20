# Naming

## Name and body correspond

Applies to every type, function, method, constant and module. Summarize the body in one
sentence, then check both directions: the sentence's verb and nouns appear in the name,
and every word of the name is borne out by the body. Judge by correspondence, never by a
list of banned words.

## Misleading is worse than vague

A vague name under-informs; a name that implies behavior the body doesn't perform
misinforms. Treat it as the more severe finding. The verb and the noun both carry
meaning.

## A constant's name is its contract

Reuse a constant only for the purpose its name states. When another purpose needs the
same value today, give it its own constant: the two will change for different reasons,
and sharing one makes a change to either silently change the other.

## Specific rules

- Name a type after what it produces, owns or does, not a generic role (`Manager`,
  `Processor`, `Helper`).
- `Builder` only for the Builder pattern.
- `Params`, not `Request`, for a group of arguments; `Request` is a request to something
  outside the process.
- Name a constructor after its source (`from_config`), not its caller.
- One verb per concept across collaborating types.
- Name a module after its primary type or concept.
