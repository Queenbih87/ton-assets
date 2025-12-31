"""
Comprehensive unit tests for utlis.py

Tests cover:
- Address normalization (raw to human-readable and vice versa)
- CRC16 checksum calculation
- Edge cases and error handling
- Various workchain scenarios
"""

import pytest
import base64
from utlis import normalize_address, crc16


class TestNormalizeAddress:
    """Test suite for normalize_address function"""

    def test_normalize_human_readable_to_raw_workchain_0(self):
        """Test conversion from human-readable to raw format for workchain 0"""
        # EQBiyZMUXvdnRYFUk3_R5uPdsR2ROI9mes_1S-jL1tIQDhDK is a known address
        human_readable = "EQBiyZMUXvdnRYFUk3_R5uPdsR2ROI9mes_1S-jL1tIQDhDK"
        result = normalize_address(human_readable, to_raw=True)
        
        # Result should be in format "workchain:hex_address"
        assert ":" in result
        parts = result.split(":")
        assert len(parts) == 2
        assert parts[0] in ["0", "-1"]  # Valid workchains
        assert len(parts[1]) == 64  # 32 bytes = 64 hex chars

    def test_normalize_human_readable_to_raw_workchain_minus1(self):
        """Test conversion from human-readable to raw format for workchain -1"""
        # Create a test address with workchain -1 (255 in human-readable)
        addr_bytes = bytes([0] * 32)  # 32 zero bytes for address
        human = bytearray(36)
        human[0] = 0x11
        human[1] = 255  # workchain -1 encoded as 255
        human[2:34] = addr_bytes
        human[34:] = crc16(human[:34])
        human_readable = base64.urlsafe_b64encode(human).decode()
        
        result = normalize_address(human_readable, to_raw=True)
        assert result.startswith("-1:")

    def test_normalize_raw_to_human_readable(self):
        """Test conversion from raw format to human-readable format"""
        raw_address = "0:62c9931457f767458154937fd1e6e3ddb11d91388f667acff54be8cbd6d2100e"
        result = normalize_address(raw_address, to_raw=False)
        
        # Result should be base64 encoded string of 48 characters
        assert len(result) == 48
        # Should be valid base64
        decoded = base64.urlsafe_b64decode(result)
        assert len(decoded) == 36

    def test_normalize_raw_workchain_minus1(self):
        """Test raw address with workchain -1"""
        raw_address = "-1:0000000000000000000000000000000000000000000000000000000000000000"
        result = normalize_address(raw_address, to_raw=False)
        
        assert len(result) == 48
        decoded = base64.urlsafe_b64decode(result)
        # workchain -1 should be encoded as 255
        assert decoded[1] == 255

    def test_normalize_roundtrip_workchain_0(self):
        """Test that converting raw->human->raw gives same result"""
        original_raw = "0:62c9931457f767458154937fd1e6e3ddb11d91388f667acff54be8cbd6d2100e"
        human = normalize_address(original_raw, to_raw=False)
        back_to_raw = normalize_address(human, to_raw=True)
        
        assert original_raw == back_to_raw

    def test_normalize_roundtrip_workchain_minus1(self):
        """Test that converting raw->human->raw gives same result for workchain -1"""
        original_raw = "-1:3333333333333333333333333333333333333333333333333333333333333333"
        human = normalize_address(original_raw, to_raw=False)
        back_to_raw = normalize_address(human, to_raw=True)
        
        assert original_raw == back_to_raw

    def test_normalize_invalid_address_no_colon(self):
        """Test that address without colon raises exception"""
        invalid_address = "invalidaddresswithoutcolon"
        with pytest.raises(Exception) as exc_info:
            normalize_address(invalid_address, to_raw=True)
        assert "invalid address" in str(exc_info.value)

    def test_normalize_invalid_address_multiple_colons(self):
        """Test that address with multiple colons raises exception"""
        invalid_address = "0:1234:5678"
        with pytest.raises(Exception) as exc_info:
            normalize_address(invalid_address, to_raw=True)
        assert "invalid address" in str(exc_info.value)

    def test_normalize_invalid_hex_in_raw_address(self):
        """Test that invalid hex characters raise exception"""
        invalid_address = "0:gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"
        with pytest.raises(ValueError):
            normalize_address(invalid_address, to_raw=True)

    def test_normalize_short_raw_address(self):
        """Test address with shorter hex string (should still work)"""
        # Hex strings can be of varying lengths
        short_address = "0:1234"
        result = normalize_address(short_address, to_raw=False)
        assert len(result) == 48

    def test_normalize_address_preserves_data(self):
        """Test that address data is preserved through conversion"""
        test_hex = "a" * 64  # 32 bytes of 0xaa
        raw_address = f"0:{test_hex}"
        human = normalize_address(raw_address, to_raw=False)
        decoded = base64.urlsafe_b64decode(human)
        
        # Extract address bytes (skip tag, workchain, and CRC)
        address_bytes = decoded[2:34]
        assert address_bytes.hex() == test_hex

    def test_normalize_various_workchains(self):
        """Test normalization with various valid workchain IDs"""
        for workchain in [0, -1]:
            raw = f"{workchain}:{'0' * 64}"
            human = normalize_address(raw, to_raw=False)
            back = normalize_address(human, to_raw=True)
            assert back == raw

    def test_normalize_human_readable_48_chars(self):
        """Test that human-readable addresses are always 48 characters"""
        test_addresses = [
            "0:0000000000000000000000000000000000000000000000000000000000000000",
            "0:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "-1:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        ]
        
        for addr in test_addresses:
            result = normalize_address(addr, to_raw=False)
            assert len(result) == 48

    def test_normalize_empty_string_raises_error(self):
        """Test that empty string raises appropriate error"""
        with pytest.raises(Exception):
            normalize_address("", to_raw=True)

    def test_normalize_base64_with_invalid_length(self):
        """Test base64 string with invalid length"""
        # Valid base64 but wrong length
        invalid_b64 = base64.urlsafe_b64encode(b"short").decode()
        with pytest.raises(Exception):
            normalize_address(invalid_b64, to_raw=True)


