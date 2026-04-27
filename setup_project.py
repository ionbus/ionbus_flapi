"""flapi/setup_project.py

Script to create a new Flapi project with sample endpoints.

Usage:
    python -m flapi.setup_project my_project_name
    python -m flapi.setup_project my_project_name --prefix MyApp
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def create_directory(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    print(f"  Created: {path}/")


def create_file(path: Path, content: str) -> None:
    """Create file with content."""
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


def setup_project(
    project_name: str,
    proxy_prefix: str | None = None,
    port: int = 5080,
) -> None:
    """Create a new Flapi project structure.

    Args:
        project_name: Name of the project directory to create.
        proxy_prefix: URL prefix for the app (defaults to project_name).
        port: Port number for the server.
    """
    if proxy_prefix is None:
        proxy_prefix = project_name.replace("_", " ").title().replace(" ", "_")

    base = Path(project_name)

    if base.exists():
        print(f"Error: Directory '{project_name}' already exists.")
        return

    print(f"Creating Flapi project: {project_name}")
    print(f"  Proxy prefix: {proxy_prefix}")
    print(f"  Port: {port}")
    print()

    # Create directories
    create_directory(base)
    create_directory(base / "config")
    create_directory(base / "static")
    create_directory(base / "static" / "themes")
    create_directory(base / "static" / "assets")
    create_directory(base / "sampleData")
    create_directory(base / "Sample")

    # Create config files
    config_content = f"""app_type: fastapi
host: 0.0.0.0
port: {port}
proxy_prefix: {proxy_prefix}
title: {proxy_prefix} Pages Being Served
"""
    create_file(base / "config" / "windows.yaml", config_content)
    create_file(base / "config" / "linux.yaml", config_content)

    # Create base.css
    base_css = """@import url("tabs.css");

/* Override monospace for code blocks */
pre, code {
    font-family: monospace !important;
}

html, body {
    font-family: Arial;
    border-collapse: collapse;
}

pre,
pre code,
code,
codehilite,
.codehilite code {
    font-family: monospace !important;
    font-style: normal;
    font-weight: normal;
}

.mono {
    font-family: monospace;
}

.base {
    border: 1px solid silver;
}

.red {
    color: red;
}

.icon {
    height: 30px;
    width: 30px;
    cursor: pointer;
}

#themeDiv {
    display: flex;
    gap: 5px;
}

#themeDiv > div {
    align-self: center;
}
"""
    create_file(base / "static" / "base.css", base_css)

    # Create tabs.css (minimal)
    tabs_css = """/* Tab styles */
.tab-container {
    display: flex;
    border-bottom: 1px solid #ccc;
}

.tab {
    padding: 10px 20px;
    cursor: pointer;
    border: 1px solid transparent;
}

.tab:hover {
    background-color: #f0f0f0;
}

.tab.active {
    border: 1px solid #ccc;
    border-bottom: 1px solid white;
    margin-bottom: -1px;
}
"""
    create_file(base / "static" / "tabs.css", tabs_css)

    # Create theme CSS files
    system_css = """@import url("./light.css") (prefers-color-scheme: light);
@import url("./dark.css") (prefers-color-scheme: dark);
"""
    create_file(base / "static" / "themes" / "system.css", system_css)

    light_css = """body {
    /* background-color: white; */
    /* color: black; */
}
"""
    create_file(base / "static" / "themes" / "light.css", light_css)

    dark_css = """body {
    background-color: #111;
    color: #ddd;
    --dark-white: #ccc4c4;
}

a {
    color: #809fff;
}

a:visited {
    color: #8c61f1;
}

select {
    background-color: #444;
    border: 1px solid #666;
    border-radius: 2px;
    color: #ddd;
}

button {
    background-color: #444;
    border: 1px solid #666;
    border-radius: 2px;
    color: #ddd;
    cursor: pointer;
}

/* Invert theme icon for visibility */
#themeButton {
    filter: invert(1);
}
"""
    create_file(base / "static" / "themes" / "dark.css", dark_css)

    # Create theme SVG assets
    system_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="4" fill="currentColor"/>
  <path d="M12 2v2m0 16v2M4 12H2m20 0h-2m-2.93-7.07l-1.41 1.41m-9.9 9.9l-1.41 1.41m0-12.73l1.41 1.41m9.9 9.9l1.41 1.41" stroke="currentColor" stroke-width="2" fill="none"/>
</svg>"""
    create_file(base / "static" / "assets" / "system-mode.svg", system_svg)

    light_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="5" fill="currentColor"/>
  <path d="M12 1v3m0 16v3M4.22 4.22l2.12 2.12m11.32 11.32l2.12 2.12M1 12h3m16 0h3M4.22 19.78l2.12-2.12m11.32-11.32l2.12-2.12" stroke="currentColor" stroke-width="2" fill="none"/>
