"""Optional LangGraph orchestration for Step 3 assessment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from qiro_rag.assess import (
    align_model_citations,
    finalize_verified_assessment,
    judge_evidence,
    verify_assessment_quotes,
)
from qiro_rag.framing import build_issue_frame, evidence_queries
from qiro_rag.index import EvidenceIndex
from qiro_rag.retrieval import retrieve
from qiro_rag.schemas import (
    IssueFrame,
    JudgeMode,
    RetrievalMode,
    SearchHit,
    Step2Finding,
    Step3Assessment,
    Step3ReviewPackage,
)

TraceEvent = dict[str, object]


class AssessGraphState(TypedDict, total=False):
    finding: Step2Finding
    pack_path: str
    retrieval_mode: RetrievalMode
    top_k: int
    judge: JudgeMode
    judge_model: str | None
    issue_frame: IssueFrame
    retrieval_queries: list[str]
    hits: list[SearchHit]
    draft_assessment: Step3Assessment
    aligned_assessment: Step3Assessment
    verified_assessment: Step3Assessment
    assessment: Step3Assessment
    trace: list[TraceEvent]


@dataclass(frozen=True)
class LangGraphAssessmentResult:
    package: Step3ReviewPackage
    trace: list[TraceEvent]


def assess_finding_langgraph(
    finding: Step2Finding,
    pack_path: Path,
    retrieval_mode: RetrievalMode = "hybrid",
    top_k: int = 10,
    judge: JudgeMode = "heuristic",
    judge_model: str | None = None,
) -> Step3ReviewPackage:
    return run_langgraph_assessment(
        finding,
        pack_path,
        retrieval_mode=retrieval_mode,
        top_k=top_k,
        judge=judge,
        judge_model=judge_model,
    ).package


def run_langgraph_assessment(
    finding: Step2Finding,
    pack_path: Path,
    retrieval_mode: RetrievalMode = "hybrid",
    top_k: int = 10,
    judge: JudgeMode = "heuristic",
    judge_model: str | None = None,
) -> LangGraphAssessmentResult:
    graph = _compile_graph()
    final_state: AssessGraphState = graph.invoke(
        {
            "finding": finding,
            "pack_path": str(pack_path),
            "retrieval_mode": retrieval_mode,
            "top_k": top_k,
            "judge": judge,
            "judge_model": judge_model,
            "trace": [],
        }
    )
    package = Step3ReviewPackage(
        issueFrame=final_state["issue_frame"],
        assessment=final_state["assessment"],
        retrievalMode=retrieval_mode,
    )
    return LangGraphAssessmentResult(package=package, trace=final_state.get("trace", []))


def write_trace(trace: list[TraceEvent], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_issue_frame_node(state: AssessGraphState) -> AssessGraphState:
    finding = state["finding"]
    frame = build_issue_frame(finding)
    update: AssessGraphState = {
        "issue_frame": frame,
        "trace": _trace(state, "build_issue_frame", claimId=finding.claim_id),
    }
    if not finding.needs_evidence_check:
        assessment = Step3Assessment(
            claimId=finding.claim_id,
            status="not_applicable",
            summary="Step 2 did not request an evidence check for this finding.",
            humanReviewRecommended=False,
        )
        update.update(
            {
                "draft_assessment": assessment,
                "aligned_assessment": assessment,
                "verified_assessment": assessment,
                "assessment": assessment,
            }
        )
    return update


def generate_queries_node(state: AssessGraphState) -> AssessGraphState:
    if _done(state):
        return {"retrieval_queries": [], "trace": _trace(state, "generate_queries", skipped=True)}
    queries = evidence_queries(state["issue_frame"])
    return {
        "retrieval_queries": queries,
        "trace": _trace(state, "generate_queries", queryCount=len(queries)),
    }


def retrieve_candidates_node(state: AssessGraphState) -> AssessGraphState:
    if _done(state):
        return {"hits": [], "trace": _trace(state, "retrieve_candidates", skipped=True)}
    hits = retrieve(
        EvidenceIndex(Path(state["pack_path"])),
        state["retrieval_queries"],
        mode=state["retrieval_mode"],
        top_k=state["top_k"],
    )
    return {"hits": hits, "trace": _trace(state, "retrieve_candidates", hitCount=len(hits))}


def judge_evidence_node(state: AssessGraphState) -> AssessGraphState:
    if _done(state):
        return {"trace": _trace(state, "judge_evidence", skipped=True)}
    frame = state["issue_frame"]
    hits = state["hits"]
    if state["judge"] == "heuristic":
        assessment = judge_evidence(frame, hits)
    else:
        from qiro_rag.llm_judge import client_from_mode, judge_with_llm

        assessment = judge_with_llm(
            frame, hits, client_from_mode(state["judge"], model=state.get("judge_model"))
        )
    return {
        "draft_assessment": assessment,
        "trace": _trace(state, "judge_evidence", judge=state["judge"], status=assessment.status),
    }


def align_model_citations_node(state: AssessGraphState) -> AssessGraphState:
    if _done(state):
        return {"trace": _trace(state, "align_model_citations", skipped=True)}
    assessment = state["draft_assessment"]
    if state["judge"] != "heuristic":
        assessment = align_model_citations(state["issue_frame"], state["hits"], assessment)
    return {
        "aligned_assessment": assessment,
        "trace": _trace(
            state,
            "align_model_citations",
            supportCount=len(assessment.supporting_evidence),
            contradictionCount=len(assessment.contradicting_evidence),
        ),
    }


def verify_quotes_node(state: AssessGraphState) -> AssessGraphState:
    if _done(state):
        return {"trace": _trace(state, "verify_quotes", skipped=True)}
    verified = verify_assessment_quotes(
        EvidenceIndex(Path(state["pack_path"])), state["aligned_assessment"]
    )
    return {
        "verified_assessment": verified,
        "trace": _trace(
            state,
            "verify_quotes",
            verifiedSupport=sum(1 for item in verified.supporting_evidence if item.verified),
            verifiedContradictions=sum(
                1 for item in verified.contradicting_evidence if item.verified
            ),
        ),
    }


def finalize_status_node(state: AssessGraphState) -> AssessGraphState:
    if _done(state):
        return {"trace": _trace(state, "finalize_status", status=state["assessment"].status)}
    assessment = finalize_verified_assessment(state["verified_assessment"])
    return {
        "assessment": assessment,
        "trace": _trace(state, "finalize_status", status=assessment.status),
    }


def _compile_graph() -> Any:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - exercised when extra is absent.
        raise RuntimeError(
            "LangGraph workflow dependencies are optional. Install with "
            "`uv sync --extra workflow` or `pip install 'qiro-rag[workflow]'`."
        ) from exc

    workflow = StateGraph(AssessGraphState)
    workflow.add_node("build_issue_frame", build_issue_frame_node)
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("retrieve_candidates", retrieve_candidates_node)
    workflow.add_node("judge_evidence", judge_evidence_node)
    workflow.add_node("align_model_citations", align_model_citations_node)
    workflow.add_node("verify_quotes", verify_quotes_node)
    workflow.add_node("finalize_status", finalize_status_node)
    workflow.add_edge(START, "build_issue_frame")
    workflow.add_edge("build_issue_frame", "generate_queries")
    workflow.add_edge("generate_queries", "retrieve_candidates")
    workflow.add_edge("retrieve_candidates", "judge_evidence")
    workflow.add_edge("judge_evidence", "align_model_citations")
    workflow.add_edge("align_model_citations", "verify_quotes")
    workflow.add_edge("verify_quotes", "finalize_status")
    workflow.add_edge("finalize_status", END)
    return workflow.compile()


def _done(state: AssessGraphState) -> bool:
    return state.get("assessment") is not None


def _trace(state: AssessGraphState, node: str, **data: object) -> list[TraceEvent]:
    return [*state.get("trace", []), {"node": node, **data}]
