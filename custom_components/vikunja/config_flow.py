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

CONF_VK_AT = "access_token"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): str,
        vol.Required(CONF_VK_AT): str,
    }
)
