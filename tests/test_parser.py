"""
Comprehensive unit tests for parser.py

Tests cover:
- TON labels repository cloning and cleanup
- Asset type detection via TonAPI
- Blacklist filtering
- Directory traversal and JSON parsing
- Asset classification (whitelist vs blacklist)
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import json
import os

from parser import (
    clone_ton_labels_repo,
    rm_ton_labels_dir,
    get_types_from_tonapi,
    is_asset_to_blacklist,
    get_asset_from_json_file,
    get_assets_from_dir,
    get_assets_from_dirs,
    main,
    BLACKLIST_NFT_TYPES,
    BLACKLIST_JETTONS_TYPES,
)


class TestCloneTonLabelsRepo:
    """Test suite for clone_ton_labels_repo function"""

    @patch('parser.os.system')
    def test_clone_ton_labels_repo_calls_git(self, mock_system):
        """Test that git clone is called"""
        clone_ton_labels_repo()
        
        mock_system.assert_called_once()
        assert 'git clone' in mock_system.call_args[0][0]
        assert 'ton-labels' in mock_system.call_args[0][0]


class TestRmTonLabelsDir:
    """Test suite for rm_ton_labels_dir function"""

    @patch('parser.shutil.rmtree')
    def test_rm_ton_labels_dir_removes_directory(self, mock_rmtree):
        """Test that directory is removed"""
        rm_ton_labels_dir()
        
        mock_rmtree.assert_called_once()
        assert 'ton-labels' in mock_rmtree.call_args[0][0]


class TestGetTypesFromTonapi:
    """Test suite for get_types_from_tonapi function"""

    @patch('parser.requests.Session')
    def test_get_types_from_tonapi_success(self, mock_session_class):
        """Test successful type fetching"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'interfaces': ['jetton_master', 'wallet']
        }
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = get_types_from_tonapi('0:test_address')
        
        assert result == ['jetton_master', 'wallet']

    @patch('parser.requests.Session')
    def test_get_types_from_tonapi_404(self, mock_session_class):
        """Test handling of 404 response"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = get_types_from_tonapi('0:nonexistent')
        
        assert result == []

    @patch('parser.requests.Session')
    def test_get_types_from_tonapi_no_interfaces(self, mock_session_class):
        """Test handling of response without interfaces"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'other_field': 'value'}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        result = get_types_from_tonapi('0:test')
        
        assert result == []

    @patch('parser.requests.Session')
    def test_get_types_from_tonapi_retry_strategy(self, mock_session_class):
        """Test that retry strategy is configured"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # This will fail but we're testing the setup
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_session.get.return_value = mock_response
        
        get_types_from_tonapi('0:test')
        
        # Verify session was configured with adapter
        assert mock_session.mount.called

    @patch('parser.requests.Session')
    def test_get_types_from_tonapi_constructs_url(self, mock_session_class):
        """Test that URL is constructed correctly"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        address = '0:1234abcd'
        get_types_from_tonapi(address)
        
        call_args = mock_session.get.call_args[0][0]
        assert address in call_args
        assert 'tonapi.io' in call_args


class TestIsAssetToBlacklist:
    """Test suite for is_asset_to_blacklist function"""

    def test_is_asset_to_blacklist_single_jetton_type(self):
        """Test that single jetton type is blacklisted"""
        for jetton_type in BLACKLIST_JETTONS_TYPES:
            assert is_asset_to_blacklist([jetton_type]) is True

    def test_is_asset_to_blacklist_nft_types(self):
        """Test that NFT types are blacklisted"""
        for nft_type in BLACKLIST_NFT_TYPES:
            assert is_asset_to_blacklist([nft_type]) is True
            assert is_asset_to_blacklist(['other', nft_type]) is True

    def test_is_asset_to_blacklist_multiple_types_not_blacklisted(self):
        """Test that multiple types including jetton are not blacklisted"""
        types = ['jetton_master', 'wallet', 'other']
        assert is_asset_to_blacklist(types) is False

    def test_is_asset_to_blacklist_empty_list(self):
        """Test that empty list is not blacklisted"""
        assert is_asset_to_blacklist([]) is False

    def test_is_asset_to_blacklist_unknown_types(self):
        """Test that unknown types are not blacklisted"""
        assert is_asset_to_blacklist(['unknown_type']) is False
        assert is_asset_to_blacklist(['custom', 'other']) is False


