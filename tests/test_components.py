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
