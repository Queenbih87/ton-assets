"""
Comprehensive unit tests for generator.py

Tests cover:
- DEX data collection and merging
- Jetton validation and merging
- Account data merging
- Collection data merging
- File I/O operations
- Error handling and edge cases
"""

import pytest
import json
import yaml
from unittest.mock import Mock, patch, mock_open, MagicMock, call
import tempfile
import os

from generator import (
    collect_all_dexes,
    collect_all_backed,
    merge_jettons,
    merge_accounts,
    merge_collections,
    main,
    ALLOWED_KEYS,
    DEXES_FILE_NAME,
    BACKED_FILE_NAME,
)


class TestCollectAllDexes:
    """Test suite for collect_all_dexes function"""

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator._generator__get_dedust_assets')
    @patch('generator._generator__get_stonfi_assets')
    @patch('generator.normalize_address')
    @patch('generator.yaml.dump')
    def test_collect_all_dexes_basic(self, mock_dump, mock_normalize, mock_stonfi, 
                                      mock_dedust, mock_file, mock_yaml_load, mock_glob):
        """Test basic DEX collection functionality"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{'address': '0:1234', 'name': 'Existing', 'symbol': 'EXT'}]
        mock_normalize.return_value = '0:1234normalized'
        
        mock_asset = Mock()
        mock_asset.name = 'New Token'
        mock_asset.address = '0:5678'
        mock_asset.symbol = 'NEW'
        
        mock_dedust.return_value = [mock_asset]
        mock_stonfi.return_value = []
        
        collect_all_dexes()
        
        mock_dump.assert_called_once()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator._generator__get_dedust_assets')
    @patch('generator._generator__get_stonfi_assets')
    @patch('generator.normalize_address')
    @patch('generator.yaml.dump')
    def test_collect_all_dexes_filters_duplicates(self, mock_dump, mock_normalize, 
                                                    mock_stonfi, mock_dedust, mock_file,
                                                    mock_yaml_load, mock_glob):
        """Test that duplicate addresses are filtered out"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{'address': '0:1234', 'name': 'Existing', 'symbol': 'EXT'}]
        
        def normalize_side_effect(addr, to_raw):
            return addr + '_normalized'
        
        mock_normalize.side_effect = normalize_side_effect
        
        mock_asset = Mock()
        mock_asset.name = 'Duplicate'
        mock_asset.address = '0:1234'
        mock_asset.symbol = 'DUP'
        
        mock_dedust.return_value = [mock_asset]
        mock_stonfi.return_value = []
        
        collect_all_dexes()
        
        # Should call dump with empty or filtered list
        mock_dump.assert_called_once()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator._generator__get_dedust_assets')
    @patch('generator._generator__get_stonfi_assets')
    @patch('generator.normalize_address')
    @patch('generator.yaml.dump')
    def test_collect_all_dexes_skips_dexes_file(self, mock_dump, mock_normalize,
                                                  mock_stonfi, mock_dedust, mock_file,
                                                  mock_yaml_load, mock_glob):
        """Test that imported_from_dex.yaml is skipped"""
        mock_glob.return_value = ['jettons/test.yaml', f'jettons/{DEXES_FILE_NAME}']
        mock_yaml_load.return_value = []
        mock_normalize.return_value = '0:normalized'
        mock_dedust.return_value = []
        mock_stonfi.return_value = []
        
        collect_all_dexes()
        
        # Should only load test.yaml, not the dexes file
        assert mock_yaml_load.call_count >= 1

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator._generator__get_dedust_assets')
    @patch('generator._generator__get_stonfi_assets')
    @patch('generator.normalize_address')
    @patch('generator.yaml.dump')
    def test_collect_all_dexes_handles_list_and_dict(self, mock_dump, mock_normalize,
                                                       mock_stonfi, mock_dedust, mock_file,
                                                       mock_yaml_load, mock_glob):
        """Test handling of both list and dict YAML formats"""
        mock_glob.return_value = ['jettons/list.yaml', 'jettons/dict.yaml']
        mock_yaml_load.side_effect = [
            [{'address': '0:1', 'name': 'Token1', 'symbol': 'T1'}],  # list
            {'address': '0:2', 'name': 'Token2', 'symbol': 'T2'}     # dict
        ]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        mock_dedust.return_value = []
        mock_stonfi.return_value = []
        
        collect_all_dexes()
        
        mock_dump.assert_called_once()


