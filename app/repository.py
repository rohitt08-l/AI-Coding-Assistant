from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

IGNORE_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".mypy_cache",
    ".idea",
    ".vscode",
}
TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".sql",
}
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "into",
    "from",
    "this",
    "your",
    "what",
    "when",
    "where",
    "them",
    "have",
    "should",
    "would",
    "could",
    "will",
    "about",
}


@dataclass(slots=True)
class RelevantFile:
    path: str
    score: float
    language: str
    excerpt: str = ""


@dataclass(slots=True)
class RepositoryContext:
    root_path: str
    total_files: int
    relevant_files: list[RelevantFile] = field(default_factory=list)
    request: str = ""

    @property
    def summary(self) -> str:
        return (
            f"Scanned {self.total_files} files under '{self.root_path}'. "
            f"Selected {len(self.relevant_files)} high-signal files for analysis."
        )


class RepositoryScanner:
    """Recursively scans a repository and highlights likely relevant files."""

    @staticmethod
    def extract_keywords(request: str) -> set[str]:
        lowered = request.lower()
        matches = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", lowered)
        keywords = {word for word in matches if word not in STOP_WORDS}
        if not keywords:
            return {"feature", "fix", "update", "test"}
        return keywords

    @classmethod
    def scan(cls, repo_path: str, request: str, limit: int = 8) -> RepositoryContext:
        repo_root = Path(repo_path).expanduser().resolve()
        if not repo_root.exists():
            logger.error("Repository path does not exist: %s", repo_path)
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        keywords = cls.extract_keywords(request)
        relevant: list[RelevantFile] = []
        total_files = 0

        for candidate in sorted(repo_root.rglob("*")):
            if not candidate.is_file():
                continue
            total_files += 1
            if any(part in IGNORE_DIR_NAMES for part in candidate.parts):
                continue
            suffix = candidate.suffix.lower()
            if suffix and suffix not in TEXT_EXTENSIONS and candidate.name not in {"Dockerfile", "Makefile"}:
                continue

            try:
                content = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                logger.warning("Unable to read candidate file: %s", candidate)
                continue
            if "\x00" in content:
                continue

            lower_name = candidate.name.lower()
            lower_content = content.lower()
            score = 0.0
            for keyword in keywords:
                if keyword in lower_name:
                    score += 4.0
                if keyword in lower_content:
                    score += 2.0
            if "error" in keywords and any(token in lower_content for token in ("raise ", "except", "traceback")):
                score += 2.0
            if "log" in keywords and "logging" in lower_content:
                score += 2.0
            if "test" in keywords and suffix == ".py":
                score += 1.0
            if "streamlit" in keywords and candidate.name in {"streamlit_app.py", "app.py"}:
                score += 5.0
            if score <= 0:
                continue

            excerpt = " ".join(content.split())[:180]
            relevant.append(
                RelevantFile(
                    path=str(candidate.relative_to(repo_root)),
                    score=round(score, 2),
                    language=suffix.lstrip(".") or "text",
                    excerpt=excerpt,
                )
            )

        relevant.sort(key=lambda item: item.score, reverse=True)
        context = RepositoryContext(
            root_path=str(repo_root),
            total_files=total_files,
            relevant_files=relevant[:limit],
            request=request,
        )
        return context
