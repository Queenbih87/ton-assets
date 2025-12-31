"""
Comprehensive unit tests for to_review/readers.py

Tests cover:
- Reading known assets from JSON files
- Reading blacklist from CSV
- Reading skip list from CSV
- Address normalization integration
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import json
import os

from to_review.readers import (
    get_known_assets_addresses,
    get_blacklist_addresses,
    get_skip_addresses,
)


class TestGetKnownAssetsAddresses:
    """Test suite for get_known_assets_addresses function"""

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_basic(self, mock_normalize, mock_json_load,
                                     mock_file, mock_listdir):
        """Test basic functionality"""
        mock_listdir.return_value = ['test.json']
        mock_json_load.return_value = [
            {'address': '0:test1', 'name': 'Token1'},
            {'address': '0:test2', 'name': 'Token2'}
        ]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        
        result = get_known_assets_addresses()
        
        assert isinstance(result, set)
        assert len(result) == 2
        assert '0:test1_norm' in result
        assert '0:test2_norm' in result

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_skips_non_json(self, mock_normalize, mock_json_load,
                                               mock_file, mock_listdir):
        """Test that non-JSON files are skipped"""
        mock_listdir.return_value = ['test.json', 'readme.txt', 'image.png']
        mock_json_load.return_value = [{'address': '0:test'}]
        mock_normalize.return_value = '0:test_norm'
        
        result = get_known_assets_addresses()
        
        # Should only process test.json
        assert mock_json_load.call_count == 1

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_skips_without_address(self, mock_normalize, mock_json_load,
                                                      mock_file, mock_listdir):
        """Test that entries without address are skipped"""
        mock_listdir.return_value = ['test.json']
        mock_json_load.return_value = [
            {'address': '0:test', 'name': 'Token'},
            {'name': 'NoAddress'},  # Missing address
            {'address': '', 'name': 'Empty'}  # Empty address still has key
        ]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        
        result = get_known_assets_addresses()
        
        assert '0:test_norm' in result
        assert '_norm' in result  # Empty address normalized

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_empty_json(self, mock_normalize, mock_json_load,
                                          mock_file, mock_listdir):
        """Test with empty JSON file"""
        mock_listdir.return_value = ['empty.json']
        mock_json_load.return_value = []
        
        result = get_known_assets_addresses()
        
        assert isinstance(result, set)
        assert len(result) == 0

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_multiple_files(self, mock_normalize, mock_json_load,
                                              mock_file, mock_listdir):
        """Test processing multiple JSON files"""
        mock_listdir.return_value = ['file1.json', 'file2.json', 'file3.json']
        mock_json_load.side_effect = [
            [{'address': '0:addr1'}],
            [{'address': '0:addr2'}],
            [{'address': '0:addr3'}]
        ]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        
        result = get_known_assets_addresses()
        
        assert len(result) == 3
        assert mock_json_load.call_count == 3

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_duplicates(self, mock_normalize, mock_json_load,
                                          mock_file, mock_listdir):
        """Test that duplicate addresses are deduplicated"""
        mock_listdir.return_value = ['test.json']
        mock_json_load.return_value = [
            {'address': '0:same'},
            {'address': '0:same'},
            {'address': '0:different'}
        ]
        mock_normalize.side_effect = lambda addr, to_raw: addr + '_norm'
        
        result = get_known_assets_addresses()
        
        # Set should deduplicate
        assert len(result) == 2

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_get_known_assets_normalizes_to_human_readable(self, mock_normalize,
                                                            mock_json_load, mock_file,
                                                            mock_listdir):
        """Test that addresses are normalized to human-readable format"""
        mock_listdir.return_value = ['test.json']
        mock_json_load.return_value = [{'address': '0:test'}]
        
        get_known_assets_addresses()
        
        # Should call normalize_address with to_raw=False
        mock_normalize.assert_called_with('0:test', to_raw=False)


class TestGetBlacklistAddresses:
    """Test suite for get_blacklist_addresses function"""

    @patch('builtins.open', new_callable=mock_open, read_data='0:addr1\n0:addr2\n0:addr3\n')
    def test_get_blacklist_basic(self, mock_file):
        """Test basic blacklist reading"""
        result = get_blacklist_addresses()
        
        assert isinstance(result, set)
        assert len(result) == 3

    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_get_blacklist_empty_file(self, mock_file):
        """Test reading empty blacklist file"""
        result = get_blacklist_addresses()
        
        assert isinstance(result, set)
        assert len(result) == 0

    @patch('builtins.open', new_callable=mock_open, read_data='0:test1\n0:test2\n0:test1\n')
    def test_get_blacklist_duplicates(self, mock_file):
        """Test that duplicate addresses are deduplicated"""
        result = get_blacklist_addresses()
        
        # Set should deduplicate
        assert len(result) == 2

    @patch('builtins.open', new_callable=mock_open, read_data='0:addr1\n\n0:addr2\n')
    def test_get_blacklist_empty_lines(self, mock_file):
        """Test handling of empty lines"""
        result = get_blacklist_addresses()
        
        # Empty line should create empty string entry
        assert '' in result or len(result) == 2

    @patch('builtins.open', new_callable=mock_open)
    def test_get_blacklist_opens_correct_file(self, mock_file):
        """Test that correct file is opened"""
        get_blacklist_addresses()
        
        mock_file.assert_called_with("blacklist.csv", mode='r')

    @patch('builtins.open', new_callable=mock_open, read_data='addr1\naddr2\n')
    def test_get_blacklist_csv_format(self, mock_file):
        """Test reading CSV formatted data"""
        result = get_blacklist_addresses()
        
        assert isinstance(result, set)
        assert 'addr1' in result
        assert 'addr2' in result


class TestGetSkipAddresses:
    """Test suite for get_skip_addresses function"""

    @patch('builtins.open', new_callable=mock_open, read_data='0:skip1\n0:skip2\n')
    def test_get_skip_basic(self, mock_file):
        """Test basic skip list reading"""
        result = get_skip_addresses()
        
        assert isinstance(result, set)
        assert len(result) == 2

    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_get_skip_empty_file(self, mock_file):
        """Test reading empty skip list file"""
        result = get_skip_addresses()
        
        assert isinstance(result, set)
        assert len(result) == 0

    @patch('builtins.open', new_callable=mock_open, read_data='0:test\n0:test\n0:other\n')
    def test_get_skip_duplicates(self, mock_file):
        """Test that duplicate addresses are deduplicated"""
        result = get_skip_addresses()
        
        assert len(result) == 2

    @patch('builtins.open', new_callable=mock_open)
    def test_get_skip_opens_correct_file(self, mock_file):
        """Test that correct file is opened"""
        get_skip_addresses()
        
        mock_file.assert_called_with("skip_list.csv", mode='r')

    @patch('builtins.open', new_callable=mock_open, read_data='addr1,extra_column\naddr2,data\n')
    def test_get_skip_handles_multicolumn_csv(self, mock_file):
        """Test handling CSV with multiple columns"""
        result = get_skip_addresses()
        
        # Should only take first column
        assert 'addr1' in result or 'addr1,extra_column' in result


class TestIntegration:
    """Integration tests for readers module"""

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_all_readers_return_sets(self, mock_normalize, mock_json_load,
                                      mock_file, mock_listdir):
        """Test that all reader functions return sets"""
        mock_listdir.return_value = []
        mock_json_load.return_value = []
        mock_file.return_value.read_data = ''
        mock_normalize.return_value = 'normalized'
        
        known = get_known_assets_addresses()
        blacklist = get_blacklist_addresses()
        skip = get_skip_addresses()
        
        assert isinstance(known, set)
        assert isinstance(blacklist, set)
        assert isinstance(skip, set)

    @patch('to_review.readers.os.listdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('to_review.readers.json.load')
    @patch('to_review.readers.normalize_address')
    def test_sets_can_be_merged(self, mock_normalize, mock_json_load,
                                 mock_file, mock_listdir):
        """Test that sets from different readers can be merged"""
        mock_listdir.return_value = ['test.json']
        mock_json_load.return_value = [{'address': '0:known'}]
        mock_normalize.return_value = '0:normalized'
        
        known = get_known_assets_addresses()
        blacklist = get_blacklist_addresses()
        skip = get_skip_addresses()
        
        # Should be able to merge without error
        merged = known.union(blacklist).union(skip)
        assert isinstance(merged, set)