"""Select optimal 50-100 documents for RAGAS test corpus (J1).

Uses pipeline_results or fetch_manifest; optional quality scores; applies diversity, balance, quality.
Output: test_corpus_manifest.json. Used by Data Curator Agent - Test Corpus Selection skill.

Usage::
    python -m evaluation.ragas_agents.scripts.select_test_corpus --pipeline-results <pipeline_results_*.json>
    python -m evaluation.ragas_agents.scripts.select_test_corpus --fetch-manifest <fetch_manifest.json> --fetched-dir <fetched_at_*>
    python -m evaluation.ragas_agents.scripts.select_test_corpus --fetch-manifest <path> --fetched-dir <path> --min-docs 50 --max-docs 50
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


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_pipeline_results(path: Path) -> dict:
    """Load pipeline_results_*.json; return pages/media info."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data


def load_quality_scores(path: Path | None) -> dict[str, float]:
    """Load document_quality_scores.json; return path -> composite score (legacy)."""
    if path is None or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    docs = data.get("documents", [])
    return {d["path"]: (d.get("readability", 0) + d.get("structure", 0)) / 2 for d in docs if "path" in d}


def load_page_quality_scores(path: Path | None) -> tuple[list[dict], dict[str, float]]:
    """Load page_quality_scores.json; return (list of page docs with path/readiness/etc), path -> readiness_score."""
    if path is None or not path.exists():
        return [], {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    docs = data.get("documents", [])
    score_map = {d["path"]: float(d.get("readiness_score", 0)) for d in docs if d.get("path")}
    return docs, score_map


def load_fetch_manifest(path: Path) -> dict:
    """Load fetch_manifest.json; return full manifest."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _ns_root(ns: str) -> str:
    """Return root namespace (first segment)."""
    return ns.split(":")[0] if ns else "root"


def build_candidates_from_page_quality(
    page_docs: list[dict],
    manifest: dict,
    fetched_dir: Path,
    namespaces_exclude: set[str],
    min_page_size_bytes: int,
    min_readiness_score: float,
    min_connectivity: int,
) -> list[dict]:
    """Build page candidates from page_quality_scores.json with auto-exclude; add media from manifest."""
    candidates: list[dict] = []
    fetched_dir = Path(fetched_dir).resolve()

    for p in page_docs:
        if p.get("is_archived"):
            continue
        ns = p.get("namespace", "root")
        if ns in namespaces_exclude:
            continue
        if (p.get("readiness_score") or 0) < min_readiness_score:
            continue
        connectivity = (p.get("link_count") or 0) + (p.get("backlink_count") or 0)
        if connectivity < min_connectivity:
            continue
        size_bytes = p.get("size_bytes", 0) or 0
        if size_bytes < min_page_size_bytes:
            continue
        path_str = p.get("path", "")
        if not path_str:
            continue
        full_path = Path(path_str)
        candidates.append({
            "path": path_str,
            "namespace": ns,
            "type": "page",
            "doc_id": p.get("page_id", ""),
            "size_bytes": size_bytes,
            "exists": full_path.exists(),
            "rel_path": str(Path("page_content") / full_path.name),
        })

    for m in manifest.get("media", []):
        media_id = m.get("id", "")
        if not media_id:
            continue
        ns = _ns_root(m.get("namespace", "root"))
        if ns in namespaces_exclude:
            continue
        safe_id = media_id.replace(":", "_")
        rel_path = Path("media") / safe_id
        full_path = fetched_dir / rel_path
        size_bytes = m.get("size_bytes", 0) or 0
        candidates.append({
            "path": str(full_path),
            "namespace": ns,
            "type": "media",
            "doc_id": media_id,
            "size_bytes": size_bytes,
            "exists": full_path.exists(),
            "rel_path": str(rel_path),
            "extension": m.get("extension", ""),
        })
    return candidates


def build_candidates_from_fetch_manifest(
    manifest: dict,
    fetched_dir: Path,
    namespaces_exclude: set[str],
    min_page_size_bytes: int,
) -> list[dict]:
    """Build candidate list from fetch_manifest pages and media. Excludes junk namespaces and tiny pages."""
    candidates: list[dict] = []
    fetched_dir = Path(fetched_dir).resolve()

    # Pages: page_content/<id>.txt
    for p in manifest.get("pages", []):
        page_id = p.get("id", "")
        if not page_id:
            continue
        ns = _ns_root(p.get("namespace", "root"))
        if ns in namespaces_exclude:
            continue
        size_bytes = p.get("size_bytes", 0) or 0
        if size_bytes < min_page_size_bytes:
            continue
        safe_id = page_id.replace(":", "_")
        rel_path = Path("page_content") / f"{safe_id}.txt"
        full_path = fetched_dir / rel_path
        candidates.append({
            "path": str(full_path),
            "namespace": ns,
            "type": "page",
            "doc_id": page_id,
            "size_bytes": size_bytes,
            "exists": full_path.exists(),
            "rel_path": str(rel_path),
        })

    # Media: media/<id with : -> _> (e.g. class:docker_kollision.jpg -> media/class_docker_kollision.jpg)
    for m in manifest.get("media", []):
        media_id = m.get("id", "")
        if not media_id:
            continue
        ns = _ns_root(m.get("namespace", "root"))
        if ns in namespaces_exclude:
            continue
        safe_id = media_id.replace(":", "_")
        rel_path = Path("media") / safe_id
        full_path = fetched_dir / rel_path
        size_bytes = m.get("size_bytes", 0) or 0
        candidates.append({
            "path": str(full_path),
            "namespace": ns,
            "type": "media",
            "doc_id": media_id,
            "size_bytes": size_bytes,
            "exists": full_path.exists(),
            "rel_path": str(rel_path),
            "extension": m.get("extension", ""),
        })
    return candidates


def build_candidate_list(pipeline_data: dict, preprocessed_base: Path) -> list[dict]:
    """Build list of candidate docs from pipeline and preprocessed dir."""
    candidates = []
    preproc = pipeline_data.get("preprocessing", {})
    pages_info = preproc.get("pages", {})
    namespaces = pages_info.get("namespaces", {})

    # Preprocessed dir: pages/ and media/
    for ns, count in namespaces.items():
        for i in range(min(count, 20)):
            # Placeholder: we don't have exact paths in pipeline_results; use preprocessed_base
            candidates.append({"namespace": ns, "type": "page", "doc_id": f"{ns}_{i}", "path_placeholder": True})

    # If we have actual preprocessed dir, scan it
    if preprocessed_base.exists():
        candidates = []
        seen_ns: dict[str, int] = {}
        for md in preprocessed_base.rglob("*.md"):
            rel = md.relative_to(preprocessed_base)
            parts = rel.parts
            ns = parts[0] if len(parts) > 1 else "root"
            seen_ns[ns] = seen_ns.get(ns, 0) + 1
            candidates.append({
                "path": str(md),
                "namespace": ns,
                "type": "page" if "pages" in parts else "media",
                "doc_id": str(rel).replace("\\", "/").replace(".md", ""),
            })

    return candidates


def _priority_index(ns: str, namespace_priority: list[str]) -> int:
    """Lower = higher priority. Unknown namespace goes to end."""
    ns_root = _ns_root(ns)
    try:
        return namespace_priority.index(ns_root)
    except ValueError:
        return len(namespace_priority)


def select_corpus(
    candidates: list[dict],
    quality_scores: dict[str, float],
    min_docs: int,
    max_docs: int,
    namespace_priority: list[str] | None = None,
    media_ratio: float = 0.2,
) -> list[dict]:
    """Select up to max_docs with page/media balance, namespace diversity and quality."""
    priority = namespace_priority or []

    def score(c: dict) -> float:
        p = c.get("path", "")
        q = quality_scores.get(p, 0.5)
        if q != 0.5:
            return q
        size = c.get("size_bytes", 0) or 0
        if size > 0:
            q = min(1.0, 0.3 + 0.7 * (min(size, 50000) / 50000))
        if c.get("exists", True):
            q += 0.1
        return q

    pages = [c for c in candidates if c.get("type") == "page"]
    media = [c for c in candidates if c.get("type") == "media"]
    media_slots = max(0, min(len(media), round(max_docs * media_ratio)))
    page_slots = max(0, max_docs - media_slots)

    def take_with_diversity(pool: list[dict], slot_count: int, key_score) -> list[dict]:
        sorted_pool = sorted(pool, key=key_score)
        selected: list[dict] = []
        ns_counts: dict[str, int] = {}
        cap_per_ns = max(3, slot_count // 8)
        for c in sorted_pool:
            if len(selected) >= slot_count:
                break
            ns = _ns_root(c.get("namespace", "root"))
            if ns_counts.get(ns, 0) >= cap_per_ns:
                continue
            selected.append(c)
            ns_counts[ns] = ns_counts.get(ns, 0) + 1
        while len(selected) < slot_count and sorted_pool:
            for c in sorted_pool:
                if c not in selected and len(selected) < slot_count:
                    selected.append(c)
                    break
            else:
                break
        return selected[:slot_count]

    def key_page(c: dict) -> tuple[int, float]:
        return (_priority_index(c.get("namespace", ""), priority), -score(c))

    def key_media(c: dict) -> tuple[int, float]:
        return (_priority_index(c.get("namespace", ""), priority), -(c.get("size_bytes", 0) or 0))

    selected_pages = take_with_diversity(pages, page_slots, key_page)
    selected_media = take_with_diversity(media, media_slots, key_media)
    combined = selected_pages + selected_media
    if len(combined) < min_docs and len(candidates) >= min_docs:
        for c in candidates:
            if c not in combined and len(combined) < min_docs:
                combined.append(c)
    return combined[:max_docs]


def main() -> int:
    parser = argparse.ArgumentParser(description="Select test corpus (50-100 docs) for RAGAS")
    parser.add_argument("--pipeline-results", type=Path, default=None, help="Path to pipeline_results_*.json")
    parser.add_argument("--fetch-manifest", type=Path, default=None, help="Path to fetch_manifest.json (fetched_at_* dir)")
    parser.add_argument("--fetched-dir", type=Path, default=None, help="Path to fetched_at_* directory (use with --fetch-manifest)")
    parser.add_argument("--quality-scores", type=Path, default=None, help="Path to page_quality_scores.json (or document_quality_scores.json fallback)")
    parser.add_argument("--preprocessed-dir", type=Path, default=None, help="Path to preprocessed directory (to list actual paths)")
    parser.add_argument("--min-docs", type=int, default=50, help="Minimum documents")
    parser.add_argument("--max-docs", type=int, default=100, help="Maximum documents")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output manifest path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    tc = config.get("test_corpus", {})
    min_docs = args.min_docs or tc.get("min_docs", 50)
    max_docs = args.max_docs or tc.get("max_docs", 100)

    namespaces_exclude = set(tc.get("namespaces_exclude", ["playground", "wiki"]))
    namespaces_priority = tc.get("namespaces_priority", [])
    min_page_size_bytes = tc.get("min_page_size_bytes", 500)
    media_ratio = float(tc.get("media_ratio", 0.2))
    auto_thresholds = tc.get("auto_exclude_thresholds", {})
    min_readiness_score = float(auto_thresholds.get("min_readiness_score", 0.3))
    min_connectivity = int(auto_thresholds.get("min_connectivity", 1))

    use_fetch = args.fetch_manifest is not None
    if use_fetch:
        if not args.fetch_manifest.exists():
            logger.error("Fetch manifest not found: %s", args.fetch_manifest)
            return 1
        fetched_dir = args.fetched_dir or args.fetch_manifest.parent
        fetched_dir = Path(fetched_dir).resolve()
        if not fetched_dir.is_dir():
            logger.error("Fetched directory not found: %s", fetched_dir)
            return 1
        manifest_data = load_fetch_manifest(args.fetch_manifest)
        out_dir = config.get("paths", {}).get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        page_quality_path = args.quality_scores or out_dir / "page_quality_scores.json"
        page_docs, quality_scores = load_page_quality_scores(page_quality_path)
        if page_docs:
            candidates = build_candidates_from_page_quality(
                page_docs,
                manifest_data,
                fetched_dir,
                namespaces_exclude,
                min_page_size_bytes,
                min_readiness_score,
                min_connectivity,
            )
            logger.info(
                "Candidates from page_quality_scores (min_readiness=%.2f, min_connectivity=%d): %d pages, %d media",
                min_readiness_score,
                min_connectivity,
                sum(1 for c in candidates if c.get("type") == "page"),
                sum(1 for c in candidates if c.get("type") == "media"),
            )
        else:
            quality_scores = load_quality_scores(args.quality_scores)
            candidates = build_candidates_from_fetch_manifest(
                manifest_data, fetched_dir, namespaces_exclude, min_page_size_bytes
            )
            n_pages = sum(1 for c in candidates if c.get("type") == "page")
            n_media = sum(1 for c in candidates if c.get("type") == "media")
            logger.info("Candidates after filters: %d pages, %d media (excluded: %s)", n_pages, n_media, namespaces_exclude)
        selected = select_corpus(
            candidates, quality_scores, min_docs, max_docs,
            namespace_priority=namespaces_priority, media_ratio=media_ratio,
        )
    else:
        if args.pipeline_results is None or not args.pipeline_results.exists():
            logger.error("Pipeline results not found (use --pipeline-results or --fetch-manifest + --fetched-dir)")
            return 1
        pipeline_path = args.pipeline_results.resolve()
        pipeline_data = load_pipeline_results(pipeline_path)
        preprocessed_base = args.preprocessed_dir
        if preprocessed_base is None:
            prep = pipeline_data.get("preprocessing", {}).get("output_dir")
            preprocessed_base = Path(prep) if prep else pipeline_path.parent / "preprocessed"
        preprocessed_base = Path(preprocessed_base).resolve() if preprocessed_base else Path()

        quality_scores = load_quality_scores(args.quality_scores)
        candidates = build_candidate_list(pipeline_data, preprocessed_base)
        selected = select_corpus(
            candidates, quality_scores, min_docs, max_docs,
            namespace_priority=namespaces_priority, media_ratio=media_ratio,
        )

    manifest = {
        "min_docs": min_docs,
        "max_docs": max_docs,
        "selected_count": len(selected),
        "documents": selected,
    }

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "test_corpus_manifest.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    docs_out = []
    for d in manifest["documents"]:
        doc = {k: v for k, v in d.items() if k not in ("exists",)}
        docs_out.append(doc)
    manifest["documents"] = docs_out
    if use_fetch:
        manifest["source"] = "fetch_manifest"
        manifest["fetch_id"] = manifest_data.get("fetch_id", "")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Wrote test_corpus_manifest.json with %d documents to %s", len(selected), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
