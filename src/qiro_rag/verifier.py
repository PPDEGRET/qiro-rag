"""Quote verification for grounded citations."""

from __future__ import annotations

from qiro_rag.index import EvidenceIndex
from qiro_rag.schemas import EvidenceCitation
from qiro_rag.utils import normalize_ws


def quote_exists(quote: str, source_text: str) -> bool:
    if not quote.strip():
        return False
    return normalize_ws(quote).lower() in normalize_ws(source_text).lower()


def verify_citation(index: EvidenceIndex, citation: EvidenceCitation) -> EvidenceCitation:
    source = index.chunk_text(citation.chunk_id) if citation.chunk_id else ""
    if not source:
        source = index.document_text(citation.doc_id)
    return citation.model_copy(update={"verified": quote_exists(citation.quote, source)})


def verify_citations(
    index: EvidenceIndex, citations: list[EvidenceCitation]
) -> list[EvidenceCitation]:
    return [verify_citation(index, citation) for citation in citations]
