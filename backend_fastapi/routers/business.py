import uuid
import json
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
        supabase.storage.from_(BUCKET).upload(
            filename, content, {"content-type": "image/jpeg", "upsert": "true"}
        )
        return supabase.storage.from_(BUCKET).get_public_url(filename)
    except Exception as e:
        print(f"Photo upload error: {e}")
        return None


@router.get("/businessid")
async def get_business_ids(conn: asyncpg.Connection = Depends(get_db)):
    rows = await conn.fetch("SELECT business_id FROM businesses ORDER BY business_id")
    return [r["business_id"] for r in rows]


@router.get("/results")
async def search_businesses(
    search_query: str = Query(""),
    user_id: Optional[str] = Depends(get_optional_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        rows = await conn.fetch("""
            SELECT business_id, name, address, city, state, postal_code,
                   latitude, longitude, stars, review_count, categories,
                   aspect_scores, photo_url
            FROM businesses
            WHERE
                name ILIKE $1 OR
                address ILIKE $1 OR
                city ILIKE $1 OR
                state ILIKE $1 OR
                EXISTS (
                    SELECT 1 FROM unnest(categories) c WHERE c ILIKE $1
                )
            ORDER BY stars DESC NULLS LAST
            LIMIT 100
        """, f"%{search_query}%")

        results = []
        user_vector = None

        if user_id:
            user_row = await conn.fetchrow(
                "SELECT preference_vector FROM users WHERE user_id = $1", user_id
            )
            if user_row and user_row["preference_vector"]:
                pref = list(user_row["preference_vector"])
                if any(v != 0 for v in pref):
                    user_vector = pref

        for row in rows:
            b = dict(row)
            b["aspect_scores"] = b["aspect_scores"] or {}
            b["categories"] = b["categories"] or []

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
async def get_business(business_id: str, conn: asyncpg.Connection = Depends(get_db)):
    try:
        row = await conn.fetchrow("""
            SELECT business_id, name, address, city, state, postal_code,
                   latitude, longitude, stars, review_count, categories,
                   aspect_scores, photo_url
            FROM businesses WHERE business_id = $1
        """, business_id)

        if not row:
            raise HTTPException(status_code=404, detail="Business not found")

        reviews = await conn.fetch("""
            SELECT r.review_id, r.text, r.stars, r.created_at, r.user_id,
                   u.name as user_name
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.business_id = $1
            ORDER BY r.created_at DESC
        """, business_id)

        result = dict(row)
        result["aspect_scores"] = result["aspect_scores"] or {}
        result["categories"] = result["categories"] or []
        result["reviews"] = [dict(r) for r in reviews]

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/business")
async def create_business(
    business: str = Form(...),
    business_pic: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        data = json.loads(business)
        business_id = str(uuid.uuid4())

        categories = data.get("categories", [])
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",") if c.strip()]

        photo_url = await upload_photo(business_pic, business_id) if business_pic else None

        await conn.execute("""
            INSERT INTO businesses (
                business_id, name, address, city, state, postal_code,
                latitude, longitude, categories, photo_url, review_count, stars
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,0,0)
        """,
            business_id,
            data.get("name"),
            data.get("address"),
            data.get("city"),
            data.get("state"),
            data.get("postal_code"),
            data.get("latitude"),
            data.get("longitude"),
            categories,
            photo_url
        )

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
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        data = json.loads(business)

        categories = data.get("categories", [])
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",") if c.strip()]

        photo_url = None
        if business_pic and business_pic.filename:
            photo_url = await upload_photo(business_pic, business_id)

        if photo_url:
            await conn.execute("""
                UPDATE businesses SET
                    name=$1, address=$2, city=$3, state=$4, postal_code=$5,
                    latitude=$6, longitude=$7, categories=$8, photo_url=$9,
                    updated_at=NOW()
                WHERE business_id=$10
            """, data.get("name"), data.get("address"), data.get("city"),
                data.get("state"), data.get("postal_code"),
                data.get("latitude"), data.get("longitude"),
                categories, photo_url, business_id)
        else:
            await conn.execute("""
                UPDATE businesses SET
                    name=$1, address=$2, city=$3, state=$4, postal_code=$5,
                    latitude=$6, longitude=$7, categories=$8, updated_at=NOW()
                WHERE business_id=$9
            """, data.get("name"), data.get("address"), data.get("city"),
                data.get("state"), data.get("postal_code"),
                data.get("latitude"), data.get("longitude"),
                categories, business_id)

        return {"message": "Business updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/business/{business_id}")
async def delete_business(business_id: str, conn: asyncpg.Connection = Depends(get_db)):
    try:
        await conn.execute("DELETE FROM businesses WHERE business_id = $1", business_id)
        return {"message": "Business deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard(
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        # Find business owned by user (stored in a has_business_id column or we find by user)
        # For now, return businesses associated with this user via a simple heuristic
        row = await conn.fetchrow("""
            SELECT b.business_id, b.name, b.address, b.city, b.state,
                   b.stars, b.review_count, b.aspect_scores, b.photo_url
            FROM businesses b
            WHERE b.business_id = (
                SELECT has_business_id FROM users WHERE user_id = $1
            )
        """, user_id)

        if not row:
            raise HTTPException(status_code=404, detail="No business found for this user")

        reviews = await conn.fetch("""
            SELECT r.review_id, r.text, r.stars, r.created_at, r.user_id,
                   u.name as user_name
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.business_id = $1
            ORDER BY r.created_at DESC
        """, row["business_id"])

        result = dict(row)
        result["reviews"] = [dict(r) for r in reviews]
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
