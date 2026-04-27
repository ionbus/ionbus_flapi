# Flapi - AI Assistant Guide

This document provides guidance for AI assistants working with Flapi codebases.

## Overview

Flapi is a low-code web framework. Key files:

- `ionbus_flapi/__init__.py` - All public exports (import from here)
- `ionbus_flapi/page.py` - FlapiPage class for building pages
- `ionbus_flapi/routing.py` - Endpoint registration functions
- `ionbus_flapi/components/` - UI components (base, layout, form, dataframe, text)
- `ionbus_flapi/request.py` - Request context and cookies
- `ionbus_flapi/shutdown.py` - Server shutdown and cleanup callbacks
- `ionbus_flapi/event_stream.py` - Server-Sent Events for real-time data

## Import Pattern

Always import from the top-level `ionbus_flapi` module:

```python
from ionbus_flapi import (
    FlapiPage,
    HtmlComponent,
    FrameComponent,
    PlotlyComponent,
    ColumnsContainer,
    DashComponent,
    register_endpoint,
    register_dash_endpoint,
    register_shutdown_callback,
    extract_variables_from_address,
    get_request_context,
    EventStreamManager,
    EventStreamTypes,
)
```

Do NOT import from submodules directly:
```python
# BAD - Don't do this
from ionbus_flapi.components.base import HtmlComponent
from ionbus_flapi.page import FlapiPage
```

## Endpoint Module Pattern

Every endpoint module should follow this structure:

```python
"""Module docstring describing endpoints."""

from __future__ import annotations

from ionbus_flapi import (
    FlapiPage,
    HtmlComponent,
    register_endpoint,
)

MODULE_NAME = "MyModule"  # Must match directory name
HTML_DESCRIPTION = "<li>Description shown on main page.</li>"


def initialize() -> None:
    """Initialize endpoints. Called by app.py."""
    register_endpoint(
        MODULE_NAME,
        "EndpointName",
        endpoint_function,
        ep_description="Tab title and dropdown text.",
    )


def endpoint_function() -> FlapiPage:
    """Endpoint docstring."""
    return FlapiPage(
        title="Page Title",
        objects=[...],
    )
```

## FlapiPage Best Practices

### Object Types

FlapiPage accepts these in `objects=[]`:

1. **Strings** - Converted to HtmlComponent automatically
2. **Components** - Any BaseComponent subclass
3. **pd.DataFrame** - Converted to FrameComponent
4. **go.Figure** - Converted to PlotlyComponent
5. **list/tuple** - Converted to Container (vertical stack)

```python
# All of these work:
FlapiPage(objects=[
    "<h1>Title</h1>",                    # String -> HtmlComponent
    HtmlComponent(html="<p>Text</p>"),   # Explicit component
    df,                                   # DataFrame -> FrameComponent
    fig,                                  # Plotly Figure -> PlotlyComponent
    [item1, item2],                       # List -> Container
])
```

### Theme Toggle

Add theme toggle button:
```python
FlapiPage(title="...", objects=[...], theme_toggle=True)
```

### Auto-Refresh

For dashboards that need periodic refresh:
```python
FlapiPage(title="...", objects=[...], refresh_in_seconds=60)
```

## Component Reference

### HtmlComponent
Raw HTML content:
```python
HtmlComponent(html="<div class='my-class'>Content</div>")
```

### FrameComponent
JQX DataGrid for pandas DataFrames:
```python
frame = FrameComponent(
    frame=df,              # pandas DataFrame (required)
    sortable=True,         # Enable column sorting
    filterable=True,       # Enable column filtering
)

# Column configuration
frame.format_dict = {
    "column_name": {
        "width": 100,              # Column width in pixels
        "cellsformat": "D2",       # Number format (D2 = 2 decimals)
        "name": "Display Name",    # Column header text
    },
}

# Sum row at bottom
frame.sum_columns = ["col1", "col2"]

# Conditional formatting (JavaScript expressions)
frame.format_tuples = [
    ('column === "status"', "boldcell"),
    ('value < 0', "redcell"),
]
```

