from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)

class AttendanceCreate(BaseModel):
    section_id: int
    student_id: int
    date: date
    status: Literal['Present', 'Absent', 'Excused']

class AttendanceUpdate(BaseModel):
    status: Literal['Present', 'Absent', 'Excused']

@router.get("/")
def list_attendance(
    section_id: int,
    student_id: Optional[int] = None,
    date_filter: Optional[date] = None,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if user["role"] == "Student":
            student_id = user["user_id"]

        if user["role"] == "Instructor":
            cursor.execute("""
                SELECT 1 FROM Course_Sections
                WHERE section_id = %s AND instructor_id = %s
            """, (section_id, user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to this section")

        query = """
        SELECT 
            a.attendance_id,
            a.date,
            a.status,
            u.full_name as student_name,
            u.user_id as student_id
        FROM Attendance a
        JOIN Users u ON a.student_id = u.user_id
        WHERE a.section_id = %s
        """
        params = [section_id]

        if student_id:
            query += " AND a.student_id = %s"
            params.append(student_id)

        if date_filter:
            query += " AND a.date = %s"
            params.append(date_filter)

        query += " ORDER BY a.date DESC"

        cursor.execute(query, params)
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

@router.get("/ratio/{section_id}/{student_id}")
def get_attendance_ratio(
    section_id: int,
    student_id: int,
    user=Depends(require_token)
):
    if user["role"] == "Student" and user["user_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(status='Present'),
                   SUM(status='Excused'),
                   SUM(status='Absent')
            FROM Attendance
            WHERE section_id = %s AND student_id = %s
        """, (section_id, student_id))

        total, present, excused, absent = cursor.fetchone()

        if total == 0:
            return {"message": "No attendance records found"}

        participation = ((present or 0) + (excused or 0)) / total * 100

        return {
            "total_classes": total,
            "present": present or 0,
            "excused": excused or 0,
            "absent": absent or 0,
            "participation_rate": f"{participation:.2f}%"
        }

    finally:
        cursor.close()
        conn.close()

@router.post("/", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def mark_attendance(
    record: AttendanceCreate,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if user["role"] == "Instructor":
            cursor.execute("""
                SELECT 1 FROM Course_Sections
                WHERE section_id = %s AND instructor_id = %s
            """, (record.section_id, user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="You do not teach this section")

        cursor.execute("""
            SELECT 1 FROM Attendance
            WHERE section_id=%s AND student_id=%s AND date=%s
        """, (record.section_id, record.student_id, record.date))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Attendance already recorded")

        cursor.execute("""
            INSERT INTO Attendance (section_id, student_id, date, status)
            VALUES (%s, %s, %s, %s)
        """, (record.section_id, record.student_id, record.date, record.status))

        conn.commit()
        return {"message": "Attendance recorded"}

    finally:
        cursor.close()
        conn.close()

@router.put("/{attendance_id}", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def update_attendance_status(
    attendance_id: int,
    update: AttendanceUpdate,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if user["role"] == "Instructor":
            cursor.execute("""
                SELECT 1
                FROM Attendance a
                JOIN Course_Sections s ON a.section_id = s.section_id
                WHERE a.attendance_id = %s AND s.instructor_id = %s
            """, (attendance_id, user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied")

        cursor.execute(
            "UPDATE Attendance SET status=%s WHERE attendance_id=%s",
            (update.status, attendance_id)
        )
        conn.commit()

        return {"message": "Attendance updated"}

    finally:
        cursor.close()
        conn.close()

@router.delete("/bulk-clear", dependencies=[Depends(require_role(["Admin"]))])
def bulk_delete_attendance(section_id: int, date: date):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM Attendance WHERE section_id=%s AND date=%s",
            (section_id, date)
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="No records found")

        return {"message": f"Deleted {cursor.rowcount} records"}

    finally:
        cursor.close()
        conn.close()