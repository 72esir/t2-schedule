from datetime import datetime
import os
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from backend.core import get_current_active_user
from backend.db import get_db
from backend.models import CollectionPeriod, ScheduleEntry, User, UserRole

router = APIRouter(prefix="/export", tags=["export"])


def standardize_time(time_str: str) -> str:
    if not time_str or ":" not in time_str:
        return time_str
    try:
        hours, minutes = map(int, time_str.split(":"))
        return f"{hours:02d}:{minutes:02d}"
    except ValueError:
        return time_str


def _build_schedule_string(entry: ScheduleEntry) -> str:
    if entry.status == "shift":
        meta = entry.meta or {}
        start = meta.get("shiftStart", "")
        end = meta.get("shiftEnd", "")
        return f"{start}-{end}" if start and end else ""
    if entry.status == "split":
        meta = entry.meta or {}
        s1 = meta.get("splitStart1", "")
        e1 = meta.get("splitEnd1", "")
        s2 = meta.get("splitStart2", "")
        e2 = meta.get("splitEnd2", "")
        return f"{s1}-{e1} {s2}-{e2}" if s1 and e1 and s2 and e2 else ""
    if entry.status == "dayoff":
        return "выходной"
    if entry.status == "vacation":
        return ""
    return ""


def _generate_excel_file(data: Dict) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "ИГ"

    all_dates = set()
    for user_info in data["data"].values():
        all_dates.update(user_info.get("schedule", {}).keys())
        all_dates.update(user_info.get("vacation_work", {}).keys())

    date_columns = sorted(all_dates, key=lambda value: datetime.strptime(value, "%Y-%m-%d"))

    headers = ["Группа", "ФИО", "Сумма часов"]
    for date_str in date_columns:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        headers.append(date_obj.strftime("%d.%b"))
        headers.append("")
    headers.extend(["", "Норма часов", "Доступность", "", "Доп. перерыв", "Комментарий"])
    ws.append(headers)

    dates_count = len(date_columns)
    for index in range(dates_count):
        start_col = 4 + index * 2
        ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=start_col + 1)

    blank_col = 3 + 2 * dates_count + 1
    norm_start = blank_col + 1
    avail_start_col = norm_start + 1
    avail_end_col = avail_start_col + 1
    ws.merge_cells(start_row=1, start_column=avail_start_col, end_row=1, end_column=avail_end_col)

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 30

    sorted_users = sorted(data["data"].items(), key=lambda item: item[1]["full_name"].lower())

    for index, (_, user_data) in enumerate(sorted_users):
        shift_data = {}
        break_data = {}
        vacation_work = user_data.get("vacation_work", {})
        schedule = user_data.get("schedule", {})

        for date_str in date_columns:
            is_vacation = date_str in vacation_work
            value = schedule.get(date_str, "")

            if is_vacation:
                shift_start, shift_end = "отпуск", ""
                break_start, break_end = "", ""
            elif not value:
                shift_start, shift_end, break_start, break_end = "", "", "", ""
            elif "-" not in value:
                shift_start, shift_end, break_start, break_end = value, "", "", ""
            else:
                intervals = value.split()
                if len(intervals) == 1:
                    parts = intervals[0].split("-")
                    if len(parts) == 2:
                        shift_start = standardize_time(parts[0].strip())
                        shift_end = standardize_time(parts[1].strip())
                        break_start, break_end = "", ""
                    else:
                        shift_start, shift_end, break_start, break_end = value, "", "", ""
                elif len(intervals) == 2:
                    parts1 = intervals[0].split("-")
                    parts2 = intervals[1].split("-")
                    if len(parts1) == 2 and len(parts2) == 2:
                        shift_start = standardize_time(parts1[0].strip())
                        shift_end = standardize_time(parts2[1].strip())
                        break_start = standardize_time(parts1[1].strip())
                        break_end = standardize_time(parts2[0].strip())
                    else:
                        shift_start, shift_end, break_start, break_end = value, "", "", ""
                else:
                    shift_start, shift_end, break_start, break_end = value, "", "", ""

            shift_data[date_str] = (shift_start, shift_end)
            break_data[date_str] = (break_start, break_end)

        row1 = [user_data["alliance"], user_data["full_name"], ""]
        for date_str in date_columns:
            row1.extend(shift_data[date_str])
        row1.extend(["", "", "", "", "", "", ""])
        ws.append(row1)

        row2 = ["Длительный перерыв", "", ""]
        for date_str in date_columns:
            row2.extend(break_data[date_str])
        row2.extend([""] * (len(headers) - len(row2)))
        ws.append(row2)

        break_row_idx = ws.max_row
        if index < len(sorted_users) - 1:
            ws.row_dimensions[break_row_idx].hidden = True
        ws.merge_cells(start_row=break_row_idx, start_column=1, end_row=break_row_idx, end_column=2)

    file_path = "temp_schedule.xlsx"
    wb.save(file_path)
    return file_path


@router.get("/schedule")
def export_schedule(
    period_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    if period_id:
        period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
        if not period:
            raise HTTPException(status_code=404, detail="Период не найден")
        if period.alliance != current_user.alliance:
            raise HTTPException(status_code=403, detail="Нет доступа к этому периоду")
    else:
        period = (
            db.query(CollectionPeriod)
            .filter(CollectionPeriod.is_open.is_(True), CollectionPeriod.alliance == current_user.alliance)
            .first()
        )
        if not period:
            raise HTTPException(status_code=400, detail="Нет активного периода сбора")

    users = db.query(User).filter(User.is_verified.is_(True), User.alliance == current_user.alliance).all()

    export_data = {"data": {}}
    for user in users:
        entries = db.query(ScheduleEntry).filter(
            ScheduleEntry.user_id == user.id,
            ScheduleEntry.period_id == period.id,
        ).all()

        schedule_dict = {}
        vacation_dict = {}
        for entry in entries:
            day_str = entry.day.isoformat()
            if entry.status == "vacation":
                vacation_dict[day_str] = True
            else:
                schedule_str = _build_schedule_string(entry)
                if schedule_str:
                    schedule_dict[day_str] = schedule_str

        export_data["data"][str(user.id)] = {
            "alliance": user.alliance or "",
            "full_name": user.full_name or user.email,
            "availability": "",
            "vacation_work": vacation_dict,
            "schedule": schedule_dict,
        }

    if not export_data["data"]:
        raise HTTPException(status_code=404, detail="Нет данных для экспорта")

    try:
        file_path = _generate_excel_file(export_data)
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"schedule_{period.period_start}_{period.period_end}.xlsx",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации файла: {exc}") from exc


@router.on_event("shutdown")
def cleanup():
    if os.path.exists("temp_schedule.xlsx"):
        os.remove("temp_schedule.xlsx")

