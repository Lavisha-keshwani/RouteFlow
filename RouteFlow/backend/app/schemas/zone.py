"""Zone and Area schemas."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ZoneCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    is_active: Optional[bool] = None


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    zone_id: int
    is_active: bool


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    city: str
    is_active: bool


class ZoneWithAreas(ZoneOut):
    areas: List[AreaOut] = []


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    zone_id: int
    is_active: bool = True


class AreaUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    zone_id: Optional[int] = None
    is_active: Optional[bool] = None