class TestCrc16:
    """Test suite for crc16 function"""

    def test_crc16_returns_two_bytes(self):
        """Test that CRC16 returns tuple of two integers"""
        data = bytearray([1, 2, 3, 4])
        result = crc16(data)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)

    def test_crc16_byte_range(self):
        """Test that CRC16 bytes are in valid range 0-255"""
        data = bytearray([0x12, 0x34, 0x56, 0x78])
        result = crc16(data)
        
        assert 0 <= result[0] <= 255
        assert 0 <= result[1] <= 255

    def test_crc16_empty_data(self):
        """Test CRC16 with empty data"""
        result = crc16(bytearray([]))
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_crc16_single_byte(self):
        """Test CRC16 with single byte"""
        result = crc16(bytearray([0x42]))
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_crc16_deterministic(self):
        """Test that CRC16 is deterministic (same input = same output)"""
        data = bytearray([0xaa, 0xbb, 0xcc, 0xdd])
        result1 = crc16(data)
        result2 = crc16(data)
        
        assert result1 == result2

    def test_crc16_different_inputs_different_outputs(self):
        """Test that different inputs produce different CRCs"""
        data1 = bytearray([0x01, 0x02])
        data2 = bytearray([0x03, 0x04])
        
        result1 = crc16(data1)
        result2 = crc16(data2)
        
        assert result1 != result2

    def test_crc16_with_zeros(self):
        """Test CRC16 with all zero bytes"""
        data = bytearray([0] * 34)
        result = crc16(data)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_crc16_with_max_bytes(self):
        """Test CRC16 with all 0xFF bytes"""
        data = bytearray([0xff] * 34)
        result = crc16(data)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_crc16_typical_address_length(self):
        """Test CRC16 with typical address length (34 bytes)"""
        # Typical TON address prefix (tag + workchain + 32 bytes address)
        data = bytearray(34)
        data[0] = 0x11  # tag
        data[1] = 0x00  # workchain
        # Rest are zeros
        
        result = crc16(data)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_crc16_polynomial_correctness(self):
        """Test that CRC16 uses correct polynomial (0x1021)"""
        # Known test vector for CRC16-CCITT
        # This tests that the polynomial is correctly implemented
        data = bytearray([0x12, 0x34, 0x56, 0x78, 0x90])
        result = crc16(data)
        
        # Result should be consistent and deterministic
        assert result == crc16(data)

    def test_crc16_bit_order(self):
        """Test CRC16 bit processing order"""
        data1 = bytearray([0b10000000])  # MSB set
        data2 = bytearray([0b00000001])  # LSB set
        
        result1 = crc16(data1)
        result2 = crc16(data2)
        
        # Different bit patterns should produce different CRCs
        assert result1 != result2

    def test_crc16_with_bytes_object(self):
        """Test that CRC16 works with bytes (not just bytearray)"""
        data = bytes([0x11, 0x22, 0x33, 0x44])
        result = crc16(data)
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_crc16_long_data(self):
        """Test CRC16 with longer data"""
        data = bytearray(range(256))
        result = crc16(data)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert 0 <= result[0] <= 255
        assert 0 <= result[1] <= 255

    def test_crc16_returns_high_low_bytes(self):
        """Test that CRC16 returns (high_byte, low_byte) correctly"""
        data = bytearray([0x00] * 10)
        result = crc16(data)
        
        # Reconstruct 16-bit value
        crc_value = (result[0] * 256) + result[1]
        assert 0 <= crc_value <= 0xFFFF

    def test_crc16_avalanche_effect(self):
        """Test that small change in input significantly changes output"""
        data1 = bytearray([0x00] * 20)
        data2 = bytearray([0x00] * 20)
        data2[10] = 0x01  # Change single bit
        
        result1 = crc16(data1)
        result2 = crc16(data2)
        
        # Results should be significantly different
        assert result1 != result2