### PlotlyComponent
Plotly charts (usually auto-converted from go.Figure):
```python
# Most common: use pandas .plot() with plotly backend
fig = df.plot(backend="plotly", title="Chart", height=500)
# fig is automatically converted to PlotlyComponent

# Explicit wrapping:
PlotlyComponent(plotly_obj=fig)
```

### ColumnsContainer
CSS Grid layout for side-by-side content:
```python
# Two equal columns
ColumnsContainer(obj1, obj2)

# Three columns with custom widths
ColumnsContainer(
    obj1, obj2, obj3,
    column_desc="200px 1fr 1fr"  # First fixed, others flexible
)

# Nested: each item can be a list for vertical stacking
ColumnsContainer(
    [title1, chart1],  # Left column: title above chart
    [title2, chart2],  # Right column: title above chart
)
```

### ImageComponent
For matplotlib or other images:
```python
import base64
from io import BytesIO

# Create matplotlib figure
fig, ax = plt.subplots()
ax.plot(data)

# Convert to base64
buf = BytesIO()
fig.savefig(buf, format="png")
buf.seek(0)
encoded = base64.b64encode(buf.read()).decode("utf-8")

ImageComponent(encoded_image=encoded, image_type="png")
```

### MarkdownComponent
Render markdown text:
```python
MarkdownComponent(text="# Heading\n\n**Bold** and *italic*")
```

### FormComponent
HTML forms with various input types:
```python
FormComponent(
    elements=[
        FormElement(name="text_input", box=True, label="Enter text"),
        FormElement(name="dropdown", values=["A", "B", "C"], default="A"),
        FormElement(name="checkbox", checkbox=True, default=True),
        FormElement(name="date", calendar={"date": {"default": "2024-01-01"}}),
        FormElement(name="textarea", text_area_dim=(5, 40)),
        FormElement(name="hidden", hidden_value="secret"),
    ],
    submit="Submit",
    table=True,  # Use table layout
)
```

For JavaScript forms that POST to an API:
```python
FormComponent(
    elements=[...],
    js_save_function="/api/save",  # POST endpoint
    save_button_text="Save",
)
```

## API Endpoints

Register JSON API endpoints:
```python
from ionbus_flapi import register_api_endpoint

def get_data() -> dict:
    """Get data from the server."""
    return {"status": "ok", "data": [...]}

def post_data() -> dict:
    """Save data to the server."""
    ctx = get_request_context()
    data = ctx.json  # POST body as dict
    # Process data...
    return {"status": "saved"}

# Registration
register_api_endpoint(MODULE_NAME, "get_data", get_data, methods="GET")
register_api_endpoint(MODULE_NAME, "save_data", post_data, methods="POST")
```

## Request Context

Access request information:
```python
from ionbus_flapi import get_request_context

def my_endpoint():
    ctx = get_request_context()

    # Common attributes:
    ctx.args          # dict: combined query + path params
    ctx.query_params  # dict: URL query parameters
    ctx.path_params   # dict: URL path parameters
    ctx.method        # str: "GET", "POST", etc.
    ctx.json          # dict: POST body (if JSON)
    ctx.form_data     # dict: Form POST data
    ctx.cookies       # dict: Request cookies
    ctx.theme         # str: "system", "light", or "dark"
    ctx.username      # str | None: Authenticated username
```

## Cookies

Set persistent cookies:
```python
from ionbus_flapi import set_cookie

set_cookie("preference", "dark_mode")
```

Read cookies:
```python
ctx = get_request_context()
value = ctx.cookies.get("preference", "default")
```

## Dash Integration

Register and embed Dash apps:

