from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)

@router.get("/")
def list_courses(department_id: Optional[int] = None, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT c.course_code, c.title, c.credits, c.description, d.name AS department_name
        FROM Courses c
        LEFT JOIN Departments d ON c.department_id = d.department_id
        """
        if department_id:
            query += " WHERE c.department_id = %s"
            cursor.execute(query, (department_id,))
        else:
            cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@router.get("/teaching-history/{instructor_id}")
def get_instructor_teaching_history(
    instructor_id: int,
    user=Depends(require_token)
):
    if user["role"] == "Instructor" and user["user_id"] != instructor_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] not in ["Instructor", "Admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT DISTINCT c.course_code, c.title, c.credits
            FROM Courses c
            JOIN Course_Sections cs ON c.course_id = cs.course_id
            WHERE cs.instructor_id = %s
        """, (instructor_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class CourseCreate(BaseModel):
    course_code: str
    title: str
    department_id: int
    credits: float
    description: Optional[str] = None

@router.post("/", dependencies=[Depends(require_role(["Admin"]))])
def create_course(course: CourseCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Courses (course_code, title, department_id, credits, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (course.course_code, course.title, course.department_id, course.credits, course.description))
        conn.commit()
        return {"message": "Course created", "course_code": course.course_code}
    finally:
        cursor.close()
        conn.close()

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    credits: Optional[float] = None
    description: Optional[str] = None
    department_id: Optional[int] = None

@router.put("/{course_code}", dependencies=[Depends(require_role(["Admin"]))])
def update_course(course_code: str, course: CourseUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = course.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [course_code]

        cursor.execute(
            f"UPDATE Courses SET {set_clause} WHERE course_code=%s",
            values
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Course not found")

        return {"message": "Course updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{course_code}", dependencies=[Depends(require_role(["Admin"]))])
def delete_course(course_code: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM Course_Sections cs JOIN Courses c ON cs.course_id=c.course_id WHERE c.course_code=%s",
            (course_code,)
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Course has sections")

        cursor.execute("""
            SELECT COUNT(*) FROM Course_Prerequisites p
            JOIN Courses c ON p.prerequisite_id=c.course_id
            WHERE c.course_code=%s
        """, (course_code,))
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Course is a prerequisite")

        cursor.execute(
            "DELETE FROM Courses WHERE course_code=%s",
            (course_code,)
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Course not found")

        return {"message": "Course deleted"}
    finally:
        cursor.close()
        conn.close()