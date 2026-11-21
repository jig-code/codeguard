# Defaults on the type

A caller never passes a value that equals the default the owning type declares for that field.

## Why

A default declared on the type and repeated by its callers is in two places, so a change to the default leaves some callers on the old value.
