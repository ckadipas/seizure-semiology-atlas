#!/usr/bin/env python3
"""Validate the public bundle as a passive projection of the normalized ledger."""

from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
GRAPH_TOOLS = ROOT / "website/tools"
sys.path.insert(0, str(GRAPH_TOOLS if GRAPH_TOOLS.is_dir() else Path(__file__).parent))

from public_relationship_graph import (
    PublicRelationshipGraph,
    assert_bundle_integrity,
    canonical_json_sha256,
    file_sha256,
)


BUNDLE_SCHEMA = "atlas-public-bundle-1.17.0"
GRAPH_SCHEMA = "atlas-normalized-relationship-graph-1.17.0"
PUBLIC_RECEIPT_SCHEMA = "atlas-public-release-receipt-1.1.0"
BUNDLE_FIELDS = {
    "schema_version", "brodmann", "scientific_relationship_graph",
    "semantic_digest",
}
PUBLIC_RECEIPT_FIELDS = {
    "schema_version", "release_id", "bundle_schema_version",
    "graph_schema_version", "graph_sha256", "bundle_content_sha256",
    "bundle_file_sha256", "database_sha256", "snapshot_sha256",
    "module_sha256", "projection_file_sha256", "semantic_digest",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_brodmann_panel(brodmann):
    require(isinstance(brodmann, dict), "Brodmann presentation data is invalid")
    require(
        "mapping" not in brodmann and "scientific_mapping_rule" not in brodmann,
        "Brodmann presentation data contains a parallel scientific mapping store",
    )


def receipt_digest(receipt):
    unbound = deepcopy(receipt)
    expected = str(unbound.pop("semantic_digest", "") or "")
    actual = canonical_json_sha256(unbound)
    require(expected == actual, "public release receipt semantic digest mismatch")
    return actual


def validate_explorer(receipt):
    docs = ROOT / "docs"
    compressed = docs / "atlas-projection.json.gz"
    module = docs / "atlas_projection.mjs"
    html_path = docs / "index.html"
    encoded = gzip.decompress(compressed.read_bytes())
    snapshot_sha256 = hashlib.sha256(encoded).hexdigest()
    projection = json.loads(encoded)
    metadata = projection.get("metadata")
    require(isinstance(metadata, dict), "public explorer metadata is absent")
    require(
        metadata.get("normalized_graph_release_id") == receipt["release_id"]
        and metadata.get("normalized_graph_sha256") == receipt["graph_sha256"]
        and metadata.get("database_sha256") == receipt["database_sha256"],
        "public explorer identity differs from the release receipt",
    )
    require(
        snapshot_sha256 == receipt["snapshot_sha256"]
        and file_sha256(module) == receipt["module_sha256"]
        and file_sha256(compressed) == receipt["projection_file_sha256"],
        "public explorer content digest differs from the release receipt",
    )
    views = ((projection.get("catalogue") or {}).get("maps") or {}).get("views")
    require(isinstance(views, dict) and views, "public explorer map views are absent")
    expected_files = {
        "index.html", "atlas_projection.mjs", "atlas-projection.json.gz",
    }
    for view in views.values():
        relative = PurePosixPath(str((view or {}).get("image_url") or ""))
        require(
            relative.parts[:2] == ("generator", "assets")
            and not relative.is_absolute() and ".." not in relative.parts,
            "public explorer map asset path is unsafe",
        )
        expected_files.add(relative.as_posix())
    actual_files = {
        path.relative_to(docs).as_posix()
        for path in docs.rglob("*") if path.is_file()
    }
    require(actual_files == expected_files, "public explorer file set differs")
    html = html_path.read_text(encoding="utf-8")
    require(
        f'data-projection="static" data-snapshot="{snapshot_sha256}"' in html
        and f"from './atlas_projection.mjs?v={receipt['module_sha256']}'" in html,
        "public explorer HTML content binding differs",
    )


def validate_manifest(path, bundle_path, bundle, graph, bundle_bytes):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(
        set(receipt) == PUBLIC_RECEIPT_FIELDS,
        "unexpected public release receipt fields",
    )
    require(
        receipt.get("schema_version") == PUBLIC_RECEIPT_SCHEMA,
        "unexpected public release receipt schema",
    )
    digest = receipt_digest(receipt)
    require(
        receipt["bundle_schema_version"] == bundle.get("schema_version") == BUNDLE_SCHEMA,
        "public release receipt bundle schema differs",
    )
    require(
        receipt["graph_schema_version"] == graph.payload.get("schema_version") == GRAPH_SCHEMA,
        "public release receipt graph schema differs",
    )
    require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", str(receipt["release_id"]))
        is not None,
        "public release receipt identifier is unsafe",
    )
    require(
        all(
            re.fullmatch(r"[0-9a-f]{64}", str(receipt[field])) is not None
            for field in (
                "graph_sha256", "bundle_content_sha256", "bundle_file_sha256",
                "database_sha256", "snapshot_sha256", "module_sha256",
                "projection_file_sha256",
            )
        ),
        "public release receipt digest is invalid",
    )
    require(
        receipt["release_id"] == (graph.payload.get("release") or {}).get("release_id"),
        "public release receipt differs from the graph release",
    )
    require(
        receipt["graph_sha256"] == graph.payload.get("semantic_digest"),
        "public release receipt graph digest differs",
    )
    require(
        receipt["bundle_content_sha256"] == bundle.get("semantic_digest"),
        "public release receipt bundle-content digest differs",
    )
    require(
        receipt["bundle_file_sha256"] == hashlib.sha256(bundle_bytes).hexdigest(),
        "public release receipt bundle-file digest differs",
    )
    validate_explorer(receipt)
    return digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bundle", nargs="?", type=Path,
        default=ROOT / "data" / "atlas_bundle.normalized.json.gz"
    )
    parser.add_argument("--canonical-db", type=Path)
    parser.add_argument("--relationship-manifest", type=Path)
    args = parser.parse_args()

    bundle_bytes = args.bundle.read_bytes()
    if args.bundle.suffix == ".gz":
        bundle_bytes = gzip.decompress(bundle_bytes)
    bundle = json.loads(bundle_bytes)
    require(set(bundle) == BUNDLE_FIELDS, "unexpected top-level bundle contract")
    require(bundle.get("schema_version") == BUNDLE_SCHEMA, "unexpected bundle schema")
    validate_brodmann_panel(bundle.get("brodmann"))
    digests = assert_bundle_integrity(bundle)
    graph = PublicRelationshipGraph(bundle["scientific_relationship_graph"])
    database_rows = (
        graph.assert_matches_database(args.canonical_db) if args.canonical_db else None
    )
    manifest_path = args.relationship_manifest or ROOT / "review/normalized-relationship-manifest.json"
    manifest = validate_manifest(
        manifest_path, args.bundle, bundle, graph, bundle_bytes
    )
    print(json.dumps({
        "bundle_content_sha256": digests["bundle_semantic_digest"],
        "canonical_database_rows": database_rows,
        "graph_sha256": digests["graph_sha256"],
        "manifest_semantic_digest": manifest,
        "result_relationships": len(graph.result_relationships),
        "status": "PASS",
        "weighted_axis_summaries": len(graph.weighted_axis_summaries),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
