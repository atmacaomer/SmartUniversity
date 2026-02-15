from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
import mysql.connector
from ..db import get_db_connection
from ..routers.auth import require_token, require_role, hash_password

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: Literal["Student", "Instructor", "Admin"]
    department_id: Optional[int] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[Literal["Student", "Instructor", "Admin"]] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

@router.get("/", dependencies=[Depends(require_role(["Admin"]))])
def list_users(search: Optional[str] = None, role: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT user_id, full_name, email, role, created_at
        FROM Users
        WHERE is_active = 1
        """
        params = []
        if search:
            query += " AND (full_name LIKE %s OR email LIKE %s)"
            s = f"%{search}%"
            params.extend([s, s])
        if role:
            query += " AND role = %s"
            params.append(role)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@router.get("/me")
def get_current_user_profile(user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT user_id, full_name, email, role, created_at 
            FROM Users WHERE user_id = %s
        """, (user["user_id"],))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

@router.put("/me/change-password")
def change_own_password(data: PasswordChangeRequest, user=Depends(require_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        user_id = user["user_id"]
        cursor.execute("SELECT password_hash FROM Users WHERE user_id = %s", (user_id,))
        db_user = cursor.fetchone()
        if not db_user or db_user["password_hash"] != hash_password(data.old_password):
            raise HTTPException(status_code=401, detail="Current password incorrect")
        new_hash = hash_password(data.new_password)
        cursor.execute("UPDATE Users SET password_hash = %s WHERE user_id = %s", (new_hash, user_id))
        conn.commit()
        return {"message": "Password updated successfully"}
    finally:
        cursor.close()
        conn.close()

@router.post("/", dependencies=[Depends(require_role(["Admin"]))])
def create_new_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Users (full_name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (user.full_name, user.email, hash_password(user.password), user.role)
        )
        user_id = cursor.lastrowid
        
        if user.role == "Student":
            # CHANGE: Check for None explicitly to allow ID 0 if valid
            if user.department_id is None:
                raise HTTPException(status_code=400, detail="Student requires department_id")
            
            cursor.execute(
                "INSERT INTO Student_Profiles (student_id, department_id, current_gpa) VALUES (%s, %s, 0.0)",
                (user_id, user.department_id)
            )
        elif user.role == "Instructor":
            # CHANGE: Check for None explicitly
            if user.department_id is None:
                raise HTTPException(status_code=400, detail="Instructor requires department_id")
            
            cursor.execute(
                "INSERT INTO Instructor_Profiles (instructor_id, department_id) VALUES (%s, %s)",
                (user_id, user.department_id)
            )
            
        conn.commit()
        return {"user_id": user_id, "message": "User created"}
        
    except mysql.connector.IntegrityError as err:
        conn.rollback()
        # Handle duplicate email (Error 1062)
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="Email already exists")
        # Handle invalid Foreign Key (e.g. Department ID 0 does not exist)
        if err.errno == 1452: 
            raise HTTPException(status_code=400, detail="Invalid department_id")
            
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

@router.put("/{user_id}", dependencies=[Depends(require_role(["Admin"]))])
def update_user(user_id: int, user_data: UserUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = user_data.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")
        if "password" in data:
            data["password_hash"] = hash_password(data.pop("password"))
        set_clause = ", ".join([f"{k}=%s" for k in data])
        values = list(data.values()) + [user_id]
        cursor.execute(f"UPDATE Users SET {set_clause} WHERE user_id = %s", values)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User updated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/{user_id}", dependencies=[Depends(require_role(["Admin"]))])
def delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Users SET is_active = 0 WHERE user_id = %s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deactivated"}
    finally:
        cursor.close()
        conn.close()

@router.delete("/hard-delete/{user_id}", dependencies=[Depends(require_role(["Admin"]))])
def hard_delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM Users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        role = row[0]
        if role == "Student":
            cursor.execute("DELETE FROM Student_Profiles WHERE student_id = %s", (user_id,))
        elif role == "Instructor":
            cursor.execute("DELETE FROM Instructor_Profiles WHERE instructor_id = %s", (user_id,))
        cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"message": "User permanently deleted"}
    finally:
        cursor.close()
        conn.close()