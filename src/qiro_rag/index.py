"""SQLite evidence index."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from qiro_rag.schemas import DocumentRecord, ParsedChunk, ParsedTable, SearchHit
from qiro_rag.utils import tokens

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  original_path TEXT,
  sha256 TEXT NOT NULL,
  detected_type TEXT,
  language TEXT,
  product_hint TEXT,
  market_hint TEXT,
  date_hint TEXT,
  confidence REAL,
  review_status TEXT,
  notes TEXT,
  parser TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  path TEXT NOT NULL,
  page INTEGER,
  sheet TEXT,
  section TEXT,
  text TEXT NOT NULL,
  FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
);
CREATE TABLE IF NOT EXISTS tables (
  table_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  path TEXT NOT NULL,
  page INTEGER,
  sheet TEXT,
  text TEXT NOT NULL,
  FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
);
CREATE TABLE IF NOT EXISTS embeddings (
  chunk_id TEXT NOT NULL,
  backend TEXT NOT NULL,
  model TEXT NOT NULL,
  dimensions INTEGER NOT NULL,
  vector_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(chunk_id, backend, model),
  FOREIGN KEY(chunk_id) REFERENCES chunks(chunk_id)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_tables_doc_id ON tables(doc_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_backend ON embeddings(backend, model);
"""

DocumentPayload = tuple[DocumentRecord, list[ParsedChunk], list[ParsedTable]]
FILTER_COLUMNS = {
    "detected_type": "d.detected_type",
    "language": "d.language",
    "market_hint": "d.market_hint",
}


