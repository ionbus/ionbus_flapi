"""Tests for flapi/components."""

from __future__ import annotations

import pytest


class TestBaseComponent:
    """Tests for BaseComponent class."""

    def test_base_component_creation(self):
        """Test creating a BaseComponent."""
        from ionbus_flapi.components.base import BaseComponent

        component = BaseComponent(name="test")
        assert component.name == "test"

    def test_base_component_auto_name(self):
        """Test auto-naming when name is None."""
        from ionbus_flapi.components.base import BaseComponent

        component = BaseComponent()
        assert component.name.startswith("BaseComponent_")
        assert "_global" in component.name

    def test_base_component_int_name(self):
        """Test integer name conversion."""
        from ionbus_flapi.components.base import BaseComponent

        component = BaseComponent(name=5)
        assert component.name == "BaseComponent_5"

    def test_base_component_get_html(self):
        """Test get_html returns empty string by default."""
        from ionbus_flapi.components.base import BaseComponent

        component = BaseComponent(name="test")
        assert component.get_html() == ""

    def test_base_component_get_document_ready_js(self):
        """Test get_document_ready_js returns empty string by default."""
        from ionbus_flapi.components.base import BaseComponent

        component = BaseComponent(name="test")
        assert component.get_document_ready_js() == ""

    def test_base_component_str(self):
        """Test __str__ calls get_html."""
        from ionbus_flapi.components.base import BaseComponent

        component = BaseComponent(name="test")
        assert str(component) == component.get_html()


class TestHtmlComponent:
    """Tests for HtmlComponent class."""

    def test_html_component_creation(self):
        """Test creating an HtmlComponent."""
        from ionbus_flapi.components.base import HtmlComponent

        html = "<p>Hello World</p>"
        component = HtmlComponent(html=html, name="test")
        assert component.html == html
        assert component.get_html() == html

    def test_html_component_empty(self):
        """Test HtmlComponent with empty HTML."""
        from ionbus_flapi.components.base import HtmlComponent

        component = HtmlComponent(name="test")
        assert component.html == ""
        assert component.get_html() == ""


class TestImageComponent:
    """Tests for ImageComponent class."""

    def test_image_component_with_encoded_image(self):
        """Test ImageComponent with encoded image."""
        from ionbus_flapi.components.base import ImageComponent

        encoded = "iVBORw0KGgo="
        component = ImageComponent(
            encoded_image=encoded,
            image_type="png",
            name="test",
        )
        assert component.encoded_image == encoded
        html = component.get_html()
        assert 'src="data:image/png;base64,iVBORw0KGgo="' in html

    def test_image_component_requires_image(self):
        """Test that ImageComponent requires an image source."""
        from ionbus_flapi.components.base import ImageComponent

        with pytest.raises(RuntimeError, match="Must include either"):
            ImageComponent(name="test")

    def test_image_component_not_both(self):
        """Test that ImageComponent can't have both sources."""
        from ionbus_flapi.components.base import ImageComponent

        with pytest.raises(RuntimeError, match="but not both"):
            ImageComponent(
                encoded_image="data",
                image_filename="test.png",
                name="test",
            )


class TestDashComponent:
    """Tests for DashComponent class."""

    def test_dash_component_creation(self):
        """Test creating a DashComponent."""
        from ionbus_flapi.components.base import DashComponent

        component = DashComponent(address="/dash/app", name="test")
        assert "dash/app/" in component.address
        html = component.get_html()
        assert '<iframe' in html
        assert 'src="' in html

    def test_dash_component_with_kwargs(self):
        """Test DashComponent with URL parameters."""
        from ionbus_flapi.components.base import DashComponent

        component = DashComponent(
            address="/dash/app",
            name="test",
            param1="value1",
            param2="value2",
        )
        assert "param1=value1" in component.address
        assert "param2=value2" in component.address


class TestContainer:
    """Tests for Container class."""

    def test_container_creation(self):
        """Test creating a Container."""
        from ionbus_flapi.components.base import HtmlComponent
        from ionbus_flapi.components.layout import Container

        c1 = HtmlComponent(html="<p>1</p>", name="c1")
        c2 = HtmlComponent(html="<p>2</p>", name="c2")
        container = Container([c1, c2], name="test")

        html = container.get_html()
        assert "<p>1</p>" in html
        assert "<p>2</p>" in html

    def test_container_with_strings(self):
        """Test Container with string content."""
        from ionbus_flapi.components.layout import Container

        container = Container(["<p>Hello</p>", "<p>World</p>"], name="test")
        html = container.get_html()
        assert "<p>Hello</p>" in html
        assert "<p>World</p>" in html


