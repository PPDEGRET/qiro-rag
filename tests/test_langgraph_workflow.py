import json
from pathlib import Path

import pytest

from qiro_rag.assess import assess_finding, load_step2_finding
from qiro_rag.cli import app
from qiro_rag.ingest import ingest_path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "examples" / "synthetic_eval"


def test_langgraph_workflow_matches_direct_synthetic_eval(tmp_path: Path) -> None:
    pytest.importorskip("langgraph")
    from qiro_rag.workflows.langgraph_assess import run_langgraph_assessment

    pack = tmp_path / "pack"
    ingest_path(EVAL / "docs", pack, reset=True)
    expected = json.loads((EVAL / "expected_statuses.json").read_text(encoding="utf-8"))

    for name, status in expected.items():
        finding = load_step2_finding(EVAL / "findings" / f"{name}.json")
        direct = assess_finding(finding, pack).assessment
        result = run_langgraph_assessment(finding, pack)
        assessment = result.package.assessment

        assert assessment.status == status, name
        assert assessment.status == direct.status, name
        assert result.trace[-1] == {"node": "finalize_status", "status": status}
        for citation in assessment.supporting_evidence + assessment.contradicting_evidence:
            assert citation.verified is True


def test_cli_langgraph_workflow_writes_trace(tmp_path: Path) -> None:
    pytest.importorskip("langgraph")
    from typer.testing import CliRunner

    pack = tmp_path / "pack"
    out = tmp_path / "step3.json"
    trace = tmp_path / "trace.json"
    ingest_path(EVAL / "docs", pack, reset=True)

    result = CliRunner().invoke(
        app,
        [
            "assess",
            str(EVAL / "findings" / "carbon.json"),
            "--pack",
            str(pack),
            "--out",
            str(out),
            "--workflow",
            "langgraph",
            "--trace-out",
            str(trace),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "partially_supported"
    assert json.loads(trace.read_text(encoding="utf-8"))[-1] == {
        "node": "finalize_status",
        "status": "partially_supported",
    }
