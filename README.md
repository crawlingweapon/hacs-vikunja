# Vikunja Task Manager

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6+-yellow.svg)](https://www.home-assistant.io)
[![PyPI](https://img.shields.io/badge/dependency-vikunja--python-blue.svg)](https://pypi.org/project/vikunja-python/)

Home Assistant custom integration for [Vikunja](https://vikunja.io/) task management. Displays your saved filters as sensors with task counts and details.

## Features

- Add Vikunja URL and API token via the HA UI config flow
- Configure which saved filters to track (e.g., Overdue, Due Today, Due Soon)
- Each filter becomes a sensor with state = task count and attributes = task list
- Supports any number of saved filters
- Options flow to add or remove filters after setup
- Polls all filters in parallel every 5 minutes

## Dependencies

This integration automatically uses HA's async session for non-blocking SSL. It is a self-contained component and does not require any additional pip packages else than what HA ships.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=hacs-vikunja&category=integration&owner=crawlingweapon)

Or manually:

1. In HACS, click the three dots in the top-right corner
2. Select "Custom repositories"
3. Add `https://github.com/crawlingweapon/hacs-vikunja` with category "Integration"
4. Click "Download" on the Vikunja Task Manager integration
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/vikunja/` directory into your Home Assistant `custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "Vikunja"
3. Enter your Vikunja URL (e.g., `https://vikunja.example.com`) and an API token
4. Click Submit
5. On the next screen, enter a Project ID (negative number) and a display name for the filter to track:
   - **Project ID**: The negative project ID of your saved filter (e.g., -3 for Overdue, -4 for Due Today)
   - **Project Name**: A friendly name for the sensor (e.g., "Overdue")
6. Click Submit
7. To add more filters later: **Settings → Devices & Services → Vikunja → Configure**

### Getting your API Token

1. Log into your Vikunja instance
2. Go to **Settings > API Tokens**
3. Create a new token with read permissions
4. Copy the token and paste it into the config flow

### Modifying Filters After Setup

1. Go to **Settings > Devices & Services**
2. Find the Vikunja integration
3. Click **Configure**
4. Add, remove, or modify your saved filters

## Sensors

Each saved filter creates a sensor:

```yaml
sensor.vikunja_-3_overdue:
  friendly_name: "Vikunja Overdue"
  state: 5  # task count
  attributes:
    tasks:
      - id: 42
        title: "Fix garage door"
        due_date: "2026-07-01T00:00:00Z"
        priority: 3
      - id: 17
        title: "Pay electric bill"
        due_date: "2026-06-28T00:00:00Z"
        priority: 1
    filter_id: -3
```

## Saved Filter IDs

Vikunja saved filters are accessed via negative project IDs. Common defaults:

| ID | Typical Name | Description |
|----|-------------|-------------|
| -2 | Due in 3 Days | Tasks due within the next 3 days |
| -3 | Overdue | Past-due incomplete tasks |
| -4 | Due Today | Tasks due today |

You can create additional saved filters in the Vikunja UI and reference them by their negative project ID.

