---
name: package-public-interface
description: Code outside a package imports from the package root.
---

# Package public interface

Code outside a package imports what the package exports from the package root, not from the module that defines it.

## Why

Using the package root keeps callers independent of the package's internal module
layout, so those modules can change without changing its callers.
