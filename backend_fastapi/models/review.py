from pydantic import BaseModel
from typing import Optional, List


class ReviewCreate(BaseModel):
    user_id: str
    stars: float
    text: str
    date: Optional[str] = None


class ReviewUpdate(BaseModel):
    stars: float
    text: str
    date: Optional[str] = None


class ReviewResponse(BaseModel):
    review_id: str
    business_id: str
    user_id: str
    text: str
    stars: Optional[float] = None
    aspect_vector: Optional[List[float]] = None
