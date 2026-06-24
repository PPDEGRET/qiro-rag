# Synthetic messy evaluation case

Fictional evidence pack for quick Step 3 regression checks.

It intentionally mixes useful evidence, marketing drafts, partial support, and contradictions. No real company data.

Run manually:

```bash
qiro-rag ingest examples/synthetic_eval/docs --pack /tmp/qiro-synth-pack --reset
qiro-rag assess examples/synthetic_eval/findings/recycled.json --pack /tmp/qiro-synth-pack --out /tmp/recycled-step3.json
```