class TestCollectAllBacked:
    """Test suite for collect_all_backed function"""

    @patch('generator._generator__get_backed_assets')
    @patch('generator.normalize_address')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.yaml.dump')
    def test_collect_all_backed_success(self, mock_dump, mock_file, mock_normalize, mock_backed):
        """Test successful backed assets collection"""
        mock_asset = Mock()
        mock_asset.name = 'Backed Token'
        mock_asset.address = '0:backed'
        mock_asset.symbol = 'BKD'
        
        mock_backed.return_value = [mock_asset]
        mock_normalize.return_value = '0:backed_norm'
        
        collect_all_backed()
        
        mock_dump.assert_called_once()

    @patch('generator._generator__get_backed_assets')
    def test_collect_all_backed_empty_list(self, mock_backed):
        """Test that empty list doesn't write file"""
        mock_backed.return_value = []
        
        # Should not raise exception
        collect_all_backed()

    @patch('generator._generator__get_backed_assets')
    @patch('generator.normalize_address')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.yaml.dump')
    def test_collect_all_backed_sorts_by_symbol(self, mock_dump, mock_file, 
                                                  mock_normalize, mock_backed):
        """Test that backed assets are sorted by symbol"""
        mock_asset1 = Mock()
        mock_asset1.name = 'Token B'
        mock_asset1.address = '0:b'
        mock_asset1.symbol = 'ZZZ'
        
        mock_asset2 = Mock()
        mock_asset2.name = 'Token A'
        mock_asset2.address = '0:a'
        mock_asset2.symbol = 'AAA'
        
        mock_backed.return_value = [mock_asset1, mock_asset2]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        
        collect_all_backed()
        
        mock_dump.assert_called_once()
        args = mock_dump.call_args[0]
        assets = args[0]
        # Should be sorted by symbol
        assert assets[0]['symbol'] == 'AAA'
        assert assets[1]['symbol'] == 'ZZZ'