class TestColumnsContainer:
    """Tests for ColumnsContainer class."""

    def test_columns_container_creation(self):
        """Test creating a ColumnsContainer."""
        from ionbus_flapi.components.base import HtmlComponent
        from ionbus_flapi.components.layout import ColumnsContainer

        c1 = HtmlComponent(html="<p>Left</p>", name="c1")
        c2 = HtmlComponent(html="<p>Right</p>", name="c2")
        container = ColumnsContainer(c1, c2, name="test")

        html = container.get_html()
        assert "grid-container" in html
        assert "<p>Left</p>" in html
        assert "<p>Right</p>" in html

    def test_columns_container_custom_desc(self):
        """Test ColumnsContainer with custom column description."""
        from ionbus_flapi.components.layout import ColumnsContainer

        container = ColumnsContainer(
            "<p>A</p>", "<p>B</p>",
            column_desc="1fr 2fr",
            name="test",
        )
        html = container.get_html()
        assert "1fr 2fr" in html


class TestComponentFactory:
    """Tests for component_factory function."""

    def test_factory_with_string(self):
        """Test component_factory with string input."""
        from ionbus_flapi.components.base import HtmlComponent
        from ionbus_flapi.components.layout import component_factory

        result = component_factory(None, "<p>test</p>")
        assert isinstance(result, HtmlComponent)
        assert result.get_html() == "<p>test</p>"

    def test_factory_with_list(self):
        """Test component_factory with list input."""
        from ionbus_flapi.components.layout import Container, component_factory

        result = component_factory(None, ["<p>1</p>", "<p>2</p>"])
        assert isinstance(result, Container)

    def test_factory_with_component(self):
        """Test component_factory with existing component."""
        from ionbus_flapi.components.base import HtmlComponent
        from ionbus_flapi.components.layout import component_factory

        original = HtmlComponent(html="<p>test</p>", name="original")
        result = component_factory(None, original)
        assert result is original


class TestFormElement:
    """Tests for FormElement class."""

    def test_form_element_creation_box(self):
        """Test creating a FormElement with box."""
        from ionbus_flapi.components.form import FormElement

        elem = FormElement(name="username", box=True, label="Username")
        html = elem.stringify()
        assert 'name="username"' in html
        assert 'type="text"' in html

    def test_form_element_creation_checkbox(self):
        """Test creating a FormElement with checkbox."""
        from ionbus_flapi.components.form import FormElement

        elem = FormElement(name="agree", checkbox=True, label="I agree")
        html = elem.stringify()
        assert 'type="checkbox"' in html
        assert 'name="agree"' in html

    def test_form_element_creation_select(self):
        """Test creating a FormElement with values (select)."""
        from ionbus_flapi.components.form import FormElement

        elem = FormElement(
            name="color",
            values=["red", "green", "blue"],
            label="Color",
        )
        html = elem.stringify()
        assert "<select" in html
        assert 'value="red"' in html
        assert 'value="green"' in html
        assert 'value="blue"' in html

    def test_form_element_creation_textarea(self):
        """Test creating a FormElement with textarea."""
        from ionbus_flapi.components.form import FormElement

        elem = FormElement(
            name="comment",
            text_area_dim=(5, 40),
            label="Comment",
        )
        html = elem.stringify()
        assert "<textarea" in html
        assert 'rows="5"' in html
        assert 'cols="40"' in html

    def test_form_element_requires_type(self):
        """Test that FormElement requires at least one type."""
        from ionbus_flapi.components.form import FormElement

        with pytest.raises(RuntimeError, match="At least one of"):
            FormElement(name="empty")


