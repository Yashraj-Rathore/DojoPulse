"""Offline Wavu metadata normalizer. No HTTP client, identity search or replay decoder."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from analysis.contracts import digest
from ingestion.contracts import (
    ExternalId,
    MatchMetadata,
    MatchMode,
    PlayerSnapshot,
    Provenance,
    ProviderClass,
)


@dataclass(frozen=True)
class Codebook:
    revision: str
    game_builds: Mapping[str, str] = field(default_factory=dict)
    modes: Mapping[str, MatchMode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.revision:
            raise ValueError("Code mapping needs a revision")


def integer(value: Any, field_name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field_name} requires a losslessly decoded JSON integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} requires an exact string")
    return value


def normalize_record(
    row: Mapping[str, Any],
    *,
    retrieved_at: datetime,
    dataset_kind: str,
    codebook: Codebook | None = None,
) -> MatchMetadata:
    participants = []
    for slot in (1, 2):
        prefix = f"p{slot}_"
        polaris = identifier(row[prefix + "polaris_id"], prefix + "polaris_id")
        numeric = integer(row[prefix + "user_id"], prefix + "user_id")
        display_name = row.get(prefix + "name")
        if display_name is not None and not isinstance(display_name, str):
            raise ValueError("Invalid display name")
        participants.append(
            PlayerSnapshot(
                slot=slot,
                identities=(
                    ExternalId("tekken:polaris", polaris),
                    ExternalId("tekken:user_id", str(numeric)),
                ),
                display_name=display_name,
                name_semantics="current_at_retrieval",
                character_code=str(integer(row[prefix + "chara_id"], prefix + "chara_id")),
                rank_code=str(integer(row[prefix + "rank"], prefix + "rank"))
                if prefix + "rank" in row
                else None,
                power=integer(row[prefix + "power"], prefix + "power")
                if prefix + "power" in row
                else None,
                rounds_won=integer(row[prefix + "rounds"], prefix + "rounds")
                if prefix + "rounds" in row
                else None,
            )
        )
    raw_version = str(integer(row["game_version"], "game_version"))
    raw_mode = str(integer(row["battle_type"], "battle_type"))
    raw_winner = integer(row["winner"], "winner")
    # Preserve unknown result codes; only the observed player-slot encoding is normalized.
    winner = raw_winner if raw_winner in {1, 2} else None
    mapped_build = codebook.game_builds.get(raw_version) if codebook else None
    mapped_mode = codebook.modes.get(raw_mode, MatchMode.UNKNOWN) if codebook else MatchMode.UNKNOWN
    return MatchMetadata(
        game="tekken8",
        external_id=ExternalId("wavu:battle_id", identifier(row["battle_id"], "battle_id")),
        played_at=datetime.fromtimestamp(integer(row["battle_at"], "battle_at"), tz=UTC),
        raw_game_version=raw_version,
        canonical_game_build=mapped_build,
        version_mapping_revision=codebook.revision
        if mapped_build is not None and codebook
        else None,
        raw_mode=raw_mode,
        mode=mapped_mode,
        mode_mapping_revision=codebook.revision
        if mapped_mode != MatchMode.UNKNOWN and codebook
        else None,
        participants=(participants[0], participants[1]),
        winner_slot=winner,
        raw_winner=str(raw_winner),
        stage_code=str(integer(row["stage_id"], "stage_id")) if "stage_id" in row else None,
        provenance=Provenance(
            provider="wavu",
            access_class=ProviderClass.COMMUNITY_PUBLIC_API,
            adapter_version="wavu-metadata/1",
            schema_version="wavu-observed-2026-09-18",
            retrieved_at=retrieved_at,
            record_digest=digest(dict(row)),
            dataset_kind=dataset_kind,
        ),
    )


def previous_window_end(before: int, overlap_seconds: int = 60) -> int:
    """For documented (before-700, before] windows; not a transport or collection scheduler."""
    if type(before) is not int or before < 700 or not 0 <= overlap_seconds < 700:
        raise ValueError("Invalid Wavu window")
    return before - 700 + overlap_seconds
