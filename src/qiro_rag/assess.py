"""Step 3 evidence assessment."""

from __future__ import annotations

import json
import re
from pathlib import Path

from qiro_rag.evidence_lenses import NON_EVIDENCE_DOCUMENT_TYPES, attribute_terms_for_text
from qiro_rag.framing import build_issue_frame, evidence_queries
from qiro_rag.index import EvidenceIndex
from qiro_rag.retrieval import retrieve
from qiro_rag.schemas import (
    EvidenceCitation,
    EvidenceRelation,
    EvidenceStatus,
    IssueFrame,
    JudgeMode,
    RetrievalMode,
    SearchHit,
    Step2Finding,
    Step3Assessment,
    Step3ReviewPackage,
)
from qiro_rag.utils import tokens, unique_preserve_order
from qiro_rag.verifier import verify_citations

SUPPORT_MARKERS = {
    "certificate",
    "certified",
    "verified",
    "contains",
    "covers",
    "calculated",
    "calculation",
    "methodology",
    "standard",
    "iso",
    "astm",
    "retired",
    "retirement",
    "post-consumer",
    "recycled",
    "recyclable",
    "compostable",
    "emissions",
    "scope",
}

LIMIT_MARKERS = {
    "aim",
    "aims",
    "target",
    "intends",
    "planned",
    "future",
    "estimate",
    "estimated",
    "subject to",
    "where available",
    "not product-specific",
    "corporate",
    "excluded",
    "not covered",
    "depends",
}

GENERIC_RELEVANCE_TERMS = {
    "basis",
    "boundaries",
    "campaign",
    "claim",
    "coverage",
    "covered",
    "data",
    "date",
    "different",
    "evidence",
    "exclusions",
    "exact",
    "market",
    "matching",
    "product",
    "relevant",
    "scope",
    "service",
    "source",
    "specific",
    "version",
}

CONTRADICTION_PATTERNS = [
    r"\bnot\s+(?:recyclable|compostable|biodegradable|carbon neutral|climate neutral)",
    r"\bdoes\s+not\s+(?:contain|cover|support|include|meet)",
    r"\bno\s+(?:evidence|certificate|calculation|offset|recycling|substantiation)",
    r"\bnot\s+covered\b",
]


def load_step2_finding(path: Path) -> Step2Finding:
    return Step2Finding.model_validate_json(path.read_text(encoding="utf-8"))


def assess_finding(
    finding: Step2Finding,
    pack_path: Path,
    retrieval_mode: RetrievalMode = "hybrid",
    top_k: int = 10,
    judge: JudgeMode = "heuristic",
    judge_model: str | None = None,
) -> Step3ReviewPackage:
    frame = build_issue_frame(finding)
    if not finding.needs_evidence_check:
        assessment = Step3Assessment(
            claimId=finding.claim_id,
            status="not_applicable",
            summary="Step 2 did not request an evidence check for this finding.",
            humanReviewRecommended=False,
        )
        return Step3ReviewPackage(
            issueFrame=frame, assessment=assessment, retrievalMode=retrieval_mode
        )

    index = EvidenceIndex(pack_path)
    hits = retrieve(index, evidence_queries(frame), mode=retrieval_mode, top_k=top_k)
    if judge == "heuristic":
        assessment = judge_evidence(frame, hits)
    else:
        from qiro_rag.llm_judge import client_from_mode, judge_with_llm

        assessment = judge_with_llm(frame, hits, client_from_mode(judge, model=judge_model))
        assessment = align_model_citations(frame, hits, assessment)
    assessment = assessment.model_copy(
        update={
            "supporting_evidence": verify_citations(index, assessment.supporting_evidence),
            "contradicting_evidence": verify_citations(index, assessment.contradicting_evidence),
        }
    )
    # Quote-backed rule: unverified evidence cannot be cited as support.
    assessment.supporting_evidence[:] = [
        citation for citation in assessment.supporting_evidence if citation.verified
    ]
    assessment.contradicting_evidence[:] = [
        citation for citation in assessment.contradicting_evidence if citation.verified
    ]
    assessment = assessment.model_copy(update={"status": _status_after_verification(assessment)})
    return Step3ReviewPackage(issueFrame=frame, assessment=assessment, retrievalMode=retrieval_mode)


