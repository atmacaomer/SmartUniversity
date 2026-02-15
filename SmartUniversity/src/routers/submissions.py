from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"]
)

class SubmissionCreate(BaseModel):
    assignment_id: int
    submission_text: Optional[str] = None
    file_path: Optional[str] = None

@router.post("/", dependencies=[Depends(require_role(["Student"]))])
def create_submission(submission: SubmissionCreate, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        student_id = user["user_id"]
        
        cursor.execute(
            "SELECT due_date FROM Assignments WHERE assignment_id = %s",
            (submission.assignment_id,)
        )
        assignment = cursor.fetchone()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if datetime.now() > assignment["due_date"]:
            raise HTTPException(status_code=400, detail="Deadline passed")

        cursor.execute("""
            SELECT 1
            FROM Enrollments e
            JOIN Assignments a ON e.section_id = a.section_id
            WHERE e.student_id = %s AND a.assignment_id = %s
        """, (student_id, submission.assignment_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Not enrolled in this course")

        cursor.execute("""
            INSERT INTO Submissions
            (student_id, assignment_id, submission_text, file_path, submission_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            student_id,
            submission.assignment_id,
            submission.submission_text,
            submission.file_path,
            datetime.now()
        ))
        conn.commit()

        return {"message": "Submission successful", "submission_id": cursor.lastrowid}

    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            raise e
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail="Already submitted")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/assignment/{assignment_id}")
def list_submissions_for_assignment(assignment_id: int, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Student":
            query = """
                SELECT s.submission_id, s.student_id, u.full_name, s.submission_text, 
                       s.file_path, s.submission_date, s.grade, s.feedback
                FROM Submissions s
                JOIN Users u ON s.student_id = u.user_id
                WHERE s.assignment_id = %s AND s.student_id = %s
            """
            cursor.execute(query, (assignment_id, user["user_id"]))
        else:
            query = """
                SELECT s.submission_id, s.student_id, u.full_name, s.submission_text, 
                       s.file_path, s.submission_date, s.grade, s.feedback
                FROM Submissions s
                JOIN Users u ON s.student_id = u.user_id
                WHERE s.assignment_id = %s
            """
            cursor.execute(query, (assignment_id,))
            
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@router.get("/student/{student_id}")
def list_student_submissions(student_id: int, user=Depends(require_token)):
    if user["role"] == "Student" and user["user_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT s.submission_id, a.title, s.submission_text, s.file_path, 
                   s.submission_date, s.grade, s.feedback
            FROM Submissions s
            JOIN Assignments a ON s.assignment_id = a.assignment_id
            WHERE s.student_id = %s
        """, (student_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class GradeSubmission(BaseModel):
    grade: float
    feedback: Optional[str] = None

@router.put("/{submission_id}/grade", dependencies=[Depends(require_role(["Instructor", "Admin"]))])
def grade_submission(submission_id: int, grade_data: GradeSubmission):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.max_score
            FROM Submissions s
            JOIN Assignments a ON s.assignment_id = a.assignment_id
            WHERE s.submission_id = %s
        """, (submission_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Submission not found")

        if grade_data.grade > row["max_score"]:
            raise HTTPException(status_code=400, detail=f"Grade exceeds max score {row['max_score']}")

        cursor.execute("""
            UPDATE Submissions SET grade = %s, feedback = %s WHERE submission_id = %s
        """, (grade_data.grade, grade_data.feedback, submission_id))
        conn.commit()

        return {"message": "Submission graded"}
    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()