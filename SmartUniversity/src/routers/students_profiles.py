from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/student-profiles",
    tags=["Student Profiles"]
)

@router.get("/")
def list_student_profiles(
    student_id: Optional[int] = None,
    department: Optional[str] = None,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Student" and student_id is not None and user["user_id"] != student_id:
            raise HTTPException(status_code=403, detail="Access denied to other profiles")

        if user["role"] == "Student" and student_id is None:
            student_id = user["user_id"]

        query = """
        SELECT 
            u.full_name,
            u.email,
            sp.student_id,
            sp.admission_year,
            sp.current_gpa,
            sp.credits_earned,
            d.name AS department_name
        FROM Student_Profiles sp
        JOIN Users u ON sp.student_id = u.user_id
        LEFT JOIN Departments d ON sp.department_id = d.department_id
        WHERE 1=1
        """
        params = []

        if student_id:
            query += " AND sp.student_id = %s"
            params.append(student_id)

        if department:
            query += " AND d.name LIKE %s"
            params.append(f"%{department}%")

        cursor.execute(query, params)

        if student_id:
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Student not found")
            return row

        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class StudentProfileUpdate(BaseModel):
    department_id: Optional[int] = None
    admission_year: Optional[int] = None

@router.put("/{student_id}")
def update_student_profile(
    student_id: int, 
    profile: StudentProfileUpdate, 
    user=Depends(require_token)
):
    if user["role"] == "Student" and user["user_id"] != student_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    
    if user["role"] == "Instructor":
        raise HTTPException(status_code=403, detail="Instructors cannot update student profiles")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = profile.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [student_id]

        cursor.execute(
            f"UPDATE Student_Profiles SET {set_clause} WHERE student_id = %s",
            values
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student profile not found")

        return {"message": "Student profile updated"}
    finally:
        cursor.close()
        conn.close()

@router.get("/{student_id}/transcript")
def get_transcript(student_id: int, user=Depends(require_token)):
    if user["role"] == "Student" and user["user_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied to other transcripts")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
        SELECT 
            c.course_code,
            c.title AS course_name,
            c.credits,
            e.grade,
            e.completion_status,
            s.semester
        FROM Enrollments e
        JOIN Course_Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_id = c.course_id
        WHERE e.student_id = %s
          AND e.grade IS NOT NULL
        """, (student_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@router.get("/{student_id}/get-gpa")
def get_gpa(student_id: int, user=Depends(require_token)):
    if user["role"] == "Student" and user["user_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT current_gpa FROM Student_Profiles WHERE student_id = %s",
            (student_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Student profile not found")
        return row
    finally:
        cursor.close()
        conn.close()

@router.post("/{student_id}/update-gpa", dependencies=[Depends(require_role(["Admin"]))])
def update_student_gpa(student_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
        SELECT e.grade, c.credits
        FROM Enrollments e
        JOIN Course_Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_id = c.course_id
        WHERE e.student_id = %s AND e.grade IS NOT NULL
        """, (student_id,))
        rows = cursor.fetchall()

        if not rows:
            return {"message": "No grades found", "gpa": 0.0}

        total_points = 0.0
        total_credits = 0

        for r in rows:
            total_points += r["grade"] * r["credits"]
            total_credits += r["credits"]

        new_gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0

        cursor.execute("""
        UPDATE Student_Profiles
        SET current_gpa = %s, credits_earned = %s
        WHERE student_id = %s
        """, (new_gpa, total_credits, student_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student profile not found")

        return {
            "student_id": student_id,
            "new_gpa": new_gpa,
            "credits_earned": total_credits
        }
    finally:
        cursor.close()
        conn.close()