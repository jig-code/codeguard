# Responsibility placement

Logic that reads only one class's attributes is a method of that class, never code outside the class that recomputes from those attributes.

## Why

Logic kept away from the data it reads is missed when that data changes.
