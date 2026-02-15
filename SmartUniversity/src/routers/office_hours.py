from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import time
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/office-hours",
    tags=["Office Hours"]
)

@router.get("/")
def list_office_hours(
    instructor_id: Optional[int] = None,
    day_filter: Optional[
        Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    ] = None,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT 
            oh.office_hour_id,
            oh.instructor_id,
            u.full_name,
            oh.day_of_week,
            oh.start_time,
            oh.end_time,
            oh.location
        FROM Office_Hours oh
        JOIN Users u ON oh.instructor_id = u.user_id
        WHERE 1=1
        """
        params = []

        if instructor_id:
            query += " AND oh.instructor_id = %s"
            params.append(instructor_id)

        if day_filter:
            query += " AND oh.day_of_week = %s"
            params.append(day_filter)

        query += """
        ORDER BY 
            CASE 
                WHEN day_of_week = 'Monday' THEN 1
                WHEN day_of_week = 'Tuesday' THEN 2
                WHEN day_of_week = 'Wednesday' THEN 3
                WHEN day_of_week = 'Thursday' THEN 4
                WHEN day_of_week = 'Friday' THEN 5
                WHEN day_of_week = 'Saturday' THEN 6
                WHEN day_of_week = 'Sunday' THEN 7
            END,
            oh.start_time ASC
        """

        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class OfficeHourCreate(BaseModel):
    day_of_week: Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    start_time: time
    end_time: time
    location: str

@router.post("/")
def create_office_hour(slot: OfficeHourCreate, user=Depends(require_role(["Instructor"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        instructor_id = user["user_id"]
        cursor.execute(
            """
            INSERT INTO Office_Hours (instructor_id, day_of_week, start_time, end_time, location)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (instructor_id, slot.day_of_week, slot.start_time, slot.end_time, slot.location)
        )
        conn.commit()
        return {"message": "Office hour slot added", "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

class OfficeHourUpdate(BaseModel):
    day_of_week: Optional[
        Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    ] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None

@router.put("/{office_hour_id}")
def update_office_hour(office_hour_id: int, update: OfficeHourUpdate, user=Depends(require_role(["Instructor"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT instructor_id FROM Office_Hours WHERE office_hour_id = %s", (office_hour_id,))
        slot = cursor.fetchone()
        
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        if slot["instructor_id"] != user["user_id"]:
            raise HTTPException(status_code=403, detail="You can only update your own office hours")

        data = update.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [office_hour_id]

        cursor.execute(f"UPDATE Office_Hours SET {set_clause} WHERE office_hour_id = %s", values)
        conn.commit()
        return {"message": "Office hour updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{office_hour_id}")
def delete_office_hour(office_hour_id: int, user=Depends(require_role(["Instructor", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT instructor_id FROM Office_Hours WHERE office_hour_id = %s", (office_hour_id,))
        slot = cursor.fetchone()

        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        
        if user["role"] == "Instructor" and slot["instructor_id"] != user["user_id"]:
            raise HTTPException(status_code=403, detail="You can only delete your own office hours")

        cursor.execute("DELETE FROM Office_Hours WHERE office_hour_id = %s", (office_hour_id,))
        conn.commit()
        return {"message": "Office hour slot removed"}
    finally:
        cursor.close()
        conn.close()