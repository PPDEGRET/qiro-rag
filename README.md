# Qiro RAG

[![CI](https://github.com/PPDEGRET/qiro-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/PPDEGRET/qiro-rag/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Local-first evidence retrieval and substantiation review for environmental marketing claims.

Qiro RAG owns **Step 3** in the Qiro workflow:

```text
Step 1   extract environmental claim signals
Step 1.5 group/protect claims
Step 2   assess potential regulatory issues
Step 3   check company evidence for support, limits, contradictions, and gaps
Step 4   produce a human-review report
```

It is **not** generic document chat and it is **not** a legal verdict engine. It turns a Step 2 issue into evidence questions, retrieves relevant company evidence, verifies source quotes, and emits a structured Step 3 review artifact.

> Qiro RAG is a risk-review aid. It does not provide legal advice, determine illegality, guarantee compliance, or replace qualified counsel/compliance review.

## What this demonstrates

- Local-first RAG architecture with no cloud calls by default.
- Evidence-pack ingestion for `md`, `txt`, `pdf`, `docx`, `xlsx`, `csv`, plus optional local OCR.
- SQLite-backed chunks, tables, metadata, hashes, and persisted embeddings.
- Keyword, semantic, and hybrid retrieval modes.
- Quote-backed citation verification to reduce hallucinated support.
- Heuristic offline judging plus opt-in Ollama/OpenAI-compatible LLM judges.
- Optional LangGraph workflow with typed nodes and local trace output.
- Human-review memory through `review_decisions.csv` and proposed playbook patches.

## Quick start

Install [`uv`](https://docs.astral.sh/uv/) and run from the repository root:

```bash
git clone https://github.com/PPDEGRET/qiro-rag.git
cd qiro-rag
uv sync --dev
```

Run the synthetic evidence-pack demo:

```bash
uv run qiro-rag ingest examples/synthetic_eval/docs --pack ./.tmp/qiro-synth-pack --reset
uv run qiro-rag assess examples/synthetic_eval/findings/recyclable.json \
  --pack ./.tmp/qiro-synth-pack \
  --out ./.tmp/recyclable-step3.json
```

Expected status:

```json
{
  "claimId": "C-RECYCLABLE",
  "status": "partially_supported",
  "humanReviewRecommended": true
}
```

The full output includes verified source quotes and missing-evidence prompts for human review.

## Optional LangGraph workflow

The default pipeline is direct typed Python. If you want node-level workflow tracing, install the optional workflow extra:

```bash
uv run --extra workflow qiro-rag assess examples/synthetic_eval/findings/recyclable.json \
  --pack ./.tmp/qiro-synth-pack \
  --out ./.tmp/recyclable-step3.json \
  --workflow langgraph \
  --trace-out ./.tmp/langgraph-trace.json
```

The LangGraph path emits the same public Step 3 JSON schema as the direct path. Framework objects stay out of output artifacts.

## Common commands

```bash
uv run qiro-rag init-pack ./evidence-pack
uv run qiro-rag pull ./company-docs --target ./staged-docs
uv run qiro-rag ingest ./staged-docs --pack ./evidence-pack --reset
uv run qiro-rag embed --pack ./evidence-pack
uv run qiro-rag retrieve "carbon neutral delivery offset basis" --pack ./evidence-pack
uv run qiro-rag assess examples/step2/finding.json --pack ./evidence-pack --out step3_evidence.json
uv run qiro-rag models
uv run qiro-rag onboard
uv run qiro-rag learn --pack ./evidence-pack --propose playbook.patch.yaml
```

## Model and privacy posture

Default behavior is local:

- no cloud model calls;
- no cloud embeddings;
- no telemetry;
- no raw document upload.

Opt-in judge profiles are available for local Ollama or OpenAI-compatible gateways:

```bash
uv run qiro-rag assess examples/step2/finding.json \
  --pack ./evidence-pack \
  --out step3_evidence.json \
  --profile ollama-private-small
```

Only retrieved candidate passages are sent to an opt-in LLM judge, and returned citations still pass local quote verification.

## Documentation

- [Step 3 product brief](docs/STEP3_PRODUCT_BRIEF.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Evidence packs](docs/EVIDENCE_PACKS.md)
- [Schemas](docs/SCHEMAS.md)
- [Privacy model](docs/PRIVACY.md)
- [Model profiles](docs/MODEL_PROFILES.md)
- [LangGraph workflow](docs/LANGGRAPH_WORKFLOW.md)
- [Roadmap](docs/ROADMAP.md)

## Repository map

```text
src/qiro_rag/                  Python package and CLI
src/qiro_rag/workflows/        Optional LangGraph workflow
docs/                          Architecture, schemas, privacy, roadmap
examples/synthetic_eval/       Fictional regression evidence pack
tests/                         Unit and pipeline tests
```

## Verification

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run --extra workflow pytest
uv build
```

## Related work

- Step 1/Step 2 analyzer: <https://github.com/PPDEGRET/EMPCOAnalyzer>
- This repository: Step 3 evidence retrieval/substantiation.

## License

Apache-2.0. See [LICENSE](LICENSE).
