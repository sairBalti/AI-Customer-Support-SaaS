# Application Layer

Contains **all business logic**.

- Orchestrates domain entities and ports
- Owns transactions and validation rules
- Calls repositories and AI services via interfaces
- Exposes use cases invoked by the API layer

Must **not** import FastAPI routers or infrastructure SDKs directly.
