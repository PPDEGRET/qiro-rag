"""Local evidence source staging.

v0.1 keeps connectors boring: local folders/files and CSV manifests only.
Hosted enterprise sources are future scope; stage them outside Qiro first.
"""

from __future__ import annotations

import csv
import shutil
import urllib.parse
from pathlib import Path

from pydantic import BaseModel, Field

from qiro_rag.utils import is_supported_file


class ConnectorSummary(BaseModel):
    source: str
    target: str
    downloaded: int = 0
    skipped: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ConnectorError(RuntimeError):
    pass


def pull_source(uri: str, target: Path) -> ConnectorSummary:
    target.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme in {"", "file", "local"} or len(parsed.scheme) == 1:
        raw_path = uri if len(parsed.scheme) == 1 else (parsed.path if parsed.scheme else uri)
        return pull_local(Path(urllib.parse.unquote(raw_path)), target, uri)
    if parsed.scheme == "manifest":
        raw_manifest = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
        return pull_manifest(Path(urllib.parse.unquote(raw_manifest)), target, uri)
    raise ConnectorError(
        "Only local paths and manifest:// CSV staging are supported in v0.1. "
        "Stage S3, SharePoint, or Drive exports locally before running qiro-rag pull."
    )


def pull_local(source: Path, target: Path, uri: str | None = None) -> ConnectorSummary:
    if not source.exists():
        raise ConnectorError(f"Local source does not exist: {source}")
    files = [source] if source.is_file() else [path for path in source.rglob("*") if path.is_file()]
    summary = ConnectorSummary(source=uri or str(source), target=str(target))
    for path in files:
        if not is_supported_file(path):
            summary.skipped.append(str(path))
            continue
        relative = path.name if source.is_file() else path.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        summary.downloaded += 1
    return summary


def pull_manifest(manifest_path: Path, target: Path, uri: str | None = None) -> ConnectorSummary:
    if not manifest_path.exists():
        raise ConnectorError(f"Manifest source does not exist: {manifest_path}")
    summary = ConnectorSummary(source=uri or str(manifest_path), target=str(target))
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw = row.get("path") or row.get("file") or row.get("source")
            if not raw:
                continue
            source = Path(raw)
            if not source.is_absolute():
                source = manifest_path.parent / source
            if not source.exists() or not is_supported_file(source):
                summary.skipped.append(str(source))
                continue
            destination = target / (row.get("target") or source.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            summary.downloaded += 1
    return summary
