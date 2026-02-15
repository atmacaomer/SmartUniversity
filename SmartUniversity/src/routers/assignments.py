from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/assignments",
    tags=["Assignments"]
)

@router.get("/")
def list_assignments(
    section_id: Optional[int] = None,
    student_id: Optional[int] = None,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Student":
            student_id = user["user_id"]

        if section_id:
            cursor.execute("""
                SELECT assignment_id, title, description, due_date, max_score, weight, section_id
                FROM Assignments
                WHERE section_id = %s
                ORDER BY due_date ASC
            """, (section_id,))
        elif student_id:
            cursor.execute("""
                SELECT a.assignment_id, a.title, a.description, a.due_date, a.max_score, a.weight, a.section_id
                FROM Assignments a
                JOIN Enrollments e ON a.section_id = e.section_id
                WHERE e.student_id = %s
                ORDER BY a.due_date ASC
            """, (student_id,))
        else:
            raise HTTPException(status_code=400, detail="section_id or student_id required")

        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class AssignmentCreate(BaseModel):
    section_id: int
    title: str
    description: Optional[str] = None
    due_date: datetime
    max_score: int
    weight: float

@router.post("/", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def create_assignment(assignment: AssignmentCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT COALESCE(SUM(weight), 0) AS total_weight
            FROM Assignments
            WHERE section_id = %s
        """, (assignment.section_id,))
        total_weight = cursor.fetchone()["total_weight"]

        if total_weight + assignment.weight > 100.0:
            raise HTTPException(status_code=400, detail="Total weight exceeds 100%")

        cursor.execute("""
            INSERT INTO Assignments (section_id, title, description, due_date, max_score, weight)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            assignment.section_id,
            assignment.title,
            assignment.description,
            assignment.due_date,
            assignment.max_score,
            assignment.weight
        ))
        conn.commit()
        return {"message": "Assignment created", "assignment_id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: Optional[int] = None
    weight: Optional[float] = None

@router.put("/{assignment_id}", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def update_assignment(assignment_id: int, assignment: AssignmentUpdate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        data = assignment.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        if "weight" in data:
            cursor.execute("SELECT section_id FROM Assignments WHERE assignment_id=%s", (assignment_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Assignment not found")

            cursor.execute("""
                SELECT COALESCE(SUM(weight), 0) AS total_weight
                FROM Assignments
                WHERE section_id = %s AND assignment_id <> %s
            """, (row["section_id"], assignment_id))
            other_weight = cursor.fetchone()["total_weight"]

            if other_weight + data["weight"] > 100.0:
                raise HTTPException(status_code=400, detail="Total weight exceeds 100%")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [assignment_id]

        cursor.execute(
            f"UPDATE Assignments SET {set_clause} WHERE assignment_id=%s",
            values
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {"message": "Assignment updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{assignment_id}", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def delete_assignment(assignment_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Assignments WHERE assignment_id=%s", (assignment_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {"message": "Assignment deleted"}
    finally:
        cursor.close()
        conn.close()