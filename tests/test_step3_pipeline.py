import json
from pathlib import Path

from qiro_rag.assess import assess_finding, best_quote, classify_hit
from qiro_rag.framing import build_issue_frame
from qiro_rag.index import EvidenceIndex
from qiro_rag.ingest import ingest_path
from qiro_rag.learning import make_review_decision, propose_playbook_patch, record_review_decision
from qiro_rag.retrieval import retrieve
from qiro_rag.schemas import SearchHit, Step2Finding


def test_ingest_retrieve_and_assess_carbon_claim(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "offset-certificate.md").write_text(
        "# Carbon offset certificate\n\n"
        "Product: Parcel delivery service EU.\n\n"
        "Certificate covers 120 tCO2e retired for 2025 parcel delivery operations.\n\n"
        "The calculation methodology uses shipment weight and distance data.\n",
        encoding="utf-8",
    )
    (docs / "brand-policy.txt").write_text(
        "Our company aims to become climate positive in the future.", encoding="utf-8"
    )

    summary = ingest_path(docs, pack, reset=True)

    assert summary.indexed_documents == 2
    assert EvidenceIndex(pack).document_count() == 2
    assert "offset_documentation" in (pack / "manifest.csv").read_text(encoding="utf-8")

    hits = retrieve(EvidenceIndex(pack), ["carbon neutral delivery offset calculation"], top_k=3)
    assert hits
    assert "120 tCO2e" in hits[0].text

    finding = Step2Finding(
        claimId="claim-carbon-neutral-delivery",
        claimText="Our delivery is carbon neutral.",
        consumerImpression="The service has no net climate impact.",
        critique="Absolute climate claim lacks clear basis, scope, and compensation disclosure.",
        ruleRefs=["EmpCo climate-related environmental claims"],
        needsEvidenceCheck=True,
    )
    package = assess_finding(finding, pack, top_k=8)
    assessment = package.assessment

    assert assessment.status in {"supported", "partially_supported"}
    assert assessment.supporting_evidence
    assert assessment.supporting_evidence[0].verified is True
    assert "120 tCO2e" in assessment.supporting_evidence[0].quote
    assert assessment.missing_evidence


