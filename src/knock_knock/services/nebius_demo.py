"""Opt-in Nebius summary for DoorMemo's synthetic group-arrival demo."""

from __future__ import annotations

import os
from typing import Any

import httpx

NEBIUS_ENDPOINT = "https://api.tokenfactory.us-central1.nebius.com/v1/chat/completions"
DEFAULT_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


class NebiusDemoError(RuntimeError):
    """A safe-to-display failure from the optional hackathon integration."""


def summarize_synthetic_visit(person_count: int, client: httpx.Client | None = None) -> str:
    """Summarize a synthetic count only; never send images, names, or real events."""
    if isinstance(person_count, bool) or not isinstance(person_count, int):
        raise ValueError("Synthetic person count must be an integer")
    if not 0 <= person_count <= 20:
        raise ValueError("Synthetic person count must be between 0 and 20")
    api_key = os.environ.get("NEBIUS_API_KEY", "")
    if not api_key or api_key.startswith("{{resolve:"):
        raise RuntimeError("A resolved NEBIUS_API_KEY is required for the opt-in demo")
    model = os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL)
    if not model.startswith("nvidia/"):
        raise ValueError("The hackathon demo requires an NVIDIA model")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "Summarize the synthetic doorbell event in one short neutral sentence. "
                "Do not infer identity, intent, risk, or details not provided."
            )},
            {"role": "user", "content": (
                f"Synthetic demonstration: doorbell event; {person_count} people detected. "
                "All identities are unknown and require owner review."
            )},
        ],
        "max_tokens": 128,
        "temperature": 0,
    }
    owns_client = client is None
    http = client or httpx.Client(timeout=30.0, follow_redirects=False)
    try:
        try:
            response = http.post(
                NEBIUS_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NebiusDemoError(
                f"Nebius request failed (HTTP {exc.response.status_code})"
            ) from None
        except httpx.RequestError:
            raise NebiusDemoError("Nebius request failed to connect or timed out") from None
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise NebiusDemoError("Nebius returned an invalid response") from None
        if not isinstance(content, str) or not content.strip():
            raise NebiusDemoError("Nebius returned an empty summary")
        return content.strip()
    finally:
        if owns_client:
            http.close()
