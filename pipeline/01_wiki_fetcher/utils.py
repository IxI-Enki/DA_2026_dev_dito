"""
Shared utility functions for the wiki fetcher pipeline.
"""


def format_bytes(size_bytes: int | float) -> str:
    """Format bytes to human readable string"""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def sanitize_filename(name: str) -> str:
    """Sanitize page/media ID for use as filename"""
    return name.replace(":", "_").replace("/", "_").replace("\\", "_")
