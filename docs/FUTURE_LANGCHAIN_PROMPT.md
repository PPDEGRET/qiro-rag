# Future prompt: add real LangChain/LangGraph orchestration

Use this only after the direct Qiro Step 3 pipeline is stable and you want traceable framework orchestration.

```text
You are working in `opensourceqirorag/`.

Goal: add an optional LangChain/LangGraph workflow without changing Qiro's public schemas or direct default path.

Constraints:
- Do not replace the typed Qiro core functions.
- Do not add hidden memory or agentic compliance decisions.
- Do not send raw evidence outside the machine unless the selected judge profile already does that explicitly.
- Keep `qiro-rag assess` default direct/local.
- Add `--workflow langgraph` only if the graph has real typed nodes, not a single RunnableLambda wrapper.
- Every citation must still pass Qiro quote verification.
- Human review must remain recommended for LLM judge output.

Implement:
1. Add optional dependencies under an extra, e.g. `workflow = ["langchain-core", "langgraph"]`.
2. Create `src/qiro_rag/workflows/langgraph_assess.py`.
3. Model graph state with Qiro-owned Pydantic/dataclass objects:
   - `Step2Finding`
   - `IssueFrame`
   - retrieval queries
   - `SearchHit[]`
   - draft `Step3Assessment`
   - verified `Step3Assessment`
4. Build real nodes:
   - `build_issue_frame_node`
   - `generate_queries_node`
   - `retrieve_candidates_node`
   - `judge_evidence_node`
   - `align_model_citations_node`
   - `verify_quotes_node`
   - `finalize_status_node`
5. Reuse existing functions from:
   - `framing.py`
   - `retrieval.py`
   - `assess.py`
   - `verifier.py`
   - `llm_judge.py`
6. Add `--workflow direct|langgraph` to CLI only after the graph is implemented.
7. Add tests proving direct and langgraph workflows produce the same expected statuses on `examples/synthetic_eval`.
8. Add a small trace/debug output option, e.g. `--trace-out graph_trace.json`, if useful.

Non-goals:
- no LangChain document loaders unless they clearly beat current parsers;
- no vector-store dependency swap unless benchmarked;
- no autonomous agents;
- no framework objects in output JSON.

Acceptance:
- `uv run pytest` passes.
- `uv build` passes.
- direct workflow remains dependency-light and default.
- LangGraph workflow has real intermediate node state useful for debugging or UI display.
```