class TestFormComponent:
    """Tests for FormComponent class."""

    def test_form_component_creation(self):
        """Test creating a FormComponent."""
        from ionbus_flapi.components.form import FormComponent, FormElement

        elements = [
            FormElement(name="username", box=True, label="Username"),
            FormElement(name="password", box=True, label="Password"),
        ]
        form = FormComponent(elements=elements, name="login_form")
        html = form.get_html()
        assert '<form id="login_form"' in html
        assert 'name="username"' in html
        assert 'name="password"' in html

    def test_form_component_table_layout(self):
        """Test FormComponent with table layout."""
        from ionbus_flapi.components.form import FormComponent, FormElement

        elements = [
            FormElement(name="field1", box=True),
        ]
        form = FormComponent(elements=elements, name="test", table=True)
        html = form.get_html()
        assert "<table>" in html

    def test_js_results_table_response_outside_table(self):
        """Test JS table forms render response outside the table."""
        from ionbus_flapi.components.form import FormComponent, FormElement

        elements = [
            FormElement(name="field1", box=True),
        ]
        form = FormComponent(
            elements=elements,
            js_results=True,
            js_save_function="/submit",
            name="test",
            table=True,
        )

        html = form.get_html()
        assert html.index('<form id="test"') < html.index("<table>")
        assert html.index('id="submitButton"') < html.index("</table>")
        assert html.index("</table>") < html.index('id="response"')
        assert html.index('id="response"') < html.index("</form>")

    def test_form_component_submit_button(self):
        """Test FormComponent submit button."""
        from ionbus_flapi.components.form import FormComponent, FormElement

        elements = [
            FormElement(name="field1", box=True),
        ]
        form = FormComponent(
            elements=elements,
            name="test",
            submit="Send",
        )
        html = form.get_html()
        assert 'value="Send"' in html


class TestBannerFunctions:
    """Tests for banner helper functions."""

    def test_pop_banner_js(self):
        """Test pop_banner_js function."""
        from ionbus_flapi.components.layout import pop_banner_js

        js = pop_banner_js(duration=5)
        assert "popup_banner" in js
        assert "5000" in js  # 5 seconds * 1000

    def test_banner_html(self):
        """Test banner_html function."""
        from ionbus_flapi.components.layout import banner_html

        html = banner_html()
        assert 'id="popupBanner"' in html
        assert "display: none" in html


class TestClickHook:
    """Tests for ClickHook dataclass."""

    def test_basic_construction(self):
        from ionbus_flapi.components.dataframe import ClickHook
        h = ClickHook("/x?s={symbol}", target="frame")
        assert h.template == "/x?s={symbol}"
        assert h.target == "frame"
        assert h.on == "single"

    def test_on_double(self):
        from ionbus_flapi.components.dataframe import ClickHook
        h = ClickHook("/x", target="f", on="double")
        assert h.on == "double"

    def test_on_invalid_raises(self):
        from ionbus_flapi.components.dataframe import ClickHook
        with pytest.raises(ValueError, match="must be 'single' or 'double'"):
            ClickHook("/x", target="f", on="bad")

    def test_placeholders_extracted(self):
        from ionbus_flapi.components.dataframe import ClickHook
        h = ClickHook(
            "/x?s={symbol}&p={price}&s2={symbol}", target="f",
        )
        assert h.placeholders() == {"symbol", "price"}

    def test_placeholders_empty_for_static_template(self):
        from ionbus_flapi.components.dataframe import ClickHook
        h = ClickHook("/static/path", target="f")
        assert h.placeholders() == set()


class TestNormalizeColumnHooks:
    """Tests for _normalize_column_hooks helper."""

    def test_none_returns_empty(self):
        from ionbus_flapi.components.dataframe import _normalize_column_hooks
        assert _normalize_column_hooks(None) == {}

    def test_empty_dict_returns_empty(self):
        from ionbus_flapi.components.dataframe import _normalize_column_hooks
        assert _normalize_column_hooks({}) == {}

    def test_single_hook_wrapped_in_list(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _normalize_column_hooks,
        )
        h = ClickHook("/x", target="f")
        result = _normalize_column_hooks({"col": h})
        assert result == {"col": [h]}

    def test_list_input_kept_as_list(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _normalize_column_hooks,
        )
        h1 = ClickHook("/a", target="A")
        h2 = ClickHook("/b", target="B", on="double")
        result = _normalize_column_hooks({"col": [h1, h2]})
        assert result == {"col": [h1, h2]}

    def test_tuple_input_coerced_to_list(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _normalize_column_hooks,
        )
        h = ClickHook("/x", target="f")
        result = _normalize_column_hooks({"col": (h,)})
        assert isinstance(result["col"], list)
        assert result["col"] == [h]

    def test_bad_value_type_raises(self):
        from ionbus_flapi.components.dataframe import _normalize_column_hooks
        with pytest.raises(
            TypeError, match="must be a ClickHook or list",
        ):
            _normalize_column_hooks({"col": "not a hook"})

    def test_bad_list_item_raises_with_position(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _normalize_column_hooks,
        )
        h = ClickHook("/x", target="f")
        with pytest.raises(
            TypeError, match=r"\[1\] must be a ClickHook",
        ):
            _normalize_column_hooks({"col": [h, "bad"]})


