"""Public Step 3 schemas.

These are deliberately small. Frameworks can use them, but they do not own them.
"""

from typing import Literal

from pydantic import BaseModel, Field

EvidenceStatus = Literal[
    "supported",
    "partially_supported",
    "contradicted",
    "insufficient_evidence",
    "unclear",
    "not_applicable",
]

EvidenceRelation = Literal["supports", "limits", "contradicts", "context", "irrelevant"]
RetrievalMode = Literal["keyword", "semantic", "hybrid"]
StorageMode = Literal["reference", "managed-copy"]
JudgeMode = Literal["heuristic", "openai", "ollama"]
EmbeddingBackend = Literal["hash", "sentence-transformers"]


class Step2Finding(BaseModel):
    """Issue from the analyzer that needs evidence review."""

    claim_id: str = Field(alias="claimId")
    claim_text: str = Field(alias="claimText")
    critique: str
    rule_refs: list[str] = Field(default_factory=list, alias="ruleRefs")
    needs_evidence_check: bool = Field(default=True, alias="needsEvidenceCheck")
    consumer_impression: str | None = Field(default=None, alias="consumerImpression")

    model_config = {"populate_by_name": True}


class IssueFrame(BaseModel):
    """Claim X + critique/law issue Y + evidence Z that may matter."""

    claim_id: str = Field(alias="claimId")
    claim_text: str = Field(alias="claimText")
    critique: str
    rule_refs: list[str] = Field(default_factory=list, alias="ruleRefs")
    what_would_help: list[str] = Field(default_factory=list, alias="whatWouldHelp")
    what_would_not_be_enough: list[str] = Field(default_factory=list, alias="whatWouldNotBeEnough")
    open_questions: list[str] = Field(default_factory=list, alias="openQuestions")

    model_config = {"populate_by_name": True}


class EvidenceCitation(BaseModel):
    """Quote-backed citation to a parsed source document."""

    doc_id: str = Field(alias="docId")
    path: str
    quote: str
    relevance: str
    relation: EvidenceRelation = "context"
    chunk_id: str | None = Field(default=None, alias="chunkId")
    page: int | None = None
    sheet: str | None = None
    section: str | None = None
    verified: bool = False

    model_config = {"populate_by_name": True}


class Step3Assessment(BaseModel):
    """Evidence review artifact consumed by Step 4."""

    claim_id: str = Field(alias="claimId")
    status: EvidenceStatus
    summary: str
    supporting_evidence: list[EvidenceCitation] = Field(
        default_factory=list, alias="supportingEvidence"
    )
    contradicting_evidence: list[EvidenceCitation] = Field(
        default_factory=list, alias="contradictingEvidence"
    )
    missing_evidence: list[str] = Field(default_factory=list, alias="missingEvidence")
    human_review_recommended: bool = Field(default=True, alias="humanReviewRecommended")

    model_config = {"populate_by_name": True}


class ReviewDecision(BaseModel):
    """Auditable reviewer feedback used as memory."""

    claim_id: str
    doc_id: str
    quote: str
    status: EvidenceRelation
    human_decision: Literal["accepted", "rejected", "edited", "unclear"]
    reason: str
    created_at: str


class DocumentRecord(BaseModel):
    """Manifest/index metadata for one evidence source."""

    doc_id: str
    path: str
    sha256: str
    detected_type: str = "unknown"
    language: str = "unknown"
    product_hint: str = ""
    market_hint: str = ""
    date_hint: str = ""
    confidence: float = 0.0
    review_status: str = "needs_review"
    notes: str = ""
    original_path: str = ""
    parser: str = "unknown"


class ParsedChunk(BaseModel):
    """Parsed text unit with source location metadata."""

    chunk_id: str
    doc_id: str
    path: str
    text: str
    page: int | None = None
    sheet: str | None = None
    section: str | None = None


class ParsedTable(BaseModel):
    """Parsed table serialized for retrieval."""

    table_id: str
    doc_id: str
    path: str
    text: str
    page: int | None = None
    sheet: str | None = None


class ParsedDocument(BaseModel):
    """Output from a document parser."""

    path: str
    parser: str
    chunks: list[ParsedChunk]
    tables: list[ParsedTable] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SearchHit(BaseModel):
    """Retrieved chunk/table candidate."""

    chunk_id: str
    doc_id: str
    path: str
    text: str
    score: float
    detected_type: str = "unknown"
    page: int | None = None
    sheet: str | None = None
    section: str | None = None


class IngestionSummary(BaseModel):
    """Result from ingesting a source folder."""

    pack_path: str
    source_path: str
    indexed_documents: int
    skipped_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Step3ReviewPackage(BaseModel):
    """Full Step 3 package for debugging or UI display."""

    issue_frame: IssueFrame = Field(alias="issueFrame")
    assessment: Step3Assessment
    retrieval_mode: RetrievalMode = Field(alias="retrievalMode")

    model_config = {"populate_by_name": True}
