from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Annotated, Dict, Literal, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from backend.models import ScheduleChangeRequestStatus, UserRole, VacationDaysStatus


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


class UserStreakPeriodResult(BaseModel):
    period_id: int
    period_start: date
    period_end: date
    deadline: datetime
    success: bool
    reason: str


class UserStreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    completed_periods_count: int
    evaluated_periods_count: int
    bonus_balance: int = 0
    redeemable_sets: int = 0
    history: list[UserStreakPeriodResult]


class UserStreakLeaderboardItem(BaseModel):
    user_id: int
    full_name: str
    email: Optional[EmailStr] = None
    current_streak: int
    longest_streak: int
    completed_periods_count: int
    bonus_balance: int = 0


class StreakRedeemOut(BaseModel):
    converted_streak: int
    awarded_bonus: int
    bonus_balance: int
    current_streak: int
    redeemable_sets: int


class VerificationRequest(BaseModel):
    token: str


class ManagerProblemEmployeeOut(BaseModel):
    user_id: int
    full_name: str
    email: Optional[EmailStr] = None
    violation_count: int
    violation_codes: list[str]
    summary: Optional["ScheduleSummary"] = None


class ManagerDashboardOut(BaseModel):
    current_period: Optional["CollectionPeriodOut"] = None
    total_employees: int
    submitted_count: int
    pending_count: int
    pending_verification_count: int
    pending_vacation_moderation_count: int
    pending_schedule_change_requests_count: int
    employees_with_violations_count: int
    problem_employees: list[ManagerProblemEmployeeOut]


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


class ScheduleChangeRequestCreate(BaseModel):
    days: Dict[date, ScheduleDayPayload]
    employee_comment: Optional[str] = None


class ScheduleChangeRequestDecision(BaseModel):
    manager_comment: Optional[str] = None


class ScheduleChangeRequestOut(BaseModel):
    id: int
    user_id: int
    period_id: int
    status: ScheduleChangeRequestStatus
    employee_comment: Optional[str] = None
    manager_comment: Optional[str] = None
    proposed_days: Dict[date, ScheduleDayPayload]
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_manager_id: Optional[int] = None


class ScheduleChangeRequestManagerOut(ScheduleChangeRequestOut):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    alliance: Optional[str] = None
    current_days: Dict[date, ScheduleDayPayload] = Field(default_factory=dict)
    changed_days: list[date] = Field(default_factory=list)


class ScheduleForUser(BaseModel):
    user: UserOut
    entries: Dict[date, ScheduleDayPayload]
    vacation_work: Optional[dict] = None


class MyScheduleState(BaseModel):
    days: Dict[date, ScheduleDayPayload]
    last_saved_at: Optional[datetime] = None


class ScheduleSummary(BaseModel):
    daily_hours: Dict[date, float]
    weekly_hours: Dict[date, float]
    period_total_hours: float
    vacation_days_count: int
    max_work_streak: int


class ScheduleViolation(BaseModel):
    code: str
    level: str
    message: str
    context: dict


class ScheduleValidationResult(BaseModel):
    is_valid: bool
    violations: list[ScheduleViolation]
    summary: ScheduleSummary


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

    @model_validator(mode="after")
    def validate_period_range(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


PeriodTemplateType = Literal["week", "two_weeks", "month", "custom"]


class PeriodTemplateOut(BaseModel):
    type: PeriodTemplateType
    label: str
    description: str
    requires_period_end: bool


class CollectionPeriodFromTemplateCreate(BaseModel):
    template_type: PeriodTemplateType
    period_start: date
    deadline: datetime
    period_end: Optional[date] = None

    @model_validator(mode="after")
    def validate_template_payload(self):
        if self.template_type == "custom":
            if self.period_end is None:
                raise ValueError("period_end is required for custom template")
            if self.period_end < self.period_start:
                raise ValueError("period_end must be on or after period_start")
        elif self.period_end is not None:
            raise ValueError("period_end is only allowed for custom template")
        return self

    def resolve_period_end(self) -> date:
        if self.template_type == "week":
            return self.period_start + timedelta(days=6)
        if self.template_type == "two_weeks":
            return self.period_start + timedelta(days=13)
        if self.template_type == "month":
            last_day = monthrange(self.period_start.year, self.period_start.month)[1]
            return date(self.period_start.year, self.period_start.month, last_day)
        return self.period_end


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


class SuggestedTemplateOut(BaseModel):
    has_suggestion: bool
    period_id: Optional[int] = None
    match_count: int = 0
    source_period_ids: list[int] = Field(default_factory=list)
    days: Dict[date, ScheduleDayPayload] = Field(default_factory=dict)


class GoogleCalendarConnectionStatusOut(BaseModel):
    connected: bool
    google_account_email: Optional[EmailStr] = None
    scopes: list[str] = Field(default_factory=list)


class GoogleOAuthConnectOut(BaseModel):
    authorization_url: str


class GoogleOAuthCallbackOut(BaseModel):
    connected: bool
    google_account_email: Optional[EmailStr] = None


class GoogleCalendarListItemOut(BaseModel):
    id: str
    summary: str
    primary: bool = False
    selected: bool = False
    access_role: Optional[str] = None
    time_zone: Optional[str] = None


class GoogleCalendarBusyIntervalOut(BaseModel):
    start: datetime
    end: datetime


class GoogleCalendarAvailabilityDayOut(BaseModel):
    all_day: bool = False
    event_count: int = 0
    busy_intervals: list[GoogleCalendarBusyIntervalOut] = Field(default_factory=list)


class GoogleCalendarAvailabilityOut(BaseModel):
    period_id: int
    calendar_id: str
    period_start: date
    period_end: date
    time_zone: Optional[str] = None
    days: Dict[date, GoogleCalendarAvailabilityDayOut] = Field(default_factory=dict)


class GoogleCalendarSuggestedScheduleOut(BaseModel):
    period_id: int
    calendar_id: str
    period_start: date
    period_end: date
    suggested_days_count: int
    days: Dict[date, ScheduleDayPayload] = Field(default_factory=dict)
