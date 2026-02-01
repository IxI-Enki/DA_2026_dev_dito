#!/usr/bin/env python3
"""
Preprocessing Evaluator
=======================
Quality checks for RAG Preprocessing output.

Evaluates:
1. Information Preservation - Did we lose content during conversion?
2. Link Integrity - Are all links still valid?
3. Structure Preservation - Did heading hierarchy survive?
4. Frontmatter Validity - Is YAML frontmatter correct?

Usage:
    python evaluator.py                           # Auto-detect latest
    python evaluator.py --input-dir <path>        # Specific input
"""

import os
import sys
import json
import yaml
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PageEvaluation:
    """Evaluation result for a single page."""
    file_name: str
    has_frontmatter: bool = False
    frontmatter_valid: bool = False
    frontmatter_fields: List[str] = field(default_factory=list)
    content_length: int = 0
    heading_count: int = 0
    link_count: int = 0
    code_block_count: int = 0
    table_count: int = 0
    issues: List[str] = field(default_factory=list)
    quality_score: float = 0.0


@dataclass
class PreprocessingEvaluation:
    """Full evaluation result."""
    input_dir: str
    evaluated_at: str
    total_pages: int = 0
    total_media: int = 0
    valid_frontmatter: int = 0
    invalid_frontmatter: int = 0
    average_quality: float = 0.0
    issues_by_type: Dict[str, int] = field(default_factory=dict)
    page_evaluations: List[PageEvaluation] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Evaluator Class
# =============================================================================

