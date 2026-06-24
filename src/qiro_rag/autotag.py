"""Local document role detection.

This is deliberately heuristic and local. It tags the manifest; it does not make
compliance decisions.
"""

from __future__ import annotations

import re
from pathlib import Path

from qiro_rag.utils import normalize_ws

TYPE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("marketing_draft", ("campaign draft claims", "draft claims", "marketing draft")),
    ("invoice_or_admin", ("invoice", "receipt", "purchase order")),
    ("certificate", ("certificate", "certification", "certified", "certificate of")),
    ("supplier_declaration", ("supplier declaration", "supplier", "declaration of conformity")),
    ("lab_test", ("lab test", "test report", "laboratory", "iso ", "en 13432", "astm")),
    ("lca_or_epd", ("life cycle assessment", "lca", "environmental product declaration", "epd")),
    ("ghg_inventory", ("ghg inventory", "greenhouse gas", "scope 1", "scope 2", "scope 3")),
    ("offset_documentation", ("offset", "carbon credit", "retired", "retirement", "vcus")),
    ("recycling_guidance", ("recyclable", "recycling", "collection", "sorting stream")),
    ("packaging_bom", ("bill of materials", "bom", "packaging components", "material list")),
    ("product_specification", ("product specification", "technical specification", "spec sheet")),
    ("marketing_approval_note", ("marketing approval", "claim approval", "approved wording")),
    ("policy_or_transition_plan", ("transition plan", "policy", "roadmap", "net zero plan")),
    ("sustainability_report", ("sustainability report", "annual sustainability", "esg report")),
]

MARKET_PATTERNS = {
    "EU": r"\b(EU|European Union|Europe)\b",
    "UK": r"\b(UK|United Kingdom|Great Britain)\b",
    "US": r"\b(US|USA|United States)\b",
}


def detect_language(text: str) -> str:
    sample = text[:3000].lower()
    common_en = sum(
        sample.count(word) for word in (" the ", " and ", " for ", " with ", " product ")
    )
    if common_en >= 2 or sample.isascii():
        return "en"
    return "unknown"


def detect_market(text: str) -> str:
    for market, pattern in MARKET_PATTERNS.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            return market
    return ""


def detect_date(text: str) -> str:
    match = re.search(
        r"\b(20\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])|20\d{2})\b", text
    )
    return match.group(1) if match else ""


def detect_document_type(path: Path, text: str) -> tuple[str, float]:
    haystack = f"{path.as_posix()}\n{normalize_ws(text[:5000])}".lower()
    best_type = "unknown"
    best_score = 0
    for doc_type, patterns in TYPE_PATTERNS:
        score = sum(1 for pattern in patterns if pattern in haystack)
        if score > best_score:
            best_type = doc_type
            best_score = score
    if best_score == 0:
        return "unknown", 0.25
    return best_type, min(0.95, 0.55 + best_score * 0.15)


def detect_product_hint(path: Path, text: str) -> str:
    for pattern in (
        r"\b(?:product|sku|item)\s*[:#-]\s*([A-Za-z0-9][A-Za-z0-9 _.-]{2,60})",
        r"\b(?:mailer|bottle|packaging|delivery|bag|box)\s+[A-Za-z0-9][A-Za-z0-9 _.-]{1,40}",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_ws(match.group(1) if match.groups() else match.group(0))[:80]
    return path.stem.replace("_", " ").replace("-", " ")[:80]


def tag_document(path: Path, text: str) -> dict[str, str | float]:
    doc_type, confidence = detect_document_type(path, text)
    return {
        "detected_type": doc_type,
        "language": detect_language(text),
        "product_hint": detect_product_hint(path, text),
        "market_hint": detect_market(text),
        "date_hint": detect_date(text),
        "confidence": confidence,
        "review_status": "auto_tagged" if confidence >= 0.7 else "needs_review",
    }
