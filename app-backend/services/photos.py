"""Proof photos: checking, cleaning and naming them."""

import io
import uuid
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from core.errors import InvalidInput

MAX_BYTES = 10 * 1024 * 1024
MAX_SIDE = 2048
# Larger images take too much memory to decode.
MAX_PIXELS = 60_000_000
FORMATS = ["JPEG", "PNG", "WEBP"]

NOT_AN_IMAGE = "The photo must be a JPEG, PNG or WebP image"
TOO_LARGE = "The photo must be 10 MB or less"


def read_upload(file: BinaryIO) -> bytes:
    data = file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InvalidInput(TOO_LARGE)
    return data


def clean(data: bytes) -> bytes:
    """Re-encode the image as a JPEG of at most MAX_SIDE px, without metadata.

    Dropping the metadata removes the GPS location phones add to photos.
    """
    try:
        with Image.open(io.BytesIO(data), formats=FORMATS) as image:
            if image.width * image.height > MAX_PIXELS:
                raise InvalidInput("The photo has too many pixels")
            # Lets JPEG decode at a smaller scale; other formats ignore it.
            image.draft("RGB", (MAX_SIDE, MAX_SIDE))
            # The rotation is in the metadata, so apply it before dropping it.
            image = ImageOps.exif_transpose(image)
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            out = io.BytesIO()
            _flatten(image).save(out, "JPEG", quality=85)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise InvalidInput(NOT_AN_IMAGE)
    return out.getvalue()


def _flatten(image: Image.Image) -> Image.Image:
    """RGB with transparent parts on white, since JPEG has no transparency."""
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        return background
    return image.convert("RGB")


def path_for(household_id: uuid.UUID, submission_id: uuid.UUID) -> str:
    return f"{household_id}/{submission_id}.jpg"
