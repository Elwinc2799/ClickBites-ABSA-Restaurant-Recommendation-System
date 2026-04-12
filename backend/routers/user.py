import uuid
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse
from supabase import create_client
import os

from auth import hash_password, verify_password, create_token, get_current_user
from models.user import UserLogin

router = APIRouter(prefix="/api", tags=["users"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = "business-photos"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_preference_vector(pref) -> list:
    if pref is None:
        return [0.0] * 5
    if isinstance(pref, list):
        return [float(x) for x in pref]
    if isinstance(pref, str):
        return [float(x) for x in pref.strip("[]").split(",")]
    return [0.0] * 5


@router.post("/signup")
async def signup(
    user: str = Form(...),
    profile_pic: Optional[UploadFile] = File(None),
):
    """Uses Supabase REST API (HTTPS) — no direct PostgreSQL connection needed."""
    try:
        user_data = json.loads(user)
        name = user_data.get("name")
        email = user_data.get("email")
        password = user_data.get("password")

        if not all([name, email, password]):
            raise HTTPException(status_code=400, detail="name, email, and password are required")

        import asyncio
        supabase = get_supabase()

        # Check if email exists
        existing = await asyncio.to_thread(
            lambda: supabase.table("users").select("user_id").eq("email", email).execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        await asyncio.to_thread(
            lambda: supabase.table("users").insert({
                "user_id": user_id,
                "name": name,
                "email": email,
                "password_hash": password_hash,
            }).execute()
        )

        return {"message": "User created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(body: UserLogin):
    """Uses Supabase REST API (HTTPS) — no direct PostgreSQL connection needed."""
    try:
        import asyncio
        supabase = get_supabase()

        result = await asyncio.to_thread(
            lambda: supabase.table("users").select("user_id,password_hash").eq("email", body.email).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")

        row = result.data[0]
        if not verify_password(body.password, row["password_hash"]):
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
async def get_has_business_flag(user_id: str = Depends(get_current_user)):
    """Uses Supabase REST API."""
    try:
        supabase = get_supabase()
        user_row = await asyncio.to_thread(
            lambda: supabase.table("users").select("has_business_id").eq("user_id", user_id).execute()
        )
        if not user_row.data or not user_row.data[0].get("has_business_id"):
            return {"has_business": False}
        biz_id = user_row.data[0]["has_business_id"]
        biz_row = await asyncio.to_thread(
            lambda: supabase.table("businesses").select("business_id").eq("business_id", biz_id).execute()
        )
        return {"has_business": bool(biz_row.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Uses Supabase REST API."""
    try:
        supabase = get_supabase()
        user_row = await asyncio.to_thread(
            lambda: supabase.table("users").select("user_id,name,email,preference_vector").eq("user_id", user_id).execute()
        )
        if not user_row.data:
            raise HTTPException(status_code=404, detail="User not found")
        user = user_row.data[0]

        reviews_raw = await asyncio.to_thread(
            lambda: supabase.rpc("get_user_profile_reviews", {"uid": user_id}).execute()
        )

        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "preference_vector": parse_preference_vector(user.get("preference_vector")),
            "reviews": reviews_raw.data or [],
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
):
    """Uses Supabase REST API."""
    try:
        user_data = json.loads(user)
        name = user_data.get("name")
        email = user_data.get("email")
        supabase = get_supabase()
        await asyncio.to_thread(
            lambda: supabase.table("users").update({"name": name, "email": email}).eq("user_id", user_id).execute()
        )
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
