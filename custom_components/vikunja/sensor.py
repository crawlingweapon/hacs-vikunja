"""Sensor platform for Vikunja Home Assistant integration."""
from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    CONF_URL,
    CONF_VK_AT,
    CONF_FILTERS,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vikunja sensors based on a config entry."""
    url = entry.data[CONF_URL].rstrip("/")
    api_token = entry.data[CONF_VK_AT]
    filters = entry.data.get(CONF_FILTERS, [])

    coordinator = VikunjaDataCoordinator(hass, url, api_token, filters)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        VikunjaTaskSensor(coordinator, f["id"], f["name"])
        for f in filters
    ]
    async_add_entities(sensors)


class VikunjaDataCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Vikunja task data for all configured saved filters."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_token: str,
        filters: list[dict],
    ) -> None:
        """Initialize coordinator."""
        self._url = url
        self._api_token = api_token
        self._filters = filters

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, dict]:
        """Fetch task counts for each configured filter using HA's async session."""
        session = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self._api_token}"}

        async def fetch(f: dict) -> tuple[str, dict]:
            key = str(f["id"])
            params = {"page": 1, "per_page": 10, "project_id": f["id"]}
            try:
                resp = await session.get(
                    f"{self._url}/tasks",
                    headers=headers,
                    params=params,
                    timeout=10,
                )
                if resp.status == 200:
                    tasks = await resp.json()
                    if not isinstance(tasks, list):
                        tasks = []
                    return key, {
                        "count": len(tasks),
                        "tasks": [
                            {
                                "id": t.get("id"),
                                "title": t.get("title"),
                                "due_date": t.get("due_date"),
                                "priority": t.get("priority", 0),
                            }
                            for t in tasks[:10]
                        ],
                    }
                _LOGGER.warning("Vikunja filter %s returned status %s", f["id"], resp.status)
                return key, {"count": 0, "tasks": [], "error": resp.status}
            except Exception as exc:
                _LOGGER.warning("Vikunja filter %s error: %s", f["id"], exc)
                return key, {"count": 0, "tasks": [], "error": str(exc)}

        import asyncio
        results = await asyncio.gather(*[fetch(f) for f in self._filters])
        return dict(results)


class VikunjaTaskSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a Vikunja saved filter."""

    def __init__(
        self,
        coordinator: VikunjaDataCoordinator,
        filter_id: int,
        filter_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        safe_name = filter_name.lower().replace(" ", "_").replace("-", "_")
        self._filter_id = filter_id
        self._filter_key = str(filter_id)
        self._attr_unique_id = f"vikunja_{self._filter_key}_{safe_name}"
        self._attr_name = f"Vikunja {filter_name}"
        self._attr_icon = "mdi:checkbox-marked-outline"

    @property
    def native_value(self) -> int:
        """Return the task count."""
        data = self.coordinator.data.get(self._filter_key, {})
        return data.get("count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return tasks as a structured attribute."""
        data = self.coordinator.data.get(self._filter_key, {})
        return {
            "tasks": data.get("tasks", [])[:20],
            "filter_id": self._filter_id,
        }
