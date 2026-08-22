"""Delivery-agent schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import AgentStatus


class AgentCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    current_zone_id: Optional[int] = None
    max_active_orders: int = Field(default=5, gt=0, le=100)


class AgentUpdate(BaseModel):
    max_active_orders: Optional[int] = Field(default=None, gt=0, le=100)
    current_zone_id: Optional[int] = None
    is_active: Optional[bool] = None


class AvailabilityUpdate(BaseModel):
    status: AgentStatus


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: AgentStatus
    current_zone_id: Optional[int] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    last_location_update: Optional[datetime] = None
    max_active_orders: int
    active_orders: int
    is_active: bool


class AgentProfile(AgentOut):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None


class ScoredAgentOut(BaseModel):
    agent_id: int
    name: str
    score: float
    distance_km: Optional[float] = None
    zone_score: float
    workload_score: float
    freshness_score: float
    distance_score: float
    explanation: str


class AssignmentResult(BaseModel):
    agent: AgentProfile
    decision: ScoredAgentOut
    candidates_considered: int
    ranking: List[ScoredAgentOut] = []
