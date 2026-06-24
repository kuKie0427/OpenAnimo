from __future__ import annotations

from decimal import Decimal


from app.services.pricing import estimate_cost, parse_pricing_overrides


def test_estimate_cost_known_model():
    """Known model with exact match returns correct cost."""
    # claude-sonnet-4-5: input=$3.0/1M, output=$15.0/1M
    # 1000 input + 500 output = (3*1000/1M) + (15*500/1M) = 0.003 + 0.0075 = 0.0105
    cost = estimate_cost("claude-sonnet-4-5", tokens_input=1000, tokens_output=500)
    assert cost == Decimal("0.0105")


def test_estimate_cost_zero_tokens():
    """Zero tokens returns zero cost for any known model."""
    cost = estimate_cost("claude-haiku-4-5", tokens_input=0, tokens_output=0)
    assert cost == Decimal("0")


def test_estimate_cost_unknown_model_fallback():
    """Unknown model uses fallback pricing ($1.0/$3.0/1M) and logs a warning."""
    # 2000 input + 1000 output = (1*2000/1M) + (3*1000/1M) = 0.002 + 0.003 = 0.005
    cost = estimate_cost("unknown-model-v1", tokens_input=2000, tokens_output=1000)
    assert cost == Decimal("0.005")


def test_estimate_cost_unknown_model_fallback_only_input():
    """Unknown model with only input tokens — fallback input rate only."""
    # 5000 input = (1*5000/1M) = 0.005
    cost = estimate_cost("made-up-model", tokens_input=5000)
    assert cost == Decimal("0.005")


def test_estimate_cost_video_model():
    """Video-specific model charges video_seconds rate (0 input/output rate)."""
    # doubao-seedance-1-5-pro: input=0, output=0, video_per_sec=0.5
    # 10 seconds of video = 10 * 0.5 = 5.0
    cost = estimate_cost(
        "doubao-seedance-1-5-pro",
        tokens_input=100,
        tokens_output=50,
        video_seconds=10,
    )
    assert cost == Decimal("5.0")


def test_estimate_cost_prefix_match():
    """Prefix-matched model uses the base model's pricing."""
    # "claude-sonnet-4-5-20250929" should prefix-match "claude-sonnet-4-5"
    # 1000 input + 0 output = (3*1000/1M) = 0.003
    cost = estimate_cost("claude-sonnet-4-5-20250929", tokens_input=1000, tokens_output=0)
    assert cost == Decimal("0.003")


def test_estimate_cost_gpt4o_variant_prefix_match():
    """Suffixed model name prefix-matches base key (gpt-4o-2024-08-06 → gpt-4o)."""
    cost = estimate_cost("gpt-4o-2024-08-06", tokens_input=10000, tokens_output=5000)
    assert cost == Decimal("0.075")


def test_estimate_cost_with_pricing_overrides():
    """Pricing overrides take precedence over defaults."""
    overrides = {
        "claude-sonnet-4-5": {"input": 0.5, "output": 2.0},
    }
    # 1000 input + 500 output = (0.5*1000/1M) + (2.0*500/1M) = 0.0005 + 0.001 = 0.0015
    cost = estimate_cost(
        "claude-sonnet-4-5",
        tokens_input=1000,
        tokens_output=500,
        pricing_overrides=overrides,
    )
    assert cost == Decimal("0.0015")


def test_estimate_cost_with_images():
    """Image cost from pricing dict is applied when provided."""
    overrides = {
        "image-model-v1": {"input": 0, "output": 0, "image_cost": 0.04},
    }
    # 5 images at $0.04 each = 0.20
    cost = estimate_cost(
        "image-model-v1",
        tokens_input=0,
        tokens_output=0,
        images=5,
        pricing_overrides=overrides,
    )
    assert cost == Decimal("0.2")


def test_parse_pricing_overrides_valid_json():
    """Valid JSON string returns parsed dict."""
    result = parse_pricing_overrides(
        '{"gpt-4o": {"input": 1.5, "output": 5.0}}'
    )
    assert result == {"gpt-4o": {"input": 1.5, "output": 5.0}}


def test_parse_pricing_overrides_empty_string():
    """Empty string returns empty dict (no warning since strip check prevents parse)."""
    result = parse_pricing_overrides("")
    assert result == {}


def test_parse_pricing_overrides_invalid_json(monkeypatch):
    """Invalid JSON logs a warning and returns empty dict."""
    warnings: list[str] = []

    def capture_warning(msg: str, *args: object) -> None:
        warnings.append(msg % args if args else msg)

    monkeypatch.setattr("app.services.pricing.logger.warning", capture_warning)
    result = parse_pricing_overrides("{not valid json")
    assert result == {}
    assert any("Failed to parse pricing_overrides JSON" in w for w in warnings)
