# Python

## Idiomatic code and the project's own code

Calling Django's `User.objects.get_or_create(...)` and unpacking `(user, created)` is
idiomatic; a rule against returning a created flag doesn't flag the call. Writing a
project function that returns `(user, created)` copies the framework's shape and is what
such a rule judges.
