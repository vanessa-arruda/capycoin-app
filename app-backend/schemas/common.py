from typing import Annotated

from pydantic import (
    AfterValidator,
    BeforeValidator,
    EmailStr,
    Field,
    StringConstraints,
)


def _normalize(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


Email = Annotated[EmailStr, AfterValidator(str.lower)]
DisplayName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Username = Annotated[
    str,
    BeforeValidator(_normalize),
    StringConstraints(min_length=3, max_length=50, pattern=r"^[a-z0-9_.-]+$"),
]
Login = Annotated[str, BeforeValidator(_normalize), StringConstraints(min_length=1)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
Code = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
