"""Zone / Area management and address → zone detection."""
from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.errors import (
    DuplicateResourceError,
    NotFoundError,
    ValidationError,
    ZoneNotFoundError,
)
from app.domain.zones import AreaAlias, match_area, normalize_text
from app.models.zone import Area, Zone
from app.schemas.zone import AreaCreate, AreaUpdate, ZoneCreate, ZoneUpdate


class ZoneService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Zones ---
    def list_zones(self) -> List[Zone]:
        return self.db.query(Zone).order_by(Zone.code).all()

    def get_zone(self, zone_id: int) -> Zone:
        zone = self.db.get(Zone, zone_id)
        if zone is None:
            raise ZoneNotFoundError(f"Zone {zone_id} not found.")
        return zone

    def create_zone(self, data: ZoneCreate) -> Zone:
        if self.db.query(Zone).filter(Zone.code == data.code).first():
            raise DuplicateResourceError(f"Zone code '{data.code}' already exists.")
        zone = Zone(
            code=data.code,
            name=data.name,
            city=data.city,
            is_active=data.is_active,
        )
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def update_zone(self, zone_id: int, data: ZoneUpdate) -> Zone:
        zone = self.get_zone(zone_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(zone, field, value)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    # --- Areas ---
    def list_areas(self, zone_id: Optional[int] = None) -> List[Area]:
        query = self.db.query(Area)
        if zone_id is not None:
            query = query.filter(Area.zone_id == zone_id)
        return query.order_by(Area.name).all()

    def create_area(self, data: AreaCreate) -> Area:
        self.get_zone(data.zone_id)  # ensure zone exists
        normalized = normalize_text(data.name)
        if not normalized:
            raise ValidationError("Area name cannot be empty after normalization.")
        if self.db.query(Area).filter(Area.normalized_name == normalized).first():
            raise DuplicateResourceError(f"Area '{data.name}' already exists.")
        area = Area(
            name=data.name,
            normalized_name=normalized,
            zone_id=data.zone_id,
            is_active=data.is_active,
        )
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return area

    def update_area(self, area_id: int, data: AreaUpdate) -> Area:
        area = self.db.get(Area, area_id)
        if area is None:
            raise NotFoundError(f"Area {area_id} not found.")
        payload = data.model_dump(exclude_unset=True)
        if "zone_id" in payload:
            self.get_zone(payload["zone_id"])  # validate target zone
        if "name" in payload and payload["name"]:
            normalized = normalize_text(payload["name"])
            clash = (
                self.db.query(Area)
                .filter(Area.normalized_name == normalized, Area.id != area_id)
                .first()
            )
            if clash:
                raise DuplicateResourceError(f"Area '{payload['name']}' already exists.")
            area.normalized_name = normalized
        for field, value in payload.items():
            setattr(area, field, value)
        self.db.commit()
        self.db.refresh(area)
        return area

    # --- Detection ---
    def detect_zone(self, address: str) -> Tuple[Area, Zone]:
        """Resolve an address to its Area and Zone via the admin-managed mapping.

        Raises :class:`ZoneNotFoundError` when the address cannot be mapped — the
        system never silently guesses a zone.
        """
        aliases = [
            AreaAlias(area_id=a.id, zone_id=a.zone_id, name=a.name)
            for a in self.db.query(Area).filter(Area.is_active.is_(True)).all()
        ]
        match = match_area(address, aliases)
        if match is None:
            raise ZoneNotFoundError(
                f"Could not detect a serviceable zone for address: '{address}'.",
                details={"address": address},
            )
        area = self.db.get(Area, match.area_id)
        zone = self.db.get(Zone, match.zone_id)
        if area is None or zone is None or not zone.is_active:
            raise ZoneNotFoundError("Matched zone is not serviceable.")
        return area, zone
