# Workers

Async ingestion workers that poll the PostgreSQL-backed job queue. Each worker process:

1. Claims the next `jobs` row via `FOR UPDATE SKIP LOCKED`
2. Dispatches to modality-specific pipelines (text, pdf, image, web)
3. Updates job status + emits job events, retries on transient failures

The scaffolding below implements the dispatcher loop so docker compose stacks can start without yet performing ingestion.

