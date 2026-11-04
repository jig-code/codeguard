# Python

## Idiomatic code and the project's own code

Calling Django's `User.objects.get_or_create(...)` and unpacking `(user, created)` is
idiomatic; a rule against returning a created flag doesn't flag the call. Writing a
project function that returns `(user, created)` copies the framework's shape and is what
such a rule judges.

## A pattern rule

A pattern rule and its test file. Each test case covers one branch, named by its
comment.

A convention: concrete models inherit `BaseModel`; abstract mixins are skipped.

### `.codeguard/rules/pattern/models-inherit-base-model.yml`

```yaml
id: models-inherit-base-model
language: python
severity: error
message: Concrete models inherit BaseModel.
note: |
  BaseModel adds the shared primary key and timestamps. Change the superclass to
  BaseModel. Abstract mixins (`class Meta: abstract = True`) are skipped.
metadata:
  why: A model on Model alone lacks the primary key and timestamps other code expects.
rule:
  kind: class_definition
  has:
    field: superclasses
    has:
      pattern: Model
  not:
    has:
      field: body
      has:
        kind: class_definition
        all:
          - has: { field: name, regex: ^Meta$ }
          - has: { field: body, stopBy: end, pattern: abstract = True }
```

### `.codeguard/rule-tests/models-inherit-base-model-test.yml`

```yaml
id: models-inherit-base-model
valid:
  # Concrete model on BaseModel
  - |
    class ExampleModel(BaseModel):
        name = CharField()

  # Abstract mixin is skipped
  - |
    class ExampleMixin(Model):
        class Meta:
            abstract = True

invalid:
  # Concrete model on Model
  - |
    class ExampleModel(Model):
        name = CharField()

  # Meta without abstract is still concrete
  - |
    class ExampleModel(Model):
        class Meta:
            ordering = ["name"]
```
