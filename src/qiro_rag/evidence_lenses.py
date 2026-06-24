"""Shared evidence lenses for framing and assessment."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceLens:
    name: str
    keywords: tuple[str, ...]
    help_prompts: tuple[str, ...]
    insufficient_prompts: tuple[str, ...]
    attribute_terms: frozenset[str]


DEFAULT_HELP = (
    "evidence matching the exact product service or campaign",
    "scope boundaries and relevant exclusions",
    "date version and market coverage",
)

DEFAULT_NOT_ENOUGH = (
    "generic corporate policy without claim-specific support",
    "old or unaudited evidence with unclear scope",
    "evidence for a different product market or timeframe",
)

NON_EVIDENCE_DOCUMENT_TYPES = {"marketing_draft", "invoice_or_admin"}

EVIDENCE_LENSES = (
    EvidenceLens(
        name="compostability",
        keywords=("biodegradable", "compostable", "compost", "home compost"),
        help_prompts=(
            "recognized test standard and laboratory result",
            "environmental conditions required for degradation or composting",
            "timeframe for degradation or composting",
            "product-specific component coverage",
            "consumer disposal instructions and limits",
        ),
        insufficient_prompts=(
            "material family claim without test conditions",
            "industrial compostability evidence for a home-composting impression",
        ),
        attribute_terms=frozenset(
            {
                "compostable",
                "compostability",
                "compost",
                "home",
                "industrial",
                "tested",
                "conditions",
            }
        ),
    ),
    EvidenceLens(
        name="recycled_content",
        keywords=(
            "recycled content",
            "post-consumer",
            "post consumer",
            "pcr",
            "recycled pet",
            "recycled material",
        ),
        help_prompts=(
            "bill of materials or product specification with recycled-content percentage",
            "supplier certificate or declaration for the specific input material",
            "mass-balance or chain-of-custody basis if used",
            "date and product or SKU coverage",
        ),
        insufficient_prompts=(
            "corporate recycled-content target without product-specific data",
            "supplier marketing statement without percentage or scope",
        ),
        attribute_terms=frozenset(
            {
                "recycled",
                "post-consumer",
                "post",
                "consumer",
                "pcr",
                "pet",
                "percentage",
                "supplier",
                "certificate",
                "bom",
            }
        ),
    ),
    EvidenceLens(
        name="recyclability",
        keywords=("recyclable", "recycling", "recycle"),
        help_prompts=(
            "product-specific material and component specification",
            "recycling compatibility for labels adhesives coatings and mixed materials",
            "market-specific collection sorting and recycling availability",
            "conditions or exclusions that must be disclosed",
        ),
        insufficient_prompts=(
            "generic statement that the material family can be recycled",
            "supplier aspiration without evidence for the sold product",
        ),
        attribute_terms=frozenset(
            {
                "recyclable",
                "recyclability",
                "recycling",
                "collection",
                "sorting",
                "adhesive",
                "compatibility",
                "qualification",
                "qualified",
                "local",
            }
        ),
    ),
    EvidenceLens(
        name="climate_positive",
        keywords=("climate positive", "positive climate", "lifecycle", "lca"),
        help_prompts=(
            "lifecycle evidence covering relevant impact categories",
            "baseline product or scenario used for comparison",
            "methodology scope and exclusions",
            "evidence that the broad positive-impression claim is not overstated",
        ),
        insufficient_prompts=(
            "generic climate policy without product scope",
            "partial LCA draft excluding material lifecycle stages",
            "single impact improvement presented as overall climate-positive packaging",
        ),
        attribute_terms=frozenset(
            {
                "climate",
                "positive",
                "lifecycle",
                "lca",
                "impact",
                "baseline",
                "packaging",
                "end-of-life",
            }
        ),
    ),
    EvidenceLens(
        name="carbon_claim",
        keywords=("carbon neutral", "climate neutral", "net zero", "zero impact", "carbon"),
        help_prompts=(
            "emissions boundary and covered activities",
            "calculation methodology and data source",
            "timeframe covered by the claim",
            "reduction versus compensation or offset split",
            "offset retirement certificates and project quality where offsets are used",
            "consumer-facing disclosure basis",
        ),
        insufficient_prompts=(
            "generic climate policy without product or service scope",
            "offset purchase without emissions calculation boundary",
            "future target without current substantiation",
        ),
        attribute_terms=frozenset(
            {
                "carbon",
                "neutral",
                "emissions",
                "tco2e",
                "offset",
                "retired",
                "retirement",
                "delivery",
                "ghg",
                "compensation",
                "calculation",
            }
        ),
    ),
    EvidenceLens(
        name="comparison",
        keywords=("lower impact", "less", "reduced", "better", "more sustainable", "compared"),
        help_prompts=(
            "baseline product or scenario used for comparison",
            "methodology and impact category",
            "time period and geography",
            "evidence that the comparison is like-for-like",
        ),
        insufficient_prompts=(
            "comparison without baseline",
            "single impact improvement presented as overall environmental superiority",
        ),
        attribute_terms=frozenset(
            {"baseline", "comparison", "reduced", "less", "methodology", "impact"}
        ),
    ),
    EvidenceLens(
        name="generic_green",
        keywords=(
            "eco",
            "green",
            "sustainable",
            "environmentally friendly",
            "planet friendly",
            "responsible",
        ),
        help_prompts=(
            "specific environmental attribute behind the broad claim",
            "recognized excellent environmental performance where relevant",
            "scope limits and consumer-facing qualifications",
            "product-specific evidence rather than corporate-level policy only",
        ),
        insufficient_prompts=(
            "generic sustainability report",
            "aspirational brand values without substantiating facts",
        ),
        attribute_terms=frozenset(
            {"environmental", "sustainable", "green", "attribute", "scope", "qualification"}
        ),
    ),
)


def keyword_matches(text: str, keyword: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def lenses_for_text(text: str) -> list[EvidenceLens]:
    lowered = text.lower()
    return [
        lens
        for lens in EVIDENCE_LENSES
        if any(keyword_matches(lowered, keyword) for keyword in lens.keywords)
    ]


def attribute_terms_for_text(text: str) -> set[str]:
    terms: set[str] = set()
    for lens in lenses_for_text(text):
        terms.update(lens.attribute_terms)
    return terms
