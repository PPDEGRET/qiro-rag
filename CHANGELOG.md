# Changelog

All notable changes to this project will be documented in this file.

## v0.1.0 - 2026-06-24

Initial developer preview.

### Added

- Evidence-pack initialization and local manifest files.
- Ingestion for Markdown, text, PDF, DOCX, XLSX, and CSV files.
- Optional local OCR hooks for image/scanned-PDF evidence.
- SQLite-backed chunks, tables, metadata, hashes, and embeddings.
- Keyword, semantic, and hybrid retrieval modes.
- Step 2 finding loader and Step 3 assessment JSON writer.
- Quote-backed heuristic evidence assessment.
- Opt-in Ollama and OpenAI-compatible LLM judges.
- Human-review memory through `review_decisions.csv`.
- Optional playbook patch proposals from reviewer decisions.
- Optional LangGraph workflow with typed nodes and trace output.
- Synthetic regression evidence pack and tests.
