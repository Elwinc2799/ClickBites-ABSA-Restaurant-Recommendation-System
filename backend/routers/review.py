import uuid
import asyncio
from typing import List, Optional
import numpy as np
import pandas as pd
from scipy import stats
from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client
import os

from models.review import ReviewCreate, ReviewUpdate
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["reviews"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# Lazy-load the AI module to avoid startup delay
_generate_vector = None


def get_generate_vector():
    global _generate_vector
    if _generate_vector is None:
        from ai.generate_vector import generate_vector
        _generate_vector = generate_vector
    return _generate_vector


# ─── Vector Utilities ────────────────────────────────────────────────────────

def normalize_vector(vector: list) -> list:
    return [(x + 1) / 2 * 4 + 1 for x in vector]


def normalize_to_distribution(lst: list, new_mean=0.5, new_std_dev=0.25) -> list:
    standardized = stats.zscore(lst)
    normalized = new_std_dev * standardized + new_mean
    return np.clip(normalized, 0, 1).tolist()


def calc_importance_scores(group, merged_df) -> list:
    scores = []
    for i in range(5):
        aspect_values = np.array(group["normalized_review_vector"].tolist())[:, i]
        weighted_sum = np.sum(group["stars"].values * aspect_values)
        rating_sqrt = np.sqrt(np.sum(group["stars"].values ** 2))
        sentiment_sqrt = np.sqrt(np.sum(aspect_values ** 2))
        denom = rating_sqrt * sentiment_sqrt
        scores.append(weighted_sum / denom if denom != 0 else 0)
    return scores


def calc_need_scores(group, merged_df) -> list:
    scores = []
    for i in range(5):
        aspect_values = np.array(group["normalized_review_vector"].tolist())[:, i]
        if np.any(aspect_values != 0):
            user_business_scores = []
            for business_id, biz_group in group.groupby("business_id"):
                aspect_df = merged_df[
                    (merged_df["business_id"] == business_id) &
                    (merged_df["normalized_review_vector"].apply(lambda x: x[i] != 0))
                ]
                if len(aspect_df) == 0:
                    continue
                Zi = aspect_df["normalized_review_vector"].apply(lambda x: x[i]).mean()
                user_score = biz_group["normalized_review_vector"].apply(lambda x: x[i]).mean()
                if Zi != 0:
                    user_business_scores.append((Zi - user_score + 1) / Zi)
            scores.append(np.mean(user_business_scores) if user_business_scores else 0)
        else:
            aspect_df = merged_df[merged_df["normalized_review_vector"].apply(lambda x: x[i] != 0)]
            if len(aspect_df) > 0:
                Z = aspect_df["normalized_review_vector"].apply(lambda x: x[i]).mean()
                scores.append(np.sum(0.1 / Z) / len(aspect_df) if Z != 0 else 0)
            else:
                scores.append(0)
    return scores


def calculate_scores(user_df, review_df) -> pd.DataFrame:
    merged_df = pd.merge(user_df, review_df, left_on="user_id", right_on="user_id")
    merged_df["normalized_review_vector"] = merged_df["aspect_vector"].apply(normalize_vector)

    def calc_scores(group):
        importance = calc_importance_scores(group, merged_df)
        need = calc_need_scores(group, merged_df)
        preference = (np.array(importance) * np.array(need)).tolist()
        return pd.Series({"vector": preference})

    return merged_df.groupby("user_id").apply(calc_scores)


def parse_vector_str(s) -> list:
    """Parse pgvector string '[0.1,0.2,...]' to list of floats."""
    if s is None:
        return [0.0] * 5
    if isinstance(s, list):
        return [float(x) for x in s]
    return [float(x) for x in str(s).strip("[]").split(",")]


async def update_user_vector(supabase, user_id: str, review_vector: list):
    """Update user preference vector after a new review (via Supabase REST)."""
    user_reviews_raw = await asyncio.to_thread(
        lambda: supabase.rpc("get_user_reviews_for_vector", {"uid": user_id}).execute()
    )
    if not user_reviews_raw.data:
        return

    user_row_raw = await asyncio.to_thread(
        lambda: supabase.rpc("get_user_preference_vector", {"uid": user_id}).execute()
    )
    current_vector = parse_vector_str(user_row_raw.data if user_row_raw.data else None)

    review_data = [{
        "user_id": r["user_id"],
        "business_id": r["business_id"],
        "stars": float(r["stars"] or 3),
        "aspect_vector": parse_vector_str(r["aspect_vector"]),
    } for r in user_reviews_raw.data]

    user_data = [{"user_id": user_id, "preference_vector": current_vector}]
    review_df = pd.DataFrame(review_data)
    user_df = pd.DataFrame(user_data)

    try:
        updated_scores = calculate_scores(user_df, review_df)
        new_vector = updated_scores.loc[user_id, "vector"]
    except Exception:
        new_vector = [0.0] * 5

    vector_to_update = []
    for i in range(5):
        rv = review_vector[i] if i < len(review_vector) else 0
        if rv != 0:
            initial = 0.5 if current_vector[i] == 0 else current_vector[i]
            if abs(rv) > 0.5:
                vector_to_update.append((1 + (new_vector[i] * abs(rv))) * initial)
            else:
                vector_to_update.append((1 - (new_vector[i] * abs(rv))) * initial)
        else:
            vector_to_update.append(current_vector[i])

    try:
        vector_to_update = normalize_to_distribution(vector_to_update)
    except Exception:
        vector_to_update = [max(0.0, min(1.0, v)) for v in vector_to_update]

    vector_str = f"[{','.join(str(v) for v in vector_to_update)}]"
    await asyncio.to_thread(
        lambda: supabase.table("users").update({"preference_vector": vector_str}).eq("user_id", user_id).execute()
    )


async def update_business_scores(supabase, business_id: str):
    """Recalculate business stars and aspect scores from all reviews."""
    reviews_raw = await asyncio.to_thread(
        lambda: supabase.rpc("get_business_reviews_for_scores", {"bid": business_id}).execute()
    )
    if not reviews_raw.data:
        return

    reviews = reviews_raw.data
    avg_stars = sum(float(r["stars"] or 3) for r in reviews) / len(reviews)

    avg_vector = [0.0] * 5
    for r in reviews:
        vec = parse_vector_str(r["aspect_vector"])
        for i, v in enumerate(vec):
            avg_vector[i] += float(v)
    for i in range(5):
        avg_vector[i] /= len(reviews)

    aspect_scores = {
        "food": avg_vector[0],
        "service": avg_vector[1],
        "price": avg_vector[2],
        "ambience": avg_vector[3],
        "misc": avg_vector[4],
    }

    await asyncio.to_thread(
        lambda: supabase.table("businesses").update({
            "stars": avg_stars,
            "aspect_scores": aspect_scores,
            "review_count": len(reviews),
        }).eq("business_id", business_id).execute()
    )


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/business/{business_id}")
async def create_review(business_id: str, body: ReviewCreate):
    """Uses Supabase REST API + RPC for vector updates."""
    try:
        vector_score = await asyncio.to_thread(get_generate_vector(), body.text)
        vector_str = f"[{','.join(str(v) for v in vector_score)}]"

        review_id = str(uuid.uuid4())
        supabase = get_supabase()

        await asyncio.to_thread(
            lambda: supabase.table("reviews").insert({
                "review_id": review_id,
                "business_id": business_id,
                "user_id": body.user_id,
                "text": body.text,
                "stars": body.stars,
                "aspect_vector": vector_str,
            }).execute()
        )

        await update_user_vector(supabase, body.user_id, vector_score)
        await update_business_scores(supabase, business_id)

        return {"message": "Review created successfully", "review_id": review_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/business/{business_id}/{review_id}")
async def update_review(business_id: str, review_id: str, body: ReviewUpdate):
    """Uses Supabase REST API."""
    try:
        vector_score = await asyncio.to_thread(get_generate_vector(), body.text)
        vector_str = f"[{','.join(str(v) for v in vector_score)}]"

        supabase = get_supabase()
        await asyncio.to_thread(
            lambda: supabase.table("reviews").update({
                "stars": body.stars,
                "text": body.text,
                "aspect_vector": vector_str,
            }).eq("review_id", review_id).execute()
        )

        await update_business_scores(supabase, business_id)

        return {"message": "Review updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/business/{business_id}/{review_id}")
async def delete_review(business_id: str, review_id: str):
    """Uses Supabase REST API."""
    try:
        supabase = get_supabase()
        await asyncio.to_thread(
            lambda: supabase.table("reviews").delete().eq("review_id", review_id).execute()
        )
        await update_business_scores(supabase, business_id)
        return {"message": "Review deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
