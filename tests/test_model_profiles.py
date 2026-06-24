from qiro_rag.model_profiles import assess_args, get_profile, recommend_profile


def test_recommend_local_small_profile() -> None:
    profile = recommend_profile(
        local_only=True, no_llm=False, hardware="small", cloud_allowed=False
    )

    assert profile.name == "ollama-private-small"
    assert assess_args(profile) == ["--judge", "ollama", "--judge-model", "qwen2.5:1.5b"]


def test_recommend_no_llm_profile() -> None:
    profile = recommend_profile(
        local_only=True, no_llm=True, hardware="workstation", cloud_allowed=False
    )

    assert profile.name == "heuristic"
    assert assess_args(profile) == ["--judge", "heuristic"]


def test_recommend_workstation_privacy_profile_prefers_mistral() -> None:
    profile = recommend_profile(
        local_only=True, no_llm=False, hardware="workstation", cloud_allowed=False
    )

    assert profile.name == "ollama-private-mistral"
    assert profile.model == "mistral-small3.2"


def test_recommend_cloud_profile_uses_flash_not_old_openai_mini() -> None:
    profile = recommend_profile(
        local_only=False, no_llm=False, hardware="balanced", cloud_allowed=True
    )

    assert profile.name == "hosted-flash"
    assert profile.model == "gemini-2.5-flash"


def test_mistral_gateway_profile_is_explicit() -> None:
    profile = get_profile("mistral-private-gateway")

    assert profile.judge == "openai"
    assert profile.model == "mistral-small-latest"
