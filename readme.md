# Flapi - FastAPI Low-Code Framework

Flapi is a low-code framework for building web applications that serve both
human-facing webpages and JSON APIs. It supports Flask and FastAPI backends.

## Installation

```bash
pip install ionbus_flapi
```

## Quick Start

### 1. Create a Config File

Create `config/windows.yaml` (or `linux.yaml`):

```yaml
app_type: fastapi  # or "flask"
host: 0.0.0.0
port: 5080
proxy_prefix: MyApp
title: My Application
shutdown_code: "secret123"  # Optional: enables /shutdown endpoint
```

### 2. Create an Endpoint Module

Create `MyEndpoints/endpoints.py`:

```python
from __future__ import annotations

from ionbus_flapi import FlapiPage, HtmlComponent, register_endpoint

MODULE_NAME = "MyEndpoints"
HTML_DESCRIPTION = "<li>My custom endpoints.</li>"


def initialize() -> None:
    """Initialize endpoints in this module."""
    register_endpoint(
        MODULE_NAME,
        "HelloWorld",
        hello_world_endpoint,
        ep_description="A simple hello world example.",
    )


def hello_world_endpoint() -> FlapiPage:
    """Display a hello world page."""
    return FlapiPage(
        title="Hello World",
        objects=[
            HtmlComponent(html="<h2>Hello, World!</h2>"),
            "<p>This is my first Flapi endpoint.</p>",  # strings work too
        ],
    )
```

### 3. Create the Main App

Create `app.py`:

```python
from __future__ import annotations

import sys
from ionbus_flapi import initialize, register_endpoint_group, serve

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise RuntimeError("Must provide .yaml config file")

    initialize(sys.argv[1])

    import MyEndpoints.endpoints

    register_endpoint_group(
        MyEndpoints.endpoints.initialize,
        MyEndpoints.endpoints.MODULE_NAME,
        MyEndpoints.endpoints.HTML_DESCRIPTION,
    )

    serve()
```

### 4. Run

```bash
python app.py config/windows.yaml
```

Visit `http://localhost:5080/MyApp/` to see your endpoints.

## Core Concepts

### FlapiPage

The main container for building HTML pages:

```python
from ionbus_flapi import FlapiPage

page = FlapiPage(
    title="My Page",
    objects=[...],           # List of components or strings
    theme_toggle=True,       # Show theme toggle button
    refresh_in_seconds=30,   # Auto-refresh interval
)
```

### Components

Components are objects that render to HTML. Available components:

| Component | Description | Example |
|-----------|-------------|---------|
| `HtmlComponent` | Raw HTML | `HtmlComponent(html="<h1>Title</h1>")` |
| `FrameComponent` | JQX Data Grid | `FrameComponent(frame=df)` |
| `PlotlyComponent` | Plotly Chart | `PlotlyComponent(plotly_obj=fig)` |
| `ImageComponent` | Base64 Image | `ImageComponent(encoded_image=b64)` |
| `MarkdownComponent` | Markdown Text | `MarkdownComponent(text="# Hello")` |
| `FormComponent` | HTML Forms | See Forms section |
| `ColumnsContainer` | Grid Layout | `ColumnsContainer(obj1, obj2)` |
| `Container` | Vertical Stack | `Container([obj1, obj2])` |

### Automatic Type Conversion

FlapiPage automatically converts common types to components:

- `str` -> `HtmlComponent`
- `list/tuple` -> `Container`
- `pd.DataFrame` -> `FrameComponent`
- `go.Figure` (Plotly) -> `PlotlyComponent`

```python
# These are equivalent:
FlapiPage(objects=[HtmlComponent(html="<p>Hello</p>")])
FlapiPage(objects=["<p>Hello</p>"])
```

### Layouts with ColumnsContainer

Place components side-by-side:

```python
from ionbus_flapi import ColumnsContainer

# Two equal columns
ColumnsContainer(chart1, chart2)

# Custom column widths
ColumnsContainer(
    chart1, chart2, chart3,
    column_desc="1fr 2fr 1fr"  # Middle column is 2x wider
)
```

### DataFrames with FrameComponent

Display pandas DataFrames as sortable, filterable grids:

```python
from ionbus_flapi import FrameComponent

frame = FrameComponent(
    frame=df,
    sortable=True,
    filterable=True,
)

# Configure columns
frame.format_dict = {
    "price": {"width": 100, "cellsformat": "D2"},
    "name": {"width": 200},
}

# Add sum row
frame.sum_columns = ["price", "quantity"]
```

### Forms

Create interactive forms:

```python
from ionbus_flapi import FormComponent, FormElement

form = FormComponent(
    elements=[
        FormElement(name="username", box=True, label="Username"),
        FormElement(name="role", values=["Admin", "User"]),
        FormElement(name="active", checkbox=True, default=True),
    ],
    submit="Save",
)
```

### API Endpoints

Register JSON API endpoints:

```python
from ionbus_flapi import register_api_endpoint

def my_api() -> dict:
    """Returns user data."""
    return {"users": [...], "count": 10}

register_api_endpoint(MODULE_NAME, "users", my_api, methods="GET")
```

