"""Human-review memory and playbook proposal helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from qiro_rag.manifest import append_review_decision, read_review_decisions
from qiro_rag.schemas import ReviewDecision
from qiro_rag.utils import tokens


def record_review_decision(pack_path: Path, decision: ReviewDecision) -> None:
    append_review_decision(pack_path / "review_decisions.csv", decision)


def make_review_decision(
    claim_id: str,
    doc_id: str,
    quote: str,
    status: str,
    human_decision: str,
    reason: str,
) -> ReviewDecision:
    return ReviewDecision(
        claim_id=claim_id,
        doc_id=doc_id,
        quote=quote,
        status=status,  # type: ignore[arg-type]
        human_decision=human_decision,  # type: ignore[arg-type]
        reason=reason,
        created_at=datetime.now(UTC).date().isoformat(),
    )


def propose_playbook_patch(decisions_path: Path, output_path: Path) -> str:
    rows = read_review_decisions(decisions_path)
    accepted = [row for row in rows if row.get("human_decision") == "accepted"]
    rejected = [row for row in rows if row.get("human_decision") == "rejected"]

    accepted_by_status: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in accepted:
        accepted_by_status[row.get("status", "context")].append(row)

    rejected_terms = Counter(
        token
        for row in rejected
        for token in tokens(" ".join([row.get("quote", ""), row.get("reason", "")]))
    )
    accepted_terms = Counter(
        token
        for row in accepted
        for token in tokens(" ".join([row.get("quote", ""), row.get("reason", "")]))
    )

    lines = [
        "# Proposed Qiro RAG playbook patch",
        "# Human review required before applying.",
        "",
        "accepted_evidence_examples:",
    ]
    if accepted:
        for status, status_rows in sorted(accepted_by_status.items()):
            lines.append(f"  {status}:")
            for row in status_rows[:5]:
                quote = _yaml_quote(row.get("quote", ""))
                reason = _yaml_quote(row.get("reason", ""))
                lines.append(f"    - claim_id: {_yaml_quote(row.get('claim_id', ''))}")
                lines.append(f"      doc_id: {_yaml_quote(row.get('doc_id', ''))}")
                lines.append(f"      quote: {quote}")
                lines.append(f"      reason: {reason}")
    else:
        lines.append("  []")

    lines.extend(["", "rejected_evidence_patterns:"])
    if rejected:
        lines.append("  common_terms:")
        for term, count in rejected_terms.most_common(12):
            lines.append(f"    - term: {_yaml_quote(term)}")
            lines.append(f"      count: {count}")
    else:
        lines.append("  []")

    lines.extend(["", "candidate_synonyms_or_markers:"])
    candidates = [term for term, _ in accepted_terms.most_common(16) if term not in rejected_terms]
    if candidates:
        for term in candidates:
            lines.append(f"  - {_yaml_quote(term)}")
    else:
        lines.append("  []")

    lines.extend(
        [
            "",
            "notes:",
            "  - This file is a proposal generated from reviewer decisions.",
            "  - Do not apply automatically; convert accepted items into versioned playbook tests/examples.",
        ]
    )
    text = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return text


def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
