# Model profiles and onboarding

Qiro RAG can run with no LLM, a local/private LLM, or an OpenAI-compatible hosted/private gateway model.

List profiles:

```bash
qiro-rag models
```

Ask a few setup questions:

```bash
qiro-rag onboard
```

Use a profile:

```bash
qiro-rag assess finding.json --pack evidence-pack --out step3.json --profile ollama-private-small
```

## Built-in profiles

- `heuristic` — default, local, no LLM. Best for CI, demos, and conservative offline smoke checks.
- `ollama-private-small` — local Ollama `qwen2.5:1.5b`. Tested; usable for private demos, still limited.
- `ollama-private-balanced` — local Ollama `qwen2.5:7b`. Recommended private baseline when hardware allows.
- `ollama-private-mistral` — local Ollama `mistral-small3.2`. Privacy-first Mistral-family option for stronger local hardware.
- `hosted-flash` — OpenAI-compatible hosted/private gateway, default `gemini-2.5-flash`. Recommended hosted default.
- `mistral-private-gateway` — OpenAI-compatible Mistral/private gateway, default `mistral-small-latest`.
- `openai-compatible-custom` — no hardcoded model; use `OPENAI_MODEL` or `--judge-model`.

## Important limitation

Small local models can misread evidence or output malformed JSON. Qiro still applies quote verification and sanity checks, but model output remains a review aid. Human review stays required.

## Private gateway pattern

For enterprise deployments, point a profile at a private gateway:

```bash
export OPENAI_BASE_URL=https://your-private-gateway.example/v1
export OPENAI_API_KEY=...
qiro-rag assess finding.json --pack evidence-pack --out step3.json --profile mistral-private-gateway
```

Or override any OpenAI-compatible gateway model explicitly:

```bash
qiro-rag assess finding.json --pack evidence-pack --out step3.json --judge openai --judge-model your-model-name
```

Only retrieved candidate passages are sent to the model, not the full evidence pack.
