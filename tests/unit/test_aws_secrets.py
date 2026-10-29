from __future__ import annotations

from typing import Any

from knock_knock.aws.secrets import load_optional_secret_json


class ResourceNotFoundException(Exception):
    pass


class _Exceptions:
    ResourceNotFoundException = ResourceNotFoundException


class UninitializedSecretClient:
    exceptions = _Exceptions()

    def get_secret_value(self, **_: Any) -> dict[str, Any]:
        raise ResourceNotFoundException


def test_optional_secret_is_empty_before_first_value_is_configured() -> None:
    assert load_optional_secret_json(UninitializedSecretClient(), "ring-secret") == {}
