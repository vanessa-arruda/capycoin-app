import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, TypeDecorator, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint names so Alembic migrations can reference them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator):
    """timestamptz that rejects naive datetimes and always reads back in UTC.

    Doesn't depend on the database session's TimeZone setting, which a
    connection pooler may not keep. See docs/database.md, "Times and dates".
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.utcoffset() is None:
            raise ValueError("datetime without a timezone; use core.clock.now()")
        return value

    def process_result_value(self, value, dialect):
        return None if value is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: UTCDateTime()}


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid7, sort_order=-100
    )


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), sort_order=100
    )


class Timestamps(CreatedAt):
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), sort_order=101
    )


def enum_column(enum_class: type[StrEnum], name: str) -> Enum:
    """Store a StrEnum as VARCHAR + CHECK using its values, not its member names."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )
