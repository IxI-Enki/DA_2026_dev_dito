"""Structured Markdown and JSON evaluation reports.

Provides ReportGenerator for executive summary, metric tables,
statistical comparison, and NFR-005 reproducibility fields.
"""

from evaluation.reports.generator import ReportGenerator

__all__: list[str] = ["ReportGenerator"]
