from __future__ import annotations

import difflib


def generate_unified_diff(original: str, updated: str, file_name: str) -> str:
    """Return a git-style unified diff for two text versions."""
    original_lines = original.splitlines(keepends=True)
    updated_lines = updated.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        updated_lines,
        fromfile=f"a/{file_name}",
        tofile=f"b/{file_name}",
        lineterm="",
    )
    return "\n".join(diff)
