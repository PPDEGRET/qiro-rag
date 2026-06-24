"""Evidence-pack filesystem helpers."""

from pathlib import Path

from qiro_rag.manifest import MANIFEST_COLUMNS, REVIEW_DECISION_COLUMNS

MANIFEST_HEADER = ",".join(MANIFEST_COLUMNS) + "\n"
REVIEW_DECISIONS_HEADER = ",".join(REVIEW_DECISION_COLUMNS) + "\n"

INGESTION_REPORT_TEMPLATE = """# Ingestion report

No documents ingested yet.

Run `qiro-rag ingest <source> --pack <this directory>` to index evidence.
"""


def init_evidence_pack(path: Path) -> list[Path]:
    """Create a minimal evidence-pack layout without overwriting existing files."""

    path.mkdir(parents=True, exist_ok=True)
    (path / "raw").mkdir(exist_ok=True)
    (path / "index").mkdir(exist_ok=True)

    created: list[Path] = []
    files = {
        path / "manifest.csv": MANIFEST_HEADER,
        path / "review_decisions.csv": REVIEW_DECISIONS_HEADER,
        path / "ingestion_report.md": INGESTION_REPORT_TEMPLATE,
    }

    for file_path, content in files.items():
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")
            created.append(file_path)

    return created
