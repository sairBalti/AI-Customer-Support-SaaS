# Domain Layer

Innermost Clean Architecture layer. Framework-agnostic.

Contains:

- **entities/** — business entities aligned with the ERD
- **enums/** — domain enumerations
- **exceptions/** — domain errors
- **interfaces/** — repository and external-service ports (Dependency Inversion)
- **value_objects/** — immutable domain concepts

No FastAPI, SQLAlchemy, or SDK imports allowed here.
