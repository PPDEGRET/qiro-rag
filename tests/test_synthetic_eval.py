import json
from pathlib import Path

from qiro_rag.assess import assess_finding, load_step2_finding
from qiro_rag.ingest import ingest_path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "examples" / "synthetic_eval"


def test_synthetic_eval_expected_statuses(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    ingest_path(EVAL / "docs", pack, reset=True)
    expected = json.loads((EVAL / "expected_statuses.json").read_text(encoding="utf-8"))

    for name, status in expected.items():
        finding = load_step2_finding(EVAL / "findings" / f"{name}.json")
        assessment = assess_finding(finding, pack).assessment
        assert assessment.status == status, name
        for citation in assessment.supporting_evidence + assessment.contradicting_evidence:
            assert citation.verified is True
