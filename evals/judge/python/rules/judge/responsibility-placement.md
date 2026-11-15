# Responsibility placement

Logic that reads only one class's attributes is a method on that class, never recomputed
by code outside it.

## Why

Logic kept away from its data is missed when that data changes, so the copies outside the
class go stale.
