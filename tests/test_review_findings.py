import csv
from pathlib import Path

import pytest

from qiro_rag.connectors import ConnectorError, pull_source
from qiro_rag.embeddings import build_embedding_index
from qiro_rag.index import EvidenceIndex
from qiro_rag.ingest import ingest_path
from qiro_rag.retrieval import retrieve


def test_sqlite_connections_close_so_db_can_be_removed(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "evidence.md").write_text(
        "Certificate covers 120 tCO2e for EU delivery.", encoding="utf-8"
    )

    ingest_path(docs, pack, reset=True)
    index = EvidenceIndex(pack)
    assert index.document_count() == 1
    assert retrieve(index, ["delivery certificate"])

    index.db_path.unlink()
    assert not index.db_path.exists()


def test_ingest_reset_replaces_manifest_rows(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    stale = docs / "stale.md"
    stale.write_text("Old certificate covers 1 tCO2e.", encoding="utf-8")
    current = docs / "current.md"
    current.write_text("Current certificate covers 120 tCO2e.", encoding="utf-8")

    ingest_path(docs, pack, reset=True)
    stale.unlink()
    ingest_path(docs, pack, reset=True)

    with (pack / "manifest.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["path"] == "raw/current.md"
    assert EvidenceIndex(pack).document_count() == 1


def test_persisted_embedding_retrieval_honors_metadata_filters(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "eu.md").write_text(
        "Certificate covers 120 tCO2e retired for EU delivery operations.", encoding="utf-8"
    )
    (docs / "us.md").write_text(
        "Certificate covers 75 tCO2e retired for US delivery operations.", encoding="utf-8"
    )
    ingest_path(docs, pack, reset=True)
    index = EvidenceIndex(pack)
    build_embedding_index(index, backend="hash", dimensions=64)

    hits = retrieve(
        index,
        ["delivery carbon certificate"],
        mode="semantic",
        filters={"market_hint": "EU"},
        top_k=5,
    )

    assert hits
    assert all("EU delivery" in hit.text for hit in hits)


def test_cloud_connectors_are_explicitly_not_v0_1(tmp_path: Path) -> None:
    with pytest.raises(ConnectorError, match="local paths and manifest"):
        pull_source("s3://bucket/prefix", tmp_path / "stage")
