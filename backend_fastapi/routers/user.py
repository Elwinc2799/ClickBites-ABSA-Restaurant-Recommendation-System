import uuid
import json
from typing import Optional
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse
from supabase import create_client
import os

from database import get_db
from auth import hash_password, verify_password, create_token, get_current_user
from models.user import UserLogin

router = APIRouter(prefix="/api", tags=["users"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = "business-photos"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@router.post("/signup")
async def signup(
    user: str = Form(...),
    profile_pic: Optional[UploadFile] = File(None),
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        user_data = json.loads(user)
        name = user_data.get("name")
        email = user_data.get("email")
        password = user_data.get("password")

        if not all([name, email, password]):
            raise HTTPException(status_code=400, detail="name, email, and password are required")

        existing = await conn.fetchrow("SELECT user_id FROM users WHERE email = $1", email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        await conn.execute("""
            INSERT INTO users (user_id, name, email, password_hash)
            VALUES ($1, $2, $3, $4)
        """, user_id, name, email, password_hash)

        return {"message": "User created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(
    body: UserLogin,
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        email = body.email
        password = body.password

        row = await conn.fetchrow(
            "SELECT user_id, password_hash FROM users WHERE email = $1", email
        )
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(password, row["password_hash"]):
            raise HTTPException(status_code=404, detail="Invalid credentials")

        token = create_token(row["user_id"])
        return {"message": "Login successful", "access_token": token}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/getUserId")
async def get_user_id(user_id: str = Depends(get_current_user)):
    return {"userId": user_id}


@router.get("/getHasBusinessFlag")
async def get_has_business_flag(
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    row = await conn.fetchrow(
        "SELECT business_id FROM businesses WHERE business_id = (SELECT has_business_id FROM users WHERE user_id = $1)",
        user_id
    )
    has_business = row is not None
    return {"has_business": has_business}


@router.get("/profile/{user_id}")
async def get_profile(user_id: str, conn: asyncpg.Connection = Depends(get_db)):
    try:
        user = await conn.fetchrow(
            "SELECT user_id, name, email, preference_vector FROM users WHERE user_id = $1",
            user_id
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        reviews = await conn.fetch("""
            SELECT r.review_id, r.text, r.stars, r.created_at,
                   b.name as business_name, b.city as business_city, b.business_id
            FROM reviews r
            JOIN businesses b ON r.business_id = b.business_id
            WHERE r.user_id = $1
            ORDER BY r.created_at DESC
        """, user_id)

        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "preference_vector": list(user["preference_vector"]) if user["preference_vector"] else [0] * 5,
            "reviews": [dict(r) for r in reviews]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/{user_id}")
async def update_profile(
    user_id: str,
    user: str = Form(...),
    profile_pic: Optional[UploadFile] = File(None),
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        user_data = json.loads(user)
        name = user_data.get("name")
        email = user_data.get("email")

        await conn.execute("""
            UPDATE users SET name = $1, email = $2, updated_at = NOW()
            WHERE user_id = $3
        """, name, email, user_id)

        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