def write_assessment(package: Step3ReviewPackage, path: Path, include_frame: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        package.model_dump(by_alias=True)
        if include_frame
        else package.assessment.model_dump(by_alias=True)
    )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def judge_evidence(frame: IssueFrame, hits: list[SearchHit]) -> Step3Assessment:
    supporting: list[EvidenceCitation] = []
    contradicting: list[EvidenceCitation] = []
    context_hits = 0

    for hit in hits:
        relation = classify_hit(frame, hit)
        if relation == "irrelevant":
            continue
        if relation == "context":
            context_hits += 1
            continue
        citation = EvidenceCitation(
            docId=hit.doc_id,
            path=hit.path,
            chunkId=hit.chunk_id,
            page=hit.page,
            sheet=hit.sheet,
            section=hit.section,
            quote=best_quote(frame, hit),
            relation=relation,
            relevance=relevance_text(relation),
        )
        if relation == "contradicts":
            contradicting.append(citation)
        else:
            supporting.append(citation)

    missing = missing_evidence(frame, hits)
    status = aggregate_status(supporting, contradicting, missing, context_hits)
    summary = summarize_assessment(status, supporting, contradicting, missing, context_hits)
    return Step3Assessment(
        claimId=frame.claim_id,
        status=status,
        summary=summary,
        supportingEvidence=supporting[:6],
        contradictingEvidence=contradicting[:4],
        missingEvidence=missing,
        humanReviewRecommended=True,
    )


def classify_hit(frame: IssueFrame, hit: SearchHit) -> EvidenceRelation:
    text = hit.text.lower()
    if hit.detected_type in NON_EVIDENCE_DOCUMENT_TYPES:
        return "context"
    claim_terms = set(
        tokens(frame.claim_text + " " + frame.critique + " " + " ".join(frame.rule_refs))
    )
    requirement_terms = set(tokens(" ".join(frame.what_would_help)))
    focus_claim_terms = claim_terms - GENERIC_RELEVANCE_TERMS
    focus_requirement_terms = requirement_terms - GENERIC_RELEVANCE_TERMS
    attribute_terms = evidence_attribute_terms(frame)
    hit_terms = set(tokens(hit.text))
    claim_overlap = focus_claim_terms & hit_terms
    requirement_overlap = focus_requirement_terms & hit_terms
    attribute_overlap = attribute_terms & hit_terms
    support_marker_count = sum(1 for marker in SUPPORT_MARKERS if marker in text)
    has_fact = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:%|tco2e|kg|g|tonnes?|months?|years?)\b", text))
    is_relevant = bool(attribute_overlap) and (
        len(claim_overlap) >= 1
        or len(requirement_overlap) >= 1
        or support_marker_count > 0
        or has_fact
    )

    if not is_relevant:
        return "irrelevant"

    quote_text = best_quote(frame, hit).lower()
    quote_support_marker_count = sum(1 for marker in SUPPORT_MARKERS if marker in quote_text)
    quote_limit_marker_count = sum(1 for marker in LIMIT_MARKERS if marker in quote_text)
    quote_has_fact = bool(
        re.search(r"\b\d+(?:\.\d+)?\s*(?:%|tco2e|kg|g|tonnes?|months?|years?)\b", quote_text)
    )
    if any(re.search(pattern, quote_text) for pattern in CONTRADICTION_PATTERNS):
        return "contradicts"
    if quote_limit_marker_count and not quote_has_fact:
        return "limits"
    if quote_support_marker_count >= 2 or quote_has_fact:
        return "supports"
    return "context"


def align_model_citations(
    frame: IssueFrame, hits: list[SearchHit], assessment: Step3Assessment
) -> Step3Assessment:
    hit_by_id = {hit.chunk_id: hit for hit in hits}
    supporting: list[EvidenceCitation] = []
    contradicting: list[EvidenceCitation] = []
    for citation in [*assessment.supporting_evidence, *assessment.contradicting_evidence]:
        hit = hit_by_id.get(citation.chunk_id or "")
        if not hit:
            continue
        relation = classify_hit(frame, hit)
        if relation in {"irrelevant", "context"}:
            continue
        fixed = citation.model_copy(
            update={"relation": relation, "relevance": relevance_text(relation)}
        )
        if relation == "contradicts":
            contradicting.append(fixed)
        else:
            supporting.append(fixed)
    return assessment.model_copy(
        update={"supporting_evidence": supporting, "contradicting_evidence": contradicting}
    )


