# API Layer (Presentation)

Responsibilities:

- Receive HTTP requests
- Validate request payloads (Pydantic schemas)
- Call application services / use cases
- Return response envelopes

Must **not**:

- Query the database
- Call the LLM directly
- Contain business rules
