"""CSV manifest helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from qiro_rag.schemas import DocumentRecord, ReviewDecision

MANIFEST_COLUMNS = [
    "doc_id",
    "path",
    "sha256",
    "detected_type",
    "language",
    "product_hint",
    "market_hint",
    "date_hint",
    "confidence",
    "review_status",
    "notes",
]

REVIEW_DECISION_COLUMNS = [
    "claim_id",
    "doc_id",
    "quote",
    "status",
    "human_decision",
    "reason",
    "created_at",
]


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["doc_id"]: row for row in reader if row.get("doc_id")}


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: item.get("doc_id", "")):
            writer.writerow({column: row.get(column, "") for column in MANIFEST_COLUMNS})


def upsert_manifest_records(path: Path, records: list[DocumentRecord]) -> None:
    existing = read_manifest(path)
    for record in records:
        existing[record.doc_id] = manifest_row(record, existing.get(record.doc_id, {}))
    write_manifest(path, list(existing.values()))


def replace_manifest_records(path: Path, records: list[DocumentRecord]) -> None:
    existing = read_manifest(path)
    write_manifest(
        path, [manifest_row(record, existing.get(record.doc_id, {})) for record in records]
    )


def manifest_row(record: DocumentRecord, old: dict[str, str] | None = None) -> dict[str, str]:
    old = old or {}
    return {
        "doc_id": record.doc_id,
        "path": record.path,
        "sha256": record.sha256,
        "detected_type": record.detected_type,
        "language": record.language,
        "product_hint": record.product_hint,
        "market_hint": record.market_hint,
        "date_hint": record.date_hint,
        "confidence": f"{record.confidence:.2f}",
        "review_status": old.get("review_status") or record.review_status,
        "notes": old.get("notes") or record.notes,
    }


def ensure_review_decisions(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_DECISION_COLUMNS)
        writer.writeheader()


def append_review_decision(path: Path, decision: ReviewDecision) -> None:
    ensure_review_decisions(path)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_DECISION_COLUMNS)
        writer.writerow(decision.model_dump())


def read_review_decisions(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
