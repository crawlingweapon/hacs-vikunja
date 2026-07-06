"""Config flow for Vikunja Home Assistant integration."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_URL,
    CONF_VK_AT,
    CONF_FILTERS,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    DEFAULT_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): str,
        vol.Required(CONF_VK_AT): str,
    }
)


def _filter_schema(existing: list[dict] | None = None) -> vol.Schema:
    """Build schema for filter configuration. Shows current filters for editing."""
    existing = existing or []
    # Always offer at least one blank row so users can start fresh
    rows = existing if existing else [{"id": "", "name": ""}]
    schema = {}
    for i, f in enumerate(rows):
        default_id = f["id"] if f["id"] != "" else ""
        default_name = f["name"] if f["name"] != "" else ""
        schema[vol.Required(f"{CONF_PROJECT_ID}_{i}", default=default_id)] = (
            vol.All(str, vol.Length(min=0))
        )
        schema[vol.Required(f"{CONF_PROJECT_NAME}_{i}", default=default_name)] = (
            vol.All(str, vol.Length(min=0))
        )
    return vol.Schema(schema)


def _extract_filters(user_input: dict) -> list[dict]:
    """Extract non-empty filters from form data."""
    filters = []
    i = 0
    while f"{CONF_PROJECT_ID}_{i}" in user_input or f"{CONF_PROJECT_NAME}_{i}" in user_input:
        pid = user_input.get(f"{CONF_PROJECT_ID}_{i}")
        pname = user_input.get(f"{CONF_PROJECT_NAME}_{i}")
        if pid and pname:
            try:
                filters.append({"id": int(pid), "name": str(pname)})
            except (ValueError, TypeError):
                pass
        i += 1
    return filters


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate URL by hitting the /info endpoint (no auth required)."""
    session = async_get_clientsession(hass)
    url = data[CONF_URL].rstrip("/")
    api_url = url.replace("/api/v1", "").rstrip("/") + "/api/v1"
    data[CONF_URL] = api_url

    try:
        resp = await session.get(f"{api_url}/info", timeout=10)
        if resp.status == 200:
            info = await resp.json()
            return {"title": f"Vikunja {info.get('version', '')}".strip()}
        resp.raise_for_status()
    except Exception as exc:
        raise CannotConnect from exc

    raise CannotConnect


class VikunjaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vikunja."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._auth_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: URL + API token."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self._auth_data = user_input
                return await self.async_step_filters()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_filters(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Configure at least one saved filter to track."""
        errors = {}
        if user_input is not None:
            filters = _extract_filters(user_input)
            if not filters:
                errors["base"] = "no_filters"
            else:
                data = {**self._auth_data, CONF_FILTERS: filters}
                await self.async_set_unique_id(
                    f"vikunja_{data[CONF_URL].replace('https://','').replace('/','_')}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Vikunja",
                    data=data,
                )

        return self.async_show_form(
            step_id="filters",
            data_schema=_filter_schema(None),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow handler."""
        return VikunjaOptionsFlow(config_entry)


class VikunjaOptionsFlow(config_entries.OptionsFlow):
    """Options flow to add/remove tracked filters."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage filters."""
        errors = {}
        if user_input is not None:
            filters = _extract_filters(user_input)
            if not filters:
                errors["base"] = "no_filters"
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_FILTERS: filters},
                )

        current = self._config_entry.data.get(CONF_FILTERS, [])
        return self.async_show_form(
            step_id="init",
            data_schema=_filter_schema(current),
            errors=errors,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
