"""Qiro RAG CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from qiro_rag.assess import assess_finding, load_step2_finding, write_assessment
from qiro_rag.connectors import pull_source
from qiro_rag.embeddings import build_embedding_index
from qiro_rag.evidence_pack import init_evidence_pack
from qiro_rag.index import EvidenceIndex
from qiro_rag.ingest import ingest_path
from qiro_rag.learning import make_review_decision, propose_playbook_patch, record_review_decision
from qiro_rag.model_profiles import assess_args, get_profile, profile_names, recommend_profile
from qiro_rag.retrieval import retrieve
from qiro_rag.schemas import EmbeddingBackend, JudgeMode, RetrievalMode, StorageMode

app = typer.Typer(
    help="Local-first evidence substantiation/RAG tools for Qiro Step 3.",
    no_args_is_help=True,
)


@app.command("init-pack")
def init_pack(
    path: Annotated[Path, typer.Argument(help="Evidence-pack directory to create.")],
) -> None:
    """Create the minimal evidence-pack layout."""

    created = init_evidence_pack(path)
    typer.echo(f"Evidence pack ready: {path}")
    if created:
        typer.echo("Created:")
        for file_path in created:
            typer.echo(f"- {file_path}")
    else:
        typer.echo("No files created; pack already had the base files.")


@app.command()
def pull(
    uri: Annotated[
        str,
        typer.Argument(
            help="Connector URI: local path, local://path, file://path, or manifest://file.csv."
        ),
    ],
    target: Annotated[Path, typer.Option(help="Local staging folder for pulled documents.")],
) -> None:
    """Pull connector files into a local staging folder."""

    summary = pull_source(uri, target)
    typer.echo(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))


@app.command()
def models(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
) -> None:
    """List recommended judge model profiles."""

    rows = [get_profile(name) for name in profile_names()]
    if json_output:
        typer.echo(json.dumps([row.__dict__ for row in rows], indent=2))
        return
    for row in rows:
        args = " ".join(assess_args(row))
        typer.echo(f"{row.name}: {args}")
        typer.echo(f"  privacy: {row.privacy}; cost: {row.cost}")
        typer.echo(f"  best for: {row.best_for}")
        typer.echo(f"  note: {row.notes}")


@app.command()
def onboard() -> None:
    """Ask a few questions and recommend a judge profile."""

    local_only = typer.confirm("Must evidence stay local/private by default?", default=True)
    no_llm = typer.confirm("Do you want no LLM at all for now?", default=False)
    cloud_allowed = (
        False
        if local_only
        else typer.confirm(
            "Can retrieved passages be sent to a hosted/private gateway model?", default=False
        )
    )
    hardware = "balanced"
    if not no_llm and (local_only or not cloud_allowed):
        hardware = typer.prompt(
            "Hardware size: small, balanced, or workstation", default="balanced"
        )
        if hardware not in {"small", "balanced", "workstation"}:
            hardware = "balanced"
    profile = recommend_profile(
        local_only=local_only,
        no_llm=no_llm,
        cloud_allowed=cloud_allowed,
        hardware=hardware,
    )
    args = " ".join(assess_args(profile))
    typer.echo("\nRecommended profile:")
    typer.echo(f"  {profile.name}")
    typer.echo(f"  {profile.notes}")
    typer.echo("\nUse:")
    typer.echo(
        f"  qiro-rag assess finding.json --pack evidence-pack --out step3.json --profile {profile.name}"
    )
    typer.echo("\nEquivalent flags:")
    typer.echo(f"  {args}")


@app.command()
def ingest(
    source: Annotated[Path, typer.Argument(help="File or folder containing evidence docs.")],
    pack: Annotated[Path | None, typer.Option(help="Evidence-pack directory.")] = None,
    storage: Annotated[
        StorageMode, typer.Option(help="reference or managed-copy.")
    ] = "managed-copy",
    parser: Annotated[
        str, typer.Option(help="auto, docling, ocr, or lightweight fallback.")
    ] = "auto",
    reset: Annotated[
        bool, typer.Option(help="Clear the local SQLite index before ingest.")
    ] = False,
) -> None:
    """Parse supported files and update the local index/manifest."""

    pack_path = pack or source
    summary = ingest_path(source, pack_path, storage_mode=storage, parser=parser, reset=reset)
    typer.echo(json.dumps(summary.model_dump(), indent=2))


@app.command()
def embed(
    pack: Annotated[Path, typer.Option(help="Evidence-pack directory.")],
    backend: Annotated[
        EmbeddingBackend, typer.Option(help="hash or sentence-transformers.")
    ] = "hash",
    model: Annotated[str | None, typer.Option(help="Embedding model name.")] = None,
    dimensions: Annotated[int, typer.Option(help="Hash vector dimensions.")] = 256,
) -> None:
    """Persist local embeddings for semantic retrieval."""

    count = build_embedding_index(
        EvidenceIndex(pack), backend=backend, model=model, dimensions=dimensions
    )
    typer.echo(
        json.dumps({"pack": str(pack), "backend": backend, "model": model, "embeddedChunks": count})
    )


@app.command("retrieve")
def retrieve_cmd(
    query: Annotated[str, typer.Argument(help="Search query.")],
    pack: Annotated[Path, typer.Option(help="Evidence-pack directory.")],
    mode: Annotated[RetrievalMode, typer.Option(help="keyword, semantic, or hybrid.")] = "hybrid",
    top_k: Annotated[int, typer.Option(help="Maximum hits to return.")] = 8,
) -> None:
    """Retrieve candidate evidence chunks for debugging."""

    hits = retrieve(EvidenceIndex(pack), [query], mode=mode, top_k=top_k)
    typer.echo(json.dumps([hit.model_dump() for hit in hits], indent=2, ensure_ascii=False))


@app.command()
def assess(
    finding: Annotated[Path, typer.Argument(help="Step 2 finding JSON file.")],
    pack: Annotated[Path, typer.Option(help="Evidence-pack directory.")],
    out: Annotated[Path, typer.Option(help="Output Step 3 JSON path.")],
    mode: Annotated[RetrievalMode, typer.Option(help="keyword, semantic, or hybrid.")] = "hybrid",
    top_k: Annotated[int, typer.Option(help="Candidate chunks to assess.")] = 10,
    include_frame: Annotated[
        bool, typer.Option(help="Write issue frame + assessment package.")
    ] = False,
    judge: Annotated[JudgeMode, typer.Option(help="heuristic, openai, or ollama.")] = "heuristic",
    judge_model: Annotated[
        str | None, typer.Option(help="Hosted/local judge model override.")
    ] = None,
    profile: Annotated[
        str | None, typer.Option(help=f"Model profile: {', '.join(profile_names())}.")
    ] = None,
) -> None:
    """Assess one Step 2 finding against an evidence pack."""

    if profile:
        selected = get_profile(profile)
        judge = selected.judge  # type: ignore[assignment]
        judge_model = selected.model
    step2 = load_step2_finding(finding)
    package = assess_finding(
        step2, pack, retrieval_mode=mode, top_k=top_k, judge=judge, judge_model=judge_model
    )
    write_assessment(package, out, include_frame=include_frame)
    typer.echo(f"Wrote {out}")


@app.command("review-add")
def review_add(
    pack: Annotated[Path, typer.Argument(help="Evidence-pack directory.")],
    claim_id: Annotated[str, typer.Option(help="Claim/finding id.")],
    doc_id: Annotated[str, typer.Option(help="Document id.")],
    quote: Annotated[str, typer.Option(help="Reviewed quote.")],
    status: Annotated[
        str, typer.Option(help="supports, limits, contradicts, context, or irrelevant.")
    ],
    human_decision: Annotated[str, typer.Option(help="accepted, rejected, edited, or unclear.")],
    reason: Annotated[str, typer.Option(help="Short reviewer rationale.")],
) -> None:
    """Append one human review decision to review_decisions.csv."""

    decision = make_review_decision(claim_id, doc_id, quote, status, human_decision, reason)
    record_review_decision(pack, decision)
    typer.echo(f"Recorded decision for {claim_id} / {doc_id}")


@app.command()
def learn(
    decisions: Annotated[
        Path | None,
        typer.Option("--from", help="review_decisions.csv path. Defaults to pack file."),
    ] = None,
    pack: Annotated[Path | None, typer.Option(help="Evidence-pack directory.")] = None,
    propose: Annotated[Path, typer.Option(help="Output playbook patch path.")] = Path(
        "playbook.patch.yaml"
    ),
) -> None:
    """Propose a human-reviewed playbook patch from review decisions."""

    decisions_path = decisions or ((pack or Path(".")) / "review_decisions.csv")
    text = propose_playbook_patch(decisions_path, propose)
    typer.echo(text)


if __name__ == "__main__":
    app()
