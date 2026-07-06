"""Config flow for Vikunja Home Assistant integration."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_URL,
    CONF_VK_AT,
    CONF_FILTERS,
    CONF_FILTER_ID,
    CONF_FILTER_NAME,
    DEFAULT_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): str,
    }
)


def _filter_schema(filters: list[dict] | None = None) -> vol.Schema:
    """Build schema for filter configuration, pre-filled with existing filters."""
    existing = filters or [{"id": -2, "name": "Due in 3 Days"}, {"id": -3, "name": "Overdue"}, {"id": -4, "name": "Due Today"}]
    schema = {}
    for i, f in enumerate(existing):
        schema[vol.Required(f"{CONF_FILTER_ID}_{i}", default=f["id"])] = int
        schema[vol.Required(f"{CONF_FILTER_NAME}_{i}", default=f["name"])] = str
    # Allow adding up to 5 more blank filters
    for i in range(len(existing), len(existing) + 5):
        schema[vol.Optional(f"{CONF_FILTER_ID}_{i}", default="")] = str
        schema[vol.Optional(f"{CONF_FILTER_NAME}_{i}", default="")] = str
    return vol.Schema(schema)


def _extract_filters(user_input: dict) -> list[dict]:
    """Extract non-empty filters from the config form data."""
    filters = []
    i = 0
    while f"{CONF_FILTER_ID}_{i}" in user_input or f"{CONF_FILTER_NAME}_{i}" in user_input:
        fid = user_input.get(f"{CONF_FILTER_ID}_{i}")
        fname = user_input.get(f"{CONF_FILTER_NAME}_{i}")
        if fid and fname:
            filters.append({"id": int(fid), "name": fname})
        i += 1
    return filters


async def validate_input(data: dict[str, Any]) -> dict[str, str]:
    """Validate by hitting the Vikunja API info endpoint."""
    session = async_get_clientsession()
    url = data[CONF_URL].rstrip("/")
    api_url = url.replace("/api/v1", "").rstrip("/") + "/api/v1"
    headers = {"Authorization": f"Bearer {data[CONF_VK_AT]}"}

    try:
        resp = await session.get(f"{api_url}/user", headers=headers, timeout=10)
        if resp.status == 200:
            data[CONF_URL] = api_url
            user = await resp.json()
            return {"title": user.get("username", "Vikunja")}
        if resp.status == 401:
            raise ValueError("Invalid API token")
        resp.raise_for_status()
    except ValueError:
        raise
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
                info = await validate_input(user_input)
                self._auth_data = user_input
                return await self.async_step_filters()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_filters(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Configure which saved filters to track."""
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

        defaults = [{"id": -2, "name": "Due in 3 Days"}, {"id": -3, "name": "Overdue"}, {"id": -4, "name": "Due Today"}]
        return self.async_show_form(
            step_id="filters",
            data_schema=_filter_schema(defaults),
            errors=errors,
            description_placeholders={"example": "Use negative IDs like -2 for saved filters"},
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
        """Manage filters options."""
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

        current_filters = self._config_entry.data.get(CONF_FILTERS, [])
        return self.async_show_form(
            step_id="init",
            data_schema=_filter_schema(current_filters),
            errors=errors,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
