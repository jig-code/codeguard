# Defaults on the type

A caller never passes a field a value that the owning type already declares as that field's default.

## Why

A default declared on the type and repeated by its callers is in two places, so a change to the default leaves some callers on the old value.
