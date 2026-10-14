"""
Home Assistant integration client.

Pushes events to HA via webhook and provides sensor data.
"""
import httpx
import logging
from typing import Optional
from . import models

logger = logging.getLogger(__name__)

async def notify_ha(config: models.HAConfig, event_type: str, data: dict) -> bool:
    """Fire a native HA event and, if configured, call the HA webhook."""
    from .ha_sync import fire_event
    await fire_event(event_type, data)
    if not config.ha_url or not config.webhook_id:
        return False

    url = f"{config.ha_url.rstrip('/')}/api/webhook/{config.webhook_id}"
    payload = {"event_type": event_type, "data": data}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except httpx.TimeoutException:
        logger.warning("HA webhook timeout for event: %s", event_type)
    except Exception as exc:
        logger.warning("HA webhook failed: %s", exc)
    return False

async def test_ha_connection(config: models.HAConfig) -> dict:
    """Verbindung zur HA-API testen."""
    from .ha_sync import ha_target
    base, token, mode = ha_target(config)
    if not base:
        return {"success": False, "error": "URL or token not configured"}

    url = f"{base}/api/"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return {"success": True, "message": "Connection successful" + (" (via Supervisor)" if mode == "supervisor" else "")}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"success": False, "error": "Connection timed out"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

async def push_sensor_state(config: models.HAConfig, entity_id: str, state: str, attributes: dict) -> bool:
    """Sensor-State in HA setzen."""
    if not config.ha_url or not config.ha_token:
        return False

    url = f"{config.ha_url.rstrip('/')}/api/states/{entity_id}"
    headers = {
        "Authorization": f"Bearer {config.ha_token}",
        "Content-Type": "application/json",
    }
    payload = {"state": state, "attributes": attributes}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code in (200, 201)
    except Exception as exc:
        logger.warning("HA state push failed: %s", exc)
    return False