def evidence_attribute_terms(frame: IssueFrame) -> set[str]:
    haystack = " ".join(
        [
            frame.claim_text,
            frame.critique,
            " ".join(frame.rule_refs),
            " ".join(frame.what_would_help),
        ]
    )
    return attribute_terms_for_text(haystack) or (
        set(tokens(frame.claim_text + " " + frame.critique)) - GENERIC_RELEVANCE_TERMS
    )


def best_quote(frame: IssueFrame, hit: SearchHit) -> str:
    terms = set(
        tokens(frame.claim_text + " " + frame.critique + " " + " ".join(frame.what_would_help))
    )
    attribute_terms = evidence_attribute_terms(frame)
    candidates = _quote_candidates(hit.text)
    if not candidates:
        return hit.text[:280]

    def score(candidate: str) -> float:
        candidate_lower = candidate.lower()
        term_score = sum(1 for term in terms if term in candidate_lower)
        attribute_score = sum(1 for term in attribute_terms if term in candidate_lower) * 3
        marker_score = sum(
            1 for marker in SUPPORT_MARKERS | LIMIT_MARKERS if marker in candidate_lower
        )
        number_score = 1 if re.search(r"\d", candidate) else 0
        return attribute_score + term_score + marker_score + number_score

    chosen = max(candidates, key=score)
    return chosen if len(chosen) <= 360 else chosen[:357].rstrip() + "..."


def missing_evidence(frame: IssueFrame, hits: list[SearchHit]) -> list[str]:
    all_text = "\n".join(hit.text.lower() for hit in hits)
    missing: list[str] = []
    for requirement in frame.what_would_help:
        requirement_terms = [term for term in tokens(requirement) if len(term) > 3]
        if not requirement_terms:
            continue
        matched = sum(1 for term in requirement_terms if term in all_text)
        needed = 1 if len(requirement_terms) <= 2 else 2
        if matched < needed:
            missing.append(requirement)
    return unique_preserve_order(missing)


def aggregate_status(
    supporting: list[EvidenceCitation],
    contradicting: list[EvidenceCitation],
    missing: list[str],
    context_hits: int,
) -> EvidenceStatus:
    if contradicting:
        return "contradicted"
    if not supporting:
        return "unclear" if context_hits else "insufficient_evidence"
    if missing:
        return "partially_supported"
    return "supported"


def summarize_assessment(
    status: EvidenceStatus,
    supporting: list[EvidenceCitation],
    contradicting: list[EvidenceCitation],
    missing: list[str],
    context_hits: int,
) -> str:
    if status == "contradicted":
        return "The supplied evidence contains at least one quote that appears inconsistent with the claim or the Step 2 issue. Review recommended."
    if status == "supported":
        return "The supplied evidence appears to include quote-backed support for the Step 2 issue, subject to human review."
    if status == "partially_supported":
        return (
            "The supplied evidence appears to support part of the Step 2 issue, but material substantiation gaps remain: "
            + "; ".join(missing[:5])
            + "."
        )
    if status == "unclear":
        return f"Qiro found {context_hits} related passage(s), but they do not clearly substantiate the Step 2 issue. Review recommended."
    return "No meaningful quote-backed support was found in the supplied evidence pack."


def relevance_text(relation: EvidenceRelation) -> str:
    return {
        "supports": "May support one or more facts relevant to the Step 2 issue.",
        "limits": "May limit or qualify the claim rather than fully substantiate it.",
        "contradicts": "May contradict the claim or a material implied impression.",
        "context": "Provides context but not direct substantiation.",
        "irrelevant": "Not relevant to the Step 2 issue.",
    }[relation]


def _quote_candidates(text: str) -> list[str]:
    lines = [line.strip() for line in re.split(r"\n+", text) if line.strip()]
    sentences: list[str] = []
    for line in lines:
        sentences.extend(part.strip() for part in re.split(r"(?<=[.!?])\s+", line) if part.strip())
    return [candidate for candidate in sentences if len(candidate) >= 30] or lines


def _status_after_verification(assessment: Step3Assessment) -> EvidenceStatus:
    if assessment.contradicting_evidence:
        return "contradicted"
    if assessment.supporting_evidence and assessment.missing_evidence:
        return "partially_supported"
    if assessment.supporting_evidence:
        return "supported"
    if assessment.status in {"not_applicable", "unclear"}:
        return assessment.status
    return "insufficient_evidence"
