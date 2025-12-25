from pathlib import Path
from typing import Final

# src/kobosync/constants.py -> ../.. -> project root
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent

SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".epub",
        ".pdf",
        ".cbz",
        ".cbr",
        ".kepub.epub",
    }
)