class TestGetAssetFromJsonFile:
    """Test suite for get_asset_from_json_file function"""

    @patch('builtins.open', new_callable=MagicMock)
    @patch('parser.json.load')
    @patch('parser.normalize_address')
    @patch('parser.get_types_from_tonapi')
    def test_get_asset_from_json_file_whitelist(self, mock_get_types, mock_normalize,
                                                  mock_json_load, mock_open):
        """Test asset added to whitelist"""
        mock_json_load.return_value = {
            'metadata': {
                'label': 'Test Label',
                'category': 'DeFi',
                'website': 'https://test.com',
                'description': 'Test description'
            },
            'addresses': [
                {'address': '0:test'}
            ]
        }
        mock_normalize.return_value = '0:test_normalized'
        mock_get_types.return_value = ['wallet', 'other']
        
        result = get_asset_from_json_file('test.json', set())
        
        assert len(result['whitelist']) == 1
        assert len(result['blacklist']) == 0
        assert result['whitelist'][0].address == '0:test_normalized'

    @patch('builtins.open', new_callable=MagicMock)
    @patch('parser.json.load')
    @patch('parser.normalize_address')
    @patch('parser.get_types_from_tonapi')
    def test_get_asset_from_json_file_blacklist(self, mock_get_types, mock_normalize,
                                                  mock_json_load, mock_open):
        """Test asset added to blacklist"""
        mock_json_load.return_value = {
            'metadata': {
                'label': 'NFT',
                'category': 'NFT',
                'website': '',
                'description': ''
            },
            'addresses': [
                {'address': '0:nft'}
            ]
        }
        mock_normalize.return_value = '0:nft_normalized'
        mock_get_types.return_value = ['nft_collection']
        
        result = get_asset_from_json_file('test.json', set())
        
        assert len(result['whitelist']) == 0
        assert len(result['blacklist']) == 1

    @patch('builtins.open', new_callable=MagicMock)
    @patch('parser.json.load')
    @patch('parser.normalize_address')
    @patch('parser.get_types_from_tonapi')
    def test_get_asset_from_json_file_skips_address(self, mock_get_types, mock_normalize,
                                                      mock_json_load, mock_open):
        """Test that skip addresses are filtered"""
        mock_json_load.return_value = {
            'metadata': {
                'label': 'Skip',
                'category': 'Test',
                'website': '',
                'description': ''
            },
            'addresses': [
                {'address': '0:skip'}
            ]
        }
        mock_normalize.return_value = '0:skip_normalized'
        skip_set = {'0:skip_normalized'}
        
        result = get_asset_from_json_file('test.json', skip_set)
        
        assert len(result['whitelist']) == 0
        assert len(result['blacklist']) == 0

    @patch('builtins.open', new_callable=MagicMock)
    @patch('parser.json.load')
    @patch('parser.normalize_address')
    @patch('parser.get_types_from_tonapi')
    def test_get_asset_from_json_file_multiple_addresses(self, mock_get_types, mock_normalize,
                                                          mock_json_load, mock_open):
        """Test processing multiple addresses in one file"""
        mock_json_load.return_value = {
            'metadata': {
                'label': 'Multi',
                'category': 'Test',
                'website': '',
                'description': ''
            },
            'addresses': [
                {'address': '0:addr1'},
                {'address': '0:addr2'}
            ]
        }
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        mock_get_types.return_value = ['wallet']
        
        result = get_asset_from_json_file('test.json', set())
        
        assert len(result['whitelist']) == 2


class TestGetAssetsFromDir:
    """Test suite for get_assets_from_dir function"""

    @patch('parser.os.chdir')
    @patch('parser.os.listdir')
    @patch('parser.get_asset_from_json_file')
    def test_get_assets_from_dir_basic(self, mock_get_asset, mock_listdir, mock_chdir):
        """Test basic directory processing"""
        mock_listdir.return_value = ['asset1.json', 'asset2.json', 'readme.md']
        mock_get_asset.return_value = {
            'whitelist': [Mock()],
            'blacklist': []
        }
        
        result = get_assets_from_dir('test_dir', set())
        
        assert len(result['whitelist']) == 2  # 2 JSON files
        assert mock_get_asset.call_count == 2

    @patch('parser.os.chdir')
    @patch('parser.os.listdir')
    @patch('parser.get_asset_from_json_file')
    def test_get_assets_from_dir_skips_non_json(self, mock_get_asset, mock_listdir, mock_chdir):
        """Test that non-JSON files are skipped"""
        mock_listdir.return_value = ['test.json', 'readme.txt', 'image.png']
        mock_get_asset.return_value = {
            'whitelist': [],
            'blacklist': []
        }
        
        get_assets_from_dir('test_dir', set())
        
        mock_get_asset.assert_called_once_with('test.json', set())

    @patch('parser.os.chdir')
    @patch('parser.os.listdir')
    def test_get_assets_from_dir_returns_to_parent(self, mock_listdir, mock_chdir):
        """Test that function returns to parent directory"""
        mock_listdir.return_value = []
        
        get_assets_from_dir('test_dir', set())
        
        # Should cd into dir and then back
        assert mock_chdir.call_count >= 2


