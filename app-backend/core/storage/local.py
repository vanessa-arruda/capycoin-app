from collections.abc import Iterable
from pathlib import Path


class LocalPhotoStore:
    """Development store: keeps photos in a folder on disk."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def _file(self, path: str) -> Path:
        file = (self.root / path).resolve()
        if not file.is_relative_to(self.root):
            raise ValueError(f"Photo path outside the store: {path}")
        return file

    def save(self, path: str, data: bytes) -> None:
        file = self._file(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)

    def read(self, path: str) -> bytes | None:
        file = self._file(path)
        return file.read_bytes() if file.is_file() else None

    def delete(self, paths: Iterable[str]) -> None:
        for path in paths:
            self._file(path).unlink(missing_ok=True)
