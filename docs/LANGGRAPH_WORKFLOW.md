# LangGraph workflow

The optional LangGraph assessment workflow is implemented. The direct Qiro pipeline remains the default and dependency-light path.

Use it when node-level tracing is useful:

```bash
uv run --extra workflow qiro-rag assess examples/step2/finding.json \
  --pack ./evidence-pack \
  --out step3_evidence.json \
  --workflow langgraph \
  --trace-out graph_trace.json
```

Implemented boundaries:

- optional dependencies live under the `workflow` extra;
- public schemas stay owned by `src/qiro_rag/schemas.py`;
- `qiro-rag assess` defaults to `--workflow direct`;
- LangGraph uses real typed nodes, not a single wrapper;
- retrieved quotes still pass Qiro quote verification;
- raw evidence only leaves the machine when the selected judge profile already opts into that.

Current nodes:

1. `build_issue_frame_node`
2. `generate_queries_node`
3. `retrieve_candidates_node`
4. `judge_evidence_node`
5. `align_model_citations_node`
6. `verify_quotes_node`
7. `finalize_status_node`

Future changes should keep this boring: no autonomous agents, no hidden memory, no framework objects in output JSON.
