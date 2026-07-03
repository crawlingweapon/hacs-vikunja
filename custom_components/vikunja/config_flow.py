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
        vol.Required(CONF_VK_AT): str,
    }
)


def _filter_schema(filters=None):
    """Build schema for filter config."""
    existing = filters or []
    if not existing:
        existing = [{"id": -2, "name": "Due in 3 Days"}, {"id": -3, "name": "Overdue"}, {"id": -4, "name": "Due Today"}]
    schema = {}
    for i, f in enumerate(existing):
        schema[vol.Required(f"{CONF_FILTER_ID}_{i}", default=f["id"])] = int
        schema[vol.Required(f"{CONF_FILTER_NAME}_{i}", default=f["name"])] = str
    for i in range(len(existing), len(existing) + 5):
        schema[vol.Optional(f"{CONF_FILTER_ID}_{i}", default="")] = str
        schema[vol.Optional(f"{CONF_FILTER_NAME}_{i}", default="")] = str
    return vol.Schema(schema)


def _extract_filters(user_input):
    """Extract non-empty filters from form data."""
    filters = []
    i = 0
    while f"{CONF_FILTER_ID}_{i}" in user_input or f"{CONF_FILTER_NAME}_{i}" in user_input:
        fid = user_input.get(f"{CONF_FILTER_ID}_{i}")
        fname = user_input.get(f"{CONF_FILTER_NAME}_{i}")
        if fid and fname:
            filters.append({"id": int(fid), "name": fname})
        i += 1
    return filters


async def validate_input(data):
    """Validate URL + token by hitting Vikunja API."""
    session = async_get_clientsession()
    raw = data[CONF_URL].rstrip("/")
    base = raw.replace("/api/v1", "").rstrip("/")
    api_url = base + "/api/v1"
    headers = {"Authorization": "Bearer " + data[CONF_VK_AT]}
    try:
        resp = await session.get(api_url + "/info", headers=headers, timeout=10)
        if resp.status == 200:
            data[CONF_URL] = api_url
            return {"title": "Vikunja"}
        if resp.status == 401:
            raise ValueError("Invalid token")
        resp.raise_for_status()
    except ValueError:
        raise
    except Exception as exc:
        raise CannotConnect from exc
    raise CannotConnect


class VikunjaConfigFlow(config_entries.ConfigFlow, domain="vikunja"):
    """Config flow for Vikunja."""
    VERSION = 1

    def __init__(self):
        self._auth_data = {}

    async def async_step_user(self, user_input=None):
        """Step 1: URL + token."""
        errors = {}
        if user_input:
            try:
                info = await validate_input(user_input)
                self._auth_data = user_input
                return await self.async_step_filters()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Config flow error")
                errors["base"] = "unknown"
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    async def async_step_filters(self, user_input=None):
        """Step 2: choose saved filters."""
        errors = {}
        if user_input:
            filters = _extract_filters(user_input)
            if not filters:
                errors["base"] = "no_filters"
            else:
                data = dict(self._auth_data)
                data["filters"] = filters
                uid = "vikunja_" + data[CONF_URL].replace("https://","").replace("/","_")
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Vikunja", data=data)
        defaults = [{"id": -2, "name": "Due in 3 Days"}, {"id": -3, "name": "Overdue"}, {"id": -4, "name": "Due Today"}]
        return self.async_show_form(step_id="filters", data_schema=_filter_schema(defaults), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return VikunjaOptionsFlow(config_entry)


class VikunjaOptionsFlow(config_entries.OptionsFlow):
    """Options flow to manage filters."""

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage filters."""
        errors = {}
        if user_input:
            f = _extract_filters(user_input)
            if not f:
                errors["base"] = "no_filters"
            else:
                return self.async_create_entry(title="", data={"filters": f})
        current = self._entry.data.get("filters", [])
        return self.async_show_form(step_id="init", data_schema=_filter_schema(current), errors=errors)


class CannotConnect(Exception):
    """Connection error."""

