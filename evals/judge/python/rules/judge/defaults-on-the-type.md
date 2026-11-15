# Defaults on the type

A field's default is declared once, on the type that owns the field, and no caller passes
that same value again.

## Why

A caller that repeats the default keeps the old value when the type's default changes,
so the two copies drift apart.
