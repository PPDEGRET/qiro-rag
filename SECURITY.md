# Security policy

## Reporting

Please report security or privacy concerns privately through GitHub Security Advisories for this repository, or open a minimal issue that does not include confidential data.

Do not paste API keys, private documents, customer data, evidence packs, generated indexes, or raw model transcripts into public issues.

## Data boundary

Qiro RAG is local-first by default:

- no cloud model calls unless an opt-in judge profile is selected;
- no cloud embeddings unless explicitly configured in future integrations;
- no telemetry;
- generated indexes and traces may contain confidential evidence and should not be committed.

## Supported versions

This is a developer preview. Security fixes target the latest released version only until the project reaches a stable release line.