class TestValidateHooks:
    """Tests for _validate_hooks helper."""

    def test_no_problems(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _validate_hooks,
        )
        row = ClickHook("/x?s={a}", target="f")
        col_hooks = {"b": [ClickHook("/y?s={a}", target="g")]}
        # Should not raise
        _validate_hooks(row, col_hooks, ["a", "b"])

    def test_unknown_column_key(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _validate_hooks,
        )
        col_hooks = {"nope": [ClickHook("/x", target="f")]}
        with pytest.raises(ValueError, match="not in dataframe"):
            _validate_hooks(None, col_hooks, ["a"])

    def test_missing_placeholder_in_row_hook(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _validate_hooks,
        )
        row = ClickHook("/x?s={zzz}", target="f")
        with pytest.raises(ValueError, match="reference unknown columns"):
            _validate_hooks(row, {}, ["a"])

    def test_missing_placeholder_in_column_hook(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _validate_hooks,
        )
        col_hooks = {"a": [ClickHook("/x?s={zzz}", target="f")]}
        with pytest.raises(ValueError, match="reference unknown columns"):
            _validate_hooks(None, col_hooks, ["a"])

    def test_duplicate_click_type_on_same_column(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, _validate_hooks,
        )
        col_hooks = {
            "a": [
                ClickHook("/1", target="f"),
                ClickHook("/2", target="g"),  # both default on="single"
            ],
        }
        with pytest.raises(ValueError, match="multiple hooks with on"):
            _validate_hooks(None, col_hooks, ["a"])

    def test_multiple_problems_reported_together(self):
        """One pass should surface all problem categories at once."""
        from ionbus_flapi.components.dataframe import (
            ClickHook, _validate_hooks,
        )
        row = ClickHook("/x?s={zzz}", target="f")
        col_hooks = {"nope": [ClickHook("/y", target="g")]}
        with pytest.raises(ValueError) as exc_info:
            _validate_hooks(row, col_hooks, ["a"])
        msg = str(exc_info.value)
        assert "not in dataframe" in msg
        assert "reference unknown columns" in msg


