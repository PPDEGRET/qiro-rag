# Roadmap

## Milestone 0: repo bootstrap

- [x] product brief;
- [x] evidence-pack initializer;
- [x] core schemas;
- [x] tests for the initializer.

## Milestone 1: ingestion

- [x] Docling parser wrapper with lightweight fallback;
- [x] support `md`, `txt`, `pdf`, `docx`, `xlsx`, `csv`;
- [x] optional OCR image/scanned-PDF parser hooks;
- [x] managed-copy mode with hashes;
- [x] manifest auto-tagging with local heuristics;
- [x] ingestion report.

## Milestone 2: local index

- [x] SQLite document/chunk/table store;
- [x] persisted SQLite embeddings table;
- [x] keyword retrieval;
- [x] metadata filters in the index API;
- [x] quote verifier.

## Milestone 3: first RAG assessment

- [x] Step 2 finding loader;
- [x] issue-frame generator;
- [x] evidence-question generator;
- [x] heuristic judge;
- [x] opt-in OpenAI-compatible judge;
- [x] opt-in local Ollama judge;
- [x] optional orchestration/tracing wrapper when real typed nodes are needed;
- [x] Step 3 JSON writer.

## Milestone 4: semantic retrieval

- [x] optional sentence-transformer embedding backend;
- [x] persisted hash embedding backend;
- [x] lightweight local semantic fallback;
- [x] hybrid retrieval;
- [ ] persisted retrieval trace output.

## Milestone 5: review memory

- [x] reviewer correction command;
- [x] `review_decisions.csv` append flow;
- [x] optional `learn --propose` playbook patch;
- [x] regression examples from accepted/rejected evidence in tests.

## Milestone 6: enterprise source staging

- [x] local folder connector;
- [x] manifest connector;
- [ ] optional S3 connector after local-pack workflow stabilizes;
- [ ] optional SharePoint/Graph connector after local-pack workflow stabilizes;
- [ ] optional Google Drive connector after local-pack workflow stabilizes.

## Later

- encrypted evidence vault;
- multilingual review packs;
- RAG evaluation with Ragas/TruLens-style checks;
- DSPy-style prompt optimization from validated examples;
- richer model judge prompts from reviewer-approved examples.
