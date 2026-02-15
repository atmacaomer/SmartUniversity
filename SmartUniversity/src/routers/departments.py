from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)

@router.get("/")
def list_departments(
    faculty_name: Optional[str] = None,
    department_name: Optional[str] = None,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT department_id, name, faculty_name, budget_code, head_of_department
        FROM Departments
        WHERE 1=1
        """
        params = []

        if faculty_name:
            query += " AND faculty_name = %s"
            params.append(faculty_name)

        if department_name:
            query += " AND name LIKE %s"
            params.append(f"%{department_name}%")

        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class DepartmentCreate(BaseModel):
    name: str
    faculty_name: str
    budget_code: str
    head_of_department: Optional[str] = None

@router.post("/", dependencies=[Depends(require_role(["Admin"]))])
def create_department(dept: DepartmentCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Departments (name, faculty_name, budget_code, head_of_department)
            VALUES (%s, %s, %s, %s)
        """, (dept.name, dept.faculty_name, dept.budget_code, dept.head_of_department))
        conn.commit()
        return {"message": "Department created", "department_id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    budget_code: Optional[str] = None
    head_of_department: Optional[str] = None

@router.put("/{department_id}", dependencies=[Depends(require_role(["Admin"]))])
def update_department(department_id: int, dept: DepartmentUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = dept.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [department_id]

        cursor.execute(
            f"UPDATE Departments SET {set_clause} WHERE department_id=%s",
            values
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Department not found")

        return {"message": "Department updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{department_id}", dependencies=[Depends(require_role(["Admin"]))])
def delete_department(department_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM Student_Profiles WHERE department_id=%s",
            (department_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Department has students")

        cursor.execute(
            "SELECT COUNT(*) FROM Instructor_Profiles WHERE department_id=%s",
            (department_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Department has instructors")

        cursor.execute(
            "SELECT COUNT(*) FROM Courses WHERE department_id=%s",
            (department_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Department has courses")

        cursor.execute(
            "DELETE FROM Departments WHERE department_id=%s",
            (department_id,)
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Department not found")

        return {"message": "Department deleted"}
    finally:
        cursor.close()
        conn.close()