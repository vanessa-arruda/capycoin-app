from collections.abc import Iterable
from typing import Protocol


class PhotoStore(Protocol):
    def save(self, path: str, data: bytes) -> None: ...

    def read(self, path: str) -> bytes | None:
        """The file's bytes, or None if it does not exist."""

    def delete(self, paths: Iterable[str]) -> None:
        """Delete the files, skipping ones that do not exist."""