class TestGetAssetsFromDirs:
    """Test suite for get_assets_from_dirs function"""

    @patch('parser.os.chdir')
    @patch('parser.os.listdir')
    @patch('parser.os.path.isfile')
    @patch('parser.get_assets_from_dir')
    def test_get_assets_from_dirs_basic(self, mock_get_dir, mock_isfile,
                                         mock_listdir, mock_chdir):
        """Test processing multiple directories"""
        mock_listdir.return_value = ['dir1', 'dir2', 'file.txt']
        mock_isfile.side_effect = [False, False, True]  # 2 dirs, 1 file
        mock_get_dir.return_value = {
            'whitelist': [Mock()],
            'blacklist': []
        }
        
        result = get_assets_from_dirs(set())
        
        assert len(result['whitelist']) == 2
        assert mock_get_dir.call_count == 2

    @patch('parser.os.chdir')
    @patch('parser.os.listdir')
    @patch('parser.os.path.isfile')
    @patch('parser.get_assets_from_dir')
    def test_get_assets_from_dirs_skips_files(self, mock_get_dir, mock_isfile,
                                                mock_listdir, mock_chdir):
        """Test that files in assets dir are skipped"""
        mock_listdir.return_value = ['dir1', 'readme.md']
        mock_isfile.side_effect = [False, True]
        mock_get_dir.return_value = {'whitelist': [], 'blacklist': []}
        
        get_assets_from_dirs(set())
        
        mock_get_dir.assert_called_once()


class TestMain:
    """Test suite for main function"""

    @patch('parser.os.chdir')
    @patch('parser.clone_ton_labels_repo')
    @patch('parser.get_known_assets_addresses')
    @patch('parser.get_blacklist_addresses')
    @patch('parser.get_skip_addresses')
    @patch('parser.get_assets_from_dirs')
    @patch('parser.generate_to_review_html')
    @patch('parser.add_blacklist')
    @patch('parser.rm_ton_labels_dir')
    def test_main_success_flow(self, mock_rm, mock_add_blacklist, mock_gen_html,
                                 mock_get_dirs, mock_skip, mock_blacklist,
                                 mock_known, mock_clone, mock_chdir):
        """Test successful main execution"""
        mock_known.return_value = set()
        mock_blacklist.return_value = set()
        mock_skip.return_value = set()
        mock_get_dirs.return_value = {
            'whitelist': [Mock()],
            'blacklist': [Mock()]
        }
        
        main()
        
        mock_clone.assert_called_once()
        mock_gen_html.assert_called_once()
        mock_add_blacklist.assert_called_once()
        mock_rm.assert_called_once()

    @patch('parser.os.chdir')
    @patch('parser.clone_ton_labels_repo')
    @patch('parser.get_known_assets_addresses')
    @patch('parser.get_blacklist_addresses')
    @patch('parser.get_skip_addresses')
    @patch('parser.get_assets_from_dirs')
    @patch('parser.generate_to_review_html')
    @patch('parser.add_blacklist')
    @patch('parser.rm_ton_labels_dir')
    def test_main_cleanup_on_error(self, mock_rm, mock_add_blacklist, mock_gen_html,
                                     mock_get_dirs, mock_skip, mock_blacklist,
                                     mock_known, mock_clone, mock_chdir):
        """Test that cleanup happens even on error"""
        mock_known.return_value = set()
        mock_blacklist.return_value = set()
        mock_skip.return_value = set()
        mock_get_dirs.side_effect = Exception('Test error')
        
        with pytest.raises(Exception):
            main()
        
        # Cleanup should still be called
        mock_rm.assert_called_once()

    @patch('parser.os.chdir')
    @patch('parser.clone_ton_labels_repo')
    @patch('parser.get_known_assets_addresses')
    @patch('parser.get_blacklist_addresses')
    @patch('parser.get_skip_addresses')
    @patch('parser.get_assets_from_dirs')
    @patch('parser.generate_to_review_html')
    @patch('parser.add_blacklist')
    @patch('parser.rm_ton_labels_dir')
    def test_main_merges_address_sets(self, mock_rm, mock_add_blacklist, mock_gen_html,
                                        mock_get_dirs, mock_skip, mock_blacklist,
                                        mock_known, mock_clone, mock_chdir):
        """Test that all address sets are merged"""
        known = {'0:known'}
        blacklist = {'0:blacklist'}
        skip = {'0:skip'}
        
        mock_known.return_value = known
        mock_blacklist.return_value = blacklist
        mock_skip.return_value = skip
        mock_get_dirs.return_value = {'whitelist': [], 'blacklist': []}
        
        main()
        
        # All three sets should be merged and passed to get_assets_from_dirs
        call_args = mock_get_dirs.call_args[0][0]
        assert '0:known' in call_args
        assert '0:blacklist' in call_args
        assert '0:skip' in call_args


class TestConstants:
    """Test suite for module constants"""

    def test_blacklist_nft_types_defined(self):
        """Test that NFT blacklist types are defined"""
        assert isinstance(BLACKLIST_NFT_TYPES, list)
        assert len(BLACKLIST_NFT_TYPES) > 0
        assert 'nft_collection' in BLACKLIST_NFT_TYPES

    def test_blacklist_jettons_types_defined(self):
        """Test that Jetton blacklist types are defined"""
        assert isinstance(BLACKLIST_JETTONS_TYPES, list)
        assert len(BLACKLIST_JETTONS_TYPES) > 0
        assert 'jetton_master' in BLACKLIST_JETTONS_TYPES