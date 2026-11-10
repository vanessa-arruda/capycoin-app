import uuid
from typing import Any

from sqlalchemy import Select
from sqlalchemy.orm import Session

from schemas.common import PageParams


def paginate(
    db: Session, query: Select, id_column: Any, page: PageParams
) -> tuple[list[Any], uuid.UUID | None]:
    """Return one page, newest first by UUIDv7 id, and the id to continue from."""
    if page.before is not None:
        query = query.where(id_column < page.before)
    rows = db.scalars(query.order_by(id_column.desc()).limit(page.limit + 1)).all()
    if len(rows) <= page.limit:
        return list(rows), None
    return list(rows[: page.limit]), rows[page.limit - 1].id
