# Contributing

Thanks for considering a contribution to Qiro RAG.

## Development setup

```bash
git clone https://github.com/PPDEGRET/qiro-rag.git
cd qiro-rag
uv sync --dev
```

## Checks before opening a PR

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run --extra workflow pytest
uv build
```

## Product language

This project is a review aid for environmental claim substantiation. Please use cautious language:

- "potential issue"
- "substantiation gap"
- "evidence appears to support"
- "human review recommended"

Avoid claims that the tool determines illegality, guarantees compliance, or replaces counsel/compliance review.

## Data hygiene

Do not commit confidential evidence packs, customer documents, raw run logs, generated indexes, API keys, or private benchmark data. Public fixtures should be synthetic or have documented provenance/licensing.
