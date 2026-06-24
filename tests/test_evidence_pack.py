from pathlib import Path

from qiro_rag.evidence_pack import init_evidence_pack
from qiro_rag.schemas import EvidenceCitation, Step3Assessment


def test_init_evidence_pack_creates_base_files(tmp_path: Path) -> None:
    created = init_evidence_pack(tmp_path / "pack")

    assert {path.name for path in created} == {
        "manifest.csv",
        "review_decisions.csv",
        "ingestion_report.md",
    }
    assert (tmp_path / "pack" / "raw").is_dir()
    assert (tmp_path / "pack" / "index").is_dir()
    assert (
        (tmp_path / "pack" / "manifest.csv")
        .read_text(encoding="utf-8")
        .startswith("doc_id,path,sha256")
    )


def test_init_evidence_pack_does_not_overwrite_existing_manifest(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    manifest = pack / "manifest.csv"
    manifest.write_text("custom\n", encoding="utf-8")

    init_evidence_pack(pack)

    assert manifest.read_text(encoding="utf-8") == "custom\n"


def test_step3_assessment_serializes_with_public_aliases() -> None:
    assessment = Step3Assessment(
        claimId="C-001",
        status="partially_supported",
        summary="Evidence supports one factual element but leaves material gaps.",
        supportingEvidence=[
            EvidenceCitation(
                docId="DOC-001",
                path="raw/certificate.pdf",
                page=2,
                quote="The mailer contains 82% post-consumer recycled PET.",
                relevance="May support the recycled-content percentage.",
                relation="supports",
                verified=True,
            )
        ],
        missingEvidence=["market-specific recyclability evidence"],
    )

    dumped = assessment.model_dump(by_alias=True)

    assert dumped["claimId"] == "C-001"
    assert dumped["supportingEvidence"][0]["docId"] == "DOC-001"
    assert dumped["humanReviewRecommended"] is True
