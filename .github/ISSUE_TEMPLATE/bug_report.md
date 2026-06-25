---
name: Bug report
description: Report a reproducible problem without sharing confidential evidence.
title: "[Bug]: "
labels: [bug]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting a problem. Do not attach confidential evidence packs, API keys, raw model transcripts, or customer documents.
  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: What happened?
    validations:
      required: true
  - type: textarea
    id: reproduce
    attributes:
      label: Reproduction steps
      description: Use synthetic/minimal data where possible.
      placeholder: |
        1. Run `uv run qiro-rag ...`
        2. See error ...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version or commit
      placeholder: v0.1.0
  - type: textarea
    id: environment
    attributes:
      label: Environment
      placeholder: Python version, OS, optional extras installed
