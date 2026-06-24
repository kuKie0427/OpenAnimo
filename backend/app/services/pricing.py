from __future__ import annotations

import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# USD per 1M tokens
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.8, "output": 4.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "doubao-seedance-1-5-pro": {"input": 0, "output": 0, "video_per_sec": 0.5},
}

# Fallback for unknown models
FALLBACK_PRICING: dict[str, float] = {"input": 1.0, "output": 3.0}


def estimate_cost(
    model_name: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    images: int = 0,
    video_seconds: int = 0,
    pricing_overrides: dict[str, dict[str, float]] | None = None,
) -> Decimal:
    """Estimate cost in USD for a given model and usage.

    Args:
        model_name: Model identifier (matched against DEFAULT_PRICING keys).
        tokens_input: Number of input tokens.
        tokens_output: Number of output tokens.
        images: Number of images generated.
        video_seconds: Total video seconds generated.
        pricing_overrides: Optional dict to override DEFAULT_PRICING
            (e.g., from env var).

    Returns:
        Decimal cost in USD (rounded to 6 decimal places).
    """
    # Merge pricing: overrides take precedence
    pricing: dict[str, dict[str, float]] = dict(DEFAULT_PRICING)
    if pricing_overrides:
        pricing.update(pricing_overrides)

    # Find matching pricing entry.
    # Exact match first, then prefix match
    # (e.g., "claude-sonnet-4-5-20250929" matches "claude-sonnet-4-5").
    rates = pricing.get(model_name)
    if rates is None:
        for key, value in pricing.items():
            if model_name.startswith(key):
                rates = value
                break

    if rates is None:
        logger.warning(
            "Unknown model '%s' - using fallback pricing ($1.0/$3.0 per 1M tokens)",
            model_name,
        )
        rates = dict(FALLBACK_PRICING)

    input_rate = Decimal(str(rates.get("input", 0)))
    output_rate = Decimal(str(rates.get("output", 0)))
    image_cost = Decimal(str(rates.get("image_cost", 0))) * Decimal(str(images))
    video_cost = Decimal(str(rates.get("video_per_sec", 0))) * Decimal(str(video_seconds))

    total = (
        input_rate * Decimal(str(tokens_input)) / Decimal("1000000")
        + output_rate * Decimal(str(tokens_output)) / Decimal("1000000")
        + image_cost
        + video_cost
    )
    return total.quantize(Decimal("0.000001"))


def parse_pricing_overrides(pricing_json: str) -> dict[str, dict[str, float]]:
    """Parse pricing overrides from a JSON string.

    Returns an empty dict if the string is empty or invalid.
    Logs a warning on parse errors rather than raising.
    """
    if not pricing_json.strip():
        return {}
    try:
        return json.loads(pricing_json)
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse pricing_overrides JSON, ignoring: %s",
            pricing_json,
        )
        return {}
