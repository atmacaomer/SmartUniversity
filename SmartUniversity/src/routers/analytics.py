from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

@router.get("/instructor-workload-performance")
def instructor_workload_performance(
    min_students: int = Query(5, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(require_role(["Admin"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        WITH instructor_load AS (
            SELECT
                s.instructor_id,
                COUNT(DISTINCT s.section_id) AS sections_taught,
                COUNT(e.student_id) AS total_students
            FROM Course_Sections s
            LEFT JOIN Enrollments e ON s.section_id = e.section_id
            GROUP BY s.instructor_id
        ),
        performance AS (
            SELECT
                s.instructor_id,
                AVG(CASE WHEN e.grade >= 2.0 THEN 1 ELSE 0 END) AS success_ratio
            FROM Course_Sections s
            JOIN Enrollments e ON s.section_id = e.section_id
            WHERE e.completion_status = 'Completed'
            GROUP BY s.instructor_id
        )
        SELECT
            u.user_id AS instructor_id,
            u.full_name,
            il.sections_taught,
            il.total_students,
            ROUND(COALESCE(p.success_ratio, 0) * 100, 2) AS success_percentage
        FROM instructor_load il
        JOIN Users u ON il.instructor_id = u.user_id
        LEFT JOIN performance p ON il.instructor_id = p.instructor_id
        WHERE il.total_students >= %s
        ORDER BY success_percentage DESC, il.total_students DESC
        LIMIT %s
        """
        cursor.execute(query, (min_students, limit))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@router.get("/most-difficult-courses")
def most_difficult_courses(
    min_students: int = Query(5, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_role(["Admin", "Instructor"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        WITH course_results AS (
            SELECT
                c.course_id,
                c.course_code,
                c.title,
                COUNT(e.enrollment_id) AS total_students,
                SUM(CASE WHEN e.grade < 1.0 THEN 1 ELSE 0 END) AS failures
            FROM Courses c
            JOIN Course_Sections s ON c.course_id = s.course_id
            JOIN Enrollments e ON s.section_id = e.section_id
            WHERE e.completion_status = 'Completed'
            GROUP BY c.course_id, c.course_code, c.title
        )
        SELECT
            course_code,
            title,
            total_students,
            failures,
            ROUND((failures / total_students) * 100, 2) AS failure_rate
        FROM course_results
        WHERE total_students >= %s
        ORDER BY failure_rate DESC, total_students DESC
        LIMIT %s
        """
        cursor.execute(query, (min_students, limit))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@router.get("/top-risk-students")
def top_risk_students(
    semester: str, 
    limit: int = Query(20, ge=1, le=200), 
    user=Depends(require_role(["Admin", "Instructor"]))
):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = """
        WITH enrolled AS (
            SELECT e.student_id, e.section_id
            FROM Enrollments e
            JOIN Course_Sections cs ON cs.section_id = e.section_id
            WHERE cs.semester = %s
        ),
        att AS (
            SELECT
                a.student_id,
                a.section_id,
                COUNT(*) AS total_classes,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absences
            FROM Attendance a
            JOIN enrolled en ON en.student_id = a.student_id AND en.section_id = a.section_id
            GROUP BY a.student_id, a.section_id
        ),
        asg AS (
            SELECT
                a.section_id,
                COUNT(*) AS total_assignments
            FROM Assignments a
            JOIN Course_Sections cs ON cs.section_id = a.section_id
            WHERE cs.semester = %s
            GROUP BY a.section_id
        ),
        sub AS (
            SELECT
                s.student_id,
                a.section_id,
                COUNT(*) AS submitted
            FROM Submissions s
            JOIN Assignments a ON a.assignment_id = s.assignment_id
            JOIN Course_Sections cs ON cs.section_id = a.section_id
            WHERE cs.semester = %s
            GROUP BY s.student_id, a.section_id
        ),
        grades AS (
            SELECT
                e.student_id,
                AVG(e.grade) AS avg_grade
            FROM Enrollments e
            JOIN Course_Sections cs ON cs.section_id = e.section_id
            WHERE cs.semester = %s
            GROUP BY e.student_id
        ),
        per_section AS (
            SELECT
                en.student_id,
                en.section_id,
                COALESCE(att.total_classes, 0) AS total_classes,
                COALESCE(att.absences, 0) AS absences,
                COALESCE(asg.total_assignments, 0) AS total_assignments,
                COALESCE(sub.submitted, 0) AS submitted
            FROM enrolled en
            LEFT JOIN att ON att.student_id = en.student_id AND att.section_id = en.section_id
            LEFT JOIN asg ON asg.section_id = en.section_id
            LEFT JOIN sub ON sub.student_id = en.student_id AND sub.section_id = en.section_id
        ),
        per_student AS (
            SELECT
                ps.student_id,
                SUM(ps.total_classes) AS total_classes,
                SUM(ps.absences) AS absences,
                SUM(ps.total_assignments) AS total_assignments,
                SUM(ps.submitted) AS submitted
            FROM per_section ps
            GROUP BY ps.student_id
        )
        SELECT
            u.user_id AS student_id,
            u.full_name,
            sp.current_gpa,
            g.avg_grade,
            ROUND(
                (CASE WHEN sp.current_gpa IS NULL THEN 0 ELSE GREATEST(0, (2.5 - sp.current_gpa)) END) * 0.45
              + (CASE WHEN st.total_classes = 0 THEN 0 ELSE (st.absences / st.total_classes) END) * 0.35
              + (CASE WHEN st.total_assignments = 0 THEN 0 ELSE ((st.total_assignments - st.submitted) / st.total_assignments) END) * 0.20
            , 4) AS risk_score
        FROM per_student st
        JOIN Users u ON u.user_id = st.student_id
        LEFT JOIN Student_Profiles sp ON sp.student_id = u.user_id
        LEFT JOIN grades g ON g.student_id = u.user_id
        WHERE u.role = 'Student' AND u.is_active = 1
        ORDER BY risk_score DESC
        LIMIT %s
        """
        cur.execute(query, (semester, semester, semester, semester, limit))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()