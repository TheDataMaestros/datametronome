# DataMetronome Streamlit UI

> **📁 DIRECTORY TYPE**: Standalone Streamlit Application  
> **🚫 NOT A PYPI PACKAGE** - This is a standalone application, not a Python library

The default Streamlit user interface for the DataMetronome data observability platform.

## Overview

The Streamlit UI provides an intuitive, tiered interface for creating and managing data quality checks. It communicates with the Podium backend exclusively via its public API.

## Features

- **Tiered Check Creation** - Guided interfaces for different check complexity levels
- **Real-time Dashboard** - Live monitoring of data quality checks
- **Interactive Results** - Rich visualizations of check results and metrics
- **User Management** - JWT-based authentication and user management
- **Responsive Design** - Works on desktop and mobile devices

## Installation

This is a standalone application. Clone the repository and run it directly:

## Quick Start

1. Ensure the Podium backend is running
2. Set the backend URL:
```bash
export DATAMETRONOME_BACKEND_URL="http://localhost:8000"
```

3. Run the UI:
```bash
streamlit run datametronome_ui_streamlit/main.py
```

The UI will start on `http://localhost:8501` by default.

## Configuration

The UI uses environment variables for configuration:

- `DATAMETRONOME_BACKEND_URL` - Backend API URL (default: http://localhost:8000)
- `DATAMETRONOME_UI_TITLE` - UI title (default: DataMetronome)
- `DATAMETRONOME_UI_THEME` - UI theme (default: light)

## Development

```bash
git clone https://github.com/datametronome/datametronome.git
cd datametronome/ui-streamlit
pip install -r requirements.txt
streamlit run datametronome_ui_streamlit/main.py
```

## Logos and Branding

Place your brand assets directly in `datametronome/ui-streamlit/assets/`:

- `logo_datametronome.svg` – main header logo (used on login and dashboard)
- `logo_datapulse.svg` – footer badge (“Powered by DataPulse”)

Optionally, you can also provide `logo_datametronome.png` which will be used as the browser page icon (favicon) since Streamlit’s `page_icon` expects an emoji or raster image.
