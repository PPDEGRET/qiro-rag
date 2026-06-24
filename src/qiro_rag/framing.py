"""Build flexible issue frames from Step 2 findings."""

from __future__ import annotations

from qiro_rag.evidence_lenses import DEFAULT_HELP, DEFAULT_NOT_ENOUGH, lenses_for_text
from qiro_rag.schemas import IssueFrame, Step2Finding
from qiro_rag.utils import unique_preserve_order


def build_issue_frame(finding: Step2Finding) -> IssueFrame:
    text = " ".join(
        [
            finding.claim_text,
            finding.critique,
            finding.consumer_impression or "",
            " ".join(finding.rule_refs),
        ]
    ).lower()
    help_items = list(DEFAULT_HELP)
    not_enough = list(DEFAULT_NOT_ENOUGH)
    matched_lenses = lenses_for_text(text)

    for lens in matched_lenses:
        help_items.extend(lens.help_prompts)
        not_enough.extend(lens.insufficient_prompts)

    open_questions = [
        "Does the evidence match the consumer-facing impression, not only the literal wording?",
        "Does the evidence cover the same product, market, and timeframe as the claim?",
    ]
    if text.count(" and ") + text.count(",") >= 2:
        open_questions.append(
            "The claim may combine several environmental ideas; check each implied impression separately."
        )
    if not matched_lenses:
        open_questions.append(
            "No existing evidence lens cleanly maps to this claim; reviewer should validate the generated evidence questions."
        )

    return IssueFrame(
        claimId=finding.claim_id,
        claimText=finding.claim_text,
        critique=finding.critique,
        ruleRefs=finding.rule_refs,
        whatWouldHelp=unique_preserve_order(help_items),
        whatWouldNotBeEnough=unique_preserve_order(not_enough),
        openQuestions=unique_preserve_order(open_questions),
    )


def evidence_queries(frame: IssueFrame) -> list[str]:
    queries = [frame.claim_text, frame.critique]
    queries.extend(frame.rule_refs)
    queries.extend(frame.what_would_help)
    return unique_preserve_order(queries)