</svg>"""
    create_file(base / "static" / "assets" / "light-mode.svg", light_svg)

    dark_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" fill="currentColor"/>
</svg>"""
    create_file(base / "static" / "assets" / "dark-mode.svg", dark_svg)

    # Create sample endpoint module
    sample_init = '"""Sample endpoint module."""\n'
    create_file(base / "Sample" / "__init__.py", sample_init)

    sample_endpoints = f'''"""Sample endpoint pages.

Sample/HelloWorld
    A simple hello world endpoint.

Sample/DataTable
    An example showing a data table.
"""

from __future__ import annotations

import pandas as pd

from ionbus_flapi import (
    ColumnsContainer,
    FlapiPage,
    FrameComponent,
    HtmlComponent,
    MarkdownComponent,
    register_endpoint,
)

MODULE_NAME = "Sample"
HTML_DESCRIPTION = """<li>Sample endpoints demonstrating Flapi features.</li>
"""


def initialize() -> None:
    """Initialize Sample endpoints."""
    register_endpoint(
        MODULE_NAME,
        "HelloWorld",
        hello_world_endpoint,
        ep_description="A simple hello world example.",
    )

    register_endpoint(
        MODULE_NAME,
        "DataTable",
        data_table_endpoint,
        ep_description="Example data table.",
    )

    register_endpoint(
        MODULE_NAME,
        "LayoutExample",
        layout_example_endpoint,
        ep_description="Layout with columns.",
    )


def hello_world_endpoint() -> FlapiPage:
    """Display a hello world page."""
    markdown_text = """# Welcome to Flapi

This is a sample endpoint demonstrating the **Flapi** framework.

## Features

- Easy page building with `FlapiPage`
- Automatic type conversion for common objects
- Theme support (system, light, dark)
- Data grids, charts, forms, and more

Click the theme icon in the top-right to change themes!
"""

    return FlapiPage(
        title="Hello World",
        objects=[
            MarkdownComponent(text=markdown_text),
            "<hr>",
            "<p>This string is automatically converted to HtmlComponent.</p>",
        ],
        theme_toggle=True,
    )


def data_table_endpoint() -> FlapiPage:
    """Display a sample data table."""
    # Create sample data
    data = {{
        "Name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "Department": ["Engineering", "Sales", "Engineering", "HR", "Sales"],
        "Salary": [85000, 72000, 92000, 68000, 78000],
        "Years": [5, 3, 8, 2, 4],
    }}
    df = pd.DataFrame(data)

    # Create frame component with configuration
    frame = FrameComponent(frame=df, sortable=True, filterable=True)
    frame.format_dict = {{
        "Name": {{"width": 120}},
        "Department": {{"width": 120}},
        "Salary": {{"width": 100, "cellsformat": "c0"}},
        "Years": {{"width": 80}},
    }}
    frame.sum_columns = ["Salary", "Years"]

    return FlapiPage(
        title="Data Table Example",
        objects=[
            "<h2>Employee Data</h2>",
            "<p>This table is sortable and filterable. Click column headers.</p>",
            frame,
        ],
        theme_toggle=True,
    )


def layout_example_endpoint() -> FlapiPage:
    """Display a layout with columns."""
    # Sample data for charts
    data1 = pd.DataFrame({{
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Sales": [100, 120, 115, 130, 145],
    }}).set_index("Month")

    data2 = pd.DataFrame({{
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Expenses": [80, 85, 90, 88, 95],
    }}).set_index("Month")

    # Create plotly charts
    chart1 = data1.plot(
        backend="plotly",
        title="Monthly Sales",
        height=350,
    )
    chart2 = data2.plot(
        backend="plotly",
        title="Monthly Expenses",
        height=350,
    )

    return FlapiPage(
        title="Layout Example",
        objects=[
            "<h2>Side-by-Side Charts</h2>",
            "<p>Using ColumnsContainer to place charts next to each other.</p>",
            ColumnsContainer(chart1, chart2),
            "<h2>Stacked Layout</h2>",
            "<p>Charts can also be stacked vertically (default behavior).</p>",
            chart1,
            chart2,
        ],
        theme_toggle=True,
    )
'''
    create_file(base / "Sample" / "endpoints.py", sample_endpoints)

    # Create app.py
    app_py = f'''"""app.py

Main entry point for running the {proxy_prefix} server.
"""

from __future__ import annotations

import sys

from ionbus_flapi import initialize, register_endpoint_group, serve


if __name__ == "__main__":
    if len(sys.argv) < 2:  # noqa: PLR2004
        raise RuntimeError("Must provide .yaml config file")
    config_name = sys.argv[1]
    initialize(config_name)

    #################################
    # Import endpoint modules here ##
    #################################
    import Sample.endpoints

    ##########################################
    # Call initialization of endpoints here ##
    ##########################################
    register_endpoint_group(
        Sample.endpoints.initialize,
        Sample.endpoints.MODULE_NAME,
        Sample.endpoints.HTML_DESCRIPTION,
    )

    # Start up server
    serve()
'''
    create_file(base / "app.py", app_py)

    # Create .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual environments
venv/
env/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
*.pkl
*.pkl.gz
"""
    create_file(base / ".gitignore", gitignore)

    print()
    print("Project created successfully!")
    print()
    print("Next steps:")
    print(f"  1. cd {project_name}")
    print("  2. Install flapi (pip install flapi or copy flapi/ directory)")
    print("  3. Run: python app.py config/windows.yaml")
    print(f"  4. Open: http://localhost:{port}/{proxy_prefix}/")


def main() -> None:
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="Create a new Flapi project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m flapi.setup_project my_project
  python -m flapi.setup_project my_project --prefix MyApp --port 8080
""",
    )
    parser.add_argument(
        "project_name",
        help="Name of the project directory to create",
    )
    parser.add_argument(
        "--prefix",
        dest="proxy_prefix",
        default=None,
        help="URL prefix for the app (defaults to project name)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5080,
        help="Port number for the server (default: 5080)",
    )

    args = parser.parse_args()

    setup_project(
        project_name=args.project_name,
        proxy_prefix=args.proxy_prefix,
        port=args.port,
    )


if __name__ == "__main__":
    main()
