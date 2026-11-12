from functools import cache

from core.config import settings

from .base import PhotoStore

__all__ = ["PhotoStore", "get_photo_store"]


@cache
def get_photo_store() -> PhotoStore:
    if settings.photo_backend == "local":
        from .local import LocalPhotoStore

        return LocalPhotoStore(settings.photo_dir)
    raise ValueError(f"Unknown photo backend: {settings.photo_backend}")
