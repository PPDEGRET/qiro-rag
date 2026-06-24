"""Judge model profiles and a tiny onboarding recommender."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    name: str
    judge: str
    model: str | None
    privacy: str
    cost: str
    best_for: str
    notes: str


PROFILES = {
    "heuristic": ModelProfile(
        name="heuristic",
        judge="heuristic",
        model=None,
        privacy="local",
        cost="free",
        best_for="default offline runs, CI, conservative smoke checks",
        notes="No LLM. Strong quote rails, less reasoning nuance.",
    ),
    "ollama-private-small": ModelProfile(
        name="ollama-private-small",
        judge="ollama",
        model="qwen2.5:1.5b",
        privacy="local",
        cost="free after install",
        best_for="laptop/private demo with a real local LLM",
        notes="Tested locally. Better than tiny 0.5B; still needs human review.",
    ),
    "ollama-private-balanced": ModelProfile(
        name="ollama-private-balanced",
        judge="ollama",
        model="qwen2.5:7b",
        privacy="local",
        cost="free after install",
        best_for="private review when hardware can run a 7B model",
        notes="Recommended local-private baseline; pull with `ollama pull qwen2.5:7b`.",
    ),
    "ollama-private-mistral": ModelProfile(
        name="ollama-private-mistral",
        judge="ollama",
        model="mistral-small3.2",
        privacy="local",
        cost="free after install",
        best_for="private review on stronger hardware with a Mistral-family model",
        notes="Private-by-default option if your Ollama setup can run it. Pull with `ollama pull mistral-small3.2`.",
    ),
    "hosted-flash": ModelProfile(
        name="hosted-flash",
        judge="openai",
        model="gemini-2.5-flash",
        privacy="hosted or private gateway",
        cost="provider billed",
        best_for="fast high-quality hosted/private-gateway review",
        notes="Recommended hosted default. Use an OpenAI-compatible Gemini/private gateway endpoint, or override --judge-model.",
    ),
    "mistral-private-gateway": ModelProfile(
        name="mistral-private-gateway",
        judge="openai",
        model="mistral-small-latest",
        privacy="hosted EU/provider or private deployment gateway",
        cost="provider billed",
        best_for="privacy-conscious enterprise gateway setups",
        notes="Good Mistral-family default for OpenAI-compatible Mistral/private gateways; override --judge-model as needed.",
    ),
    "openai-compatible-custom": ModelProfile(
        name="openai-compatible-custom",
        judge="openai",
        model=None,
        privacy="depends on configured gateway",
        cost="provider billed",
        best_for="custom enterprise model gateways",
        notes="Uses OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL or explicit --judge-model.",
    ),
}


def profile_names() -> list[str]:
    return list(PROFILES)


def get_profile(name: str) -> ModelProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown model profile `{name}`. Choose one of: {', '.join(PROFILES)}"
        ) from exc


def recommend_profile(
    *,
    local_only: bool,
    no_llm: bool,
    hardware: str,
    cloud_allowed: bool,
) -> ModelProfile:
    if no_llm:
        return PROFILES["heuristic"]
    if local_only or not cloud_allowed:
        if hardware == "small":
            return PROFILES["ollama-private-small"]
        if hardware == "workstation":
            return PROFILES["ollama-private-mistral"]
        return PROFILES["ollama-private-balanced"]
    return PROFILES["hosted-flash"]


def assess_args(profile: ModelProfile) -> list[str]:
    if profile.judge == "heuristic":
        return ["--judge", "heuristic"]
    args = ["--judge", profile.judge]
    if profile.model:
        args.extend(["--judge-model", profile.model])
    return args
