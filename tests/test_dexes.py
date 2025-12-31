"""
Comprehensive unit tests for dexes.py

Tests cover:
- Pydantic model validation
- API data fetching functions
- Error handling for network failures
- Data filtering and transformation
- Edge cases for each DEX integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from pydantic import ValidationError

from dexes import (
    Asset,
    MegatonAsset,
    StonfiAsset,
    _dexes__get_stonfi_assets,
    _dexes__get_megaton_assets,
    _dexes__get_dedust_assets,
    _dexes__get_backed_assets,
    update_stonfi_routers,
)


class TestAssetModel:
    """Test suite for Asset Pydantic model"""

    def test_asset_valid_creation(self):
        """Test creating a valid Asset"""
        asset = Asset(
            name="Test Token",
            address="0:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            symbol="TEST"
        )
        
        assert asset.name == "Test Token"
        assert asset.address == "0:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert asset.symbol == "TEST"

    def test_asset_missing_field(self):
        """Test that Asset requires all fields"""
        with pytest.raises(ValidationError):
            Asset(name="Test", symbol="TEST")  # Missing address

    def test_asset_empty_strings(self):
        """Test Asset with empty strings"""
        asset = Asset(name="", address="", symbol="")
        assert asset.name == ""
        assert asset.address == ""
        assert asset.symbol == ""

    def test_asset_unicode_support(self):
        """Test Asset with Unicode characters"""
        asset = Asset(
            name="Tökën 测试",
            address="0:" + "a" * 64,
            symbol="TÖK"
        )
        assert "测试" in asset.name

    def test_asset_dict_conversion(self):
        """Test Asset model_dump method"""
        asset = Asset(name="Token", address="0:abc", symbol="TKN")
        data = asset.model_dump() if hasattr(asset, 'model_dump') else asset.dict()
        
        assert data['name'] == "Token"
        assert data['address'] == "0:abc"
        assert data['symbol'] == "TKN"


class TestMegatonAssetModel:
    """Test suite for MegatonAsset Pydantic model"""

    def test_megaton_asset_valid_creation(self):
        """Test creating a valid MegatonAsset"""
        asset = MegatonAsset(
            name="Megaton Token",
            address="0:abcd",
            symbol="MGT",
            type=2,
            isVisible=1
        )
        
        assert asset.type == 2
        assert asset.isVisible == 1

    def test_megaton_asset_type_validation(self):
        """Test that type must be integer"""
        with pytest.raises(ValidationError):
            MegatonAsset(
                name="Test",
                address="0:1234",
                symbol="TST",
                type="not_an_int",
                isVisible=1
            )

    def test_megaton_asset_visibility_zero(self):
        """Test MegatonAsset with isVisible=0"""
        asset = MegatonAsset(
            name="Hidden",
            address="0:1234",
            symbol="HID",
            type=1,
            isVisible=0
        )
        assert asset.isVisible == 0

    def test_megaton_asset_inherits_from_asset(self):
        """Test that MegatonAsset has Asset fields"""
        asset = MegatonAsset(
            name="Test",
            address="0:test",
            symbol="TST",
            type=2,
            isVisible=1
        )
        assert hasattr(asset, 'name')
        assert hasattr(asset, 'address')
        assert hasattr(asset, 'symbol')


class TestStonfiAssetModel:
    """Test suite for StonfiAsset Pydantic model"""

    def test_stonfi_asset_valid_creation(self):
        """Test creating a valid StonfiAsset"""
        asset = StonfiAsset(
            contract_address="0:1234",
            display_name="STON Token",
            symbol="STON",
            kind="Jetton",
            decimals=9,
            community=False,
            deprecated=False,
            blacklisted=False
        )
        
        assert asset.contract_address == "0:1234"
        assert asset.kind == "Jetton"
        assert asset.decimals == 9

    def test_stonfi_asset_boolean_flags(self):
        """Test StonfiAsset boolean flags"""
        asset = StonfiAsset(
            contract_address="0:test",
            display_name="Test",
            symbol="TST",
            kind="Jetton",
            decimals=9,
            community=True,
            deprecated=True,
            blacklisted=True
        )
        
        assert asset.community is True
        assert asset.deprecated is True
        assert asset.blacklisted is True

    def test_stonfi_asset_decimals_validation(self):
        """Test that decimals must be integer"""
        with pytest.raises(ValidationError):
            StonfiAsset(
                contract_address="0:test",
                display_name="Test",
                symbol="TST",
                kind="Jetton",
                decimals="nine",
                community=False,
                deprecated=False,
                blacklisted=False
            )

    def test_stonfi_asset_different_kinds(self):
        """Test StonfiAsset with different kind values"""
        for kind in ["Jetton", "NFT", "Token"]:
            asset = StonfiAsset(
                contract_address="0:test",
                display_name="Test",
                symbol="TST",
                kind=kind,
                decimals=9,
                community=False,
                deprecated=False,
                blacklisted=False
            )
            assert asset.kind == kind


class TestGetStonfiAssets:
    """Test suite for __get_stonfi_assets function"""

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_success(self, mock_get):
        """Test successful fetching of STON.fi assets"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset_list": [
                {
                    "contract_address": "0:1234",
                    "display_name": "Token 1",
                    "symbol": "TK1",
                    "kind": "Jetton",
                    "decimals": 9,
                    "community": False,
                    "deprecated": False,
                    "blacklisted": False
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert len(result) == 1
        assert result[0].name == "Token 1"
        assert result[0].symbol == "TK1"

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_filters_community(self, mock_get):
        """Test that community tokens are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset_list": [
                {
                    "contract_address": "0:1234",
                    "display_name": "Community Token",
                    "symbol": "COM",
                    "kind": "Jetton",
                    "decimals": 9,
                    "community": True,
                    "deprecated": False,
                    "blacklisted": False
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_filters_blacklisted(self, mock_get):
        """Test that blacklisted tokens are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset_list": [
                {
                    "contract_address": "0:1234",
                    "display_name": "Bad Token",
                    "symbol": "BAD",
                    "kind": "Jetton",
                    "decimals": 9,
                    "community": False,
                    "deprecated": False,
                    "blacklisted": True
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_filters_deprecated(self, mock_get):
        """Test that deprecated tokens are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset_list": [
                {
                    "contract_address": "0:1234",
                    "display_name": "Old Token",
                    "symbol": "OLD",
                    "kind": "Jetton",
                    "decimals": 9,
                    "community": False,
                    "deprecated": True,
                    "blacklisted": False
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_filters_non_jetton(self, mock_get):
        """Test that non-Jetton assets are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset_list": [
                {
                    "contract_address": "0:1234",
                    "display_name": "NFT Item",
                    "symbol": "NFT",
                    "kind": "NFT",
                    "decimals": 0,
                    "community": False,
                    "deprecated": False,
                    "blacklisted": False
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    @patch('dexes.logging.error')
    def test_get_stonfi_assets_network_error(self, mock_log, mock_get):
        """Test handling of network errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert result == []
        mock_log.assert_called_once()

    @patch('dexes.requests.get')
    @patch('dexes.logging.error')
    def test_get_stonfi_assets_404_error(self, mock_log, mock_get):
        """Test handling of 404 errors"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert result == []
        mock_log.assert_called_once()

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_empty_list(self, mock_get):
        """Test handling of empty asset list"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"asset_list": []}
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert result == []

    @patch('dexes.requests.get')
    def test_get_stonfi_assets_multiple_valid(self, mock_get):
        """Test fetching multiple valid assets"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset_list": [
                {
                    "contract_address": "0:1111",
                    "display_name": "Token 1",
                    "symbol": "TK1",
                    "kind": "Jetton",
                    "decimals": 9,
                    "community": False,
                    "deprecated": False,
                    "blacklisted": False
                },
                {
                    "contract_address": "0:2222",
                    "display_name": "Token 2",
                    "symbol": "TK2",
                    "kind": "Jetton",
                    "decimals": 6,
                    "community": False,
                    "deprecated": False,
                    "blacklisted": False
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_stonfi_assets()
        
        assert len(result) == 2
        assert result[0].symbol == "TK1"
        assert result[1].symbol == "TK2"


class TestGetMegatonAssets:
    """Test suite for __get_megaton_assets function"""

    @patch('dexes.requests.get')
    def test_get_megaton_assets_success(self, mock_get):
        """Test successful fetching of Megaton assets"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "Megaton Token",
                "address": "0:abcd",
                "symbol": "MGT",
                "type": 2,
                "isVisible": 1
            }
        ]
        mock_get.return_value = mock_response
        
        result = _dexes__get_megaton_assets()
        
        assert len(result) == 1
        assert result[0].name == "Megaton Token"

    @patch('dexes.requests.get')
    def test_get_megaton_assets_filters_invisible(self, mock_get):
        """Test that invisible assets are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "Hidden Token",
                "address": "0:1234",
                "symbol": "HID",
                "type": 2,
                "isVisible": 0
            }
        ]
        mock_get.return_value = mock_response
        
        result = _dexes__get_megaton_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    def test_get_megaton_assets_filters_wrong_type(self, mock_get):
        """Test that wrong type assets are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "Wrong Type",
                "address": "0:1234",
                "symbol": "WRG",
                "type": 1,
                "isVisible": 1
            }
        ]
        mock_get.return_value = mock_response
        
        result = _dexes__get_megaton_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    @patch('dexes.logging.error')
    def test_get_megaton_assets_network_error(self, mock_log, mock_get):
        """Test handling of network errors"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        result = _dexes__get_megaton_assets()
        
        assert result == []
        mock_log.assert_called_once()


class TestGetDedustAssets:
    """Test suite for __get_dedust_assets function"""

    @patch('dexes.requests.get')
    def test_get_dedust_assets_success(self, mock_get):
        """Test successful fetching of DeDust assets"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "DeDust Token",
                "address": "0:dddd",
                "symbol": "DDT"
            }
        ]
        mock_get.return_value = mock_response
        
        result = _dexes__get_dedust_assets()
        
        assert len(result) == 1
        assert result[0].name == "DeDust Token"

    @patch('dexes.requests.get')
    def test_get_dedust_assets_filters_blacklisted(self, mock_get):
        """Test that blacklisted addresses are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "Blacklisted",
                "address": "EQBiyZMUXvdnRYFUk3_R5uPdsR2ROI9mes_1S-jL1tIQDhDK",
                "symbol": "BLK"
            }
        ]
        mock_get.return_value = mock_response
        
        result = _dexes__get_dedust_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    def test_get_dedust_assets_filters_missing_address(self, mock_get):
        """Test that items without address are filtered"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "No Address",
                "symbol": "NOA"
            }
        ]
        mock_get.return_value = mock_response
        
        result = _dexes__get_dedust_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    @patch('dexes.logging.error')
    def test_get_dedust_assets_network_error(self, mock_log, mock_get):
        """Test handling of network errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = _dexes__get_dedust_assets()
        
        assert result == []
        mock_log.assert_called_once()


class TestGetBackedAssets:
    """Test suite for __get_backed_assets function"""

    @patch('dexes.requests.get')
    def test_get_backed_assets_success(self, mock_get):
        """Test successful fetching of Backed assets"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "nodes": [
                {
                    "name": "Backed Token",
                    "symbol": "BKD",
                    "deployments": [
                        {
                            "network": "ton",
                            "address": "ton:0:1234abcd"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_backed_assets()
        
        assert len(result) == 1
        assert result[0].name == "Backed Token"
        assert result[0].address == "0:1234abcd"

    @patch('dexes.requests.get')
    def test_get_backed_assets_filters_non_ton(self, mock_get):
        """Test that non-TON deployments are filtered"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "nodes": [
                {
                    "name": "Ethereum Token",
                    "symbol": "ETH",
                    "deployments": [
                        {
                            "network": "ethereum",
                            "address": "0x1234"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_backed_assets()
        
        assert len(result) == 0

    @patch('dexes.requests.get')
    def test_get_backed_assets_removes_ton_prefix(self, mock_get):
        """Test that 'ton:' prefix is removed from addresses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "nodes": [
                {
                    "name": "Token",
                    "symbol": "TKN",
                    "deployments": [
                        {
                            "network": "TON",
                            "address": "ton:0:abcdef"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_backed_assets()
        
        assert len(result) == 1
        assert result[0].address == "0:abcdef"
        assert not result[0].address.startswith("ton:")

    @patch('dexes.requests.get')
    @patch('dexes.logging.error')
    def test_get_backed_assets_network_error(self, mock_log, mock_get):
        """Test handling of network errors"""
        mock_response = Mock()
        mock_response.status_code = 502
        mock_get.return_value = mock_response
        
        result = _dexes__get_backed_assets()
        
        assert result == []
        mock_log.assert_called_once()

    @patch('dexes.requests.get')
    def test_get_backed_assets_case_insensitive_network(self, mock_get):
        """Test that network matching is case-insensitive"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "nodes": [
                {
                    "name": "Token",
                    "symbol": "TKN",
                    "deployments": [
                        {
                            "network": "ToN",
                            "address": "ton:0:test"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _dexes__get_backed_assets()
        
        assert len(result) == 1


class TestUpdateStonfiRouters:
    """Test suite for update_stonfi_routers function"""

    @patch('dexes.requests.get')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('dexes.yaml.safe_dump')
    def test_update_stonfi_routers_success(self, mock_dump, mock_open, mock_get):
        """Test successful update of STON.fi routers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "router_list": [
                {"address": "0:router1"},
                {"address": "0:router2"}
            ]
        }
        mock_get.return_value = mock_response
        
        update_stonfi_routers()
        
        mock_dump.assert_called_once()
        args = mock_dump.call_args[0]
        routers = args[0]
        assert len(routers) == 2
        assert all(r["name"] == "STON.fi DEX" for r in routers)

    @patch('dexes.requests.get')
    @patch('dexes.logging.error')
    def test_update_stonfi_routers_network_error(self, mock_log, mock_get):
        """Test handling of network errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        update_stonfi_routers()
        
        mock_log.assert_called_once()

    @patch('dexes.requests.get')
    def test_update_stonfi_routers_empty_list(self, mock_get):
        """Test handling of empty router list"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"router_list": []}
        mock_get.return_value = mock_response
        
        # Should not raise exception
        update_stonfi_routers()

    @patch('dexes.requests.get')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('dexes.yaml.safe_dump')
    def test_update_stonfi_routers_file_writing(self, mock_dump, mock_open, mock_get):
        """Test that routers are written to correct file"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "router_list": [{"address": "0:test"}]
        }
        mock_get.return_value = mock_response
        
        update_stonfi_routers()
        
        mock_open.assert_called_with("accounts/ston.yaml", "w")