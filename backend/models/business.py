from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class BusinessCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    categories: Optional[List[str]] = []
    description: Optional[str] = None
    is_open: Optional[int] = 1
    hours: Optional[Dict[str, Any]] = None


class BusinessUpdate(BusinessCreate):
    pass


class BusinessResponse(BaseModel):
    business_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stars: Optional[float] = None
    review_count: int = 0
    categories: Optional[List[str]] = []
    aspect_scores: Optional[Dict[str, Any]] = {}
    photo_url: Optional[str] = None
    similarity: Optional[float] = None
