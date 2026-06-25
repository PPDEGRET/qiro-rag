# Evidence packs

An evidence pack is the local working copy/index for a company-provided evidence corpus.

## Minimal layout

```text
evidence-pack/
  raw/
  manifest.csv
  review_decisions.csv
  index/
  ingestion_report.md
```

`index/` is generated and should not be committed.

## Required source formats for v0.1 target

- Markdown: `.md`
- Text: `.txt`
- PDF: `.pdf`
- Word: `.docx`
- Excel: `.xlsx`
- CSV: `.csv`
- Optional OCR image evidence: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`

Docling is the intended parser where installed. Lightweight local parsers cover the required formats. OCR image/scanned-PDF support requires `uv sync --extra ocr` plus local OCR system tools.

## Manifest columns

Initial `manifest.csv` columns:

```csv
doc_id,path,sha256,detected_type,language,product_hint,market_hint,date_hint,confidence,review_status,notes
```

Detected type examples:

- `product_specification`
- `certificate`
- `supplier_declaration`
- `lab_test`
- `lca_or_epd`
- `ghg_inventory`
- `offset_documentation`
- `recycling_guidance`
- `packaging_bom`
- `marketing_approval_note`
- `policy_or_transition_plan`
- `sustainability_report`
- `unknown`

## Review decisions columns

Initial `review_decisions.csv` columns:

```csv
claim_id,doc_id,quote,status,human_decision,reason,created_at
```

Use this as auditable memory before adding any self-improvement system.

## Storage modes

- `reference`: index points to source file paths.
- `managed-copy`: copy files into `raw/` and hash them.
- `encrypted-copy`: future enterprise option.

Recommended default: `managed-copy`, because it makes later audits easier.

## Connector staging

Use `qiro-rag pull` to stage enterprise sources locally before ingesting:

```bash
qiro-rag pull ./exported-company-docs --target ./staged-docs
qiro-rag ingest ./staged-docs --pack ./evidence-pack
```

Supported connector URI families:

- local path / `local://` / `file://`;
- `manifest://files.csv`.

S3, SharePoint, and Drive connectors are not in v0.1. Export or sync those files locally first.

## Ingestion report

`ingestion_report.md` should list:

- files parsed;
- files skipped;
- parser warnings;
- low-confidence document tags;
- unsupported formats;
- documents requiring human metadata review.
