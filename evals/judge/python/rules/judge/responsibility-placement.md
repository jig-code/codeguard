---
name: responsibility-placement
description: Put logic on the type whose data it reads.
---

# Responsibility placement

Put logic on the type whose data it reads. Code that reads only one class's attributes belongs on that class as a method. Code outside a class must call the class's methods instead of recomputing from its attributes.
