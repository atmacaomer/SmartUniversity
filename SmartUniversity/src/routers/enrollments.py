from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/enrollments",
    tags=["Enrollments"]
)

@router.get("/")
def list_enrollments(section_id: Optional[int] = None, student_id: Optional[int] = None, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Student":
            student_id = user["user_id"]

        query = """
        SELECT 
            e.enrollment_id,
            e.student_id,
            u.full_name as student_name,
            e.section_id,
            c.course_code,
            c.title as course_name,
            e.grade,
            e.completion_status
        FROM Enrollments e
        JOIN Users u ON e.student_id = u.user_id
        JOIN Course_Sections s ON e.section_id = s.section_id
        JOIN Courses c ON s.course_id = c.course_id
        WHERE 1=1
        """
        params = []

        if section_id:
            query += " AND e.section_id = %s"
            params.append(section_id)

        if student_id:
            query += " AND e.student_id = %s"
            params.append(student_id)

        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class EnrollmentCreate(BaseModel):
    section_id: int

@router.post("/", dependencies=[Depends(require_role(["Student"]))])
def enroll_student(enrollment: EnrollmentCreate, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        student_id = user["user_id"]

        cursor.execute("""
            SELECT s.course_id, s.capacity,
                   (SELECT COUNT(*) FROM Enrollments WHERE section_id = s.section_id) AS current_count
            FROM Course_Sections s
            WHERE s.section_id = %s
        """, (enrollment.section_id,))
        section = cursor.fetchone()

        if not section:
            raise HTTPException(status_code=404, detail="Section not found")

        if section["current_count"] >= section["capacity"]:
            raise HTTPException(status_code=400, detail="Section is full")

        target_course_id = section["course_id"]

        cursor.execute("""
            SELECT prerequisite_id
            FROM Course_Prerequisites
            WHERE course_id = %s
        """, (target_course_id,))
        prereqs = cursor.fetchall()

        for p in prereqs:
            cursor.execute("""
                SELECT 1
                FROM Enrollments e
                JOIN Course_Sections s ON e.section_id = s.section_id
                WHERE e.student_id = %s
                  AND s.course_id = %s
                  AND e.completion_status = 'Completed'
            """, (student_id, p["prerequisite_id"]))

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail=f"Prerequisite course ID {p['prerequisite_id']} not completed"
                )

        cursor.execute("""
            INSERT INTO Enrollments (student_id, section_id, completion_status)
            VALUES (%s, %s, 'Enrolled')
        """, (student_id, enrollment.section_id))

        conn.commit()
        return {"message": "Enrollment successful"}

    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            raise e
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail="Already enrolled in this section")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

class GradeUpdate(BaseModel):
    grade: Optional[float] = None
    completion_status: Optional[Literal["Enrolled", "Completed", "Dropped", "Failed"]] = None

@router.put("/{enrollment_id}", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def update_grade_or_status(enrollment_id: int, update: GradeUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = update.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [enrollment_id]

        cursor.execute(
            f"UPDATE Enrollments SET {set_clause} WHERE enrollment_id=%s",
            values
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Enrollment not found")

        return {"message": "Enrollment updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{enrollment_id}")
def drop_course(enrollment_id: int, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT student_id FROM Enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cursor.fetchone()
        
        if not enrollment:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        
        if user["role"] == "Student" and user["user_id"] != enrollment["student_id"]:
            raise HTTPException(status_code=403, detail="You can only drop your own enrollments")

        cursor.execute("DELETE FROM Enrollments WHERE enrollment_id = %s", (enrollment_id,))
        conn.commit()

        return {"message": "Enrollment dropped"}
    finally:
        cursor.close()
        conn.close()