import uuid
import asyncio
from typing import List, Optional
import asyncpg
import numpy as np
import pandas as pd
from scipy import stats
from fastapi import APIRouter, Depends, HTTPException
from sklearn.preprocessing import MinMaxScaler

from database import get_db
from models.review import ReviewCreate, ReviewUpdate

router = APIRouter(prefix="/api", tags=["reviews"])

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
    """Map [-1,1] aspect scores to [1,5] range"""
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


async def update_user_vector(conn: asyncpg.Connection, user_id: str, review_vector: list):
    """Update user preference vector after a new review (PostgreSQL version)"""
    # Get all user's reviews
    user_reviews = await conn.fetch("""
        SELECT r.review_id, r.business_id, r.stars, r.aspect_vector, r.user_id
        FROM reviews r WHERE r.user_id = $1
    """, user_id)

    if not user_reviews:
        return

    # Get current user data
    user_row = await conn.fetchrow(
        "SELECT user_id, preference_vector FROM users WHERE user_id = $1", user_id
    )
    if not user_row:
        return

    current_vector = list(user_row["preference_vector"]) if user_row["preference_vector"] else [0.0] * 5

    # Build DataFrames
    review_data = [{
        "user_id": r["user_id"],
        "business_id": r["business_id"],
        "stars": float(r["stars"] or 3),
        "aspect_vector": list(r["aspect_vector"]) if r["aspect_vector"] else [0] * 5
    } for r in user_reviews]

    user_data = [{"user_id": user_id, "preference_vector": current_vector}]
    review_df = pd.DataFrame(review_data)
    user_df = pd.DataFrame(user_data)

    # Calculate updated scores
    try:
        updated_scores = calculate_scores(user_df, review_df)
        new_vector = updated_scores.loc[user_id, "vector"]
    except Exception:
        new_vector = [0.0] * 5

    # Apply update formula
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

    # Normalize
    try:
        vector_to_update = normalize_to_distribution(vector_to_update)
    except Exception:
        vector_to_update = [max(0.0, min(1.0, v)) for v in vector_to_update]

    # Average stars
    avg_stars = sum(float(r["stars"] or 3) for r in user_reviews) / len(user_reviews)

    vector_str = f"[{','.join(str(v) for v in vector_to_update)}]"
    await conn.execute("""
        UPDATE users SET preference_vector = $1::vector, updated_at = NOW()
        WHERE user_id = $2
    """, vector_str, user_id)


async def update_business_scores(conn: asyncpg.Connection, business_id: str):
    """Recalculate business stars and aspect scores from all reviews"""
    reviews = await conn.fetch("""
        SELECT stars, aspect_vector FROM reviews WHERE business_id = $1
    """, business_id)

    if not reviews:
        return

    avg_stars = sum(float(r["stars"] or 3) for r in reviews) / len(reviews)

    avg_vector = [0.0] * 5
    for r in reviews:
        if r["aspect_vector"]:
            for i, v in enumerate(list(r["aspect_vector"])):
                avg_vector[i] += float(v)

    for i in range(5):
        avg_vector[i] /= len(reviews)

    aspect_scores = {
        "food": avg_vector[0],
        "service": avg_vector[1],
        "price": avg_vector[2],
        "ambience": avg_vector[3],
        "misc": avg_vector[4]
    }

    import json
    await conn.execute("""
        UPDATE businesses
        SET stars = $1, aspect_scores = $2::jsonb, review_count = $3, updated_at = NOW()
        WHERE business_id = $4
    """, avg_stars, json.dumps(aspect_scores), len(reviews), business_id)


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/business/{business_id}/review")
async def create_review(
    business_id: str,
    body: ReviewCreate,
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        # Generate ABSA vector in thread pool (CPU-intensive)
        vector_score = await asyncio.to_thread(get_generate_vector(), body.text)
        vector_str = f"[{','.join(str(v) for v in vector_score)}]"

        review_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO reviews (review_id, business_id, user_id, text, stars, aspect_vector)
            VALUES ($1, $2, $3, $4, $5, $6::vector)
        """, review_id, business_id, body.user_id, body.text, body.stars, vector_str)

        # Update user preference vector and business scores
        await update_user_vector(conn, body.user_id, vector_score)
        await update_business_scores(conn, business_id)

        return {"message": "Review created successfully", "review_id": review_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/business/{business_id}/review/{review_id}")
async def update_review(
    business_id: str,
    review_id: str,
    body: ReviewUpdate,
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        vector_score = await asyncio.to_thread(get_generate_vector(), body.text)
        vector_str = f"[{','.join(str(v) for v in vector_score)}]"

        await conn.execute("""
            UPDATE reviews SET stars = $1, text = $2, aspect_vector = $3::vector
            WHERE review_id = $4
        """, body.stars, body.text, vector_str, review_id)

        await update_business_scores(conn, business_id)

        return {"message": "Review updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/business/{business_id}/review/{review_id}")
async def delete_review(
    business_id: str,
    review_id: str,
    conn: asyncpg.Connection = Depends(get_db)
):
    try:
        await conn.execute("DELETE FROM reviews WHERE review_id = $1", review_id)
        await update_business_scores(conn, business_id)
        return {"message": "Review deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
