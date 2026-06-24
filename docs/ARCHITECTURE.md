# Architecture

## Design stance

Keep v0.1 local, typed, and boring. Framework orchestration is optional and only exists where it provides real typed nodes and tracing.

```text
Connectors     = explicit pull into local staging folders
Docling        = preferred document parsing when installed
Light parsers  = default local parsers for common office formats
OCR            = optional local pytesseract/pdf2image fallback
SQLite/files   = local storage, chunks, tables, embeddings, audit trail
Vector index   = persisted local embeddings in SQLite
LLM judge      = heuristic by default, OpenAI-compatible/Ollama opt-in
Qiro schemas   = source of truth
LangGraph      = optional workflow wrapper with typed Step 3 nodes
CSV/playbooks  = human-approved memory
```

## Pipeline

```text
Enterprise source
  -> optional connector pull into local staging folder
  -> ingest with Docling/light parser/optional OCR
  -> extract text, tables, pages, sections, metadata, hashes
  -> auto-tag documents locally
  -> store chunks/tables in local index
  -> optionally persist local embeddings
  -> Step 2 findings become issue frames
  -> hybrid retrieval finds candidate evidence
  -> direct functions or optional LangGraph nodes run the same assessment steps
  -> heuristic or opt-in LLM assessor judges support/gaps/contradictions
  -> quote verifier removes ungrounded citations
  -> Step 3 JSON artifact feeds Step 4 report
  -> reviewer decisions feed optional learning proposals
```

## Local storage

Start with SQLite:

- `documents` table: doc id, path, hash, detected type, language, date, product hints.
- `chunks` table: chunk id, doc id, page/sheet/section, text, token estimate.
- `tables` table: table id, doc id, sheet/page, serialized rows.
- `embeddings` table: chunk id, backend, model, dimensions, vector JSON.
- `retrieval_hits` table: future optional debug trace.
- `assessments` table: future optional cached Step 3 results.

Use files for:

- `manifest.csv`;
- `review_decisions.csv`;
- `playbook.yaml`;
- `step3_evidence.json`.

## Retrieval

Retrieval modes:

- `keyword`: SQLite FTS / lexical matching;
- `semantic`: local or explicitly configured embedding index;
- `hybrid`: combined keyword, semantic, and metadata filtering.

Run `qiro-rag embed --pack <pack>` to persist hash embeddings. Use `--backend sentence-transformers` with `uv sync --extra local-embeddings` for stronger local semantic retrieval.

## Workflow orchestration

`qiro-rag assess` defaults to `--workflow direct`: the CLI calls typed Qiro functions with no LangChain dependency.

Install the optional graph dependencies to use LangGraph:

```bash
uv sync --extra workflow
uv run --extra workflow qiro-rag assess finding.json --pack evidence-pack --out step3.json --workflow langgraph --trace-out graph_trace.json
```

The LangGraph path is a linear graph of typed nodes: issue framing, query generation, retrieval, judging, model-citation alignment, quote verification, and status finalization. It emits the same public Step 3 JSON shape as the direct path; framework objects never appear in output artifacts.

## LLM judge

Default judge is `heuristic`, so no model call happens.

Opt-in judges:

- `--judge openai`: OpenAI-compatible `/chat/completions`, configured by `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`.
- `--judge ollama`: local Ollama `/api/chat`, configured by `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.

The LLM judge receives only retrieved candidate passages. Returned citations still pass through quote verification; invented quotes are removed.

## Connectors

Connectors stage documents locally before ingestion:

- local paths / `local://` / `file://`;
- `manifest://path/to/files.csv`.

S3, SharePoint, and Drive exports are future scope. Stage those files locally before v0.1 ingestion.

## Autosort

Autosort document role detection should be layered:

1. path and filename hints;
2. Docling metadata;
3. keyword patterns;
4. optional local embedding classifier;
5. optional local LLM;
6. cloud-assisted mode only when explicitly requested.

Autosort writes tags to the manifest. It should not silently move or rename source documents.

## Quote verifier

The quote verifier is deliberately boring:

```text
for each cited quote:
  normalize whitespace
  check it exists in the parsed chunk/table text
  keep if found
  downgrade/remove if not found
```

This prevents model-invented citations while still allowing semantic retrieval.

## Memory

Memory starts as `review_decisions.csv`.

Optional learning creates proposals:

```text
review decisions -> reflection prompt -> playbook.patch.yaml -> human approval -> versioned playbook
```

No silent self-changing model behavior.
