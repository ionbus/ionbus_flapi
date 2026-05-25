"""flapi/components/dataframe.py

DataFrame component for displaying data as JQX grids.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import numpy as np
import pandas as pd

from ionbus_utils.enumerate import Enumerate
from ionbus_utils.general import multiline_comma_join

from ionbus_flapi.components.base import BaseComponent

if TYPE_CHECKING:
    from ionbus_flapi.page import FlapiPage

# Matches {column_name} placeholders in ClickHook templates.
HOOK_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


@dataclass
class ClickHook:
    """Per-cell click hook for FrameComponent.

    template: URL template with {column_name} placeholders. Values are
        URL-encoded (encodeURIComponent) on the client at click time.
        Placeholders are treated as query-value substitutions; for URL
        path segments, build the URL via a computed column.
    target: The HTML target= for the link. Either a named iframe (loads
        into that iframe; falls back to a new named window if no such
        iframe exists), or `_blank` for an always-new window. Required.
    on: Which click gesture triggers this hook. "single" or "double",
        not both. Different hooks in the same grid may use different
        click types; the framework disambiguates via a ~250ms timer on
        single clicks when a double-click hook is also possible on that
        cell.
    """

    template: str
    target: str
    on: Literal["single", "double"] = "single"

    def placeholders(self) -> set[str]:
        return set(HOOK_PLACEHOLDER_RE.findall(self.template))


def _validate_hooks(
    row_hook: ClickHook | None,
    column_hooks: dict[str, ClickHook],
    columns: list[str],
) -> None:
    """Validate ClickHook templates against the dataframe's columns.

    Raises ValueError listing every problem found in one pass.
    """
    column_set = set(columns)
    problems: list[str] = []

    bad_keys = sorted(set(column_hooks) - column_set)
    if bad_keys:
        problems.append(
            f"column_hooks references columns not in dataframe: {bad_keys}"
        )

    missing_placeholders: set[str] = set()
    if row_hook is not None:
        missing_placeholders |= row_hook.placeholders() - column_set
    for hook in column_hooks.values():
        missing_placeholders |= hook.placeholders() - column_set
    if missing_placeholders:
        problems.append(
            f"ClickHook templates reference unknown columns: "
            f"{sorted(missing_placeholders)}"
        )

    if problems:
        raise ValueError("; ".join(problems))

NP_FLOAT_TYPE = np.dtype("float64")
NP_INT_TYPE = np.dtype("int64")

# Regex for matching JQX column format specifiers
JQX_FORMAT_RE = re.compile(r"^(\w)(\d+)$")

# Javascript strftime dictionary
JS_ST_DICT = {
    re.compile(r"mm(.)dd(.)yyyy", re.IGNORECASE): r"%m\1%d\2%Y",
    re.compile(r"yyyy(.?)mm(.?)dd", re.IGNORECASE): r"%Y\1%m\2%d",
    re.compile(r"mm(.)dd(.)yy", re.IGNORECASE): r"%m\1%d\2%y",
    re.compile(r"yy(.?)mm(.?)dd", re.IGNORECASE): r"%y\1%m\2%d",
}

SELECTION_MODES = Enumerate(
    {
        "NONE": "none",
        "SINGLE_CELL": "singlecell",
        "SINGLE_ROW": "singlerow",
        "MULTIPLE_CELLS_EXTENDED": "multiplecellsextended",
    }
)


def cleanup_frame_values_for_js(val: Any) -> str | Any | None:
    """Converts a Python variable to a JSON-safe value."""
    if pd.isna(val):
        return None
    if isinstance(val, (dt.date, dt.datetime, pd.Timestamp, np.datetime64)):
        return str(val)
    return val


def guess_width_for_column(
    col_name: str,
    series: pd.Series,
    format_val: str | None = None,
    factor: int = 8,
    max_width: int | None = None,
) -> int:
    """Gets the approximate visual width, in pixels, for a grid column."""

    def _formatted_value_for_width(
        value: Any,
        format_val: str | None = None,
        factor: int = 10,
    ) -> int:
        """Returns the approximate screen width, in pixels, of a value."""
        if value is None:
            return 0

        additional = 0
        if isinstance(
            value, (dt.date, dt.datetime, pd.Timestamp, np.datetime64)
        ):
            value = str(value)
        elif not isinstance(value, str):
            # we think this is a number
            digits = 0
            if format_val is not None:
                match = JQX_FORMAT_RE.search(format_val)
                if match:
                    letter = match.group(1)
                    digits = int(match.group(2))
                    if letter.lower() in {"c", "p"}:
                        additional = 1
            value = "{:,.{digits}f}".format(value, digits=digits)
        return int((len(value) + additional) * factor)

    max_col_width = max(
        series.map(
            lambda x: _formatted_value_for_width(x, format_val, factor)
        ).max(),
        len(col_name) * factor,
    )
    if pd.isna(max_col_width):
        max_col_width = 100
    if max_width:
        max_col_width = min(max_width, max_col_width)
    return int(max_col_width)


def get_javascript_aggregation(label_str: str | None = None) -> str:
    """Returns the JavaScript code to aggregate a column."""
    if label_str:
        return f""", aggregates: ['sum'],
                    aggregatesrenderer: function (aggregates) {{
                        return `<div class="totalcell"
                            style="position: relative; margin: 4px;
                            overflow: hidden;">{label_str}</div>`;
                    }}"""
    return """, aggregates: ['sum'],
                aggregatesrenderer: function (aggregates) {
                    return renderAggregates(aggregates);
                }"""


_CLICK_HOOK_JS_TEMPLATE = r"""
            // Click hook setup for grid: __FLAPI_GRID_ID__
            window.FLAPI_GRID_HOOKS = window.FLAPI_GRID_HOOKS || {};
            window.FLAPI_GRID_HOOKS[__FLAPI_GRID_NAME__] = __FLAPI_HOOKS_JSON__;
            (function() {
                var HOOKS = window.FLAPI_GRID_HOOKS[__FLAPI_GRID_NAME__];
                var pendingClick = null;
                var DOUBLE_CLICK_DELAY_MS = 250;
                var $grid = $("#grid__FLAPI_GRID_ID__");

                function resolveHook(event, clickType) {
                    var col = event.args.column.datafield;
                    var colHook = HOOKS.columns ? HOOKS.columns[col] : undefined;
                    if (colHook && colHook.on === clickType) return colHook;
                    if (HOOKS.row && HOOKS.row.on === clickType) return HOOKS.row;
                    return null;
                }

                function fillAndOpen(hook, rowData) {
                    var url = hook.template.replace(/\{(\w+)\}/g, function(_, n) {
                        var v = rowData[n] != null ? rowData[n] : "";
                        return encodeURIComponent(v);
                    });
                    window.open(url, hook.target);
                }

                function getRowData(event) {
                    return $grid.jqxGrid("getrowdata", event.args.row);
                }

                function anyHookOn(clickType) {
                    if (HOOKS.row && HOOKS.row.on === clickType) return true;
                    if (HOOKS.columns) {
                        for (var k in HOOKS.columns) {
                            if (HOOKS.columns[k].on === clickType) return true;
                        }
                    }
                    return false;
                }

                if (anyHookOn("single")) {
                    $grid.on("cellclick", function(event) {
                        // Timer resets on every click; the wait is measured
                        // from the LAST click. Intentional — dblclick fires
                        // right after the second click, so this gives it
                        // room to land.
                        if (pendingClick) clearTimeout(pendingClick);
                        var hook = resolveHook(event, "single");
                        if (!hook) return;
                        var rowData = getRowData(event);
                        if (resolveHook(event, "double")) {
                            pendingClick = setTimeout(function() {
                                fillAndOpen(hook, rowData);
                                pendingClick = null;
                            }, DOUBLE_CLICK_DELAY_MS);
                        } else {
                            fillAndOpen(hook, rowData);
                        }
                    });
                }
                if (anyHookOn("double")) {
                    $grid.on("celldoubleclick", function(event) {
                        if (pendingClick) {
                            clearTimeout(pendingClick);
                            pendingClick = null;
                        }
                        var hook = resolveHook(event, "double");
                        if (hook) fillAndOpen(hook, getRowData(event));
                    });
                }
            })();
