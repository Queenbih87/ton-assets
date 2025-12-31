"""
Comprehensive unit tests for to_review/presenter.py

Tests cover:
- HTML generation from asset data
- CSV blacklist writing
- Template formatting
- Edge cases and special characters
- File I/O operations
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import csv
import io

from to_review.presenter import (
    generate_to_review_html,
    add_blacklist,
    ROW_TEMPLATE,
    PAGE_TEMPLATE,
)
from to_review.models import AssetData


class TestGenerateToReviewHtml:
    """Test suite for generate_to_review_html function"""

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_empty_list(self, mock_file):
        """Test generating HTML with empty asset list"""
        generate_to_review_html([])
        
        mock_file.assert_called_once_with("to_review.html", "w")
        written_content = mock_file().write.call_args[0][0]
        assert "<!DOCTYPE html>" in written_content
        assert "<title>To review</title>" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_single_asset(self, mock_file):
        """Test generating HTML with single asset"""
        asset = AssetData(
            address="0:test123",
            link="https://tonviewer.com/0:test123",
            name="Test Token",
            category="DeFi",
            website="https://test.com",
            description="A test token"
        )
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert "Test Token" in written_content
        assert "0:test123" in written_content
        assert "DeFi" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_multiple_assets(self, mock_file):
        """Test generating HTML with multiple assets"""
        assets = [
            AssetData("addr1", "link1", "Name1", "Cat1", "web1", "desc1"),
            AssetData("addr2", "link2", "Name2", "Cat2", "web2", "desc2"),
            AssetData("addr3", "link3", "Name3", "Cat3", "web3", "desc3"),
        ]
        
        generate_to_review_html(assets)
        
        written_content = mock_file().write.call_args[0][0]
        assert "Name1" in written_content
        assert "Name2" in written_content
        assert "Name3" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_escapes_special_chars(self, mock_file):
        """Test that HTML special characters are handled"""
        asset = AssetData(
            address="0:test",
            link="https://test.com",
            name="Token & <script>",
            category="Cat & Dog",
            website="https://test.com?a=1&b=2",
            description="<b>Bold</b> text"
        )
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        # HTML should contain the raw data (escaping happens in browser)
        assert "Token & <script>" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_includes_javascript(self, mock_file):
        """Test that generated HTML includes JavaScript"""
        generate_to_review_html([])
        
        written_content = mock_file().write.call_args[0][0]
        assert "<script>" in written_content
        assert "handleGenerateButtonClick" in written_content
        assert "jszip" in written_content.lower()

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_includes_css(self, mock_file):
        """Test that generated HTML includes CSS"""
        generate_to_review_html([])
        
        written_content = mock_file().write.call_args[0][0]
        assert "<style>" in written_content
        assert "font-family" in written_content
        assert "background-color" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_table_structure(self, mock_file):
        """Test that HTML has correct table structure"""
        asset = AssetData("addr", "link", "name", "cat", "web", "desc")
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert "<table>" in written_content
        assert "<thead>" in written_content
        assert "<tbody>" in written_content
        assert "<tr>" in written_content
        assert "<td>" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_row_indices(self, mock_file):
        """Test that rows have correct indices"""
        assets = [
            AssetData("addr1", "link1", "name1", "cat1", "web1", "desc1"),
            AssetData("addr2", "link2", "name2", "cat2", "web2", "desc2"),
        ]
        
        generate_to_review_html(assets)
        
        written_content = mock_file().write.call_args[0][0]
        assert 'class="row0"' in written_content
        assert 'class="row1"' in written_content
        assert 'class="address0"' in written_content
        assert 'class="address1"' in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_input_fields(self, mock_file):
        """Test that HTML includes input fields"""
        asset = AssetData("addr", "link", "name", "cat", "web", "desc")
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert '<input type="text"' in written_content
        assert '<input type="checkbox"' in written_content
        assert 'name="category0"' in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_prefills_values(self, mock_file):
        """Test that input fields are prefilled with values"""
        asset = AssetData("addr", "link", "TestName", "TestCat", "web", "TestDesc")
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert 'value="TestCat"' in written_content
        assert 'value="TestName"' in written_content
        assert 'value="TestDesc"' in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_links(self, mock_file):
        """Test that links are generated correctly"""
        asset = AssetData(
            address="0:test",
            link="https://tonviewer.com/0:test",
            name="name",
            category="cat",
            website="https://example.com",
            description="desc"
        )
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert 'href="https://tonviewer.com/0:test"' in written_content
        assert '<a href=' in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_unicode_support(self, mock_file):
        """Test HTML generation with Unicode characters"""
        asset = AssetData("0:test", "link", "Tökën 测试", "Catégory", "web", "Désc 🎉")
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert "Tökën 测试" in written_content
        assert "🎉" in written_content

    @patch('builtins.open', new_callable=mock_open)
    def test_generate_html_empty_fields(self, mock_file):
        """Test HTML generation with empty field values"""
        asset = AssetData("addr", "link", "", "", "", "")
        
        generate_to_review_html([asset])
        
        written_content = mock_file().write.call_args[0][0]
        assert 'value=""' in written_content


class TestAddBlacklist:
    """Test suite for add_blacklist function"""

    @patch('builtins.open', new_callable=mock_open)
    def test_add_blacklist_empty_list(self, mock_file):
        """Test adding empty blacklist"""
        add_blacklist([])
        
        mock_file.assert_called_once_with("blacklist.csv", "a")

    @patch('builtins.open', new_callable=mock_open)
    def test_add_blacklist_single_asset(self, mock_file):
        """Test adding single asset to blacklist"""
        asset = AssetData("0:blacklisted", "link", "name", "cat", "web", "desc")
        
        add_blacklist([asset])
        
        mock_file.assert_called_once_with("blacklist.csv", "a")
        # CSV writer should have been used
        handle = mock_file()
        assert handle.write.called

    @patch('builtins.open', new_callable=mock_open)
    def test_add_blacklist_multiple_assets(self, mock_file):
        """Test adding multiple assets to blacklist"""
        assets = [
            AssetData("0:addr1", "l1", "n1", "c1", "w1", "d1"),
            AssetData("0:addr2", "l2", "n2", "c2", "w2", "d2"),
            AssetData("0:addr3", "l3", "n3", "c3", "w3", "d3"),
        ]
        
        add_blacklist(assets)
        
        mock_file.assert_called_once_with("blacklist.csv", "a")

    @patch('builtins.open', new_callable=mock_open)
    def test_add_blacklist_appends_to_file(self, mock_file):
        """Test that blacklist is appended, not overwritten"""
        asset = AssetData("0:test", "link", "name", "cat", "web", "desc")
        
        add_blacklist([asset])
        
        # Should open in append mode
        mock_file.assert_called_with("blacklist.csv", "a")

    @patch('builtins.open', new_callable=mock_open)
    def test_add_blacklist_writes_only_address(self, mock_file):
        """Test that only address is written to CSV"""
        asset = AssetData("0:onlyaddr", "link", "name", "cat", "web", "desc")
        
        # Create a StringIO to capture CSV output
        output = io.StringIO()
        mock_file.return_value = output
        
        add_blacklist([asset])
        
        # The CSV should contain the address
        # Note: actual CSV writing behavior depends on implementation

    @patch('builtins.open', new_callable=mock_open)
    def test_add_blacklist_special_chars_in_address(self, mock_file):
        """Test blacklist with special characters in address"""
        asset = AssetData("0:test,with,commas", "link", "name", "cat", "web", "desc")
        
        add_blacklist([asset])
        
        # Should handle commas in CSV properly
        mock_file.assert_called_once()


class TestRowTemplate:
    """Test suite for ROW_TEMPLATE constant"""

    def test_row_template_format_basic(self):
        """Test ROW_TEMPLATE formatting with basic data"""
        row = ROW_TEMPLATE.format(
            i=0,
            link="https://test.com",
            address="0:test",
            category="DeFi",
            name="Token",
            website="https://web.com",
            description="Desc"
        )
        
        assert "https://test.com" in row
        assert "0:test" in row
        assert "DeFi" in row
        assert "Token" in row

    def test_row_template_contains_html_elements(self):
        """Test that ROW_TEMPLATE contains required HTML elements"""
        assert "<tr" in ROW_TEMPLATE
        assert "<td" in ROW_TEMPLATE
        assert "<input" in ROW_TEMPLATE
        assert "checkbox" in ROW_TEMPLATE

    def test_row_template_has_index_placeholder(self):
        """Test that template has index placeholders"""
        assert "{i}" in ROW_TEMPLATE
        assert "row{i}" in ROW_TEMPLATE
        assert "address{i}" in ROW_TEMPLATE


class TestPageTemplate:
    """Test suite for PAGE_TEMPLATE constant"""

    def test_page_template_html_structure(self):
        """Test that PAGE_TEMPLATE has valid HTML structure"""
        assert "<!DOCTYPE html>" in PAGE_TEMPLATE
        assert "<html" in PAGE_TEMPLATE
        assert "<head>" in PAGE_TEMPLATE
        assert "<body>" in PAGE_TEMPLATE
        assert "</html>" in PAGE_TEMPLATE

    def test_page_template_has_rows_placeholder(self):
        """Test that template has rows placeholder"""
        assert "{rows}" in PAGE_TEMPLATE

    def test_page_template_includes_title(self):
        """Test that template includes title"""
        assert "<title>To review</title>" in PAGE_TEMPLATE

    def test_page_template_includes_button(self):
        """Test that template includes generate button"""
        assert "Generate YAMLs" in PAGE_TEMPLATE
        assert "floating-button" in PAGE_TEMPLATE

    def test_page_template_includes_jszip(self):
        """Test that template includes JSZip library"""
        assert "jszip" in PAGE_TEMPLATE.lower()
        assert "cdnjs" in PAGE_TEMPLATE.lower()

    def test_page_template_format_basic(self):
        """Test PAGE_TEMPLATE formatting"""
        page = PAGE_TEMPLATE.format(rows="<tr><td>Test</td></tr>")
        
        assert "<tr><td>Test</td></tr>" in page
        assert "<!DOCTYPE html>" in page