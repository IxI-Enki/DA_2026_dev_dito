"""
Content Evaluator
================
Simplified interface for content evaluation before embedding.
Integrates with existing analyzers for quality scoring.

Usage:
    from evaluator import ContentEvaluator
    
    evaluator = ContentEvaluator(fetch_dir="data/fetched/fetch_123")
    report = evaluator.evaluate()
    evaluator.save_report(Path("data/evaluated/"))
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import EvaluationConfig, get_config

# =============================================================================
# Evaluation Result Data Structures
# =============================================================================


@dataclass
class PageEvaluation:
    """Evaluation result for a single page"""

    page_id: str
    quality_score: float = 0.0  # 0.0-1.0 overall quality
    embedding_recommendation: str = "include"  # include, exclude, review

    # Flags
    flags: List[Dict[str, str]] = field(default_factory=list)

    # Quality components
    content_quality: float = 0.0
    structure_quality: float = 0.0
    link_quality: float = 0.0
    freshness_score: float = 0.0

    # Content metrics
    word_count: int = 0
    char_count: int = 0
    heading_count: int = 0
    link_count: int = 0
    code_block_count: int = 0
    table_count: int = 0

    # Issues
    is_empty: bool = False
    is_stub: bool = False
    is_template_only: bool = False
    has_broken_links: bool = False
    is_orphan: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "quality_score": round(self.quality_score, 3),
            "embedding_recommendation": self.embedding_recommendation,
            "flags": self.flags,
            "scores": {
                "content": round(self.content_quality, 3),
                "structure": round(self.structure_quality, 3),
                "links": round(self.link_quality, 3),
                "freshness": round(self.freshness_score, 3),
            },
            "metrics": {
                "word_count": self.word_count,
                "char_count": self.char_count,
                "heading_count": self.heading_count,
                "link_count": self.link_count,
                "code_blocks": self.code_block_count,
                "tables": self.table_count,
            },
            "issues": {
                "is_empty": self.is_empty,
                "is_stub": self.is_stub,
                "is_template_only": self.is_template_only,
                "has_broken_links": self.has_broken_links,
                "is_orphan": self.is_orphan,
            },
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report for a fetch"""

    fetch_id: str = ""
    evaluated_at: str = ""

    # Overall scores
    overall_quality: float = 0.0
    pages_evaluated: int = 0

    # Recommendation counts
    pages_to_include: int = 0
    pages_to_exclude: int = 0
    pages_to_review: int = 0

    # Issue counts
    empty_pages: int = 0
    stub_pages: int = 0
    orphan_pages: int = 0
    broken_link_count: int = 0

    # Distribution
    quality_distribution: Dict[str, int] = field(default_factory=dict)

    # Page evaluations
    page_evaluations: List[PageEvaluation] = field(default_factory=list)

    # Flagged pages (for quick access)
    flagged_pages: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.evaluated_at:
            self.evaluated_at = datetime.now().isoformat()
        if not self.quality_distribution:
            self.quality_distribution = {
                "excellent": 0,  # 0.9-1.0
                "good": 0,  # 0.7-0.9
                "fair": 0,  # 0.5-0.7
                "poor": 0,  # 0.3-0.5
                "very_poor": 0,  # 0.0-0.3
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fetch_id": self.fetch_id,
            "evaluated_at": self.evaluated_at,
            "overall": {
                "quality_score": round(self.overall_quality, 3),
                "pages_evaluated": self.pages_evaluated,
            },
            "recommendations": {
                "include": self.pages_to_include,
                "exclude": self.pages_to_exclude,
                "review": self.pages_to_review,
            },
            "issues": {
                "empty_pages": self.empty_pages,
                "stub_pages": self.stub_pages,
                "orphan_pages": self.orphan_pages,
                "broken_links": self.broken_link_count,
            },
            "quality_distribution": self.quality_distribution,
            "flagged_pages": self.flagged_pages,
            "pages": [p.to_dict() for p in self.page_evaluations],
        }


# =============================================================================
# ContentEvaluator Class
# =============================================================================


