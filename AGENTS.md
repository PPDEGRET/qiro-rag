# Qiro RAG agent instructions

These instructions apply under `opensourceqirorag/`.

## Scope

This repo is for Qiro Step 3: local-first evidence ingestion, retrieval, substantiation assessment, and reviewer feedback memory.

Do not move Step 1/1.5/2 analyzer behavior into this repo. Consume analyzer outputs through explicit JSON contracts.

## Language

Use cautious review language:

- potential issue
- substantiation gap
- evidence may support
- evidence appears insufficient
- review recommended

Avoid:

- illegal verdict
- guaranteed compliant
- autonomous legal certainty
- replaces legal counsel

Every public-facing doc must include or preserve a not-legal-advice disclaimer.

## Architecture rules

- Local-first is the default. Cloud models, cloud embeddings, and telemetry must be opt-in.
- RAG citations must be quote-backed. If a quote cannot be verified in parsed source text, do not cite it as evidence.
- Playbooks are lenses, not hard legal rules. They help ask better evidence questions and must allow edge cases.
- Human feedback can propose updates, but no silent self-modifying compliance behavior.
- Prefer boring storage first: files, CSV, SQLite. Add databases/connectors only when the local pack works.

## Verification

Suggested commands:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build
```