```python
from ionbus_flapi import register_dash_endpoint, DashComponent, FlapiPage
from dash import dcc, html, Input, Output

def initialize():
    # Register standalone Dash app
    dash_app = register_dash_endpoint(
        MODULE_NAME,
        "interactive_chart",
        ep_description="Interactive Dash chart",
        show_in_dir=True,
    )

    # Configure layout
    dash_app.layout = html.Div([
        dcc.Dropdown(id="ticker", options=[...], multi=True),
        dcc.Graph(id="chart"),
    ])

    # Add callbacks
    @dash_app.callback(
        Output("chart", "figure"),
        Input("ticker", "value"),
    )
    def update_chart(tickers):
        # Return plotly figure
        ...

def page_with_dash() -> FlapiPage:
    """Embed Dash app in a FlapiPage."""
    return FlapiPage(
        title="Dashboard",
        objects=[
            HtmlComponent(html="<h2>Embedded Dash App</h2>"),
            DashComponent("interactive_chart", height="600px"),
        ],
    )
```

### DashComponent

Embeds a Dash app via iframe:

```python
DashComponent(
    address="my_dash_app",  # Registered dash app name
    height="800px",         # Default: "800px"
    width="100%",           # Default: "100%"
    param1="value",         # Extra kwargs become URL params
)
```

### extract_variables_from_address

Parse URL query parameters (useful in Dash callbacks):

```python
from ionbus_flapi import extract_variables_from_address

# In a Dash callback receiving URL from dcc.Location
url = "/MyApp/page?foo=bar&count=5"
params = extract_variables_from_address(url)
# {'foo': 'bar', 'count': '5'}
```

## Server Shutdown

### Configuration

Enable shutdown endpoint in YAML config:

```yaml
app_type: fastapi
port: 5080
proxy_prefix: MyApp
shutdown_code: "secret123"  # Required to enable shutdown
```

### Shutdown Endpoint

Access `/MyApp/shutdown?code=secret123` to shut down the server.

### Shutdown Callbacks

Register cleanup functions to run before shutdown:

```python
from ionbus_flapi import register_shutdown_callback
from ionbus_utils.cache_utils import InMemoryCache

def cleanup_resources():
    """Called when server shuts down."""
    InMemoryCache.clear(MODULE_NAME)
    # Close connections, save state, etc.

def initialize():
    # ... setup code ...

    # Register cleanup
    register_shutdown_callback(cleanup_resources)
```

Callbacks run in registration order before `os._exit(0)`.

## Real-Time Data Streaming (SSE)

Use `EventStreamManager` to push live updates to the browser:

```python
from ionbus_flapi import (
    EventStreamManager,
    EventStreamTypes,
    FlapiPage,
    HtmlComponent,
    get_flapi,
    register_shutdown_callback,
)
import threading
import time

# Create manager - supports GRID, DIV, LINE_PLOT, OHLC_PLOT
esm = EventStreamManager(
    "MyStream",
    modes=EventStreamTypes.GRID | EventStreamTypes.DIV,
    subscribe_func=lambda t: print(f"Subscribed: {t}"),
    unsubscribe_func=lambda t: print(f"Unsubscribed: {t}"),
    include_pause=True,
)

_shutdown = threading.Event()

def initialize():
    esm.register(get_flapi())  # Must call after initialize()
    threading.Thread(target=_data_thread, daemon=True).start()
    register_shutdown_callback(lambda: _shutdown.set())

def _data_thread():
    while not _shutdown.is_set():
        if esm.has_subscriptions():
            # Update div innerHTML
            esm.broadcast_event("channel", {
                "MessageType": "div",
                "DivId": "status",
                "Html": f"Time: {time.time():.2f}",
            })
            # Update JQX Grid rows
            esm.broadcast_event("channel", {
                "MessageType": "grid",
                "GridName": "MyGrid",
                "UpdateId": "id",  # Column to match for updates
                "Rows": [{"id": 1, "price": 100.5}],
            })
        time.sleep(0.5)

def live_endpoint() -> FlapiPage:
    stream_addr = esm.get_stream_address("channel")
    return FlapiPage(
        title="Live Data",
        objects=[HtmlComponent(html=f'''
            <div id="status">Loading...</div>
            {esm.html()}
            <script>
            $(document).ready(function() {{
                {esm.javascript(stream_addr)}
            }});
            </script>
        ''')],
    )
```