class ContentEvaluator:
    """
    Evaluates fetched content quality for embedding suitability.

    Scores each page on:
    - Content quality (length, substance, clarity)
    - Structure quality (headings, formatting)
    - Link quality (valid links, not orphaned)
    - Freshness (age, update frequency)
    """

    # Quality thresholds
    MIN_CONTENT_LENGTH = 100  # Chars - below is empty
    STUB_THRESHOLD = 500  # Chars - below is stub
    MIN_QUALITY_FOR_INCLUDE = 0.5  # Below this = exclude
    REVIEW_THRESHOLD = 0.7  # Below this = review

    def __init__(
        self,
        fetch_dir: str | None = None,
        config: EvaluationConfig | None = None,
        verbose: bool = True,
    ):
        self.verbose = verbose

        # Get config - evaluation can work without full config
        if config:
            self.config = config
        else:
            try:
                self.config = get_config()
            except (ValueError, FileNotFoundError) as e:
                # Basic evaluation doesn't need full config
                self.log(f"[WARN] Config load warning: {e}")
                self.log("[INFO] Using minimal config for evaluation")
                self.config = None

        # Set fetch directory
        if fetch_dir:
            self.fetch_dir = Path(fetch_dir)
        elif (
            self.config
            and hasattr(self.config, "fetched_data_dir")
            and self.config.fetched_data_dir
        ):
            self.fetch_dir = Path(self.config.fetched_data_dir)
        else:
            raise ValueError("No fetch directory specified")

        # Paths within fetch
        self.page_content_dir = self.fetch_dir / "page_content"
        self.page_metadata_dir = self.fetch_dir / "page_metadata"
        self.page_links_dir = self.fetch_dir / "page_links"
        self.page_html_dir = self.fetch_dir / "page_html"
        self.page_backlinks_dir = self.fetch_dir / "page_backlinks"

        # Results
        self.report: EvaluationReport | None = None

        # Internal tracking
        self._all_page_ids: Set[str] = set()
        self._linked_pages: Set[str] = set()
        self._broken_links: Dict[str, List[str]] = {}

    def log(self, message: str):
        """Print if verbose"""
        if self.verbose:
            print(message)

    # -------------------------------------------------------------------------
    # Main Evaluation
    # -------------------------------------------------------------------------

    def evaluate(self) -> EvaluationReport:
        """
        Run complete evaluation.

        Returns:
            EvaluationReport with all results
        """
        self.log("\n" + "=" * 60)
        self.log("CONTENT EVALUATION")
        self.log("=" * 60)
        self.log(f"Fetch: {self.fetch_dir.name}")

        # Initialize report
        self.report = EvaluationReport(
            fetch_id=self.fetch_dir.name,
        )

        # Collect all pages
        self._collect_pages()

        # Build link graph for orphan detection
        self._build_link_graph()

        # Evaluate each page
        self.log("\n[1/3] Evaluating pages...")
        for page_id in sorted(self._all_page_ids):
            evaluation = self._evaluate_page(page_id)
            self.report.page_evaluations.append(evaluation)

        # Calculate aggregate stats
        self.log("\n[2/3] Calculating statistics...")
        self._calculate_statistics()

        # Determine flagged pages
        self.log("\n[3/3] Identifying flagged pages...")
        self._identify_flagged()

        self.log("\n" + "-" * 60)
        self.log("EVALUATION COMPLETE")
        self.log("-" * 60)
        self.log(f"  Pages evaluated: {self.report.pages_evaluated}")
        self.log(f"  Overall quality: {self.report.overall_quality:.2f}")
        self.log(f"  To include: {self.report.pages_to_include}")
        self.log(f"  To exclude: {self.report.pages_to_exclude}")
        self.log(f"  To review: {self.report.pages_to_review}")
        self.log(f"  Flagged: {len(self.report.flagged_pages)}")
        self.log("=" * 60)

        return self.report

    def _collect_pages(self):
        """Collect all page IDs from content directory"""
        if not self.page_content_dir.exists():
            raise FileNotFoundError(f"Page content directory not found: {self.page_content_dir}")

        for content_file in self.page_content_dir.glob("*.txt"):
            page_id = content_file.stem.replace("_", ":")
            self._all_page_ids.add(page_id)

        self.log(f"  Found {len(self._all_page_ids)} pages to evaluate")

    def _build_link_graph(self):
        """Build link graph for orphan detection"""
        if not self.page_links_dir.exists():
            return

        for links_file in self.page_links_dir.glob("*_links.json"):
            try:
                with open(links_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Track link targets
                for link in data.get("internal_links", []):
                    target = link.get("target", "")
                    if target:
                        self._linked_pages.add(target)

                    # Track broken links
                    if not link.get("exists", True):
                        page_id = data.get("page_id", "")
                        if page_id not in self._broken_links:
                            self._broken_links[page_id] = []
                        self._broken_links[page_id].append(target)
            except (OSError, json.JSONDecodeError):
                pass

        self.log(f"  Built link graph: {len(self._linked_pages)} linked pages")

    # -------------------------------------------------------------------------
    # Page Evaluation
    # -------------------------------------------------------------------------

    def _evaluate_page(self, page_id: str) -> PageEvaluation:
        """Evaluate a single page"""
        safe_name = page_id.replace(":", "_").replace("/", "_")

        evaluation = PageEvaluation(page_id=page_id)

        # Read content
        content_file = self.page_content_dir / f"{safe_name}.txt"
        content = ""
        if content_file.exists():
            content = content_file.read_text(encoding="utf-8")

        # Basic metrics
        evaluation.char_count = len(content)
        evaluation.word_count = len(content.split())

        # Check for empty/stub
        if evaluation.char_count < self.MIN_CONTENT_LENGTH:
            evaluation.is_empty = True
            evaluation.flags.append({"type": "empty", "message": "Page has minimal content"})
        elif evaluation.char_count < self.STUB_THRESHOLD:
            evaluation.is_stub = True
            evaluation.flags.append(
                {"type": "stub", "message": f"Page is a stub ({evaluation.char_count} chars)"}
            )

        # Check for template-only
        if self._is_template_only(content):
            evaluation.is_template_only = True
            evaluation.flags.append(
                {"type": "template", "message": "Page contains only template markup"}
            )

        # Count structure elements
        evaluation.heading_count = (
            content.count("====") + content.count("===") + content.count("==")
        )
        evaluation.code_block_count = content.count("<code>") + content.count("<file>")
        evaluation.table_count = content.count("^") // 2  # Rough estimate

        # Get link info
        links_file = self.page_links_dir / f"{safe_name}_links.json"
        if links_file.exists():
            try:
                with open(links_file, encoding="utf-8") as f:
                    links_data = json.load(f)
                evaluation.link_count = links_data.get("summary", {}).get("total_links", 0)
            except (OSError, json.JSONDecodeError):
                pass

        # Check broken links
        if page_id in self._broken_links:
            evaluation.has_broken_links = True
            evaluation.flags.append(
                {
                    "type": "broken_links",
                    "message": f"Has {len(self._broken_links[page_id])} broken links",
                }
            )

        # Check orphan status
        if page_id not in self._linked_pages and page_id != "start":
            evaluation.is_orphan = True
            evaluation.flags.append({"type": "orphan", "message": "No pages link to this page"})

        # Calculate quality scores
        evaluation.content_quality = self._score_content(content, evaluation)
        evaluation.structure_quality = self._score_structure(evaluation)
        evaluation.link_quality = self._score_links(evaluation)
        evaluation.freshness_score = self._score_freshness(page_id)

        # Calculate overall score (weighted average)
        evaluation.quality_score = (
            evaluation.content_quality * 0.4
            + evaluation.structure_quality * 0.2
            + evaluation.link_quality * 0.2
            + evaluation.freshness_score * 0.2
        )

        # Determine recommendation
        if evaluation.quality_score < self.MIN_QUALITY_FOR_INCLUDE or evaluation.is_empty:
            evaluation.embedding_recommendation = "exclude"
        elif evaluation.quality_score < self.REVIEW_THRESHOLD or evaluation.is_stub:
            evaluation.embedding_recommendation = "review"
        else:
            evaluation.embedding_recommendation = "include"

        return evaluation

    def _is_template_only(self, content: str) -> bool:
        """Check if content is just template markup"""
        # Remove common wiki markup
        cleaned = content
        for pattern in ["{{", "}}", "[[", "]]", "====", "===", "==", "  *", "  -"]:
            cleaned = cleaned.replace(pattern, "")

        # Check if remaining content is minimal
        return len(cleaned.strip()) < 50

    def _score_content(self, content: str, evaluation: PageEvaluation) -> float:
        """Score content quality (0.0-1.0)"""
        if evaluation.is_empty:
            return 0.0

        score = 0.0

        # Length score (up to 0.4)
        if evaluation.char_count > 2000:
            score += 0.4
        elif evaluation.char_count > 1000:
            score += 0.3
        elif evaluation.char_count > 500:
            score += 0.2
        else:
            score += 0.1

        # Word density (up to 0.3)
        if evaluation.word_count > 0:
            avg_word_len = evaluation.char_count / evaluation.word_count
            if 4 <= avg_word_len <= 8:  # Normal word length
                score += 0.3
            else:
                score += 0.1

        # Content variety (up to 0.3)
        has_variety = (
            evaluation.heading_count > 0
            or evaluation.code_block_count > 0
            or evaluation.table_count > 0
        )
        if has_variety:
            score += 0.3
        elif evaluation.char_count > 500:
            score += 0.1

        return min(score, 1.0)

    def _score_structure(self, evaluation: PageEvaluation) -> float:
        """Score structure quality (0.0-1.0)"""
        score = 0.0

        # Headings
        if evaluation.heading_count >= 3:
            score += 0.4
        elif evaluation.heading_count >= 1:
            score += 0.2

        # Code blocks
        if evaluation.code_block_count > 0:
            score += 0.3

        # Tables
        if evaluation.table_count > 0:
            score += 0.3

        return min(score, 1.0)

    def _score_links(self, evaluation: PageEvaluation) -> float:
        """Score link quality (0.0-1.0)"""
        score = 0.5  # Base score

        # Good: has links
        if evaluation.link_count > 0:
            score += 0.2

        # Good: not orphaned
        if not evaluation.is_orphan:
            score += 0.2

        # Bad: broken links
        if evaluation.has_broken_links:
            score -= 0.3

        return max(0.0, min(score, 1.0))

    def _score_freshness(self, page_id: str) -> float:
        """Score freshness (0.0-1.0) based on metadata"""
        safe_name = page_id.replace(":", "_").replace("/", "_")

        # Try to load metadata
        meta_file = self.page_metadata_dir / f"{safe_name}_info.json"
        if not meta_file.exists():
            return 0.5  # Unknown = neutral

        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)

            revision = meta.get("revision", 0)
            if revision:
                # Score based on age (assuming revision is Unix timestamp)
                now = datetime.now().timestamp()
                age_days = (now - revision) / 86400

                if age_days < 30:
                    return 1.0
                elif age_days < 180:
                    return 0.8
                elif age_days < 365:
                    return 0.6
                elif age_days < 730:
                    return 0.4
                else:
                    return 0.2
        except (OSError, json.JSONDecodeError):
            pass

        return 0.5

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def _calculate_statistics(self):
        """Calculate aggregate statistics from evaluations"""
        if not self.report or not self.report.page_evaluations:
            return

        total_quality = 0.0

        for eval in self.report.page_evaluations:
            total_quality += eval.quality_score

            # Count recommendations
            if eval.embedding_recommendation == "include":
                self.report.pages_to_include += 1
            elif eval.embedding_recommendation == "exclude":
                self.report.pages_to_exclude += 1
            else:
                self.report.pages_to_review += 1

            # Count issues
            if eval.is_empty:
                self.report.empty_pages += 1
            if eval.is_stub:
                self.report.stub_pages += 1
            if eval.is_orphan:
                self.report.orphan_pages += 1
            if eval.has_broken_links:
                self.report.broken_link_count += len(self._broken_links.get(eval.page_id, []))

            # Quality distribution
            if eval.quality_score >= 0.9:
                self.report.quality_distribution["excellent"] += 1
            elif eval.quality_score >= 0.7:
                self.report.quality_distribution["good"] += 1
            elif eval.quality_score >= 0.5:
                self.report.quality_distribution["fair"] += 1
            elif eval.quality_score >= 0.3:
                self.report.quality_distribution["poor"] += 1
            else:
                self.report.quality_distribution["very_poor"] += 1

        self.report.pages_evaluated = len(self.report.page_evaluations)
        if self.report.pages_evaluated > 0:
            self.report.overall_quality = total_quality / self.report.pages_evaluated

    def _identify_flagged(self):
        """Identify pages needing attention"""
        if not self.report:
            return
        for eval in self.report.page_evaluations:
            if eval.flags:
                self.report.flagged_pages.append(eval.page_id)

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def save_report(self, output_dir: Path) -> Path:
        """Save evaluation report to JSON"""
        if not self.report:
            self.evaluate()
        if not self.report:
            raise RuntimeError("Evaluation did not produce a report")
        report = self.report

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / f"evaluation_{report.fetch_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        self.log(f"\n[OK] Report saved: {report_path}")
        return report_path

    def get_pages_to_embed(self) -> List[str]:
        """Get list of pages recommended for embedding"""
        if not self.report:
            self.evaluate()
        if not self.report:
            return []
        report = self.report
        return [
            eval.page_id
            for eval in report.page_evaluations
            if eval.embedding_recommendation == "include"
        ]

    def get_pages_to_review(self) -> List[PageEvaluation]:
        """Get pages that need human review"""
        if not self.report:
            self.evaluate()
        if not self.report:
            return []
        report = self.report
        return [
            eval for eval in report.page_evaluations if eval.embedding_recommendation == "review"
        ]


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate fetched content")
    parser.add_argument("fetch_dir", nargs="?", help="Path to fetch directory")
    parser.add_argument("--output", "-o", help="Output directory for report")
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce output")

    args = parser.parse_args()

    evaluator = ContentEvaluator(
        fetch_dir=args.fetch_dir,
        verbose=not args.quiet,
    )

    report = evaluator.evaluate()

    if args.output:
        evaluator.save_report(Path(args.output))
    else:
        # Print summary
        print("\nPages to include:")
        for pid in evaluator.get_pages_to_embed()[:10]:
            print(f"  - {pid}")

        print("\nPages to review:")
        for eval in evaluator.get_pages_to_review()[:5]:
            print(f"  - {eval.page_id}: {eval.flags}")
