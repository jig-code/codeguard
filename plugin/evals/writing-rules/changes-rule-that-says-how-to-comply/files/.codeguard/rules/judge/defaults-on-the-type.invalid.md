# Defaults on the type

A caller never passes a field's default value again: leave the argument out and let the default the type declares apply.

## Why

A default repeated at each call can drift from the one the type declares, and changing
the default then means finding every caller.

## How to fix

Delete the argument from the call, so the type's default applies.
