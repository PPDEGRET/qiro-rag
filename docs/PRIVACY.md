# Privacy model

Qiro RAG should be enterprise-friendly by default.

## Default

- No cloud model calls.
- No cloud embeddings.
- No telemetry.
- No raw document upload.
- Local indexes only.

## Explicit opt-in

Cloud or hosted behavior must require an explicit option and clear docs.

Examples:

```bash
qiro-rag assess finding.json --pack ./evidence-pack --out step3.json --profile hosted-flash
qiro-rag assess finding.json --pack ./evidence-pack --out step3.json --profile mistral-private-gateway
qiro-rag assess finding.json --pack ./evidence-pack --out step3.json --profile ollama-private-small
qiro-rag pull ./exported-company-docs --target ./staged-docs
```

`--judge openai` uses `OPENAI_API_KEY` and optional `OPENAI_BASE_URL` / `OPENAI_MODEL`.
`--judge ollama` uses a local Ollama server by default.
Hosted storage connectors are not part of v0.1; sync/export files locally first.

## Generated data

Generated indexes, parsed chunks, and assessment traces may contain confidential company data. Keep them out of git:

```text
.qiro/
index/
runs/
*.sqlite
```

## Public fixtures

Public fixtures must be synthetic and fictional unless provenance/licensing is documented.
