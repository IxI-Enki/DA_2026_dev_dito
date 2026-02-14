"""Analyze fetch_manifest.json and compute page/media quality scores for test corpus selection.

Reads page metadata (size_bytes, namespace, link_count, backlink_count, has_history)
and computes content_score, connectivity_score, readiness_score. Outputs page_quality_scores.json
and media_quality_scores.json. Used by Data Curator - precedes select_test_corpus.

Usage::
    python -m evaluation.ragas_agents.scripts.analyze_manifest --fetch-manifest <fetch_manifest.json>
    python -m evaluation.ragas_agents.scripts.analyze_manifest --fetch-manifest <path> --fetched-dir <path> --output <dir>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
RAGAS_AGENTS_ROOT = SCRIPT_DIR.parent
REPO_ROOT = RAGAS_AGENTS_ROOT.parent.parent

# Normalization caps for scores (bytes, links)
MAX_SIZE_BYTES = 100_000
MAX_CONNECTIVITY = 50


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ns_root(ns: str) -> str:
    return ns.split(":")[0] if ns else "root"


def analyze_pages(manifest: dict, config: dict) -> list[dict]:
    """Compute quality scores for each page from manifest metadata."""
    tc = config.get("test_corpus", {})
    exclude_ns = set(tc.get("namespaces_exclude", ["playground", "wiki"]))
    pages = manifest.get("pages", [])
    results = []

    for p in pages:
        page_id = p.get("id", "")
        if not page_id:
            continue
        ns = ns_root(p.get("namespace", "root"))
        size_bytes = p.get("size_bytes", 0) or 0
        link_count = p.get("link_count", 0) or 0
        backlink_count = p.get("backlink_count", 0) or 0
        has_history = p.get("has_history", False)
        has_backlinks = p.get("has_backlinks", False)

        connectivity = link_count + backlink_count
        content_score = min(1.0, size_bytes / MAX_SIZE_BYTES) if size_bytes > 0 else 0.0
        connectivity_score = min(1.0, connectivity / MAX_CONNECTIVITY) if connectivity > 0 else 0.0
        history_bonus = 0.1 if has_history or has_backlinks else 0.0

        namespace_penalty = 0.0
        if ns in exclude_ns:
            namespace_penalty = -1.0 if ns == "playground" else -0.5
        is_archived = ns == "archive" or page_id.startswith("archive:")

        readiness_score = max(
            0.0,
            min(
                1.0,
                0.4 * content_score
                + 0.35 * connectivity_score
                + 0.15 * (0.5 if size_bytes >= 500 else 0.0)
                + history_bonus
                + namespace_penalty,
            ),
        )

        results.append({
            "page_id": page_id,
            "namespace": ns,
            "size_bytes": size_bytes,
            "link_count": link_count,
            "backlink_count": backlink_count,
            "content_score": round(content_score, 4),
            "connectivity_score": round(connectivity_score, 4),
            "readiness_score": round(readiness_score, 4),
            "is_archived": is_archived,
            "path": "",  # filled by caller if fetched_dir known
        })
    return results


def analyze_media(manifest: dict, config: dict) -> list[dict]:
    """Compute simple quality scores for media entries."""
    tc = config.get("test_corpus", {})
    exclude_ns = set(tc.get("namespaces_exclude", ["playground", "wiki"]))
    media_list = manifest.get("media", [])
    results = []

    max_media_size = 5_000_000
    for m in media_list:
        media_id = m.get("id", "")
        if not media_id:
            continue
        ns = ns_root(m.get("namespace", "root"))
        if ns in exclude_ns:
            continue
        size_bytes = m.get("size_bytes", 0) or 0
        ext = m.get("extension", "")
        score = min(1.0, size_bytes / max_media_size) if size_bytes > 0 else 0.0
        results.append({
            "media_id": media_id,
            "namespace": ns,
            "size_bytes": size_bytes,
            "extension": ext,
            "quality_score": round(score, 4),
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze fetch_manifest and output quality scores")
    parser.add_argument("--fetch-manifest", type=Path, required=True, help="Path to fetch_manifest.json")
    parser.add_argument("--fetched-dir", type=Path, default=None, help="Path to fetched_at_* (optional, for path in output)")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output directory for JSON files")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    manifest_path = args.fetch_manifest.resolve()
    if not manifest_path.exists():
        logger.error("Fetch manifest not found: %s", manifest_path)
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    pages = analyze_pages(manifest, config)
    media = analyze_media(manifest, config)

    fetched_dir = args.fetched_dir or manifest_path.parent
    fetched_dir = Path(fetched_dir).resolve()
    for r in pages:
        safe_id = r["page_id"].replace(":", "_")
        r["path"] = str(fetched_dir / "page_content" / f"{safe_id}.txt")

    out_dir = args.output
    if out_dir is None:
        out_dir = config.get("paths", {}).get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    page_out = out_dir / "page_quality_scores.json"
    with open(page_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": "fetch_manifest",
                "fetch_id": manifest.get("fetch_id", ""),
                "documents": pages,
                "aggregate": {
                    "total": len(pages),
                    "avg_readiness": round(sum(p["readiness_score"] for p in pages) / len(pages), 4) if pages else 0,
                },
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info("Wrote page_quality_scores.json with %d pages to %s", len(pages), page_out)

    media_out = out_dir / "media_quality_scores.json"
    with open(media_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": "fetch_manifest",
                "fetch_id": manifest.get("fetch_id", ""),
                "documents": media,
                "aggregate": {"total": len(media)},
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info("Wrote media_quality_scores.json with %d media to %s", len(media), media_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