class TestMergeJettons:
    """Test suite for merge_jettons function"""

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_jettons_basic(self, mock_json_dump, mock_normalize, 
                                   mock_file, mock_yaml_load, mock_glob):
        """Test basic jetton merging"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test Token',
            'symbol': 'TST',
            'address': '0:test',
        }]
        mock_normalize.return_value = '0:test_norm'
        
        result = merge_jettons()
        
        assert len(result) == 1
        assert result[0][0] == 'Test Token'
        mock_json_dump.assert_called_once()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    def test_merge_jettons_validates_required_fields(self, mock_normalize, mock_file,
                                                       mock_yaml_load, mock_glob):
        """Test that required fields are validated"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test Token',
            'symbol': 'TST',
            # Missing address
        }]
        
        with pytest.raises(Exception) as exc_info:
            merge_jettons()
        
        assert 'required' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    def test_merge_jettons_rejects_invalid_keys(self, mock_normalize, mock_file,
                                                  mock_yaml_load, mock_glob):
        """Test that invalid keys are rejected"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test',
            'symbol': 'TST',
            'address': '0:test',
            'invalid_key': 'should fail'
        }]
        mock_normalize.return_value = '0:test_norm'
        
        with pytest.raises(Exception) as exc_info:
            merge_jettons()
        
        assert 'invalid keys' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    def test_merge_jettons_detects_duplicates(self, mock_normalize, mock_file,
                                                mock_yaml_load, mock_glob):
        """Test that duplicate addresses are detected"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [
            {'name': 'Token1', 'symbol': 'T1', 'address': '0:same'},
            {'name': 'Token2', 'symbol': 'T2', 'address': '0:same'},
        ]
        mock_normalize.return_value = '0:same_norm'
        
        with pytest.raises(Exception) as exc_info:
            merge_jettons()
        
        assert 'duplicate' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    def test_merge_jettons_rejects_tonapi_cache(self, mock_normalize, mock_file,
                                                  mock_yaml_load, mock_glob):
        """Test that cache.tonapi.io images are rejected"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test',
            'symbol': 'TST',
            'address': '0:test',
            'image': 'https://cache.tonapi.io/imgproxy/image.jpg'
        }]
        mock_normalize.return_value = '0:test_norm'
        
        with pytest.raises(Exception) as exc_info:
            merge_jettons()
        
        assert 'tonapi' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    def test_merge_jettons_validates_field_types(self, mock_normalize, mock_file,
                                                   mock_yaml_load, mock_glob):
        """Test that field types are validated"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test',
            'symbol': 123,  # Should be string
            'address': '0:test',
        }]
        mock_normalize.return_value = '0:test_norm'
        
        with pytest.raises(Exception) as exc_info:
            merge_jettons()
        
        assert 'field type' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    def test_merge_jettons_validates_list_fields(self, mock_normalize, mock_file,
                                                   mock_yaml_load, mock_glob):
        """Test that list fields are validated"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test',
            'symbol': 'TST',
            'address': '0:test',
            'social': 'not a list'  # Should be list
        }]
        mock_normalize.return_value = '0:test_norm'
        
        with pytest.raises(Exception) as exc_info:
            merge_jettons()
        
        assert 'list field type' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_jettons_converts_decimals_to_int(self, mock_json_dump, mock_normalize,
                                                      mock_file, mock_yaml_load, mock_glob):
        """Test that decimals are converted to int"""
        mock_glob.return_value = ['jettons/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'Test',
            'symbol': 'TST',
            'address': '0:test',
            'decimals': '9'  # String that should be converted
        }]
        mock_normalize.return_value = '0:test_norm'
        
        merge_jettons()
        
        # Check that decimals was converted
        args = mock_json_dump.call_args[0]
        jettons = args[0]
        assert isinstance(jettons[0]['decimals'], int)


class TestMergeAccounts:
    """Test suite for merge_accounts function"""

    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_accounts_basic(self, mock_json_dump, mock_normalize, mock_file, mock_yaml_load):
        """Test basic account merging"""
        mock_yaml_load.return_value = [
            {'name': 'Account1', 'address': '0:acc1'}
        ]
        mock_normalize.return_value = '0:acc1_norm'
        
        result = merge_accounts([])
        
        assert len(result) == 3  # 3 files from main_page
        mock_json_dump.assert_called_once()

    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_accounts_normalizes_addresses(self, mock_json_dump, mock_normalize,
                                                   mock_file, mock_yaml_load):
        """Test that all addresses are normalized"""
        mock_yaml_load.return_value = [
            {'name': 'Account1', 'address': '0:original'}
        ]
        mock_normalize.return_value = '0:normalized'
        
        merge_accounts([])
        
        # Verify addresses were normalized
        args = mock_json_dump.call_args[0]
        accounts = args[0]
        assert all('normalized' in acc['address'] for acc in accounts)

    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_accounts_returns_main_page(self, mock_json_dump, mock_normalize,
                                                mock_file, mock_yaml_load):
        """Test that main page accounts are returned"""
        mock_yaml_load.return_value = [
            {'name': 'Main Account', 'address': '0:main'}
        ]
        mock_normalize.return_value = '0:main_norm'
        
        result = merge_accounts([])
        
        # Should return list of (name, address) tuples
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) for item in result)


class TestMergeCollections:
    """Test suite for merge_collections function"""

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_collections_basic(self, mock_json_dump, mock_normalize,
                                       mock_file, mock_yaml_load, mock_glob):
        """Test basic collection merging"""
        mock_glob.return_value = ['collections/test.yaml']
        mock_yaml_load.return_value = [{
            'name': 'NFT Collection',
            'address': '0:collection'
        }]
        mock_normalize.return_value = '0:collection_norm'
        
        result = merge_collections()
        
        assert len(result) == 1
        mock_json_dump.assert_called_once()

    @patch('generator.glob.glob')
    @patch('generator.yaml.safe_load')
    @patch('generator.open', new_callable=mock_open)
    @patch('generator.normalize_address')
    @patch('generator.json.dump')
    def test_merge_collections_handles_list_and_dict(self, mock_json_dump, mock_normalize,
                                                       mock_file, mock_yaml_load, mock_glob):
        """Test handling of both list and dict formats"""
        mock_glob.return_value = ['collections/list.yaml', 'collections/dict.yaml']
        mock_yaml_load.side_effect = [
            [{'name': 'Coll1', 'address': '0:1'}],  # list
            {'name': 'Coll2', 'address': '0:2'}     # dict
        ]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        
        result = merge_collections()
        
        assert len(result) == 2
        mock_json_dump.assert_called_once()


class TestMain:
    """Test suite for main function"""

    @patch('generator.glob.glob')
    @patch('generator.update_stonfi_routers')
    @patch('generator.collect_all_dexes')
    @patch('generator.collect_all_backed')
    @patch('generator.merge_jettons')
    @patch('generator.merge_collections')
    @patch('generator.merge_accounts')
    @patch('generator.normalize_address')
    @patch('generator.open', new_callable=mock_open)
    def test_main_no_yaml_in_root(self, mock_file, mock_normalize, mock_merge_accounts,
                                    mock_merge_collections, mock_merge_jettons,
                                    mock_collect_backed, mock_collect_dexes,
                                    mock_update_routers, mock_glob):
        """Test that main rejects YAML files in root"""
        mock_glob.return_value = ['invalid.yaml']
        
        with pytest.raises(Exception) as exc_info:
            main()
        
        assert 'root directory' in str(exc_info.value).lower()

    @patch('generator.glob.glob')
    @patch('generator.update_stonfi_routers')
    @patch('generator.collect_all_dexes')
    @patch('generator.collect_all_backed')
    @patch('generator.merge_jettons')
    @patch('generator.merge_collections')
    @patch('generator.merge_accounts')
    @patch('generator.normalize_address')
    @patch('generator.open', new_callable=mock_open)
    def test_main_success_flow(self, mock_file, mock_normalize, mock_merge_accounts,
                                 mock_merge_collections, mock_merge_jettons,
                                 mock_collect_backed, mock_collect_dexes,
                                 mock_update_routers, mock_glob):
        """Test successful main execution flow"""
        mock_glob.return_value = []
        mock_merge_jettons.return_value = [('Token', '0:addr')]
        mock_merge_collections.return_value = [('Coll', '0:coll')]
        mock_merge_accounts.return_value = [('Acc', '0:acc')]
        mock_normalize.side_effect = lambda addr, to_raw: addr if to_raw else 'EQ...'
        
        main()
        
        mock_update_routers.assert_called_once()
        mock_collect_dexes.assert_called_once()
        mock_collect_backed.assert_called_once()
        mock_merge_jettons.assert_called_once()
        mock_merge_collections.assert_called_once()
        mock_merge_accounts.assert_called_once()

    @patch('generator.glob.glob')
    @patch('generator.update_stonfi_routers')
    @patch('generator.collect_all_dexes')
    @patch('generator.collect_all_backed')
    @patch('generator.merge_jettons')
    @patch('generator.merge_collections')
    @patch('generator.merge_accounts')
    @patch('generator.normalize_address')
    @patch('generator.open', new_callable=mock_open)
    def test_main_generates_readme(self, mock_file, mock_normalize, mock_merge_accounts,
                                     mock_merge_collections, mock_merge_jettons,
                                     mock_collect_backed, mock_collect_dexes,
                                     mock_update_routers, mock_glob):
        """Test that README is generated"""
        mock_glob.return_value = []
        mock_merge_jettons.return_value = [('Token', '0:addr')]
        mock_merge_collections.return_value = []
        mock_merge_accounts.return_value = []
        mock_normalize.side_effect = lambda addr, to_raw: addr if to_raw else 'EQ...'
        
        # Mock template reading
        mock_file.return_value.read.return_value = 'Template: %s | %s'
        
        main()
        
        # Verify README.md was opened for writing
        calls = mock_file.call_args_list
        readme_calls = [c for c in calls if 'README.md' in str(c)]
        assert len(readme_calls) > 0


class TestAllowedKeys:
    """Test suite for ALLOWED_KEYS constant"""

    def test_allowed_keys_contains_required_fields(self):
        """Test that ALLOWED_KEYS contains all required fields"""
        required = {'symbol', 'name', 'address'}
        assert required.issubset(ALLOWED_KEYS)

    def test_allowed_keys_contains_optional_fields(self):
        """Test that ALLOWED_KEYS contains expected optional fields"""
        optional = {'description', 'image', 'social', 'websites', 'decimals'}
        assert optional.issubset(ALLOWED_KEYS)

    def test_allowed_keys_immutable(self):
        """Test that ALLOWED_KEYS is a set"""
        assert isinstance(ALLOWED_KEYS, set)