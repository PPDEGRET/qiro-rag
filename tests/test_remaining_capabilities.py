import json
from pathlib import Path

from qiro_rag.assess import assess_finding
from qiro_rag.connectors import pull_source
from qiro_rag.embeddings import build_embedding_index
from qiro_rag.index import EvidenceIndex
from qiro_rag.ingest import ingest_path
from qiro_rag.llm_judge import StaticJSONClient, judge_with_llm
from qiro_rag.parsing import parse_file
from qiro_rag.retrieval import retrieve
from qiro_rag.schemas import Step2Finding


def test_persisted_hash_embeddings_are_used_for_semantic_retrieval(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "recycling.md").write_text(
        "The mailer is recyclable where PE film collection exists.", encoding="utf-8"
    )
    (docs / "carbon.md").write_text(
        "Certificate covers 120 tCO2e retired for 2025 delivery operations.", encoding="utf-8"
    )
    ingest_path(docs, pack, reset=True)
    index = EvidenceIndex(pack)

    count = build_embedding_index(index, backend="hash", dimensions=64)
    hits = retrieve(
        index, ["delivery emissions compensation certificate"], mode="semantic", top_k=1
    )

    assert count == 2
    assert index.embedding_count("hash") == 2
    assert hits
    assert "tCO2e" in hits[0].text


def test_llm_judge_partitions_misplaced_contradictions(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    quote = "The mailer is not compostable at home under the tested conditions."
    (docs / "compostability.md").write_text(quote, encoding="utf-8")
    ingest_path(docs, pack, reset=True)
    finding = Step2Finding(
        claimId="C-COMPOST",
        claimText="The mailer is compostable at home.",
        critique="Compostability claim needs product-specific test conditions.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    frame = assess_finding(finding, pack, top_k=4).issue_frame
    hits = retrieve(EvidenceIndex(pack), ["compostable at home tested conditions"], top_k=4)
    response = json.dumps(
        {
            "status": "supported",
            "summary": "Bad model bucketed contradiction as support.",
            "supportingEvidence": [
                {
                    "chunkId": hits[0].chunk_id,
                    "quote": quote,
                    "relation": "contradicts",
                    "relevance": "Contradicts home compostability.",
                }
            ],
            "contradictingEvidence": [],
            "missingEvidence": [],
            "humanReviewRecommended": True,
        }
    )

    assessment = judge_with_llm(frame, hits, StaticJSONClient(response))

    assert not assessment.supporting_evidence
    assert assessment.contradicting_evidence


def test_llm_judge_uses_quote_backed_candidate_payload(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    quote = "Certificate covers 120 tCO2e retired for 2025 parcel delivery operations."
    (docs / "offset.md").write_text(quote, encoding="utf-8")
    ingest_path(docs, pack, reset=True)
    finding = Step2Finding(
        claimId="C-CARBON",
        claimText="Our delivery is carbon neutral.",
        critique="Absolute climate claim lacks clear basis, scope, and compensation disclosure.",
        ruleRefs=["EmpCo climate-related environmental claims"],
    )
    heuristic_package = assess_finding(finding, pack, top_k=4)
    frame = heuristic_package.issue_frame
    hits = retrieve(EvidenceIndex(pack), ["carbon neutral delivery certificate"], top_k=4)
    response = json.dumps(
        {
            "status": "partially_supported",
            "summary": "Offset evidence may support compensation volume, but scope gaps remain.",
            "supportingEvidence": [
                {
                    "chunkId": hits[0].chunk_id,
                    "quote": quote,
                    "relation": "supports",
                    "relevance": "May support compensation volume for the delivery claim.",
                }
            ],
            "contradictingEvidence": [],
            "missingEvidence": ["calculation methodology"],
            "humanReviewRecommended": False,
        }
    )

    assessment = judge_with_llm(frame, hits, StaticJSONClient(response))

    assert assessment.status == "partially_supported"
    assert assessment.supporting_evidence[0].quote == quote
    assert assessment.human_review_recommended is True


def test_assess_openai_like_judge_verifies_and_keeps_exact_quote(
    tmp_path: Path, monkeypatch
) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    quote = "The mailer contains 82% post-consumer recycled PET."
    (docs / "spec.md").write_text(quote, encoding="utf-8")
    ingest_path(docs, pack, reset=True)
    finding = Step2Finding(
        claimId="C-REC",
        claimText="Our mailer contains recycled content.",
        critique="The claim needs product-specific recycled-content evidence.",
        ruleRefs=["EmpCo substantiation requirements"],
    )

    class FakeClient:
        def complete(self, system: str, user: str) -> str:  # noqa: ARG002
            chunk_id = json.loads(user)["candidatePassages"][0]["chunkId"]
            return json.dumps(
                {
                    "status": "supported",
                    "summary": "The source quote may support recycled-content wording.",
                    "supportingEvidence": [
                        {
                            "chunkId": chunk_id,
                            "quote": quote,
                            "relation": "contradicts",
                            "relevance": "Bad model label for product-specific recycled-content evidence.",
                        }
                    ],
                    "contradictingEvidence": [],
                    "missingEvidence": [],
                    "humanReviewRecommended": True,
                }
            )

    monkeypatch.setattr(
        "qiro_rag.llm_judge.client_from_mode", lambda mode, model=None: FakeClient()
    )

    assessment = assess_finding(finding, pack, judge="openai").assessment

    assert assessment.status == "supported"
    assert assessment.supporting_evidence[0].verified is True


def test_image_ocr_parser_is_optional_and_chunked(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"not a real image; OCR is monkeypatched")
    seen = []

    def fake_ocr(image_or_path):
        seen.append(image_or_path)
        return "Scanned certificate states the product is recyclable."

    monkeypatch.setattr("qiro_rag.parsing._ocr_image", fake_ocr)

    parsed = parse_file(image, doc_id="DOC-OCR", stored_path="raw/scan.png", parser="ocr")

    assert parsed.parser == "image-ocr"
    assert parsed.chunks
    assert "recyclable" in parsed.chunks[0].text
    assert seen == [image]


def test_local_and_manifest_connectors_stage_supported_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "evidence.md").write_text("Product evidence", encoding="utf-8")
    (source / "ignore.exe").write_text("no", encoding="utf-8")
    target = tmp_path / "stage"

    summary = pull_source(str(source), target)

    assert summary.downloaded == 1
    assert (target / "evidence.md").exists()
    assert summary.skipped

    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        f"path,target\n{source / 'evidence.md'},copied/evidence.md\n", encoding="utf-8"
    )
    target2 = tmp_path / "stage2"

    summary2 = pull_source(f"manifest://{manifest}", target2)

    assert summary2.downloaded == 1
    assert (target2 / "copied" / "evidence.md").exists()
