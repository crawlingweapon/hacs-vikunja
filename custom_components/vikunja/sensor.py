"""Sensor platform for Vikunja Home Assistant integration."""
from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    CONF_URL,
    CONF_API_TOKEN,
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
    api_token = entry.data[CONF_API_TOKEN]
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

    async def _async_update_data(self) -> dict[int, list[dict]]:
        """Fetch data for all configured filters via the vikunja-python library."""
        from vikunja_python.core.client import VikunjaClient

        async with VikunjaClient(self._url, self._api_token) as client:
            data = await client.get_dashboard_summary()
            return data["filters"]


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