"""


class FrameComponent(BaseComponent):
    """JQX Grid component for displaying pandas DataFrames."""

    class_name: ClassVar[str] = "FrameComponent"
    default_treegrid_parent: ClassVar[str] = "tg_parent"
    default_treegrid_key: ClassVar[str] = "tg_key"

    frame: pd.DataFrame
    column_header_height: int | float | None = None
    default_sort_column: str | None = None
    editable: bool = False
    expand_column: str | None = None
    expand_tier: int | None = None
    filterable: bool | None = False
    grid_height: int | None = None
    grid_width: int | None = None
    page_size: int | None = None
    page_size_options: list[int] | None = None
    selection_mode: str = "singlerow"
    show_headers: bool = True
    sortable: bool | None = None
    reorderable: bool = True
    sort_direction: str = "asc"
    # tree grid settings
    treegrid_key: str | None = None
    treegrid_parent: str | None = None
    treegrid_expand: int = 0
    treegrid_filter_mode: str = "simple"
    is_treegrid: bool = False
    treegrid_level_col: str = "_level"
    # Format settings
    format_dict: dict[str, dict[str, Any]]
    format_number_tuples: list[tuple[str, str]]
    format_tuples: list[tuple[str, str]]
    sum_columns: list[str]
    # Click hook settings
    row_hook: ClickHook | None = None
    column_hooks: dict[str, ClickHook]

    def __init__(
        self,
        frame: pd.DataFrame,
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.format_dict = kwargs.pop("format_dict", {})
        self.format_number_tuples = kwargs.pop("format_number_tuples", [])
        self.format_tuples = kwargs.pop("format_tuples", [])
        self.sum_columns = kwargs.pop("sum_columns", [])
        self.row_hook = kwargs.pop("row_hook", None)
        self.column_hooks = kwargs.pop("column_hooks", {}) or {}

        # Set attributes from kwargs
        for key in [
            "column_header_height", "default_sort_column", "editable",
            "expand_column", "expand_tier", "filterable", "grid_height",
            "grid_width", "page_size", "page_size_options", "selection_mode",
            "show_headers", "sortable", "reorderable", "sort_direction",
            "treegrid_key", "treegrid_parent", "treegrid_expand",
            "treegrid_filter_mode", "is_treegrid", "treegrid_level_col",
        ]:
            if key in kwargs:
                setattr(self, key, kwargs.pop(key))

        super().__init__(page, name, **kwargs)

        # Handle treegrid settings
        if self.treegrid_key or self.treegrid_parent or self.is_treegrid:
            if not self.treegrid_key or not self.treegrid_parent:
                self.treegrid_key = self.default_treegrid_key
                self.treegrid_parent = self.default_treegrid_parent
            self.is_treegrid = True
        if self.editable and self.is_treegrid:
            raise RuntimeError(
                "Editable tree grids are not supported in FrameComponent"
            )

        # Clean up frame values for JavaScript
        # Use applymap for pandas < 2.1, map for pandas >= 2.1
        if hasattr(frame, "map"):
            self.frame = frame.map(cleanup_frame_values_for_js)
        else:
            self.frame = frame.applymap(cleanup_frame_values_for_js)

        # Validate click hooks against actual dataframe columns.
        if self.row_hook is not None or self.column_hooks:
            if self.is_treegrid:
                raise RuntimeError(
                    "Click hooks (row_hook / column_hooks) are not "
                    "currently supported on tree grids."
                )
            _validate_hooks(
                self.row_hook,
                self.column_hooks,
                list(self.frame.columns),
            )

    def get_html(self) -> str:
        return f'<div id="grid{self.name}"></div>'

    def set_requirements(self) -> None:
        if self.page is None:
            return
        # Set jqx_headers if page supports it
        if hasattr(self.page, "jqx_headers"):
            self.page.jqx_headers = True

    def get_document_ready_js(self) -> str:  # noqa: C901, PLR0912, PLR0915
        """Generate JavaScript for the JQX grid."""
        data = self.frame.to_dict(orient="records")
        data_fields = []

        # All tables with aggregated columns should be sortable
        if self.sortable is None:
            self.sortable = len(self.sum_columns) > 0

        columns = []
        dropdown_fields = ""
        total_width = 0

        show_aggregates = len(self.sum_columns) > 0
        first_column = True
        override_filter = False
        if self.filterable is None and np.any(
            [
                True
                for i in self.format_dict.values()
                if i.get("filterable") is not None
            ]
        ):
            self.filterable = True
            override_filter = True

        # Loop over each column
        for col in self.frame.columns:
            if col == self.treegrid_level_col:
                continue
            series = self.frame[col]
            format_val = None
            extra = ""
            if series.dtype in {NP_FLOAT_TYPE, NP_INT_TYPE}:
                type_str = "number"
                format_val = "F0"
                extra = ", cellsalign:'right'"
                number = "Number"
            else:
                type_str = "string"
                number = ""
            row_format = self.format_dict.get(col, {})
            pretty = row_format.get("name", col)
            format_val = row_format.get("format", format_val)
            format_val = row_format.get("cellsformat", format_val)

            # Force number if column format specified
            if (
                type_str == "string"
                and format_val
                and JQX_FORMAT_RE.search(format_val)
            ):
                type_str = "number"
                extra = ", cellsalign:'right'"
                number = "Number"

            width = row_format.get(
                "width", guess_width_for_column(col, series, format_val)
            )
            if format_val:
                extra += f', cellsformat:"{format_val}"'
            if row_format.get("hidden", False):
                extra += ", hidden: true"
            if row_format.get("pinned", False):
                extra += ", pinned: true"
            if align := row_format.get("align"):
                extra += f", align:'{align}'"
            if cellsalign := row_format.get("cellsalign"):
                extra += f", cellsalign:'{cellsalign}'"
            if columntype := row_format.get("columntype"):
                extra += f", columntype:'{columntype}'"
            if (coledit := row_format.get("editable")) is not None:
                extra += f", editable: {str(coledit).lower()}"
            if col in self.sum_columns:
                extra += get_javascript_aggregation(
                    row_format.get("overrideTotal")
                )
            elif show_aggregates and first_column:
                extra += get_javascript_aggregation("Total")
            if not row_format.get("filterable", not override_filter):
                extra += ", filterable: false"

            # Handle dropdown fields
            if columntype in {"dropdownlist", "combobox"}:
                columnfields = row_format.get("columnfields", [])
                all_values = ""
                for value in columnfields:
                    all_values += f'{{ value: "{value}" }},'
                colname = col.replace(" ", "")
                dropdown_fields += f"""
                var dropdown{colname}{self.name} =
                    new $.jqx.dataAdapter([{all_values}],
                    {{autoBind: true}});"""
                if columntype == "combobox":
                    extra += f""",
                    createeditor: function (row, value, editor) {{
                        editor.jqxComboBox({{
                            source: dropdown{colname}{self.name},
                            showArrow: false,
                            displayMember: 'value',
                            valueMember: 'value',
                            autoDropDownHeight: true
                        }});
                    }}"""
                else:
                    extra += f""",
                    createeditor: function (row, value, editor) {{
                        editor.jqxDropDownList({{
                            source: dropdown{colname}{self.name},
                            displayMember: 'value',
                            valueMember: 'value',
                            autoDropDownHeight: true
                        }});
                    }}"""

            if columntype == "datetimeinput":
                extra += f""",
                    createeditor: function (row, value, editor) {{
                        editor.jqxDateTimeInput({{
                            formatString: '{format_val}'
                        }});
                    }}"""

            data_fields.append(f"{{ name : '{col}', type: '{type_str}'}}")
            total_width += width
            if col not in (self.treegrid_key, self.treegrid_parent):
                columns.append(
                    f"{{text: '{pretty}', datafield: '{col}', "
                    f"width: {width}"
                    f",cellclassname: render{number}{self.name}{extra} }}"
                )
            first_column = False

        # Build the JavaScript
        data_string = json.dumps(data, indent=4)
        data_field_string = multiline_comma_join(data_fields, 24)
        columns_string = multiline_comma_join(columns, 24)
        sortable = "true" if self.sortable else "false"

        if show_aggregates:
            aggregates = """true,
                showstatusbar: true,
                statusbarheight: 28"""
        else:
            aggregates = "false"

        # Grid dimensions
        if self.grid_width:
            width_js = f'"{self.grid_width}"'
            autowidth = "false"
        else:
            width_js = "null"
            autowidth = "true"
        if self.grid_height:
            height_js = f'"{self.grid_height}"'
            autoheight = "false"
        else:
            height_js = "null"
            autoheight = "true"

        selection_mode = (
            SELECTION_MODES.SINGLE_CELL
            if self.editable
            else self.selection_mode
        )

        # Build extra settings
        extra_settings_list = [
            f"width: {width_js}",
            f"height: {height_js}",
            f"sortable: {sortable}",
            f"columnsReorder: {str(self.reorderable).lower()}",
        ]
        if self.page_size:
            page_size_str = "pageSize" if self.is_treegrid else "pagesize"
            extra_settings_list.extend(
                ["pageable: true", f"{page_size_str}: {self.page_size}"]
            )
            if self.is_treegrid:
                extra_settings_list.append("pagerMode: `advanced`")
            if self.page_size_options:
                pso_str = str([str(x) for x in self.page_size_options])
                pso_name = (
                    "pageSizeOptions" if self.is_treegrid else "pagesizeoptions"
                )
                extra_settings_list.append(f"{pso_name}: {pso_str}")

        if not self.is_treegrid:
            extra_settings_list.extend([
                "columnsresize: true",
                f"autoheight: {autoheight}",
                f"autowidth: {autowidth}",
                f"selectionmode: '{selection_mode}'",
                f"showheader: {str(self.show_headers).lower()}",
                f"showaggregates: {aggregates}",
            ])

        if self.column_header_height:
            extra_settings_list.append(
                f'columnsheight: "{self.column_header_height}"'
            )
        if self.filterable:
            extra_settings_list.extend([
                "filterable: true",
                f"filterMode: '{self.treegrid_filter_mode}'"
                if self.is_treegrid
                else "showFilterRow: true",
            ])

        extra_settings_list.append(f"""columns: [
                    {columns_string}
                ]""")

        editable_render = ""
        if self.editable:
            extra_settings_list.extend([
                "editable: true",
                "editmode: 'click'",
            ])
            editable_render = f"""if ($('#grid{self.name}').jqxGrid(
                'getcolumnproperty', column, 'editable')) {{
                    return 'editablecell'
                }}"""

        space_comma = ",\n" + " " * 20
        extra_settings = space_comma.join(extra_settings_list) + ",\n"

        grid_spec = "jqxTreeGrid" if self.is_treegrid else "jqxGrid"
        dropdown_fields = dropdown_fields + "\n" if dropdown_fields else ""

        # Build render functions
        render_string = ""
        for cond, effect in self.format_tuples:
            render_string += f"""if ({cond}) {{
                    return '{effect}';
                }}
                """

        number = f"""
        function renderNumber{self.name}(row, column, value, data) {{
            """
        for cond, effect in self.format_number_tuples:
            number += f"""if ({cond} && value < 0) {{
                    return 'red{effect}';
                }}
                """
            number += f"""if ({cond}) {{
                    return '{effect}';
                }}
                """
        for cond, effect in self.format_tuples + [("value < 0", "redcell")]:
            number += f"""if ({cond}) {{
                return '{effect}';
            }}
            """
        number += "\n        }\n        "

        # Sort column
        sortcolumn = ""
        if self.default_sort_column:
            sortcolumn = f""",sortcolumn: '{self.default_sort_column}',
            sortdirection: '{self.sort_direction}'"""

        # Hierarchy for tree grid
        hierarchy = (
            f"""hierarchy: {{
                    keyDataField: {{ name: '{self.treegrid_key}' }},
                    parentDataField: {{ name: '{self.treegrid_parent}' }}
                }},
                id: '{self.treegrid_key}',"""
            if self.is_treegrid
            else ""
        )
        dark = 'theme: "metrodark",' if self.is_treegrid else ""

        grid_js = f"""
            // Data for grid: {self.name}
            // Use window scope for SSE streaming compatibility
            window.data{self.name} = {data_string};
            {dropdown_fields}
            var dataAdapter{self.name} = new $.jqx.dataAdapter({{
                localdata: window.data{self.name},
                datafields: [
                    {data_field_string}
                ],
                {hierarchy}
                datatype: 'json'{sortcolumn}
            }});

            // Render functions

            function render{self.name}(row, column, value, data) {{
                {render_string}{editable_render}
            }}
            {number}

            // Constructing grid

            $("#grid{self.name}").{grid_spec}(
            {{
                {dark}
                {extra_settings}
                source: dataAdapter{self.name},
            }});
        """
        return grid_js + self._click_hook_js()

    def _click_hook_js(self) -> str:
        """Generate JS for click hook handlers (empty if no hooks).

        Emits the per-grid config into window.FLAPI_GRID_HOOKS, then an
        IIFE that registers cellclick / celldoubleclick handlers. The
        IIFE's closure scopes pendingClick per-grid.
        """
        if self.row_hook is None and not self.column_hooks:
            return ""

        hooks_dict: dict[str, Any] = {}
        if self.row_hook is not None:
            hooks_dict["row"] = asdict(self.row_hook)
        if self.column_hooks:
            hooks_dict["columns"] = {
                col: asdict(hook)
                for col, hook in self.column_hooks.items()
            }

        # Build the JS as a literal (no f-string) and substitute the two
        # unique tokens at the end — avoids brace-escaping hell.
        template = _CLICK_HOOK_JS_TEMPLATE
        return (
            template
            .replace("__FLAPI_GRID_NAME__", json.dumps(self.name))
            .replace("__FLAPI_GRID_ID__", self.name)
            .replace("__FLAPI_HOOKS_JSON__", json.dumps(hooks_dict))
        )