class EvidenceIndex:
    """Small SQLite index for local evidence packs."""

    def __init__(self, pack_path: Path) -> None:
        self.pack_path = pack_path
        self.db_path = pack_path / "index" / "qiro_rag.sqlite"

    def connect(self) -> sqlite3.Connection:
        """Open a raw SQLite connection.

        Callers own closing. Internal methods use connection() so Windows does not
        keep the pack DB locked after operations.
        """

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def reset(self) -> None:
        with self.connection() as connection:
            self._clear(connection)

    def replace_documents(self, payloads: Iterable[DocumentPayload]) -> None:
        with self.connection() as connection:
            self._clear(connection)
            for record, chunks, tables in payloads:
                self._upsert_document(connection, record, chunks, tables)

    def upsert_document(
        self, record: DocumentRecord, chunks: Iterable[ParsedChunk], tables: Iterable[ParsedTable]
    ) -> None:
        with self.connection() as connection:
            self._upsert_document(connection, record, list(chunks), list(tables))

    def all_chunks(self, filters: dict[str, str] | None = None) -> list[SearchHit]:
        where_sql, params = document_filter_sql(filters)
        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT c.chunk_id, c.doc_id, c.path, c.page, c.sheet, c.section, c.text,
                       d.detected_type
                FROM chunks c
                JOIN documents d ON d.doc_id = c.doc_id
                {where_sql}
                """,
                params,
            ).fetchall()
        return [search_hit_from_row(row) for row in rows]

    def search_keyword(
        self, query: str, limit: int = 8, filters: dict[str, str] | None = None
    ) -> list[SearchHit]:
        query_terms = tokens(query)
        if not query_terms:
            return []
        hits: list[SearchHit] = []
        for hit in self.all_chunks(filters):
            haystack = hit.text.lower()
            path_text = hit.path.lower()
            score = 0.0
            for term in query_terms:
                score += haystack.count(term) * 2.0
                score += path_text.count(term) * 0.75
            phrase = query.lower().strip()
            if phrase and phrase in haystack:
                score += 8.0
            if score > 0:
                hits.append(hit.model_copy(update={"score": score}))
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    def document_text(self, doc_id: str) -> str:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT text FROM chunks WHERE doc_id = ? ORDER BY chunk_id", (doc_id,)
            ).fetchall()
        return "\n".join(row["text"] for row in rows)

    def chunk_text(self, chunk_id: str) -> str:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT text FROM chunks WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()
        return row["text"] if row else ""

    def document_count(self) -> int:
        with self.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return int(row["count"])

    def upsert_embeddings(
        self, backend: str, model: str, dimensions: int, vectors: dict[str, list[float]]
    ) -> None:
        with self.connection() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO embeddings (chunk_id, backend, model, dimensions, vector_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (chunk_id, backend, model, dimensions, json.dumps(vector))
                    for chunk_id, vector in vectors.items()
                ],
            )

    def embedding_rows(
        self,
        backend: str | None = None,
        model: str | None = None,
        filters: dict[str, str] | None = None,
    ) -> list[tuple[SearchHit, list[float]]]:
        where_sql, params = document_filter_sql(filters)
        if backend:
            where_sql, params = append_where(where_sql, params, "e.backend = ?", backend)
        if model:
            where_sql, params = append_where(where_sql, params, "e.model = ?", model)
        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT e.vector_json, c.chunk_id, c.doc_id, c.path, c.page, c.sheet, c.section,
                       c.text, d.detected_type
                FROM embeddings e
                JOIN chunks c ON c.chunk_id = e.chunk_id
                JOIN documents d ON d.doc_id = c.doc_id
                {where_sql}
                """,
                params,
            ).fetchall()
        return [(search_hit_from_row(row), json.loads(row["vector_json"])) for row in rows]

    def embedding_count(self, backend: str | None = None, model: str | None = None) -> int:
        where_sql = ""
        params: list[str] = []
        if backend:
            where_sql, params = append_where(where_sql, params, "backend = ?", backend)
        if model:
            where_sql, params = append_where(where_sql, params, "model = ?", model)
        with self.connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM embeddings {where_sql}", params
            ).fetchone()
        return int(row["count"])

    def default_embedding_backend(self) -> tuple[str, str] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT backend, model, COUNT(*) AS count
                FROM embeddings
                GROUP BY backend, model
                ORDER BY count DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        return str(row["backend"]), str(row["model"])

    def _clear(self, connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM embeddings")
        connection.execute("DELETE FROM tables")
        connection.execute("DELETE FROM chunks")
        connection.execute("DELETE FROM documents")

    def _upsert_document(
        self,
        connection: sqlite3.Connection,
        record: DocumentRecord,
        chunks: list[ParsedChunk],
        tables: list[ParsedTable],
    ) -> None:
        connection.execute(
            "DELETE FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)",
            (record.doc_id,),
        )
        connection.execute("DELETE FROM tables WHERE doc_id = ?", (record.doc_id,))
        connection.execute("DELETE FROM chunks WHERE doc_id = ?", (record.doc_id,))
        connection.execute(
            """
            INSERT OR REPLACE INTO documents (
              doc_id, path, original_path, sha256, detected_type, language,
              product_hint, market_hint, date_hint, confidence, review_status,
              notes, parser
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.doc_id,
                record.path,
                record.original_path,
                record.sha256,
                record.detected_type,
                record.language,
                record.product_hint,
                record.market_hint,
                record.date_hint,
                record.confidence,
                record.review_status,
                record.notes,
                record.parser,
            ),
        )
        connection.executemany(
            """
            INSERT INTO chunks (chunk_id, doc_id, path, page, sheet, section, text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.path,
                    chunk.page,
                    chunk.sheet,
                    chunk.section,
                    chunk.text,
                )
                for chunk in chunks
            ],
        )
        connection.executemany(
            """
            INSERT INTO tables (table_id, doc_id, path, page, sheet, text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (table.table_id, table.doc_id, table.path, table.page, table.sheet, table.text)
                for table in tables
            ],
        )


def document_filter_sql(filters: dict[str, str] | None = None) -> tuple[str, list[str]]:
    where = []
    params: list[str] = []
    for key, column in FILTER_COLUMNS.items():
        if filters and filters.get(key):
            where.append(f"{column} = ?")
            params.append(filters[key])
    return (f"WHERE {' AND '.join(where)}" if where else "", params)


def append_where(
    where_sql: str, params: list[str], clause: str, value: str
) -> tuple[str, list[str]]:
    prefix = "WHERE" if not where_sql else "AND"
    return f"{where_sql} {prefix} {clause}".strip(), [*params, value]


def search_hit_from_row(row: sqlite3.Row) -> SearchHit:
    return SearchHit(
        chunk_id=row["chunk_id"],
        doc_id=row["doc_id"],
        path=row["path"],
        page=row["page"],
        sheet=row["sheet"],
        section=row["section"],
        text=row["text"],
        detected_type=row["detected_type"] or "unknown",
        score=0.0,
    )
