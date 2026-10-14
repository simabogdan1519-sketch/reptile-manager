"""
Automatic sync of Reptile Manager data into Home Assistant.

Every change made in the app (new animal, feeding, shed, pairing, edit, delete…)
schedules a debounced sync that pushes one sensor per animal plus a few summary
sensors to Home Assistant via its REST API. A periodic sync keeps "days since
feeding" current and re-creates the entities after an HA restart.

Connection:
  1. Explicit HA URL + long-lived token from Settings, if both are set.
  2. Otherwise, when running as an HA add-on with `homeassistant_api: true`,
     the Supervisor proxy (http://supervisor/core) with $SUPERVISOR_TOKEN —
     zero configuration needed.
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from . import models
from .database import SessionLocal

logger = logging.getLogger("reptile.ha_sync")

ENTITY_PREFIX = "sensor.reptile_"
MARKER = "reptile_manager"            # attribute that marks entities we own
DEBOUNCE_SECONDS = 2.0
PERIODIC_SECONDS = 15 * 60

status = {
    "last_sync": None,      # ISO timestamp
    "ok": None,             # bool
    "entities": 0,
    "error": None,
    "mode": None,           # "token" | "supervisor" | None
}

_pending: Optional[asyncio.Task] = None
_lock = asyncio.Lock()


# ── Connection ────────────────────────────────────────────────────────────────

def ha_target(cfg: Optional[models.HAConfig]):
    """Return (base_url, token, mode) or (None, None, None)."""
    if cfg and cfg.ha_url and cfg.ha_token:
        return cfg.ha_url.rstrip("/"), cfg.ha_token, "token"
    sup = os.environ.get("SUPERVISOR_TOKEN")
    if sup:
        return "http://supervisor/core", sup, "supervisor"
    return None, None, None


def sync_enabled(cfg: Optional[models.HAConfig]) -> bool:
    if cfg is None:
        return True
    return cfg.entity_sync is not False


# ── Data → entities ───────────────────────────────────────────────────────────

def _aware(d):
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def build_entities(db) -> dict:
    """entity_id -> {"state": str, "attributes": dict}"""
    now = datetime.now(timezone.utc)
    cfg = db.query(models.HAConfig).first()
    global_threshold = (cfg.feeding_reminder_days if cfg else None) or 7

    out = {}
    animals = db.query(models.Animal).order_by(models.Animal.name).all()
    due_names, active = [], 0

    for a in animals:
        is_active = (a.status or "active") == "active"
        active += is_active
        last_feed = (db.query(models.Feeding)
                     .filter(models.Feeding.animal_id == a.id, models.Feeding.accepted.is_(True))
                     .order_by(models.Feeding.date.desc()).first())
        last_any_feed = (db.query(models.Feeding)
                         .filter(models.Feeding.animal_id == a.id)
                         .order_by(models.Feeding.date.desc()).first())
        last_shed = (db.query(models.Shedding)
                     .filter(models.Shedding.animal_id == a.id)
                     .order_by(models.Shedding.date.desc()).first())
        feed_count = db.query(models.Feeding).filter(models.Feeding.animal_id == a.id).count()

        days_fed = (now - _aware(last_feed.date)).days if last_feed else None
        days_shed = (now - _aware(last_shed.date)).days if last_shed else None
        interval = a.feeding_reminder_days or global_threshold
        reminder = a.feeding_reminder_enabled is not False
        needs = bool(is_active and reminder and (days_fed is None or days_fed >= interval))
        if needs:
            due_names.append(a.name)

        entity_id = f"{ENTITY_PREFIX}{a.id}"
        out[entity_id] = {
            "state": str(days_fed) if days_fed is not None else "unknown",
            "attributes": {
                MARKER: True,
                "friendly_name": a.name,
                "icon": "mdi:snake",
                "unit_of_measurement": "d",
                "state_class": "measurement",
                "animal_id": a.id,
                "tracking_id": a.tracking_id,
                "name": a.name,
                "species": a.species,
                "common_name": a.common_name,
                "morph": a.morph,
                "sex": a.sex.value if a.sex else "unknown",
                "status": a.status or "active",
                "group": a.group.name if a.group else None,
                "weight_g": a.weight_g,
                "length_cm": a.length_cm,
                "date_of_birth": a.date_of_birth.isoformat() if a.date_of_birth else None,
                "needs_feeding": needs,
                "feeding_reminder": reminder,
                "feeding_interval_days": interval,
                "days_since_feeding": days_fed,
                "last_feeding": _aware(last_feed.date).isoformat() if last_feed else None,
                "last_feeding_food": " ".join(x for x in [
                    f"{last_any_feed.food_count}x" if last_any_feed and (last_any_feed.food_count or 1) > 1 else None,
                    last_any_feed.food_size if last_any_feed else None,
                    last_any_feed.food_type if last_any_feed else None] if x) or None,
                "last_feeding_accepted": last_any_feed.accepted if last_any_feed else None,
                "feedings_total": feed_count,
                "days_since_shed": days_shed,
                "last_shed": _aware(last_shed.date).isoformat() if last_shed else None,
                "last_shed_complete": last_shed.complete if last_shed else None,
                "temp_day_c": a.temp_day_c,
                "temp_night_c": a.temp_night_c,
                "humidity_min": a.humidity_min,
                "humidity_max": a.humidity_max,
            },
        }

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    out[f"{ENTITY_PREFIX}manager_active_animals"] = {
        "state": str(active),
        "attributes": {MARKER: True, "friendly_name": "Reptiles active", "icon": "mdi:snake",
                       "unit_of_measurement": "animals", "state_class": "measurement",
                       "total_animals": len(animals)},
    }
    out[f"{ENTITY_PREFIX}manager_feeding_due"] = {
        "state": str(len(due_names)),
        "attributes": {MARKER: True, "friendly_name": "Reptiles feeding due", "icon": "mdi:food-drumstick-off",
                       "unit_of_measurement": "animals", "state_class": "measurement",
                       "animals": due_names},
    }
    out[f"{ENTITY_PREFIX}manager_feedings_today"] = {
        "state": str(db.query(models.Feeding).filter(models.Feeding.date >= today).count()),
        "attributes": {MARKER: True, "friendly_name": "Reptile feedings today", "icon": "mdi:food-drumstick",
                       "unit_of_measurement": "feedings", "state_class": "measurement"},
    }
    return out


# ── Push ──────────────────────────────────────────────────────────────────────

async def sync_now() -> dict:
    """Push all entities and remove ones that no longer exist."""
    async with _lock:
        db = SessionLocal()
        try:
            cfg = db.query(models.HAConfig).first()
            base, token, mode = ha_target(cfg)
            status["mode"] = mode
            if not sync_enabled(cfg):
                status.update(ok=None, error="disabled")
                return dict(status)
            if not base:
                status.update(ok=False, error="No Home Assistant connection (set URL + token in Settings)")
                return dict(status)
            entities = build_entities(db)
        finally:
            db.close()

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        pushed, errors = 0, []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for entity_id, body in entities.items():
                    r = await client.post(f"{base}/api/states/{entity_id}", json=body, headers=headers)
                    if r.status_code in (200, 201):
                        pushed += 1
                    else:
                        errors.append(f"{entity_id}: HTTP {r.status_code}")
                        if r.status_code in (401, 403):
                            break
                # Remove stale entities we created earlier (deleted animals)
                r = await client.get(f"{base}/api/states", headers=headers)
                if r.status_code == 200:
                    for st in r.json():
                        eid = st.get("entity_id", "")
                        if eid.startswith(ENTITY_PREFIX) and st.get("attributes", {}).get(MARKER) and eid not in entities:
                            await client.delete(f"{base}/api/states/{eid}", headers=headers)
        except Exception as exc:  # network errors etc.
            errors.append(str(exc))

        status.update(
            last_sync=datetime.now(timezone.utc).isoformat(),
            ok=not errors,
            entities=pushed,
            error="; ".join(errors[:3]) or None,
        )
        if errors:
            logger.warning("HA sync finished with errors: %s", status["error"])
        return dict(status)


async def fire_event(event_type: str, data: dict) -> bool:
    """Fire a native HA event (usable as automation trigger)."""
    db = SessionLocal()
    try:
        cfg = db.query(models.HAConfig).first()
        base, token, _ = ha_target(cfg)
        if not base or not sync_enabled(cfg):
            return False
    finally:
        db.close()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{base}/api/events/{event_type}", json=data,
                                  headers={"Authorization": f"Bearer {token}"})
            return r.status_code == 200
    except Exception as exc:
        logger.warning("HA event %s failed: %s", event_type, exc)
        return False


def schedule_sync(delay: float = DEBOUNCE_SECONDS):
    """Debounced: many quick changes result in a single sync."""
    global _pending
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _pending and not _pending.done():
        _pending.cancel()

    async def _run():
        try:
            await asyncio.sleep(delay)
            await sync_now()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("HA sync failed: %s", exc)

    _pending = loop.create_task(_run())


async def periodic_loop():
    await asyncio.sleep(10)
    while True:
        try:
            await sync_now()
        except Exception as exc:
            logger.warning("Periodic HA sync failed: %s", exc)
        await asyncio.sleep(PERIODIC_SECONDS)
