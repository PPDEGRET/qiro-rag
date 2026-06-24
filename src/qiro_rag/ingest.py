"""Evidence-pack ingestion."""

from __future__ import annotations

import shutil
from pathlib import Path

from qiro_rag.autotag import tag_document
from qiro_rag.evidence_pack import init_evidence_pack
from qiro_rag.index import EvidenceIndex
from qiro_rag.manifest import replace_manifest_records, upsert_manifest_records
from qiro_rag.parsing import parse_file, parsed_text
from qiro_rag.schemas import DocumentRecord, IngestionSummary, StorageMode
from qiro_rag.utils import is_supported_file, relative_to_or_name, sha256_file


def ingest_path(
    source_path: Path,
    pack_path: Path,
    storage_mode: StorageMode = "managed-copy",
    parser: str = "auto",
    reset: bool = False,
) -> IngestionSummary:
    """Parse supported documents and update the local index/manifest."""

    source_path = source_path.resolve()
    pack_path = pack_path.resolve()
    init_evidence_pack(pack_path)

    index = EvidenceIndex(pack_path)
    files = list(iter_evidence_files(source_path, pack_path))
    records: list[DocumentRecord] = []
    payloads = []
    warnings: list[str] = []
    skipped: list[str] = []

    for file_path in files:
        try:
            digest = sha256_file(file_path)
            doc_id = f"DOC-{digest[:12].upper()}"
            stored_file = _stored_file(file_path, source_path, pack_path, storage_mode, digest)
            stored_path = relative_to_or_name(stored_file, pack_path)
            parsed = parse_file(stored_file, doc_id=doc_id, stored_path=stored_path, parser=parser)
            text = parsed_text(parsed)
            tags = tag_document(stored_file, text)
            record = DocumentRecord(
                doc_id=doc_id,
                path=stored_path,
                original_path=str(file_path),
                sha256=digest,
                detected_type=str(tags["detected_type"]),
                language=str(tags["language"]),
                product_hint=str(tags["product_hint"]),
                market_hint=str(tags["market_hint"]),
                date_hint=str(tags["date_hint"]),
                confidence=float(tags["confidence"]),
                review_status=str(tags["review_status"]),
                parser=parsed.parser,
            )
            payloads.append((record, parsed.chunks, parsed.tables))
            records.append(record)
            warnings.extend(f"{stored_path}: {warning}" for warning in parsed.warnings)
        except Exception as exc:  # noqa: BLE001 - ingestion should report and continue
            skipped.append(str(file_path))
            warnings.append(f"{file_path}: {exc}")

    if reset:
        index.replace_documents(payloads)
        replace_manifest_records(pack_path / "manifest.csv", records)
    else:
        for record, chunks, tables in payloads:
            index.upsert_document(record, chunks, tables)
        upsert_manifest_records(pack_path / "manifest.csv", records)
    _write_ingestion_report(pack_path, records, skipped, warnings)
    return IngestionSummary(
        pack_path=str(pack_path),
        source_path=str(source_path),
        indexed_documents=len(records),
        skipped_files=skipped,
        warnings=warnings,
    )


def iter_evidence_files(source_path: Path, pack_path: Path) -> list[Path]:
    if source_path.is_file():
        return [source_path] if is_supported_file(source_path) else []

    files: list[Path] = []
    for path in source_path.rglob("*"):
        if not is_supported_file(path):
            continue
        if _is_generated_pack_file(path, pack_path):
            continue
        files.append(path)
    return sorted(files)


def _is_generated_pack_file(path: Path, pack_path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(pack_path.resolve())
    except ValueError:
        return False
    if relative.parts and relative.parts[0] in {"index", ".git"}:
        return True
    return relative.name in {"manifest.csv", "review_decisions.csv", "ingestion_report.md"}


def _stored_file(
    file_path: Path, source_path: Path, pack_path: Path, storage_mode: StorageMode, digest: str
) -> Path:
    raw_dir = pack_path / "raw"
    try:
        file_path.resolve().relative_to(raw_dir.resolve())
        return file_path
    except ValueError:
        pass

    if storage_mode == "reference":
        return file_path

    raw_dir.mkdir(parents=True, exist_ok=True)
    relative = relative_to_or_name(
        file_path, source_path if source_path.is_dir() else file_path.parent
    )
    target = raw_dir / relative
    if target.exists() and sha256_file(target) != digest:
        target = target.with_name(f"{target.stem}-{digest[:8]}{target.suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or sha256_file(target) != digest:
        shutil.copy2(file_path, target)
    return target


def _write_ingestion_report(
    pack_path: Path, records: list[DocumentRecord], skipped: list[str], warnings: list[str]
) -> None:
    lines = ["# Ingestion report", "", f"Indexed documents: {len(records)}", ""]
    if records:
        lines.append("## Documents")
        lines.append("")
        for record in records:
            lines.append(
                f"- `{record.doc_id}` `{record.path}` — {record.detected_type} "
                f"({record.confidence:.2f}, {record.review_status})"
            )
        lines.append("")
    if skipped:
        lines.append("## Skipped files")
        lines.append("")
        lines.extend(f"- `{path}`" for path in skipped)
        lines.append("")
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    if not warnings:
        lines.extend(["## Warnings", "", "None.", ""])
    (pack_path / "ingestion_report.md").write_text("\n".join(lines), encoding="utf-8")
