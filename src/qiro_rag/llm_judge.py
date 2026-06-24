"""Hosted/local LLM judge for Step 3.

Cloud use is opt-in. OpenAI-compatible and Ollama calls use stdlib HTTP so the
core package stays small.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from qiro_rag.schemas import EvidenceCitation, IssueFrame, SearchHit, Step3Assessment

SYSTEM_PROMPT = """You are Qiro Step 3, a cautious substantiation review aid.
You do not give legal advice or legal verdicts.

Task:
Given a flagged environmental marketing claim, the Step 2 critique/law issue,
and retrieved company evidence passages, decide whether the passages potentially
support, partially support, contradict, or fail to substantiate the Step 2 issue.

Rules:
- Use only the supplied candidate passages.
- Every evidence item MUST include an exact quote copied from a candidate passage.
- If evidence supports facts but not the broad consumer impression, use partially_supported.
- If a quote is ambiguous, mark unclear or partially_supported and recommend human review.
- Be conservative about broad/generic claims.
- Output JSON only.
- Use actual chunkId values from candidatePassages. Never write placeholder ids.
- missingEvidence must be an array of short strings, not objects.
"""


class ChatClient(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Return model text."""


@dataclass
class OpenAICompatibleClient:
    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 60

    @classmethod
    def from_env(cls, model: str | None = None) -> OpenAICompatibleClient:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for --judge openai.")
        return cls(
            model=model or os.environ.get("OPENAI_MODEL", "gemini-2.5-flash"),
            api_key=api_key,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        )

    def complete(self, system: str, user: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return _read_chat_response(request, self.timeout)


@dataclass
class OllamaClient:
    model: str = "qwen2.5:1.5b"
    base_url: str = "http://localhost:11434"
    timeout: int = 120

    @classmethod
    def from_env(cls, model: str | None = None) -> OllamaClient:
        return cls(
            model=model or os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        )

    def complete(self, system: str, user: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - explicit local/opt-in URL
            body = json.loads(response.read().decode("utf-8"))
        return str(body.get("message", {}).get("content", ""))


@dataclass
class StaticJSONClient:
    """Test helper for deterministic LLM judge tests."""

    response: str

    def complete(self, system: str, user: str) -> str:  # noqa: ARG002
        return self.response


def client_from_mode(mode: str, model: str | None = None) -> ChatClient:
    if mode == "openai":
        return OpenAICompatibleClient.from_env(model=model)
    if mode == "ollama":
        return OllamaClient.from_env(model=model)
    raise ValueError(f"Unsupported LLM judge mode: {mode}")


def judge_with_llm(frame: IssueFrame, hits: list[SearchHit], client: ChatClient) -> Step3Assessment:
    prompt = build_user_prompt(frame, hits)
    raw = client.complete(SYSTEM_PROMPT, prompt)
    payload = parse_json_object(raw)
    return assessment_from_payload(frame, hits, payload)


def build_user_prompt(frame: IssueFrame, hits: list[SearchHit]) -> str:
    candidates = []
    for hit in hits:
        candidates.append(
            {
                "chunkId": hit.chunk_id,
                "docId": hit.doc_id,
                "path": hit.path,
                "page": hit.page,
                "sheet": hit.sheet,
                "section": hit.section,
                "text": hit.text[:2200],
            }
        )
    return json.dumps(
        {
            "claim": frame.claim_text,
            "critique": frame.critique,
            "ruleRefs": frame.rule_refs,
            "whatWouldHelp": frame.what_would_help,
            "whatWouldNotBeEnough": frame.what_would_not_be_enough,
            "openQuestions": frame.open_questions,
            "candidatePassages": candidates,
            "important": [
                "Use only chunkId values present in candidatePassages.",
                "Copy quotes exactly from candidate text.",
                "Do not put evidence objects inside missingEvidence.",
            ],
            "requiredOutputShape": {
                "status": "supported | partially_supported | contradicted | insufficient_evidence | unclear | not_applicable",
                "summary": "short cautious review summary",
                "supportingEvidence": [
                    {
                        "chunkId": "candidate chunkId",
                        "quote": "exact quote from candidate text",
                        "relation": "supports | limits | context",
                        "relevance": "why this matters to the Step 2 issue",
                    }
                ],
                "contradictingEvidence": [
                    {
                        "chunkId": "candidate chunkId",
                        "quote": "exact quote from candidate text",
                        "relation": "contradicts",
                        "relevance": "why this may contradict the claim",
                    }
                ],
                "missingEvidence": ["remaining substantiation gaps"],
                "humanReviewRecommended": True,
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def parse_json_object(text: str) -> dict[str, object]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        loaded = json.loads(match.group(0))
    if not isinstance(loaded, dict):
        raise ValueError("LLM judge did not return a JSON object.")
    return loaded


def assessment_from_payload(
    frame: IssueFrame, hits: list[SearchHit], payload: dict[str, object]
) -> Step3Assessment:
    hit_by_id = {hit.chunk_id: hit for hit in hits}
    supporting = _citations_from_payload(payload.get("supportingEvidence"), hit_by_id)
    contradicting = _citations_from_payload(payload.get("contradictingEvidence"), hit_by_id)
    missing = payload.get("missingEvidence")
    if isinstance(missing, list):
        missing_list = [str(item) for item in missing if not isinstance(item, dict)]
    else:
        missing_list = frame.what_would_help
    status = str(payload.get("status", "unclear"))
    if status not in {
        "supported",
        "partially_supported",
        "contradicted",
        "insufficient_evidence",
        "unclear",
        "not_applicable",
    }:
        status = "unclear"
    summary = str(
        payload.get("summary") or "LLM judge returned an evidence assessment. Review recommended."
    )
    if not supporting and not contradicting:
        supporting = _citations_from_payload(payload.get("evidence"), hit_by_id)
    supporting, misplaced_contradictions = _partition_citations(supporting)
    misplaced_support, contradicting = _partition_citations(contradicting)
    supporting.extend(misplaced_support)
    contradicting.extend(misplaced_contradictions)
    return Step3Assessment(
        claimId=frame.claim_id,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        supportingEvidence=supporting,
        contradictingEvidence=contradicting,
        missingEvidence=missing_list,
        humanReviewRecommended=True,
    )


def _partition_citations(
    citations: list[EvidenceCitation],
) -> tuple[list[EvidenceCitation], list[EvidenceCitation]]:
    supporting: list[EvidenceCitation] = []
    contradicting: list[EvidenceCitation] = []
    for citation in citations:
        if citation.relation == "contradicts":
            contradicting.append(citation)
        else:
            supporting.append(citation)
    return supporting, contradicting


def _citations_from_payload(
    value: object, hit_by_id: dict[str, SearchHit]
) -> list[EvidenceCitation]:
    if not isinstance(value, list):
        return []
    citations: list[EvidenceCitation] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunkId", ""))
        hit = hit_by_id.get(chunk_id)
        if not hit:
            hit = _hit_containing_quote(str(item.get("quote", "")), hit_by_id)
        if not hit:
            continue
        relation = str(item.get("relation", "context"))
        if relation not in {"supports", "limits", "contradicts", "context", "irrelevant"}:
            relation = "context"
        citations.append(
            EvidenceCitation(
                docId=hit.doc_id,
                path=hit.path,
                chunkId=hit.chunk_id,
                page=hit.page,
                sheet=hit.sheet,
                section=hit.section,
                quote=str(item.get("quote", "")),
                relation=relation,  # type: ignore[arg-type]
                relevance=str(item.get("relevance", "Potentially relevant to the Step 2 issue.")),
            )
        )
    return citations


def _hit_containing_quote(quote: str, hit_by_id: dict[str, SearchHit]) -> SearchHit | None:
    quote = quote.strip().lower()
    if not quote:
        return None
    return next((hit for hit in hit_by_id.values() if quote in hit.text.lower()), None)


def _read_chat_response(request: urllib.request.Request, timeout: int) -> str:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit opt-in URL
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM judge request failed: HTTP {exc.code}: {detail}") from exc
    return str(body.get("choices", [{}])[0].get("message", {}).get("content", ""))
