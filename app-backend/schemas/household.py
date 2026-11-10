import uuid
from functools import cache
from typing import Annotated
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints


@cache
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _check_timezone(value: str) -> str:
    if value not in _timezones():
        raise ValueError("must be an IANA timezone name, such as Europe/Stockholm")
    return value


HouseholdName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Timezone = Annotated[str, AfterValidator(_check_timezone)]


class HouseholdCreate(BaseModel):
    name: HouseholdName
    timezone: Timezone


class HouseholdUpdate(BaseModel):
    name: HouseholdName | None = None
    timezone: Timezone | None = None


class HouseholdDelete(BaseModel):
    confirm_name: str


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    timezone: str


class MyHouseholdResponse(HouseholdResponse):
    is_admin: bool
