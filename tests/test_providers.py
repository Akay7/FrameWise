"""Fast, network-free unit tests for the provider layer.

Stubs the provider SDKs (google-genai / openai / anthropic) via sys.modules so
selection, credential, and parsing logic can be exercised with no network, no
keys, and no SDKs installed.

Runs under pytest (`python -m pytest tests/test_providers.py`) or standalone
(`python tests/test_providers.py`).
"""

import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _install_fake_sdks():
    """Register minimal fake SDK modules so adapter __init__ imports succeed."""
    # google.genai
    google = types.ModuleType("google")
    genai = types.ModuleType("google.genai")

    class _Client:
        def __init__(self, api_key=None):
            self.api_key = api_key

    genai.Client = _Client
    google.genai = genai
    sys.modules["google"] = google
    sys.modules["google.genai"] = genai

    # openai
    openai = types.ModuleType("openai")

    class _OpenAI:
        def __init__(self, api_key=None, base_url=None, timeout=None):
            self.api_key = api_key
            self.base_url = base_url

    openai.OpenAI = _OpenAI
    sys.modules["openai"] = openai

    # anthropic
    anthropic = types.ModuleType("anthropic")

    class _Anthropic:
        def __init__(self, api_key=None, timeout=None):
            self.api_key = api_key

    anthropic.Anthropic = _Anthropic
    sys.modules["anthropic"] = anthropic


_install_fake_sdks()

import providers  # noqa: E402


def _clear_keys():
    for var in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "CAPTION_PROVIDER"):
        os.environ.pop(var, None)


def test_unknown_provider_raises():
    _clear_keys()
    try:
        providers.get_provider("bogus")
    except SystemExit as e:
        assert "bogus" in str(e) and "gemini" in str(e)
    else:
        raise AssertionError("expected SystemExit for unknown provider")


def test_missing_key_raises_named_var():
    _clear_keys()
    try:
        providers.get_provider("openai")
    except SystemExit as e:
        assert "OPENAI_API_KEY" in str(e)
    else:
        raise AssertionError("expected SystemExit for missing key")


def test_default_provider_is_gemini():
    _clear_keys()
    os.environ["GEMINI_API_KEY"] = "test-key"
    prov = providers.get_provider()  # no CAPTION_PROVIDER set -> default
    assert isinstance(prov, providers.GeminiProvider)


def test_explicit_provider_selection():
    _clear_keys()
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    prov = providers.get_provider("anthropic")
    assert isinstance(prov, providers.AnthropicProvider)


def test_openai_base_url_needs_no_real_key():
    # Pointing at a local OpenAI-compatible server (e.g. Lemonade) must not
    # require OPENAI_API_KEY.
    _clear_keys()
    os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/api/v1"
    try:
        prov = providers.get_provider("openai")
        assert isinstance(prov, providers.OpenAIProvider)
        assert prov._client.base_url == "http://localhost:8000/api/v1"
    finally:
        os.environ.pop("OPENAI_BASE_URL", None)


def test_parse_returns_only_requested_styles():
    text = (
        'Here you go: {"formal": "A cat sleeps.", "sarcastic": "Wow, a nap.", '
        '"humorous_tech": "404 energy not found.", '
        '"humorous_non_tech": "Peak Sunday mood."}'
    )
    styles = ["formal", "humorous_tech"]
    out = providers.parse_captions(text, styles)
    assert set(out.keys()) == set(styles)
    assert out["formal"] == "A cat sleeps."
    assert out["humorous_tech"] == "404 energy not found."


def test_parse_fills_missing_style_with_empty():
    out = providers.parse_captions('{"formal": "Only this one."}',
                                   ["formal", "sarcastic"])
    assert out["formal"] == "Only this one."
    assert out["sarcastic"] == ""


def test_parse_tolerates_garbage():
    out = providers.parse_captions("not json at all", ["formal"])
    assert out == {"formal": ""}


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
