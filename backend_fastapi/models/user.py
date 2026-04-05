from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserSignup(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    preference_vector: Optional[List[float]] = None
