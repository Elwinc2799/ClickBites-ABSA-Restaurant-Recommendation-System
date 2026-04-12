import uuid
import json
import asyncio
from typing import Optional, List
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query
from supabase import create_client
import os
import numpy as np

from database import get_db
from auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api", tags=["businesses"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = "business-photos"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def upload_photo(file: UploadFile, business_id: str) -> Optional[str]:
    if not file or not file.filename:
        return None
    try:
        supabase = get_supabase()
        content = await file.read()
        filename = f"{business_id}.jpg"
        await asyncio.to_thread(lambda: supabase.storage.from_(BUCKET).upload(
            filename, content, {"content-type": "image/jpeg", "upsert": "true"}
        ))
        return supabase.storage.from_(BUCKET).get_public_url(filename)
    except Exception as e:
        print(f"Photo upload error: {e}")
        return None


@router.get("/businessid")
async def get_business_ids():
    """Uses Supabase REST API."""
    supabase = get_supabase()
    result = await asyncio.to_thread(
        lambda: supabase.table("businesses").select("business_id").order("business_id").execute()
    )
    return [r["business_id"] for r in result.data]


@router.get("/results")
async def search_businesses(
    search_query: str = Query(""),
    user_id: Optional[str] = Depends(get_optional_user),
):
    """Uses Supabase REST API via RPC for ILIKE + unnest search."""
    try:
        supabase = get_supabase()

        rows = await asyncio.to_thread(
            lambda: supabase.rpc("search_businesses", {"q": search_query}).execute()
        )

        results = []
        user_vector = None

        if user_id:
            user_row = await asyncio.to_thread(
                lambda: supabase.table("users").select("preference_vector").eq("user_id", user_id).execute()
            )
            if user_row.data:
                pref = user_row.data[0].get("preference_vector")
                if pref:
                    if isinstance(pref, str):
                        pref = [float(x) for x in pref.strip("[]").split(",")]
                    if any(v != 0 for v in pref):
                        user_vector = pref

        for row in rows.data:
            b = dict(row)
            b["aspect_scores"] = b.get("aspect_scores") or {}
            b["categories"] = b.get("categories") or []

            if user_vector and b["aspect_scores"]:
                scores = b["aspect_scores"]
                biz_vector = [
                    scores.get("food", 0),
                    scores.get("service", 0),
                    scores.get("price", 0),
                    scores.get("ambience", 0),
                    scores.get("misc", 0)
                ]
                b["similarity"] = cosine_similarity(user_vector, biz_vector)
            else:
                b["similarity"] = float(b.get("stars") or 0) / 5.0

            results.append(b)

        if user_vector:
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/business/{business_id}")
async def get_business(business_id: str):
    """Uses Supabase RPC to fetch business + reviews in one call."""
    try:
        supabase = get_supabase()

        result = await asyncio.to_thread(
            lambda: supabase.rpc("get_business_with_reviews", {"bid": business_id}).execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Business not found")

        data = result.data
        # RPC returns the jsonb directly
        if isinstance(data, list):
            data = data[0] if data else None
        if not data:
            raise HTTPException(status_code=404, detail="Business not found")

        data["aspect_scores"] = data.get("aspect_scores") or {}
        data["categories"] = data.get("categories") or []
        data["reviews"] = data.get("reviews") or []

        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/business")
async def create_business(
    business: str = Form(...),
    business_pic: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user),
):
    """Uses Supabase REST API."""
    try:
        data = json.loads(business)
        business_id = str(uuid.uuid4())

        categories = data.get("categories", [])
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",") if c.strip()]

        photo_url = await upload_photo(business_pic, business_id) if business_pic else None

        supabase = get_supabase()
        await asyncio.to_thread(lambda: supabase.table("businesses").insert({
            "business_id": business_id,
            "name": data.get("name"),
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "postal_code": data.get("postal_code"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "categories": categories,
            "photo_url": photo_url,
            "review_count": 0,
            "stars": 0,
        }).execute())

        return {"message": "Business created successfully", "business_id": business_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/business/{business_id}")
async def update_business(
    business_id: str,
    business: str = Form(...),
    business_pic: Optional[UploadFile] = File(None),
):
    """Uses Supabase REST API."""
    try:
        data = json.loads(business)

        categories = data.get("categories", [])
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",") if c.strip()]

        photo_url = await upload_photo(business_pic, business_id) if (business_pic and business_pic.filename) else None

        update_data = {
            "name": data.get("name"),
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "postal_code": data.get("postal_code"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "categories": categories,
        }
        if photo_url:
            update_data["photo_url"] = photo_url

        supabase = get_supabase()
        await asyncio.to_thread(lambda: supabase.table("businesses").update(update_data).eq("business_id", business_id).execute())

        return {"message": "Business updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/business/{business_id}")
async def delete_business(business_id: str):
    """Uses Supabase REST API."""
    try:
        supabase = get_supabase()
        await asyncio.to_thread(lambda: supabase.table("businesses").delete().eq("business_id", business_id).execute())
        return {"message": "Business deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard(user_id: str = Depends(get_current_user)):
    """Uses Supabase REST API."""
    try:
        supabase = get_supabase()

        # Get user's business id
        user_row = await asyncio.to_thread(
            lambda: supabase.table("users").select("has_business_id").eq("user_id", user_id).execute()
        )
        if not user_row.data or not user_row.data[0].get("has_business_id"):
            raise HTTPException(status_code=404, detail="No business found for this user")

        biz_id = user_row.data[0]["has_business_id"]
        result = await asyncio.to_thread(
            lambda: supabase.rpc("get_business_with_reviews", {"bid": biz_id}).execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="No business found for this user")

        data = result.data
        if isinstance(data, list):
            data = data[0] if data else None
        if not data:
            raise HTTPException(status_code=404, detail="No business found for this user")

        data["reviews"] = data.get("reviews") or []
        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