### EventStreamTypes

| Type | MessageType | Required Fields |
|------|-------------|-----------------|
| `GRID` | "grid" | GridName, UpdateId, Rows |
| `DIV` | "div" | DivId, Html |
| `LINE_PLOT` | "line_plot" | PlotName, Points (x, y, name) |
| `OHLC_PLOT` | "ohlc_plot" | PlotName, Points (x, open, high, low, close, name) |

## Common Patterns

### Data Loading with Cache
```python
from ionbus_utils.cache_utils import InMemoryCache
from ionbus_flapi import register_shutdown_callback

def cleanup():
    InMemoryCache.clear(MODULE_NAME)

def initialize():
    data = {}
    data["my_data"] = pd.read_pickle("sampleData/data.pkl.gz")
    InMemoryCache.put_many(data, MODULE_NAME)

    # Register cleanup for graceful shutdown
    register_shutdown_callback(cleanup)

def my_endpoint():
    df = InMemoryCache.get(MODULE_NAME, "my_data")
    # Use df...
```

### Conditional Content
```python
def my_endpoint():
    ctx = get_request_context()
    show_detail = ctx.args.get("detail") == "true"

    objects = [HtmlComponent(html="<h1>Summary</h1>")]
    if show_detail:
        objects.append(detailed_component)

    return FlapiPage(title="Page", objects=objects)
```

### Redirect After Form Submit
```python
from ionbus_flapi import FlapiForwardPage

def my_endpoint():
    ctx = get_request_context()
    if ctx.method == "POST":
        # Process form...
        return FlapiForwardPage("/success_page")
    return FlapiPage(...)
```

## Directory Structure

Standard project layout:
```
project/
├── app.py                    # Main entry point
├── config/
│   ├── windows_fastapi.yaml  # FastAPI backend config
│   ├── windows_flask.yaml    # Flask backend config
│   ├── linux_fastapi.yaml
│   └── linux_flask.yaml
├── static/
│   ├── base.css
│   ├── tabs.css
│   ├── themes/
│   │   ├── system.css
│   │   ├── light.css
│   │   └── dark.css
│   ├── assets/
│   │   ├── system-mode.svg
│   │   ├── light-mode.svg
│   │   └── dark-mode.svg
│   ├── jqwidgets/           # For FrameComponent
│   └── plotly/              # For PlotlyComponent
├── sampleData/              # Data files
├── ionbus_flapi/            # Framework (or installed package)
└── EndpointModule/          # One directory per endpoint group
    ├── __init__.py          # Can be empty
    └── endpoints.py         # Must have initialize(), MODULE_NAME
```

## Debugging Tips

1. **Check server logs** - Endpoint registration and requests are logged
2. **Inspect HTML** - View page source to see generated HTML
3. **Component conversion** - If objects don't render, check type conversion
4. **CSS issues** - Ensure static files are served (check `/static/base.css`)
5. **Theme not applying** - Check `flapi_theme` cookie is set

## Anti-Patterns to Avoid

1. **Don't import from submodules** - Use `from ionbus_flapi import ...`
2. **Don't return None from endpoints** - Always return FlapiPage or str
3. **Don't modify objects after adding to FlapiPage** - Create fresh objects
4. **Don't use `get_request_context()` at module level** - Only in endpoints
5. **Don't hardcode URLs** - Use `prepare_url()` for proper prefix handling

## Testing Endpoints

Endpoints can be tested by mocking the request context:
```python
from ionbus_flapi.request import HTTPRequest, set_request_context

def test_my_endpoint():
    # Create mock request
    req = HTTPRequest()
    req.args = {"param": "value"}
    req.method = "GET"
    set_request_context(req)

    # Call endpoint
    result = my_endpoint()
    assert "Expected" in str(result)
```
