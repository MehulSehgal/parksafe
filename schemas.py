from typing import Optional
from pydantic import BaseModel, Field


class SpotIn(BaseModel):
    name: str
    area: str
    lat: float
    lng: float
    price: float = 0
    spots_left: int = 1
    total: int = 1
    legal_status: str = Field(default="Legal", pattern="^(Legal|Restricted|Illegal)$")
    cctv: bool = False
    lighting: bool = False
    patrolled: bool = False
    tow_zone: bool = False
    theft_reports: int = 0
    reported_by: Optional[str] = None


class SpotOut(SpotIn):
    id: int
    safety_score: int
    theft_risk: str
    community_rating: float
    reviews_count: int
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class ReviewIn(BaseModel):
    author: str = "Anonymous"
    stars: int = Field(ge=1, le=5)
    text: str = ""


class ReviewOut(ReviewIn):
    id: int
    spot_id: int

    class Config:
        from_attributes = True


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    name: str


class ChallanIn(BaseModel):
    spot_id: int
    plate: str
    amount: float = 500
    reason: str = "Parked in a tow-risk / illegal zone"


class TowZoneIn(BaseModel):
    area: str
    lat: float
    lng: float
    radius_m: float = 50
    reason: str = "Reported by municipal admin"