def test_assess_contradiction(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "recycling-note.md").write_text(
        "# Recycling note\n\nThe mailer is not recyclable in municipal EU recycling streams.\n",
        encoding="utf-8",
    )
    ingest_path(docs, pack, reset=True)

    finding = Step2Finding(
        claimId="claim-recyclable-mailer",
        claimText="Our mailer is recyclable.",
        critique="The claim may be too broad if recyclability depends on collection systems.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    assessment = assess_finding(finding, pack, top_k=5).assessment

    assert assessment.status == "contradicted"
    assert assessment.contradicting_evidence
    assert assessment.contradicting_evidence[0].verified is True


def test_recycled_content_does_not_trigger_recyclability_lens() -> None:
    finding = Step2Finding(
        claimId="claim-recycled-content",
        claimText="Our mailer contains recycled content.",
        critique="The claim needs product-specific recycled-content evidence.",
        ruleRefs=["EmpCo substantiation requirements"],
    )

    frame = build_issue_frame(finding)

    assert (
        "bill of materials or product specification with recycled-content percentage"
        in frame.what_would_help
    )
    assert (
        "recycling compatibility for labels adhesives coatings and mixed materials"
        not in frame.what_would_help
    )


def test_unrelated_contradiction_is_ignored(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "offset.md").write_text(
        "Certificate covers 120 tCO2e retired for 2025 parcel delivery operations.",
        encoding="utf-8",
    )
    (docs / "recycling-lab.md").write_text(
        "The adhesive does not meet the recycling compatibility threshold in this test.",
        encoding="utf-8",
    )
    ingest_path(docs, pack, reset=True)

    finding = Step2Finding(
        claimId="claim-carbon-neutral-delivery",
        claimText="Our delivery is carbon neutral.",
        critique="Absolute climate claim lacks clear basis, scope, and compensation disclosure.",
        ruleRefs=["EmpCo climate-related environmental claims"],
    )
    assessment = assess_finding(finding, pack, top_k=10).assessment

    assert assessment.status != "contradicted"
    assert not assessment.contradicting_evidence


def test_product_name_overlap_alone_is_not_relevant() -> None:
    finding = Step2Finding(
        claimId="claim-compostable",
        claimText="ReBox Mailer is compostable at home.",
        critique="Compostability claim needs product-specific test conditions.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    frame = build_issue_frame(finding)
    hit = SearchHit(
        chunk_id="x",
        doc_id="d",
        path="raw/spec.docx",
        text="The ReBox Mailer contains 82% post-consumer recycled PET.",
        score=1,
    )

    assert classify_hit(frame, hit) == "irrelevant"


def test_non_evidence_detected_type_is_context_not_path_spaghetti() -> None:
    finding = Step2Finding(
        claimId="claim-recycled",
        claimText="ReBox Mailer contains 82% post-consumer recycled PET.",
        critique="The claim needs product-specific recycled-content evidence.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    frame = build_issue_frame(finding)
    hit = SearchHit(
        chunk_id="x",
        doc_id="d",
        path="raw/anything.txt",
        text="Campaign draft claims: ReBox Mailer contains 82% post-consumer recycled PET.",
        detected_type="marketing_draft",
        score=1,
    )

    assert classify_hit(frame, hit) == "context"


def test_relation_uses_selected_quote_not_unrelated_sentence() -> None:
    finding = Step2Finding(
        claimId="claim-recycled",
        claimText="ReBox Mailer contains 82% post-consumer recycled PET.",
        critique="The claim needs product-specific recycled-content evidence.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    frame = build_issue_frame(finding)
    hit = SearchHit(
        chunk_id="x",
        doc_id="d",
        path="raw/spec.docx",
        text=(
            "The sold ReBox Mailer RB-1 contains 82% post-consumer recycled PET. "
            "Recyclability depends on local PE film collection and sorting availability."
        ),
        score=1,
    )

    assert classify_hit(frame, hit) == "supports"


def test_best_quote_prefers_active_evidence_attribute() -> None:
    finding = Step2Finding(
        claimId="claim-recyclable",
        claimText="ReBox Mailer is recyclable across Europe.",
        critique="The claim may be too broad if recyclability depends on collection systems.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    frame = build_issue_frame(finding)
    hit = SearchHit(
        chunk_id="x",
        doc_id="d",
        path="raw/spec.docx",
        text=(
            "The sold ReBox Mailer RB-1 contains 82% post-consumer recycled PET. "
            "Recyclability depends on local PE film collection and sorting availability."
        ),
        score=1,
    )

    assert best_quote(frame, hit).startswith("Recyclability depends")


def test_review_decisions_generate_playbook_patch(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    record_review_decision(
        pack,
        make_review_decision(
            claim_id="C-1",
            doc_id="DOC-1",
            quote="The mailer contains 82% post-consumer recycled PET.",
            status="supports",
            human_decision="accepted",
            reason="Product-specific supplier certificate.",
        ),
    )
    record_review_decision(
        pack,
        make_review_decision(
            claim_id="C-2",
            doc_id="DOC-2",
            quote="We aim to use more recycled content in future.",
            status="limits",
            human_decision="rejected",
            reason="Aspirational and not product-specific.",
        ),
    )

    output = tmp_path / "playbook.patch.yaml"
    text = propose_playbook_patch(pack / "review_decisions.csv", output)

    assert output.exists()
    assert "accepted_evidence_examples" in text
    assert "rejected_evidence_patterns" in text
    assert "post-consumer" in text


def test_assessment_output_json_shape(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    pack = tmp_path / "pack"
    docs.mkdir()
    (docs / "spec.csv").write_text(
        "sku,recycled_content\nMAILER-1,82% post-consumer recycled PET\n",
        encoding="utf-8",
    )
    ingest_path(docs, pack, reset=True)
    finding = Step2Finding(
        claimId="claim-recycled-content",
        claimText="Our mailer uses recycled content.",
        critique="The claim needs product-specific recycled-content evidence.",
        ruleRefs=["EmpCo substantiation requirements"],
    )
    assessment = assess_finding(finding, pack).assessment
    dumped = assessment.model_dump(by_alias=True)

    assert json.loads(json.dumps(dumped))["claimId"] == "claim-recycled-content"
    assert "supportingEvidence" in dumped
