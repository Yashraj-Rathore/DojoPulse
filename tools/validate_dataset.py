"""Validate private manifests, hashes, consent, independent splits and reviews."""
import argparse
import json
from pathlib import Path
from typing import Any

from analysis.annotations import validate_annotations
from analysis.media import file_hash


def confined(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError("Absolute private path is not permitted in manifest")
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Private root escape")
    return result


def validate_manifest(manifest: dict[str, Any], root: Path, metadata_only: bool = False) -> dict[str, Any]:
    if manifest.get("schema_version") != "dataset/1":
        raise ValueError("Unknown manifest schema")
    if manifest.get("dataset_kind") not in {"real", "synthetic"}:
        raise ValueError("Dataset kind required")
    seen: dict[str, dict[str, str]] = {k: {} for k in ("source_id", "sha256", "player_id", "session_id")}
    for source in manifest["sources"]:
        split = source["split"]
        if split not in {"development", "validation", "held-out"}:
            raise ValueError("Invalid split")
        for key, group in seen.items():
            value = source[key]
            if value in group and (key in {"source_id", "sha256"} or group[value] != split):
                raise ValueError(f"Duplicate/leaked {key}")
            group[value] = split
        if not source["consent"]["service_processing"]:
            raise ValueError("Missing processing consent")
        media = confined(root, source["relative_path"])
        annotations_path = confined(root, source["annotation_path"])
        if not metadata_only:
            if file_hash(media) != source["sha256"]:
                raise ValueError("Source hash mismatch")
            annotation = json.loads(annotations_path.read_text(encoding="utf-8"))
            validate_annotations(annotation, source["sha256"])
            if (annotation["game_build"] != source["game_build"]
                or annotation["session_id"] != source["session_id"]
                or annotation["source_id"] != source["source_id"]
                or annotation["dataset_kind"] != manifest["dataset_kind"]):
                raise ValueError("Annotation manifest mismatch")
    return {"status": "VALID", "source_count": len(manifest["sources"]),
            "source_bytes_verified": not metadata_only, "dataset_kind": manifest["dataset_kind"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    result = validate_manifest(json.loads(args.manifest.read_text(encoding="utf-8")),
                               args.root, args.metadata_only)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
