"""flapi/components/form.py

Form components for building HTML forms.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Sequence

import pandas as pd

from ionbus_utils.enumerate import Enumerate
from ionbus_utils.exceptions import log_exception
from ionbus_utils.logging_utils import logger

from ionbus_flapi.components.base import BaseComponent
from ionbus_flapi.request import get_request_context
from ionbus_flapi.response import RedirectResponse

if TYPE_CHECKING:
    from ionbus_flapi.page import FlapiPage

NON_LETTER_RE = re.compile(r"\W")

CHECK_BOX_ENUM = Enumerate("label name value checked", name_as_value=True)
ELEMENT_ENUM = Enumerate(
    "hiddenValue fixedValue box textAreaDim table className quiet "
    "fullWidth checkbox calendar placeholder label minWidthPx "
    "section spacing rowExtra extraButton extraElement",
    name_as_value=True,
)


class FormElement:
    """HTML form element.

    At least one of `box`, `calendar`, `checkbox`, `section`,
    `fixed_value`, `hidden_value`, `text_area_dim`, or `values`
    should be specified.
    """

    name: str
    box: bool = False
    calendar: dict[str, dict[str, Any]] | bool = False
    checkbox: bool = False
    default: str | list[str] | None = None
    extra_button: dict[str, str] | None = None
    extra_element: str | None = None
    fixed_value: str | None = None
    full_width: str | bool = False
    hidden_value: str | None = None
    is_editable: bool = True
    label: str | None = None
    min_width_px: int = 177
    newline: bool | None = None
    placeholder: str | None = None
    quiet: bool = False
    row_extra: str | None = None
    section: bool = False
    text_area_dim: Sequence[int] | None = None
    values: Sequence[Any] | None = None

    def __init__(self, name: str = "", **kwargs: Any):
        self.name = name
        # Set attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Validate that at least one element type is specified
        not_none = sum(
            0 if x is None or x is False else 1
            for x in [
                self.box,
                self.calendar,
                self.checkbox,
                self.section,
                self.fixed_value,
                self.hidden_value,
                self.text_area_dim,
                self.values,
            ]
        )
        if not not_none:
            raise RuntimeError(
                "At least one of `box`, `calendar`, `checkbox`, `section`, "
                "`fixed_value`, `hidden_value`, `text_area_dim`, or `values` "
                "should be specified."
            )

    def stringify(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self,
        spacing: str = "",
        table: bool = False,
        class_name: str | None = None,
    ) -> str:
        """Returns needed HTML text."""
        width = f'style="min-width:{self.min_width_px}px;"'
        extra = f"{width} {self.extra_element}" if self.extra_element else width

        if table:
            br, tr1, tr2, th1, th2, td1, td2, td1l, tdcbx = (
                "",
                "<tr>",
                "</tr>",
                '<th align="left">',
                "</th>",
                '<td align="left">',
                "</td>",
                '<td align="left">',
                '<td align="left" style="font-size:13px">',
            )
            if self.row_extra:
                tr1 = f"<tr {self.row_extra}>"
            elif class_name:
                tr1, th1, th2, td1, td1l, tdcbx = (
                    f'<tr class="{class_name}">',
                    f'<th class="{class_name}">&nbsp;',
                    "&nbsp;</th>",
                    f'<td class="{class_name}">',
                    f'<td class="{class_name}" align="left">',
                    f'<td class="{class_name}" align="left" '
                    f'style="font-size:13px">',
                )
        else:
            br, tr1, tr2, th1, th2, td1, td2, td1l, tdcbx = ("<br>",) + (
                "",
            ) * 8
            if self.row_extra:
                tr1, tr2 = f"<div {self.row_extra}>", "</div>"

        if self.label is None:
            self.label = self.name

        if self.extra_button:
            td2 = "&nbsp;" + self._end_form(**(self.extra_button or {})) + td2

        if not self.extra_element:
            self.extra_element = ""

        # Section
        if self.section:
            return f"""{tr1}{th1}{self.label}{th2}
            {td1}&nbsp;{td2}{tr2}\n"""

        # Calendar date element
        if self.calendar:
            if not isinstance(self.calendar, dict):
                raise RuntimeError("calendar must be a dictionary")
            info = self.calendar.get(self.name)
            if not info:
                raise RuntimeError(
                    f"calendar must have dictionary with key {self.name}"
                )
            default = info.get("default", self.default)
            if default:
                default = pd.Timestamp(default).strftime("%m/%d/%Y")
                value = f'value = "{default}"'
            else:
                value = ""
            return f"""{tr1}{th1}<label for="{self.name}">
            {spacing}{self.label}:</label>
            {th2}{td1}
            <input type="text" id="{self.name}" name="{self.name}"
            {value} {extra}>{td2}{tr2}\n"""

        # Fixed or hidden value
        hidden_value = self.fixed_value or self.hidden_value
        if hidden_value is not None:
            if self.fixed_value is not None:
                retval = f"""{tr1}{th1}{spacing}{self.label}{th2}
                {td1l}&nbsp;{self.fixed_value}&nbsp;{td2}{tr2}\n"""
            else:
                retval = ""
            retval += (
                f' <input type="hidden" name="{self.name}" '
                f'value="{self.hidden_value}">'
            )
            return retval

        # Text box
        if self.box:
            extra_values = ""
            value = f'value = "{self.default}"' if self.default else ""
            ts_type = "text"
            if self.values:
                if not self.placeholder:
                    self.placeholder = f"pick {self.name} value"
                list_name = f"{self.name}_listname"
                value += f'list="{list_name}" placeholder="{self.placeholder}"'
                extra_values = f'   <datalist id="{list_name}">'
                for item in self.values or []:
                    extra_values += f'  <option value="{item}">'
                extra_values += "</datalist>"
                ts_type = "search"
            if not self.label:
                self.label = "&nbsp;"
                colon = ""
            else:
                colon = ":"
            return f"""{tr1}{th1}
            <label for="{self.name}">{spacing}{self.label}{colon}
            </label>{th2}
            {td1}
            <input type="{ts_type}" id="{self.name}"
                name="{self.name}"{value} {extra}>
            {td2}{tr2}\n{extra_values}"""

        # Checkboxes
        if self.checkbox:
            if self.values:
                # Many checkboxes
                if self.default is None:
                    self.default = []
                ret_string = f"""{tr1}{th1}{spacing}{self.label}:{th2}
            {tdcbx}"""
                first = True
                for info_dict in self.values or []:
                    if CHECK_BOX_ENUM.name not in info_dict:
                        raise RuntimeError(f"Must include name {self.name=}")
                    name = info_dict[CHECK_BOX_ENUM.name]
                    value = info_dict.get(CHECK_BOX_ENUM.value, "on")
                    this_label = info_dict.get(CHECK_BOX_ENUM.label, name)
                    long_name = f"{self.name}_{name}"
                    is_checked = (
                        info_dict.get(CHECK_BOX_ENUM.checked)
                        or long_name in self.default
                    )
                    checked = 'checked ="checked"' if is_checked else ""
                    if first:
                        first = False
                    else:
                        ret_string += ", "
                    ret_string += f"""<label for="{long_name}"
                    style="white-space: nowrap;" >
                <input type="checkbox" name="{long_name}" value="{value}"
                    {checked}>
                {this_label}</label>\n"""
                ret_string += f"{td2}{tr2}\n"
                return ret_string

            # Single checkbox
            checked = 'checked ="checked"' if self.default else ""
            return f"""{tr1}{th1}
            <label for="{self.name}">{spacing}{self.label}:</label>
            {th2}{td1}
            <input type="checkbox" id="{self.name}"
                name="{self.name}"
                {checked}>
            {td2}{tr2}\n"""

        # Large text area
        if self.text_area_dim is not None:
            value = self.default or ""
            if not self.label:
                self.label = "&nbsp;"
                colon = ""
            else:
                colon = ":"
            return f"""{br}{tr1}{th1}
            <label for="{self.name}">{spacing}{self.label}{colon}</label>
        {th2}
        {td1}<textarea id="{self.name}" name="{self.name}"
            rows="{self.text_area_dim[0]}" cols="{self.text_area_dim[1]}"
                {self.extra_element}>{value}</textarea>
        {td2}{tr2}\n"""

        # Drop down selection
        values = self.values or [self.default]
        if isinstance(values, list):
            values = {x: x for x in values}
        options = ""
        for key, text in values.items():
            selected = ""
            if key == self.default:
                selected = ' selected="selected"'
            options += f'<option value="{key}"{selected}>{text}</option>\n'
        print_var = "" if self.quiet else f"{spacing}{self.label}:"
        full_width = 'style="width:100%;"' if self.full_width else width
        extra = f"{full_width} {self.extra_element}"
        return f"""{tr1}{th1}<label for="{self.name}">{print_var}</label>
    {th2}\n
    {td1l}<select name="{self.name}" id="{self.name}" {extra}">
        {options}</select>{td2}{tr2}\n"""

    def _end_form(self, submit: str | None = None, **kwargs: Any) -> str:
        """HTML to end form element."""
        return f'<input type="submit" value="{submit}">'


class FormComponent(BaseComponent):
    """HTML form component."""

    class_name: str = "FormComponent"
    elements: list[FormElement]
    action: str | None = None
    form_class_name: str | None = None
    on_submit_code: str | None = None
    show_spinner: bool = False
    submit: str | list[str] = "Submit"
    table: bool = False
    use_post: bool = False
    jqx_grid_names: list[str]
    js_save_function: Callable | str | None = None
    js_load_function: Callable | str | None = None
    js_history_function: Callable | str | None = None
    history_title: str | None = None
    js_results: bool = False
    js_loading_text: str | None = None
    ctrl_enter_name: str | None = None
    save_button_text: str = "Save"
    not_empty_fields: str | list | None = None

    def __init__(
        self,
        elements: list[FormElement],
        page: FlapiPage | None = None,
        name: str | int = "",
        **kwargs: Any,
    ):
        self.jqx_grid_names = []
        self.elements = elements

        # Set attributes from kwargs
        for key in [
            "action", "form_class_name", "on_submit_code", "show_spinner",
            "submit", "table", "use_post", "js_save_function",
            "js_load_function", "js_history_function", "history_title",
            "js_results", "js_loading_text", "ctrl_enter_name",
            "save_button_text", "not_empty_fields",
        ]:
            if key in kwargs:
                setattr(self, key, kwargs.pop(key))

        if self.js_load_function and not self.js_save_function:
            raise RuntimeError(
                "js_load_function is set but js_save_function is not"
            )

        super().__init__(page, name, **kwargs)

        if isinstance(self.not_empty_fields, str):
            self.not_empty_fields = [self.not_empty_fields]
        elif not self.not_empty_fields:
            self.not_empty_fields = []

    def get_html(self) -> str:
        all_options = ""
        spacing = ""

        for element in self.elements:
            if element.section:
                spacing = "&nbsp;" * 4
                break
        for element in self.elements:
            all_options += element.stringify(
                spacing, self.table, self.form_class_name
            )

        if self.table:
            table1, table2, before, after = (
                "<table>",
                "</table>",
                '<tr><td colspan=2 align="center">',
                "</td></tr>",
            )
            if self.form_class_name:
                table1 = f'<table class="{self.form_class_name}">'
        else:
            table1, table2, before, after = "", "", "", ""

        after_table = ""
        if self.table and self.is_javascript_form:
            end = self._javascript_submit_html()
            after_table = self._javascript_feedback_html()
        elif isinstance(self.submit, list):
            end = ""
            for text in self.submit:
                end += "&nbsp;" + self.end_form(text, name="submit")
        else:
            end = self.end_form(self.submit)

        if self.table:
            return f"""\n{self.begin_form()}\n{table1}
{all_options}\n
        {before}{end}{after}
        {table2}
        {after_table}
        </form>"""

        return f"""\n{table1}{self.begin_form()}\n{all_options}\n
        {before}{end}{after}
        </form>\n{table2}"""

    def get_document_ready_js(self) -> str:
        """Returns javascript to run when the document is ready."""
        if not self.is_javascript_form:
            return ""

        form_vars = f"{' ' * 17}formData: {{\n" if self.elements else ""
        for obj in self.elements:
            if obj.hidden_value:
                form_vars += f'{" " * 24}{obj.name}: "{obj.hidden_value}",\n'
                continue
            value = 'is(":checked")' if obj.checkbox else "val()"
            form_vars += f'{" " * 24}{obj.name}: $("#{obj.name}").{value},\n'
        if form_vars:
            form_vars += f"{' ' * 17}}},\n"

        grids_vars = ""
        for name in self.jqx_grid_names:
            if grids_vars:
                grids_vars += f"\n{'' * 17}"
            grids_vars += f'{name}: $("#{name}").jqxGrid("getrows"),\n'

        return self._js_save_no_reload(form_vars, grids_vars)

    def _js_save_no_reload(
        self, form_vars: str, grids_vars: str
    ) -> str:
        """Returns javascript for a save without a reload."""
        results_or_message = ""
        if self.js_results:
            results_or_message = """
                        // Display response
                        $('#responseContent').text(
                            JSON.stringify(response, null, 2));
                        $('#response').show();\n"""
        elif self.js_history_function:
            results_or_message = """
                        // Hide loading indicator
                        $('#loadingIndicator').hide();
                        // Add the pre-formatted HTML response to history
                        $('#qaHistory').prepend(response.formatted_response);
                        // Clear the question input
                        $('#question').val('');\n"""
        elif not self.history_title:
            results_or_message = """
                        // Show success message
                        showMessage("Form submitted successfully!", "success");
                        \n"""

        before = ""
        if self.js_history_function:
            before = f"""
            // Load chat history when page loads
            loadChatHistory();

            function loadChatHistory() {{
                $.ajax({{
                    url: '{self.js_history_function}',
                    type: 'GET',
                    success: function(data) {{
                        $('#qaHistory').html(data.formatted_history);
                    }},
                    error: function(xhr, status, error) {{
                        const errorHtml = '<div class="error-message">' +
                            'Error loading chat history: ' + error + '</div>';
                        $('#qaHistory').html(errorHtml);
                    }}
                }});
            }}
            """

        if self.ctrl_enter_name:
            before += f"""
            // Handle Ctrl+Enter for {self.ctrl_enter_name}
            $('#{self.ctrl_enter_name}').on('keydown', function(e) {{
                if (e.ctrlKey && e.keyCode === 13) {{
                    e.preventDefault();
                    submitForm();
                }}
            }});\n"""

        load_indicator_on_plus = ""
        for field in self.not_empty_fields or []:
            load_indicator_on_plus += f"""
                const {field}Text = $('#{field}').val();
                if (! {field}Text.trim()) {{
                    return;
                }}\n"""
        if self.js_loading_text:
            load_indicator_on_plus += """// Show loading indicator
                    $('#loadingIndicator').show();\n"""

        return f"""
            function getCurrentValues() {{
                return {{
{form_vars}
                    {grids_vars}
                }};
            }}

            // Show message function
            function showMessage(message, type, timeout) {{
                timeout = timeout || 3000;
                $("#zz_message_zz").text(message);
                $("#zz_message_zz").removeClass("success error warning")
                    .addClass(type);
                $("#zz_message_zz").show();
                setTimeout(function() {{
                    $("#zz_message_zz").fadeOut();
                }}, timeout);
            }}

            {before}

            // Form submission using jQuery
            $("#{self.name}").submit(function(e) {{
                e.preventDefault();
                submitForm();
            }});

            // function to submit the form to endpoint
            function submitForm() {{

                {load_indicator_on_plus}
                var formData = getCurrentValues();

                // Send data to server using jQuery AJAX
                $.ajax({{
                    url: '{self.js_save_function}',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(formData),
                    success: function(response) {{
                        {'$("#loadingIndicator").hide();'
                            if self.js_loading_text else ''}
                        // redirect if requested
                        if (response.redirect_url) {{
                            window.location.href = response.redirect_url;
                        }}
                       {results_or_message}
                    }},
                    error: function(xhr, status, error) {{
                        {'$("#loadingIndicator").hide();'
                            if self.js_loading_text else ''}
                        var errorMessage = "Error: " + error;
                        try {{
                            var responseJson = JSON.parse(xhr.responseText);
                            if (responseJson && responseJson.message) {{
                                errorMessage = responseJson.message;
                                if (responseJson.error_code) {{
                                    errorMessage += " (Code: " +
                                        responseJson.error_code + ")";
                                }}
                            }}
                        }} catch (e) {{
                            console.log("Could not parse error response:", e);
                        }}
                        showMessage(errorMessage, "error", 10000);
                    }}
                }});
            }}\n"""

    @property
    def is_javascript_form(self) -> bool:
        """Returns true if this is a javascript form."""
        return self.js_save_function is not None

    def begin_form(self) -> str:
        """HTML to begin form."""
        if not self.is_javascript_form:
            if self.action:
                action = self.action
            else:
                try:
                    action = get_request_context().base_path.strip("/")
                except Exception:
                    action = ""
        else:
            action = ""
        method = 'method="POST"' if self.use_post and action else ""
        submit_code = ""
        if self.show_spinner or self.on_submit_code:
            submit_code = 'onsubmit="'
            if self.on_submit_code:
                submit_code += (
                    f"var x = {self.on_submit_code}; "
                    f"if (x == null || !x) {{ hideSpinner(); }} return x;\""
                )
            else:
                submit_code += 'return true;" '

        html = ""
        if self.show_spinner:
            html += self.add_busy_spinner()
        extra = ""
        if action:
            extra += f' action="/{action}"'
        if method:
            extra += f" {method}"
        if submit_code:
            extra += f" {submit_code}"
        html += f'<form id="{self.name}"{extra}>'
        return html

    def end_form(
        self, submit: str | None = None, name: str | None = None
    ) -> str:
        """HTML to end form."""
        if self.is_javascript_form:
            return (
                self._javascript_submit_html()
                + self._javascript_feedback_html()
            )

        name_attr = f'name="{name}"' if name else ""
        return f'<input type="submit" {name_attr} value="{submit}">'

    def _javascript_submit_html(self) -> str:
        """Return the submit controls for a JavaScript-backed form."""
        reload = (
            '<button id="reloadButton">Reload</button>'
            if self.js_load_function
            else ""
        )
        return f"""
            <div style="margin-top: 20px;">
                <button type="submit" id="submitButton">
                    {self.save_button_text}</button>
            </div>
                {reload}\n"""

    def _javascript_feedback_html(self) -> str:
        """Return JavaScript form feedback/results markup."""
        ret_str = (
            """
            <div id="response" class="response">
                <h3>Server Response:</h3>
                <div id="responseContent" class="monoleft"></div>
            </div>\n"""
            if self.js_results
            else '<div id="zz_message_zz"></div>'
        )
        if self.js_loading_text:
            ret_str += f"""
                <div class="loading-container">
                    <div class="loading" id="loadingIndicator">
                        {self.js_loading_text}</div>
                </div>\n"""
        if self.history_title:
            ret_str += f"""
            <div id="historyContainer" class="history-container">
                <h2>{self.history_title}</h2>
                <div id="qaHistory"></div>
            </div>\n"""
        return ret_str

    def add_busy_spinner(self) -> str:
        """Returns the HTML code for a busy spinner."""
        return """<style>
            .spinloader {
                position: absolute; left: 50%; top: 50%; z-index: 1000;
                border: 8px solid #ffffff; border-radius: 50%;
                border-right: 8px dotted black;
                border-bottom: 8px dotted black;
                border-left: 8px dotted black;
                background-color: #ffffff;
                width: 30px; height: 30px;
                animation: spin 2s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
        <script type="text/javascript">
        function showSpinner() {
            document.getElementById("spinloader").style.display = "block";
        }
        function hideSpinner() {
            document.getElementById("spinloader").style.display = "none";
        }
        </script>
        <div id="spinloader" class="spinloader" style="display:none"></div>"""


def is_form_update(
    update_func: Callable[[dict[str, Any]], str | None],
) -> RedirectResponse | None:
    """Checks whether this is a form update (POST) or display (GET).

    If the request was not a POST, returns None. A common snippet
    at the top of an endpoint containing a JS Form might be:

    ```
    if handling := is_form_update(update_func):
        return handling
    ```

    NOTE: should only be used during an active request.
    """
    if get_request_context().method == "GET":
        return None
    updates = get_request_context().json
    if updates is None:
        updates = {}
    if update_func:
        ret = None
        try:
            ret = update_func(updates)
        except Exception as excp:
            logger.error(f"Calling {update_func} failed")
            log_exception(excp)
        if ret:
            return RedirectResponse(ret)
    return None