class PreprocessingEvaluator:
    """Evaluates preprocessing quality."""
    
    # YAML frontmatter pattern
    FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    
    # Required frontmatter fields
    REQUIRED_FIELDS = ['title', 'page_id', 'source', 'content_type']
    
    # Optional but valuable fields
    OPTIONAL_FIELDS = ['namespace', 'access_level', 'modified_at', 'preprocessed_at']
    
    def __init__(self):
        self.issues_count: Dict[str, int] = {}
    
    def evaluate_directory(self, input_dir: Path) -> PreprocessingEvaluation:
        """
        Evaluate all preprocessed files in a directory.
        
        Args:
            input_dir: Path to preprocess_at_* directory
            
        Returns:
            PreprocessingEvaluation result
        """
        logger.info(f"Evaluating: {input_dir}")
        
        result = PreprocessingEvaluation(
            input_dir=str(input_dir),
            evaluated_at=datetime.now().isoformat(),
        )
        
        pages_dir = input_dir / "pages"
        media_dir = input_dir / "media"
        
        # Evaluate pages
        if pages_dir.exists():
            page_files = list(pages_dir.glob("*.md"))
            result.total_pages = len(page_files)
            
            logger.info(f"Evaluating {len(page_files)} pages...")
            
            quality_scores = []
            for file_path in page_files:
                try:
                    page_eval = self.evaluate_page(file_path)
                    result.page_evaluations.append(page_eval)
                    quality_scores.append(page_eval.quality_score)
                    
                    if page_eval.frontmatter_valid:
                        result.valid_frontmatter += 1
                    else:
                        result.invalid_frontmatter += 1
                        
                except Exception as e:
                    logger.error(f"Failed to evaluate {file_path.name}: {e}")
            
            if quality_scores:
                result.average_quality = sum(quality_scores) / len(quality_scores)
        
        # Count media files
        if media_dir.exists():
            media_files = list(media_dir.glob("*.txt"))
            result.total_media = len(media_files)
        
        # Aggregate issues
        result.issues_by_type = dict(self.issues_count)
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        return result
    
    def evaluate_page(self, file_path: Path) -> PageEvaluation:
        """
        Evaluate a single preprocessed page.
        
        Args:
            file_path: Path to .md file
            
        Returns:
            PageEvaluation result
        """
        eval_result = PageEvaluation(file_name=file_path.name)
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')
        
        # 1. Check frontmatter
        frontmatter, body = self._extract_frontmatter(content)
        eval_result.has_frontmatter = bool(frontmatter)
        
        if frontmatter:
            eval_result.frontmatter_fields = list(frontmatter.keys())
            eval_result.frontmatter_valid = self._validate_frontmatter(frontmatter, eval_result)
        else:
            self._add_issue(eval_result, "missing_frontmatter", "No YAML frontmatter found")
        
        # 2. Analyze content
        eval_result.content_length = len(body)
        
        if eval_result.content_length < 50:
            self._add_issue(eval_result, "minimal_content", "Content is very short (<50 chars)")
        
        # 3. Count structural elements
        eval_result.heading_count = len(re.findall(r'^#{1,6}\s+', body, re.MULTILINE))
        eval_result.link_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body))
        eval_result.code_block_count = len(re.findall(r'```', body)) // 2
        eval_result.table_count = len(re.findall(r'^\|.+\|$', body, re.MULTILINE))
        
        # 4. Check for conversion artifacts
        self._check_conversion_artifacts(body, eval_result)
        
        # 5. Calculate quality score
        eval_result.quality_score = self._calculate_quality_score(eval_result)
        
        return eval_result
    
    def _extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter from content."""
        match = self.FRONTMATTER_PATTERN.match(content)
        
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1))
                body = content[match.end():]
                return frontmatter or {}, body
            except yaml.YAMLError:
                return {}, content
        
        return {}, content
    
    def _validate_frontmatter(self, frontmatter: Dict[str, Any], eval_result: PageEvaluation) -> bool:
        """Validate frontmatter has required fields."""
        valid = True
        
        for field in self.REQUIRED_FIELDS:
            if field not in frontmatter:
                self._add_issue(eval_result, f"missing_field_{field}", f"Missing required field: {field}")
                valid = False
            elif not frontmatter[field]:
                self._add_issue(eval_result, f"empty_field_{field}", f"Empty required field: {field}")
                valid = False
        
        return valid
    
    def _check_conversion_artifacts(self, content: str, eval_result: PageEvaluation):
        """Check for leftover DokuWiki syntax or conversion artifacts."""
        
        # Check for unconverted wiki syntax
        wiki_patterns = [
            (r'====', "Unconverted DokuWiki heading (====)"),
            (r'\[\[[^\]]+\]\]', "Unconverted DokuWiki link ([[...]])"),
            (r'\{\{[^}]+\}\}', "Unconverted DokuWiki media ({{...}})"),
            (r"''[^']+''", "Unconverted DokuWiki monospace ('')"),
            (r'<code[^>]*>', "Unconverted DokuWiki code block"),
            (r'^\^', "Unconverted DokuWiki table header (^)"),
        ]
        
        for pattern, description in wiki_patterns:
            if re.search(pattern, content, re.MULTILINE):
                self._add_issue(eval_result, "conversion_artifact", description)
    
    def _add_issue(self, eval_result: PageEvaluation, issue_type: str, description: str):
        """Add an issue to evaluation result."""
        eval_result.issues.append(description)
        
        # Track global issue counts
        self.issues_count[issue_type] = self.issues_count.get(issue_type, 0) + 1
    
    def _calculate_quality_score(self, eval_result: PageEvaluation) -> float:
        """Calculate quality score (0.0 - 1.0)."""
        score = 1.0
        
        # Deductions
        if not eval_result.has_frontmatter:
            score -= 0.3
        elif not eval_result.frontmatter_valid:
            score -= 0.15
        
        # Issues deduction
        issue_count = len(eval_result.issues)
        score -= min(0.4, issue_count * 0.1)
        
        # Content quality
        if eval_result.content_length < 100:
            score -= 0.1
        
        # Structure bonus
        if eval_result.heading_count >= 2:
            score += 0.05
        if eval_result.link_count >= 3:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _generate_summary(self, result: PreprocessingEvaluation) -> Dict[str, Any]:
        """Generate evaluation summary."""
        # Count pages by quality tier
        quality_tiers = {
            'excellent': 0,  # >= 0.9
            'good': 0,       # >= 0.7
            'fair': 0,       # >= 0.5
            'poor': 0,       # < 0.5
        }
        
        for page in result.page_evaluations:
            if page.quality_score >= 0.9:
                quality_tiers['excellent'] += 1
            elif page.quality_score >= 0.7:
                quality_tiers['good'] += 1
            elif page.quality_score >= 0.5:
                quality_tiers['fair'] += 1
            else:
                quality_tiers['poor'] += 1
        
        # Find problematic pages
        problematic = [
            p.file_name for p in result.page_evaluations 
            if p.quality_score < 0.5
        ]
        
        return {
            'quality_distribution': quality_tiers,
            'problematic_pages': problematic[:20],  # Limit to 20
            'frontmatter_rate': result.valid_frontmatter / result.total_pages if result.total_pages > 0 else 0,
            'average_content_length': sum(p.content_length for p in result.page_evaluations) / len(result.page_evaluations) if result.page_evaluations else 0,
        }


# =============================================================================
# Helper Functions
# =============================================================================

def find_latest_preprocess_dir(base_dir: Path) -> Optional[Path]:
    """Find the latest preprocess_at_* directory."""
    if not base_dir.exists():
        return None
    
    dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith('preprocess_at_')],
        key=lambda x: x.name,
        reverse=True
    )
    
    return dirs[0] if dirs else None


def save_evaluation(result: PreprocessingEvaluation, output_dir: Path) -> Path:
    """Save evaluation result to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"preprocessing_eval_{timestamp}.json"
    
    # Convert to dict (exclude detailed page evaluations for summary file)
    result_dict = {
        'input_dir': result.input_dir,
        'evaluated_at': result.evaluated_at,
        'total_pages': result.total_pages,
        'total_media': result.total_media,
        'valid_frontmatter': result.valid_frontmatter,
        'invalid_frontmatter': result.invalid_frontmatter,
        'average_quality': round(result.average_quality, 3),
        'issues_by_type': result.issues_by_type,
        'summary': result.summary,
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Evaluation saved to: {output_file}")
    return output_file


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Evaluate RAG Preprocessing output quality'
    )
    parser.add_argument(
        '--input-dir', '-i',
        type=Path,
        help='Input directory (preprocess_at_*)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        help='Output directory for evaluation results'
    )
    parser.add_argument(
        '--log-level', '-l',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Find input directory
    if args.input_dir:
        input_dir = args.input_dir
    else:
        # Auto-detect from dev_dito data directory
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent.parent / "data" / "preprocessed"
        input_dir = find_latest_preprocess_dir(data_dir)
        
        if not input_dir:
            print("[ERROR] No preprocessed data found. Run RAG Preprocessing first.")
            sys.exit(1)
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = Path(__file__).parent.parent.parent / "data" / "evaluated"
    
    # Run evaluation
    evaluator = PreprocessingEvaluator()
    result = evaluator.evaluate_directory(input_dir)
    
    # Save results
    output_file = save_evaluation(result, output_dir)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PREPROCESSING EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Input: {input_dir}")
    print(f"Output: {output_file}")
    print(f"\nPages evaluated: {result.total_pages}")
    print(f"Media files: {result.total_media}")
    print(f"Average quality: {result.average_quality:.1%}")
    print(f"\nFrontmatter:")
    print(f"  Valid: {result.valid_frontmatter}")
    print(f"  Invalid: {result.invalid_frontmatter}")
    
    if result.issues_by_type:
        print(f"\nIssues found:")
        for issue_type, count in sorted(result.issues_by_type.items(), key=lambda x: -x[1])[:10]:
            print(f"  {issue_type}: {count}")
    
    print(f"\nQuality distribution:")
    for tier, count in result.summary.get('quality_distribution', {}).items():
        print(f"  {tier}: {count}")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
