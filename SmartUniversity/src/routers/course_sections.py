from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/sections",
    tags=["Course Sections"]
)

@router.get("/")
def list_sections(semester: Optional[str] = None, course_code: Optional[str] = None, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT 
            s.section_id,
            c.course_code,
            c.title AS course_name,
            s.semester,
            s.year,
            s.schedule_day,
            s.schedule_time,
            s.classroom,
            s.capacity,
            u.full_name AS instructor_name,
            (SELECT COUNT(*) FROM Enrollments e WHERE e.section_id = s.section_id) AS current_enrolled
        FROM Course_Sections s
        JOIN Courses c ON s.course_id = c.course_id
        LEFT JOIN Users u ON s.instructor_id = u.user_id
        WHERE 1=1
        """
        params = []

        if semester:
            query += " AND s.semester = %s"
            params.append(semester)

        if course_code:
            query += " AND c.course_code = %s"
            params.append(course_code)

        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class SectionCreate(BaseModel):
    course_code: str
    instructor_id: int
    semester: str
    year: int
    day: str
    time: str
    classroom: str
    capacity: int

@router.post("/", dependencies=[Depends(require_role(["Admin"]))])
def create_section(section: SectionCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT course_id FROM Courses WHERE course_code=%s",
            (section.course_code,)
        )
        course = cursor.fetchone()
        if not course:
            raise HTTPException(status_code=400, detail="Course not found")

        cursor.execute("""
            SELECT section_id FROM Course_Sections
            WHERE semester=%s AND year=%s
              AND schedule_day=%s AND schedule_time=%s
              AND classroom=%s
        """, (section.semester, section.year, section.day, section.time, section.classroom))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Classroom conflict")

        cursor.execute("""
            INSERT INTO Course_Sections
            (course_id, instructor_id, semester, year, schedule_day, schedule_time, classroom, capacity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            course["course_id"],
            section.instructor_id,
            section.semester,
            section.year,
            section.day,
            section.time,
            section.classroom,
            section.capacity
        ))
        conn.commit()
        return {"message": "Section created", "section_id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

class SectionUpdate(BaseModel):
    classroom: Optional[str] = None
    capacity: Optional[int] = None
    instructor_id: Optional[int] = None

@router.put("/{section_id}", dependencies=[Depends(require_role(["Admin"]))])
def update_section(section_id: int, section: SectionUpdate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        data = section.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        cursor.execute("""
            SELECT semester, year, schedule_day, schedule_time, classroom
            FROM Course_Sections WHERE section_id=%s
        """, (section_id,))
        current = cursor.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Section not found")

        new_day = current["schedule_day"]
        new_time = current["schedule_time"]
        new_room = data.get("classroom", current["classroom"])

        cursor.execute("""
            SELECT section_id FROM Course_Sections
            WHERE semester=%s AND year=%s
              AND schedule_day=%s AND schedule_time=%s
              AND classroom=%s AND section_id<>%s
        """, (
            current["semester"],
            current["year"],
            new_day,
            new_time,
            new_room,
            section_id
        ))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Classroom conflict")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [section_id]

        cursor.execute(
            f"UPDATE Course_Sections SET {set_clause} WHERE section_id=%s",
            values
        )
        conn.commit()
        return {"message": "Section updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{section_id}", dependencies=[Depends(require_role(["Admin"]))])
def delete_section(section_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM Enrollments WHERE section_id=%s",
            (section_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Students already enrolled")

        cursor.execute(
            "DELETE FROM Course_Sections WHERE section_id=%s",
            (section_id,)
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Section not found")

        return {"message": "Section deleted"}
    finally:
        cursor.close()
        conn.close()