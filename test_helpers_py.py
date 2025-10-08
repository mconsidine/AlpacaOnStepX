#!/usr/bin/env python3
"""Test helper functions"""

import sys
sys.path.insert(0, '..')

import alpaca_helpers as helpers

def test_coordinate_parsing():
    print("Testing coordinate parsing...")
    
    # Test RA parsing
    ra = helpers.parse_ra_to_hours("12:30:45")
    assert abs(ra - 12.5125) < 0.001, f"Expected 12.5125, got {ra}"
    print(f"  RA parse: {ra:.4f} hours ✓")
    
    # Test Dec parsing
    dec = helpers.parse_dec_to_degrees("+45:30:15")
    assert abs(dec - 45.504167) < 0.001, f"Expected 45.504167, got {dec}"
    print(f"  Dec parse: {dec:.4f} degrees ✓")
    
    # Test RA formatting
    ra_str = helpers.format_ra_hours(12.5125)
    print(f"  RA format: {ra_str} ✓")
    assert "12:" in ra_str
    
    # Test Dec formatting
    dec_str = helpers.format_dec_degrees(45.504167)
    print(f"  Dec format: {dec_str} ✓")
    assert "45:" in dec_str
    
    # Test negative Dec
    dec_str = helpers.format_dec_degrees(-30.5)
    assert dec_str.startswith('-'), "Negative Dec should start with -"
    print(f"  Negative Dec format: {dec_str} ✓")
    
    print("✓ Coordinate parsing OK\n")

def test_validation():
    print("Testing validation...")
    
    valid, msg = helpers.validate_range(50, 0, 100, "test")
    assert valid == True, "50 should be valid in range 0-100"
    print("  Range validation (valid value) ✓")
    
    valid, msg = helpers.validate_range(150, 0, 100, "test")
    assert valid == False, "150 should be invalid in range 0-100"
    assert msg is not None, "Error message should be provided"
    print(f"  Range rejection (invalid value) ✓: {msg}")
    
    valid, msg = helpers.validate_range(-10, 0, 100, "test")
    assert valid == False, "-10 should be invalid in range 0-100"
    print("  Range rejection (negative) ✓")
    
    print("✓ Validation OK\n")

def test_clamp():
    print("Testing clamp...")
    
    assert helpers.clamp(50, 0, 100) == 50, "50 should remain 50"
    print("  Clamp within range ✓")
    
    assert helpers.clamp(-10, 0, 100) == 0, "-10 should clamp to 0"
    print("  Clamp below minimum ✓")
    
    assert helpers.clamp(150, 0, 100) == 100, "150 should clamp to 100"
    print("  Clamp above maximum ✓")
    
    print("✓ Clamp OK\n")

def test_transaction_ids():
    print("Testing transaction IDs...")
    
    id1 = helpers.get_next_transaction_id()
    id2 = helpers.get_next_transaction_id()
    
    assert id2 > id1, "Transaction IDs should increment"
    print(f"  Transaction IDs increment: {id1} -> {id2} ✓")
    
    print("✓ Transaction IDs OK\n")

if __name__ == '__main__':
    test_coordinate_parsing()
    test_validation()
    test_clamp()
    test_transaction_ids()
    print("✅ Helper functions PASSED\n")
