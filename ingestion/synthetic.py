"""Two deterministic, in-memory providers for exercising the adapter boundary."""

from datetime import UTC, datetime, timedelta

from analysis.contracts import digest
from ingestion.contracts import (
    DiscoveryPage,
    ExternalId,
    IdentityCandidate,
    MatchMetadata,
    MatchMode,
    Operation,
    PayloadReceipt,
    PlayerSnapshot,
    Provenance,
    ProviderClass,
    ReplayReference,
)

PLAYER = ExternalId("synthetic:polaris", "ExamplePlayer-A")
START = datetime(2026, 9, 1, tzinfo=UTC)
END = START + timedelta(days=1)


class SyntheticProvider:
    def __init__(self, key: str = "synthetic-a") -> None:
        if key not in {"synthetic-a", "synthetic-b"}:
            raise ValueError("Unknown synthetic provider")
        self.key = key

    def provenance(self, record: str) -> Provenance:
        return Provenance(
            provider=self.key,
            access_class=ProviderClass.USER_UPLOAD,
            adapter_version="synthetic/1",
            schema_version="synthetic/1",
            retrieved_at=END,
            record_digest=digest(record),
            dataset_kind="synthetic",
        )

    def resolve_player(self, query: str, kind: Operation) -> tuple[IdentityCandidate, ...]:
        if kind != Operation.RESOLVE_ID:
            raise NotImplementedError("Synthetic provider supports exact ID selection only")
        if query != PLAYER.value:
            return ()
        return (IdentityCandidate(PLAYER, (), "Synthetic Player", self.provenance("identity")),)

    def discover_matches(
        self, identity: ExternalId, cursor: str | None, start: datetime, end: datetime
    ) -> DiscoveryPage:
        if identity != PLAYER or start != START or end != END or cursor not in {None, "second"}:
            raise ValueError("Unsupported synthetic query")
        index = 1 if cursor is None else 2
        # Same external string across providers deliberately tests namespace isolation.
        record = MatchMetadata(
            game="tekken8",
            external_id=ExternalId("synthetic:battle", str(index)),
            played_at=START + timedelta(hours=index),
            raw_game_version="unmapped-999",
            canonical_game_build=None,
            version_mapping_revision=None,
            raw_mode="unmapped-mode",
            mode=MatchMode.UNKNOWN,
            mode_mapping_revision=None,
            participants=(
                PlayerSnapshot(
                    1, (PLAYER,), "Synthetic Player", "current_at_retrieval", "42", None, None, 3
                ),
                PlayerSnapshot(
                    2,
                    (ExternalId("synthetic:polaris", "ExampleOpponent-B"),),
                    "Synthetic Opponent",
                    "current_at_retrieval",
                    "43",
                    None,
                    None,
                    1,
                ),
            ),
            winner_slot=1,
            raw_winner="1",
            stage_code=None,
            provenance=self.provenance(f"match-{index}"),
        )
        return DiscoveryPage(
            (record,), "second" if index == 1 else None, start, end, "COMPLETE_FOR_QUERY"
        )

    def fetch_replay(self, reference: ReplayReference) -> PayloadReceipt:
        raise NotImplementedError("Metadata-only fixture has no gameplay payload")
