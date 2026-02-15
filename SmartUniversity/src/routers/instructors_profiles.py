from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/instructor-profiles",
    tags=["Instructor Profiles"]
)

@router.get("/")
def list_instructor_profiles(
    instructor_id: Optional[int] = None,
    department: Optional[str] = None,
    research: Optional[str] = None,
    title: Optional[str] = None,
    user=Depends(require_token)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT 
            u.full_name,
            u.email,
            ip.instructor_id,
            ip.title,
            ip.office_location,
            ip.research_interests,
            d.name AS department_name
        FROM Instructor_Profiles ip
        JOIN Users u ON ip.instructor_id = u.user_id
        LEFT JOIN Departments d ON ip.department_id = d.department_id
        WHERE 1=1
        """
        params = []

        if instructor_id:
            query += " AND ip.instructor_id = %s"
            params.append(instructor_id)

        if department:
            query += " AND d.name LIKE %s"
            params.append(f"%{department}%")

        if research:
            query += " AND ip.research_interests LIKE %s"
            params.append(f"%{research}%")

        if title:
            query += " AND ip.title LIKE %s"
            params.append(f"%{title}%")

        cursor.execute(query, params)

        if instructor_id:
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Instructor profile not found")
            return row

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

class InstructorProfileUpdate(BaseModel):
    title: Optional[str] = None
    office_location: Optional[str] = None
    research_interests: Optional[str] = None

@router.put("/{instructor_id}")
def update_instructor_profile(
    instructor_id: int, 
    profile: InstructorProfileUpdate, 
    user=Depends(require_token)
):
    if user["role"] == "Instructor" and user["user_id"] != instructor_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    
    if user["role"] == "Student":
        raise HTTPException(status_code=403, detail="Students cannot update instructor profiles")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        update_data = profile.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k} = %s" for k in update_data])
        values = list(update_data.values()) + [instructor_id]

        cursor.execute(
            f"UPDATE Instructor_Profiles SET {set_clause} WHERE instructor_id = %s",
            values
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Instructor profile not found")

        return {"message": "Instructor profile updated"}

    finally:
        cursor.close()
        conn.close()