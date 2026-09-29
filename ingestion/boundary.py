"""Offline provider boundary primitives. This module does not implement HTTP access.

A reviewed transport must pin the validated DNS answer to its connection, verify TLS
for the exact hostname, disable proxies and redirects, and stream through the cap.
"""

import ipaddress
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from ingestion.contracts import Operation
from ingestion.policy import ProviderPolicy, require_operation


@dataclass(frozen=True)
class FetchBoundary:
    policy: ProviderPolicy
    hostname: str
    allowed_paths: frozenset[str]
    max_bytes: int = 1_048_576

    def validate_target(
        self,
        url: str,
        operation: Operation,
        purpose: str,
        now: datetime,
        resolved_addresses: Iterable[str],
    ) -> tuple[str, ...]:
        require_operation(self.policy, operation, purpose, now)
        target = urlsplit(url)
        if (
            not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)+", self.hostname)
            or target.scheme != "https"
            or target.netloc != self.hostname
            or target.path not in self.allowed_paths
            or target.fragment
            or any(ord(c) < 33 or ord(c) > 126 for c in url)
            or "\\" in url
            or "%" in target.path
            or ".." in target.path
        ):
            raise ValueError("PROVIDER_TARGET_REJECTED")
        try:
            ipaddress.ip_address(self.hostname)
        except ValueError:
            pass
        else:
            raise ValueError("PROVIDER_IP_LITERAL_REJECTED")
        addresses = tuple(resolved_addresses)
        if not addresses:
            raise ValueError("PROVIDER_DNS_EMPTY")
        for value in addresses:
            address = ipaddress.ip_address(value)
            if (
                not address.is_global
                or address.is_multicast
                or getattr(address, "ipv4_mapped", None) is not None
                or getattr(address, "sixtofour", None) is not None
                or getattr(address, "teredo", None) is not None
            ):
                raise ValueError("PROVIDER_ADDRESS_REJECTED")
        return addresses

    def decode_json(
        self,
        chunks: Iterable[bytes],
        *,
        status: int,
        content_type: str,
        content_encoding: str = "identity",
        content_length: int | None = None,
    ) -> Any:
        if status != 200:
            # Redirects, rate limiting and errors never get parsed as match data.
            raise ValueError("PROVIDER_RESPONSE_STATUS")
        if (
            content_type.lower().split(";", 1)[0].strip() != "application/json"
            or content_encoding != "identity"
        ):
            raise ValueError("PROVIDER_RESPONSE_ENCODING")
        if content_length is not None and not 0 <= content_length <= self.max_bytes:
            raise ValueError("PROVIDER_RESPONSE_LIMIT")
        body = bytearray()
        for chunk in chunks:
            if len(body) + len(chunk) > self.max_bytes:
                raise ValueError("PROVIDER_RESPONSE_LIMIT")
            body.extend(chunk)
        if content_length is not None and len(body) != content_length:
            raise ValueError("PROVIDER_RESPONSE_TRUNCATED")

        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in items:
                if key in result:
                    raise ValueError("PROVIDER_DUPLICATE_KEY")
                result[key] = value
            return result

        def constant(value: str) -> None:
            raise ValueError("PROVIDER_NONFINITE_NUMBER")

        try:
            result = json.loads(
                body.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
            )
        except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
            raise ValueError("PROVIDER_INVALID_JSON") from error
        queue = [(result, 0)]
        count = 0
        while queue:
            value, depth = queue.pop()
            count += 1
            if depth > 32 or count > 10_000:
                raise ValueError("PROVIDER_JSON_COMPLEXITY")
            if isinstance(value, dict):
                queue.extend((child, depth + 1) for child in value.values())
            elif isinstance(value, list):
                queue.extend((child, depth + 1) for child in value)
            elif isinstance(value, float):
                import math

                if not math.isfinite(value):
                    raise ValueError("PROVIDER_NONFINITE_NUMBER")
        return result  # The adapter MUST still validate its exact reviewed schema.
