# Package public interface

No consumer beyond a package's perimeter, reaching past the facade that hands a symbol out, pulls that symbol from its home module.

## Why

Going through the facade keeps consumers independent of the package's internal module
layout, so those modules can change without changing their consumers.
