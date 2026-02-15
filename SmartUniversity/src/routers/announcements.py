from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_db_connection
from ..routers.auth import require_token, require_role

router = APIRouter(
    prefix="/announcements",
    tags=["Announcements"]
)

@router.get("/")
def list_announcements(section_id: int, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Student":
            cursor.execute("""
                SELECT 1 FROM Enrollments 
                WHERE student_id = %s AND section_id = %s
            """, (user["user_id"], section_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="You are not enrolled in this section")

        cursor.execute(
            """
            SELECT announcement_id, section_id, title, content, publish_date
            FROM Announcements
            WHERE section_id = %s
            ORDER BY publish_date DESC
            """,
            (section_id,)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

class AnnouncementCreate(BaseModel):
    section_id: int
    title: str
    content: str

@router.post("/")
def create_announcement(post: AnnouncementCreate, user=Depends(require_role(["Instructor", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Instructor":
            cursor.execute("""
                SELECT 1 FROM Course_Sections 
                WHERE section_id = %s AND instructor_id = %s
            """, (post.section_id, user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="You do not teach this section")

        cursor.execute(
            "INSERT INTO Announcements (section_id, title, content) VALUES (%s, %s, %s)",
            (post.section_id, post.title, post.content)
        )
        conn.commit()
        return {"message": "Announcement posted", "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

@router.put("/{announcement_id}")
def update_announcement(announcement_id: int, post: AnnouncementUpdate, user=Depends(require_role(["Instructor", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Instructor":
            cursor.execute("""
                SELECT 1 FROM Announcements a
                JOIN Course_Sections s ON a.section_id = s.section_id
                WHERE a.announcement_id = %s AND s.instructor_id = %s
            """, (announcement_id, user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied")

        data = post.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [announcement_id]

        cursor.execute(f"UPDATE Announcements SET {set_clause} WHERE announcement_id = %s", values)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")

        return {"message": "Announcement updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: int, user=Depends(require_role(["Instructor", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user["role"] == "Instructor":
            cursor.execute("""
                SELECT 1 FROM Announcements a
                JOIN Course_Sections s ON a.section_id = s.section_id
                WHERE a.announcement_id = %s AND s.instructor_id = %s
            """, (announcement_id, user["user_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=403, detail="Access denied")

        cursor.execute("DELETE FROM Announcements WHERE announcement_id = %s", (announcement_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")

        return {"message": "Announcement deleted"}
    finally:
        cursor.close()
        conn.close()