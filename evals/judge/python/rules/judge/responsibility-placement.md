# Responsibility placement

Code outside a class never holds logic that reads only that class's attributes.

## Why

Logic kept away from the data it reads is missed when that data changes.
