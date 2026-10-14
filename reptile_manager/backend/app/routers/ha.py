"""
Home Assistant integration endpoints.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from ..access import require_admin
from ..ha_client import test_ha_connection, push_sensor_state

router = APIRouter()

@router.get("/config", response_model=schemas.HAConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    cfg = db.query(models.HAConfig).first()
    if not cfg:
        raise HTTPException(404, "HA config not found")
    return cfg

@router.put("/config", response_model=schemas.HAConfigResponse)
def update_config(
    data: schemas.HAConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    cfg = db.query(models.HAConfig).first()
    if not cfg:
        cfg = models.HAConfig()
        db.add(cfg)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    db.commit()
    db.refresh(cfg)
    return cfg

@router.post("/test")
async def test_connection(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    cfg = db.query(models.HAConfig).first()
    if not cfg:
        return {"success": False, "error": "No HA config found"}
    return await test_ha_connection(cfg)

@router.get("/sensors")
def get_sensors(db: Session = Depends(get_db)):
    """
    Public endpoint — no auth required so Home Assistant REST sensor can poll it.

    Configure in HA configuration.yaml:

        rest:
          - resource: http://YOUR_SERVER:8000/api/ha/sensors
            sensor:
              - name: Reptile Animals Count
                value_template: "{{ value_json.summary.active_animals }}"
              - name: Reptiles Not Fed
                value_template: "{{ value_json.summary.animals_not_fed }}"
    """
    now = datetime.now(timezone.utc)

    # Load global HA config for fallback threshold
    ha_cfg = db.query(models.HAConfig).first()
    global_threshold = ha_cfg.feeding_reminder_days if ha_cfg else 7

    animals = db.query(models.Animal).filter(models.Animal.is_active.is_(True)).all()

    sensor_data = []
    for a in animals:
        # Per-animal threshold overrides global; None = use global
        threshold = a.feeding_reminder_days if a.feeding_reminder_days else global_threshold
        reminder_active = a.feeding_reminder_enabled if a.feeding_reminder_enabled is not None else True

        last_feeding = (
            db.query(models.Feeding)
            .filter(models.Feeding.animal_id == a.id, models.Feeding.accepted.is_(True))
            .order_by(models.Feeding.date.desc())
            .first()
        )
        last_shedding = (
            db.query(models.Shedding)
            .filter(models.Shedding.animal_id == a.id)
            .order_by(models.Shedding.date.desc())
            .first()
        )

        days_since_feeding = None
        if last_feeding:
            d = last_feeding.date
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            days_since_feeding = (now - d).days

        days_since_shedding = None
        if last_shedding:
            d = last_shedding.date
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            days_since_shedding = (now - d).days

        needs_feeding = reminder_active and (
            days_since_feeding is None or days_since_feeding >= threshold
        )

        sensor_data.append({
            "id": a.id,
            "name": a.name,
            "species": a.species,
            "morph": a.morph,
            "sex": a.sex.value if a.sex else "unknown",
            "weight_g": a.weight_g,
            "length_cm": a.length_cm,
            "days_since_last_feeding": days_since_feeding,
            "days_since_last_shedding": days_since_shedding,
            "feeding_reminder_enabled": reminder_active,
            "feeding_reminder_threshold_days": threshold,
            "needs_feeding": needs_feeding,
            "last_feeding_type": last_feeding.food_type if last_feeding else None,
        })

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "summary": {
            "active_animals": len(animals),
            "animals_not_fed": sum(1 for a in sensor_data if a["needs_feeding"]),
            "total_feedings_today": db.query(models.Feeding)
                .filter(models.Feeding.date >= today_start)
                .count(),
        },
        "animals": sensor_data,
        "generated_at": now.isoformat(),
    }

@router.post("/sync")
async def sync_to_ha(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Push every animal as a sensor entity to Home Assistant right now."""
    from ..ha_sync import sync_now
    result = await sync_now()
    if result.get("ok") is False:
        raise HTTPException(502, result.get("error") or "Sync failed")
    return result


@router.get("/sync-status")
def sync_status(current_user: models.User = Depends(auth.get_current_user)):
    from ..ha_sync import status
    return status
