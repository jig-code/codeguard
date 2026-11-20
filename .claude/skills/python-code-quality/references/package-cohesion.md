# Package cohesion

Modules that collaborate as one flow or feature live in one package. The test: could a
reader who knows what a concept does guess which package it lives in?

Flag:

- **A flow split across siblings** that reach into each other sideways. Put the stages
  under one package, or make a deliberate split an import-linter layer.
- **A thin wrapper package** that only re-exports another. Fold it into the package it
  wraps.
- **A misplaced module** whose concept belongs to a neighbouring package. Move it to the
  owner; rename a vaguely named package after what it does.
- **A bucket package** of unrelated single-purpose modules. Each module needs an owning
  concept the package name predicts.

Place a new package in the import-linter layer its imports and importers imply, not in a
new top layer for convenience. Same-layer packages stay independent of each other.
