from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import hashlib
from ..db import get_db_connection

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 2

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: int, role: str):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(data: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, password_hash, role FROM Users WHERE email = %s AND is_active = 1",
        (data.email,)
    )
    user = cursor.fetchone()
    if not user or user["password_hash"] != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["user_id"], user["role"])
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register")
def register(data: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Users (full_name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (data.full_name, data.email, hash_password(data.password), data.role)
        )
        conn.commit()
        return {"message": "User registered successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

def require_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(allowed_roles: list[str]):
    def role_checker(payload: dict = Depends(require_token)):
        if payload["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    return role_checker