### Request Context

Access request data within endpoints:

```python
from ionbus_flapi import get_request_context

def my_endpoint():
    ctx = get_request_context()
    user = ctx.username
    params = ctx.args
    theme = ctx.theme
    # ...
```

### Cookies

Set cookies for persistence:

```python
from ionbus_flapi import set_cookie

set_cookie("my_preference", "value")
```

## Themes

Flapi supports three themes: `system`, `light`, and `dark`.

The theme toggle button cycles through themes when clicked. To add it:

```python
FlapiPage(title="My Page", objects=[...], theme_toggle=True)
```

## Directory Structure

Recommended project structure:

```
my_project/
├── app.py
├── config/
│   ├── windows.yaml
│   └── linux.yaml
├── static/
│   ├── base.css
│   ├── themes/
│   │   ├── system.css
│   │   ├── light.css
│   │   └── dark.css
│   └── assets/
├── sampleData/
└── MyEndpoints/
    ├── __init__.py
    └── endpoints.py
```

## Dash Integration

Embed interactive Dash apps within Flapi pages:

```python
from ionbus_flapi import register_dash_endpoint, DashComponent, FlapiPage
from dash import dcc, html

def initialize():
    # Register a standalone Dash app
    dash_app = register_dash_endpoint(
        MODULE_NAME,
        "my_dash_app",
        ep_description="Interactive Dash application",
        show_in_dir=True,
    )

    # Configure Dash layout
    dash_app.layout = html.Div([
        dcc.Dropdown(id="dropdown", options=[...]),
        dcc.Graph(id="graph"),
    ])

    # Add callbacks
    @dash_app.callback(...)
    def update_graph(...):
        ...

def my_page() -> FlapiPage:
    # Embed Dash app in a FlapiPage
    return FlapiPage(
        title="Page with Dash",
        objects=[
            DashComponent("my_dash_app", height="600px"),
        ],
    )
```

## Server Shutdown

Configure graceful server shutdown with callbacks.

### Config

Add `shutdown_code` to your YAML config:

```yaml
app_type: fastapi
port: 5080
proxy_prefix: MyApp
shutdown_code: "my_secret_code"  # Required to enable shutdown endpoint
```

### Shutdown Endpoint

Once configured, access `/MyApp/shutdown?code=my_secret_code` to shut down the
server.

### Shutdown Callbacks

Register functions to run before shutdown (cleanup resources, save state, etc.):

```python
from ionbus_flapi import register_shutdown_callback

def cleanup_resources():
    """Called when server shuts down."""
    print("Cleaning up...")
    # Close database connections, save state, etc.

# Register during initialization
register_shutdown_callback(cleanup_resources)
```

## Real-Time Data Streaming

Use `EventStreamManager` for Server-Sent Events (SSE) to push live data updates:

```python
from ionbus_flapi import (
    EventStreamManager,
    EventStreamTypes,
    FlapiPage,
    HtmlComponent,
    get_flapi,
)
import threading

# Create manager supporting grid and div updates
esm = EventStreamManager(
    "MyStream",
    modes=EventStreamTypes.GRID | EventStreamTypes.DIV,
    include_pause=True,
)

def initialize():
    # Register with FlapiApp (after initialize(), before serve())
    esm.register(get_flapi())

    # Start data thread
    threading.Thread(target=data_thread, daemon=True).start()

def data_thread():
    while True:
        if esm.has_subscriptions():
            # Update a div
            esm.broadcast_event("ticker", {
                "MessageType": "div",
                "DivId": "myDiv",
                "Html": "Updated content",
            })
            # Update a grid
            esm.broadcast_event("ticker", {
                "MessageType": "grid",
                "GridName": "MyGrid",
                "UpdateId": "id",  # Column to match rows
                "Rows": [{"id": 1, "value": 42}],
            })
        time.sleep(0.5)

def live_page() -> FlapiPage:
    stream_addr = esm.get_stream_address("ticker")
    js = esm.javascript(stream_addr)
    html = esm.html()  # Pause button

    return FlapiPage(
        title="Live Data",
        objects=[HtmlComponent(html=f'''
            <div id="myDiv">Loading...</div>
            {html}
            <script>$(document).ready(function() {{ {js} }});</script>
        ''')],
    )
```

### EventStreamTypes

| Type | Description |
|------|-------------|
| `GRID` | Update JQX Grid rows |
| `DIV` | Update div innerHTML |
| `LINE_PLOT` | Extend Plotly line chart |
| `OHLC_PLOT` | Extend Plotly OHLC chart |

Combine types with `|`: `EventStreamTypes.GRID | EventStreamTypes.DIV`

## URL Utilities

### extract_variables_from_address

Parse query parameters from URL strings (useful in Dash callbacks):

```python
from ionbus_flapi import extract_variables_from_address

url = "/MyApp/page?foo=bar&baz=123"
params = extract_variables_from_address(url)
# {'foo': 'bar', 'baz': '123'}
```

## Setup Script

Use the setup script to create a new project:

```bash
python -m ionbus_flapi.setup_project my_new_project
```

This creates the full directory structure with a sample endpoint.
