from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..db import get_db_connection
from ..routers.auth import require_token, require_role
import mysql.connector

router = APIRouter(
    prefix="/prerequisites",
    tags=["Prerequisites"]
)

@router.get("/{course_code}")
def get_course_prerequisites(course_code: str, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT 
            prereq.course_code,
            prereq.title
        FROM Course_Prerequisites p
        JOIN Courses main ON p.course_id = main.course_id
        JOIN Courses prereq ON p.prerequisite_id = prereq.course_id
        WHERE main.course_code = %s
        """
        cursor.execute(query, (course_code,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class PrerequisiteCreate(BaseModel):
    course_code: str
    prerequisite_code: str

@router.post("/", dependencies=[Depends(require_role(["Admin"]))])
def add_prerequisite(prereq: PrerequisiteCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if prereq.course_code == prereq.prerequisite_code:
            raise HTTPException(status_code=400, detail="Course cannot be prerequisite of itself")

        cursor.execute(
            "SELECT course_id, course_code FROM Courses WHERE course_code IN (%s, %s)",
            (prereq.course_code, prereq.prerequisite_code)
        )
        results = cursor.fetchall()

        if len(results) < 2:
            raise HTTPException(status_code=404, detail="Course code not found")

        id_map = {r["course_code"]: r["course_id"] for r in results}

        cursor.execute(
            "INSERT INTO Course_Prerequisites (course_id, prerequisite_id) VALUES (%s, %s)",
            (id_map[prereq.course_code], id_map[prereq.prerequisite_code])
        )
        conn.commit()

        return {"message": "Prerequisite added"}

    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="Prerequisite already exists")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

@router.delete("/{course_code}/{prerequisite_code}", dependencies=[Depends(require_role(["Admin"]))])
def delete_prerequisite(course_code: str, prerequisite_code: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT course_id, course_code FROM Courses WHERE course_code IN (%s, %s)",
            (course_code, prerequisite_code)
        )
        results = cursor.fetchall()

        if len(results) < 2:
            raise HTTPException(status_code=404, detail="Course code not found")

        id_map = {r["course_code"]: r["course_id"] for r in results}

        cursor.execute(
            """
            DELETE FROM Course_Prerequisites
            WHERE course_id = %s AND prerequisite_id = %s
            """,
            (id_map[course_code], id_map[prerequisite_code])
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Prerequisite link not found")

        return {"message": "Prerequisite deleted"}

    finally:
        cursor.close()
        conn.close()