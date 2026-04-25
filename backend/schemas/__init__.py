from datetime import date, datetime
from typing import Annotated, Dict, Literal, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from backend.models import UserRole, VacationDaysStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    role: UserRole
    is_verified: bool
    exp: int


class UserBase(BaseModel):
    external_id: Optional[str] = Field(None, description="External numeric/string identifier")
    full_name: Optional[str] = None
    alliance: Optional[str] = None
    category: Optional[str] = None


class EmployeeRegisterRequest(UserBase):
    email: EmailStr
    password: str
    vacation_days_declared: Optional[int] = Field(default=None, ge=0, le=365)

    @field_validator("password")
    @classmethod
    def check_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password too long, must be <= 72 bytes")
        return value


class VacationDaysModerationRequest(BaseModel):
    approved_days: int = Field(..., ge=0, le=365)
    status: VacationDaysStatus


class UserOut(UserBase):
    id: int
    email: Optional[EmailStr] = None
    registered: bool
    is_verified: bool
    role: UserRole
    vacation_days_declared: Optional[int] = None
    vacation_days_approved: Optional[int] = None
    vacation_days_status: VacationDaysStatus

    class Config:
        from_attributes = True


class UserMe(UserOut):
    pass


class VerificationRequest(BaseModel):
    token: str


def _parse_time_value(value: str) -> tuple[int, int]:
    try:
        hours_str, minutes_str = value.split(":")
        hours = int(hours_str)
        minutes = int(minutes_str)
    except ValueError as exc:
        raise ValueError("Time must be in HH:MM format") from exc

    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError("Time must be in HH:MM format")

    return hours, minutes


def _time_to_minutes(value: str) -> int:
    hours, minutes = _parse_time_value(value)
    return hours * 60 + minutes


class ShiftMeta(BaseModel):
    shiftStart: str
    shiftEnd: str

    @field_validator("shiftStart", "shiftEnd")
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        _parse_time_value(value)
        return value

    @model_validator(mode="after")
    def validate_shift_order(self):
        if _time_to_minutes(self.shiftStart) >= _time_to_minutes(self.shiftEnd):
            raise ValueError("shiftStart must be earlier than shiftEnd")
        return self


class SplitShiftMeta(BaseModel):
    splitStart1: str
    splitEnd1: str
    splitStart2: str
    splitEnd2: str

    @field_validator("splitStart1", "splitEnd1", "splitStart2", "splitEnd2")
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        _parse_time_value(value)
        return value

    @model_validator(mode="after")
    def validate_split_order(self):
        start1 = _time_to_minutes(self.splitStart1)
        end1 = _time_to_minutes(self.splitEnd1)
        start2 = _time_to_minutes(self.splitStart2)
        end2 = _time_to_minutes(self.splitEnd2)

        if start1 >= end1:
            raise ValueError("splitStart1 must be earlier than splitEnd1")
        if start2 >= end2:
            raise ValueError("splitStart2 must be earlier than splitEnd2")
        if end1 > start2:
            raise ValueError("Second interval must start after first interval ends")
        return self


class ShiftDayPayload(BaseModel):
    status: Literal["shift"]
    meta: ShiftMeta


class SplitDayPayload(BaseModel):
    status: Literal["split"]
    meta: SplitShiftMeta


class DayOffDayPayload(BaseModel):
    status: Literal["dayoff"]
    meta: None = None


class VacationDayPayload(BaseModel):
    status: Literal["vacation"]
    meta: None = None


ScheduleDayPayload = Annotated[
    Union[ShiftDayPayload, SplitDayPayload, DayOffDayPayload, VacationDayPayload],
    Field(discriminator="status"),
]


class ScheduleBulkUpdate(BaseModel):
    days: Dict[date, ScheduleDayPayload]


class ScheduleForUser(BaseModel):
    user: UserOut
    entries: Dict[date, ScheduleDayPayload]
    vacation_work: Optional[dict] = None


class ScheduleSummary(BaseModel):
    daily_hours: Dict[date, float]
    weekly_hours: Dict[date, float]
    period_total_hours: float
    vacation_days_count: int
    max_work_streak: int


class CollectionPeriodOut(BaseModel):
    id: int
    alliance: str
    period_start: date
    period_end: date
    deadline: datetime
    is_open: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionPeriodCreate(BaseModel):
    period_start: date
    period_end: date
    deadline: datetime


class ScheduleTemplateCreate(BaseModel):
    name: str
    work_days: int = Field(..., ge=1, le=7)
    rest_days: int = Field(..., ge=0, le=7)
    shift_start: str
    shift_end: str
    has_break: bool = False
    break_start: Optional[str] = None
    break_end: Optional[str] = None


class ScheduleTemplateOut(BaseModel):
    id: int
    user_id: int
    name: str
    work_days: int
    rest_days: int
    shift_start: str
    shift_end: str
    has_break: bool
    break_start: Optional[str]
    break_end: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