class TestFrameComponentHooks:
    """Tests for FrameComponent's row_hook / column_hooks support."""

    @staticmethod
    def _df():
        import pandas as pd
        return pd.DataFrame(
            {"symbol": ["AAPL", "GOOG"], "price": [185.0, 142.5]},
        )

    def test_no_hooks_no_hook_js(self):
        """FrameComponent with no hooks must not emit hook setup JS."""
        from ionbus_flapi.components.dataframe import FrameComponent
        fc = FrameComponent(self._df(), name="g")
        assert fc.row_hook is None
        assert fc.column_hooks == {}
        js = fc.get_document_ready_js()
        assert "FLAPI_GRID_HOOKS" not in js

    def test_row_hook_emits_hook_js(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, FrameComponent,
        )
        fc = FrameComponent(
            self._df(),
            name="g",
            row_hook=ClickHook("/x?s={symbol}", target="f"),
        )
        js = fc.get_document_ready_js()
        assert "FLAPI_GRID_HOOKS" in js
        assert "cellclick" in js

    def test_column_hooks_normalized_to_list(self):
        """Even a single ClickHook input becomes a list internally."""
        from ionbus_flapi.components.dataframe import (
            ClickHook, FrameComponent,
        )
        h = ClickHook("/x?s={symbol}", target="f")
        fc = FrameComponent(
            self._df(), name="g", column_hooks={"price": h},
        )
        assert fc.column_hooks == {"price": [h]}

    def test_treegrid_with_hooks_raises(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, FrameComponent,
        )
        import pandas as pd
        df = pd.DataFrame({
            "tg_key": [1, 2], "tg_parent": [None, 1],
            "symbol": ["AAPL", "GOOG"], "price": [185.0, 142.5],
        })
        with pytest.raises(RuntimeError, match="tree grid"):
            FrameComponent(
                df,
                name="g",
                is_treegrid=True,
                row_hook=ClickHook("/x?s={symbol}", target="f"),
            )

    def test_invalid_template_raises_at_construction(self):
        from ionbus_flapi.components.dataframe import (
            ClickHook, FrameComponent,
        )
        with pytest.raises(ValueError, match="reference unknown columns"):
            FrameComponent(
                self._df(),
                name="g",
                row_hook=ClickHook("/x?s={nonexistent}", target="f"),
            )

    def test_emitted_hook_config_shape(self):
        """Parse the JS hook config back to JSON and verify the structure."""
        import json
        import re
        from ionbus_flapi.components.dataframe import (
            ClickHook, FrameComponent,
        )
        fc = FrameComponent(
            self._df(),
            name="testgrid",
            row_hook=ClickHook("/r?s={symbol}", target="A"),
            column_hooks={
                "price": [
                    ClickHook("/c1?s={symbol}", target="B", on="single"),
                    ClickHook("/c2?s={symbol}", target="C", on="double"),
                ],
            },
        )
        js = fc.get_document_ready_js()
        m = re.search(
            r'FLAPI_GRID_HOOKS\["testgrid"\]\s*=\s*(\{.+?\});', js,
        )
        assert m is not None, "expected FLAPI_GRID_HOOKS assignment"
        config = json.loads(m.group(1))
        assert config["row"] == {
            "template": "/r?s={symbol}",
            "target": "A",
            "on": "single",
        }
        assert config["columns"]["price"] == [
            {"template": "/c1?s={symbol}", "target": "B", "on": "single"},
            {"template": "/c2?s={symbol}", "target": "C", "on": "double"},
        ]


class TestIframeComponent:
    """Tests for IframeComponent class."""

    def test_basic_html(self):
        from ionbus_flapi.components.layout import IframeComponent
        c = IframeComponent(frame_name="myframe", name="i1")
        html = c.get_html()
        assert 'name="myframe"' in html
        assert 'src="about:blank"' in html
        assert 'id="iframei1"' in html

    def test_empty_frame_name_raises(self):
        from ionbus_flapi.components.layout import IframeComponent
        with pytest.raises(ValueError, match="non-empty frame_name"):
            IframeComponent(frame_name="")

    def test_src_width_height(self):
        from ionbus_flapi.components.layout import IframeComponent
        c = IframeComponent(
            frame_name="f",
            src="/some/url",
            width="100%",
            height="200px",
            name="i1",
        )
        html = c.get_html()
        assert 'src="/some/url"' in html
        assert "width: 100%" in html
        assert "height: 200px" in html

    def test_frame_name_quote_does_not_break_attribute(self):
        """A quote in frame_name must NOT break out of the HTML attribute."""
        from ionbus_flapi.components.layout import IframeComponent
        c = IframeComponent(
            frame_name='evil"><script>x</script>', name="i1",
        )
        html = c.get_html()
        # Raw <script> must NOT appear — would mean attribute injection
        assert "<script>x</script>" not in html
        # The escaped form must appear
        assert "&quot;" in html

    def test_src_with_injection_payload_escaped(self):
        from ionbus_flapi.components.layout import IframeComponent
        c = IframeComponent(
            frame_name="f", src='"><script>x</script>', name="i1",
        )
        html = c.get_html()
        assert "<script>x</script>" not in html
        assert "&quot;" in html or "&lt;script&gt;" in html

    def test_width_with_payload_escaped(self):
        from ionbus_flapi.components.layout import IframeComponent
        c = IframeComponent(
            frame_name="f",
            width='"><script>x</script>',
            name="i1",
        )
        html = c.get_html()
        assert "<script>x</script>" not in html

    def test_style_is_trusted_raw_css(self):
        """`style` is intentionally NOT escaped — documented trusted input.

        This test locks the contract: if a future change starts escaping
        `style`, normal CSS like `color: red; border: 1px solid blue` will
        still pass through unchanged.
        """
        from ionbus_flapi.components.layout import IframeComponent
        c = IframeComponent(
            frame_name="f",
            style="color: red; border: 1px solid blue",
            name="i1",
        )
        html = c.get_html()
        assert "color: red" in html
        assert "border: 1px solid blue" in html
