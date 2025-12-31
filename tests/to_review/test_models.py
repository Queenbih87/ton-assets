"""
Comprehensive unit tests for to_review/models.py

Tests cover:
- AssetData class initialization
- Field assignment and access
- Data integrity
- Edge cases with special characters
"""

import pytest
from to_review.models import AssetData


class TestAssetData:
    """Test suite for AssetData class"""

    def test_asset_data_basic_creation(self):
        """Test creating AssetData with all fields"""
        asset = AssetData(
            address="0:test_address",
            link="https://tonviewer.com/0:test",
            name="Test Asset",
            category="DeFi",
            website="https://test.com",
            description="Test description"
        )
        
        assert asset.address == "0:test_address"
        assert asset.link == "https://tonviewer.com/0:test"
        assert asset.name == "Test Asset"
        assert asset.category == "DeFi"
        assert asset.website == "https://test.com"
        assert asset.description == "Test description"

    def test_asset_data_empty_strings(self):
        """Test AssetData with empty strings"""
        asset = AssetData(
            address="",
            link="",
            name="",
            category="",
            website="",
            description=""
        )
        
        assert asset.address == ""
        assert asset.link == ""
        assert asset.name == ""
        assert asset.category == ""
        assert asset.website == ""
        assert asset.description == ""

    def test_asset_data_unicode_support(self):
        """Test AssetData with Unicode characters"""
        asset = AssetData(
            address="0:тест",
            link="https://test.com",
            name="测试 Token",
            category="DéFì",
            website="https://тест.com",
            description="Description with émojis 🎉"
        )
        
        assert "测试" in asset.name
        assert "тест" in asset.address
        assert "🎉" in asset.description

    def test_asset_data_special_characters(self):
        """Test AssetData with special characters"""
        asset = AssetData(
            address="0:test<>",
            link="https://test.com?param=value&other=test",
            name="Test & Co.",
            category="NFT's",
            website='https://test.com/path"with"quotes',
            description="Line 1\nLine 2\tTabbed"
        )
        
        assert "<>" in asset.address
        assert "&" in asset.name
        assert "'" in asset.category
        assert "\n" in asset.description

    def test_asset_data_long_strings(self):
        """Test AssetData with very long strings"""
        long_string = "x" * 10000
        asset = AssetData(
            address=long_string,
            link=long_string,
            name=long_string,
            category=long_string,
            website=long_string,
            description=long_string
        )
        
        assert len(asset.address) == 10000
        assert len(asset.description) == 10000

    def test_asset_data_field_types(self):
        """Test that all fields are strings"""
        asset = AssetData(
            address="addr",
            link="link",
            name="name",
            category="cat",
            website="web",
            description="desc"
        )
        
        assert isinstance(asset.address, str)
        assert isinstance(asset.link, str)
        assert isinstance(asset.name, str)
        assert isinstance(asset.category, str)
        assert isinstance(asset.website, str)
        assert isinstance(asset.description, str)

    def test_asset_data_whitespace_handling(self):
        """Test AssetData with whitespace"""
        asset = AssetData(
            address="  0:test  ",
            link="  https://test.com  ",
            name="  Test Name  ",
            category="  Category  ",
            website="  https://web.com  ",
            description="  Description  "
        )
        
        # Whitespace should be preserved
        assert asset.address.startswith("  ")
        assert asset.name.endswith("  ")

    def test_asset_data_realistic_example(self):
        """Test AssetData with realistic data"""
        asset = AssetData(
            address="0:62c9931457f767458154937fd1e6e3ddb11d91388f667acff54be8cbd6d2100e",
            link="https://tonviewer.com/0:62c9931457f767458154937fd1e6e3ddb11d91388f667acff54be8cbd6d2100e",
            name="Tether USD",
            category="Stablecoin",
            website="https://tether.to",
            description="Tether USD stablecoin on TON blockchain"
        )
        
        assert len(asset.address) == 66  # 0: + 64 hex chars
        assert asset.link.startswith("https://tonviewer.com/")
        assert "Tether" in asset.name

    def test_asset_data_html_special_chars(self):
        """Test AssetData with HTML special characters"""
        asset = AssetData(
            address="0:test",
            link="https://test.com",
            name="<script>alert('xss')</script>",
            category="Cat & Dog",
            website="https://test.com?a=1&b=2",
            description="<b>Bold</b> & <i>Italic</i>"
        )
        
        assert "<script>" in asset.name
        assert "&" in asset.category
        assert "<b>" in asset.description

    def test_asset_data_url_formats(self):
        """Test AssetData with various URL formats"""
        asset = AssetData(
            address="0:test",
            link="https://tonviewer.com/test",
            name="Test",
            category="Test",
            website="http://example.com:8080/path?query=value#fragment",
            description="Test"
        )
        
        assert asset.website.startswith("http://")
        assert ":8080" in asset.website
        assert "?" in asset.website
        assert "#fragment" in asset.website

    def test_asset_data_multiple_instances(self):
        """Test creating multiple AssetData instances"""
        asset1 = AssetData("addr1", "link1", "name1", "cat1", "web1", "desc1")
        asset2 = AssetData("addr2", "link2", "name2", "cat2", "web2", "desc2")
        
        assert asset1.address != asset2.address
        assert asset1.name != asset2.name
        # Verify instances are independent
        asset1.address = "modified"
        assert asset2.address == "addr2"

    def test_asset_data_category_variations(self):
        """Test AssetData with various category values"""
        categories = ["DeFi", "NFT", "Gaming", "Infrastructure", "Bridge", ""]
        
        for cat in categories:
            asset = AssetData("0:addr", "link", "name", cat, "web", "desc")
            assert asset.category == cat

    def test_asset_data_description_multiline(self):
        """Test AssetData with multiline description"""
        description = """This is a multi-line description.
It spans multiple lines.
And includes various formatting."""
        
        asset = AssetData(
            address="0:test",
            link="link",
            name="name",
            category="cat",
            website="web",
            description=description
        )
        
        assert "\n" in asset.description
        assert asset.description.count("\n") == 2

    def test_asset_data_numeric_strings(self):
        """Test AssetData with numeric strings"""
        asset = AssetData(
            address="0:123456",
            link="https://test.com/123",
            name="Token 2.0",
            category="v1.5",
            website="https://test.com",
            description="Version 3.14159"
        )
        
        assert "123456" in asset.address
        assert "2.0" in asset.name
        assert "3.14159" in asset.description