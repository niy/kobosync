from typing import Final

SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".epub",
        ".pdf",
        ".cbz",
        ".cbr",
        ".kepub.epub",
    }
)
