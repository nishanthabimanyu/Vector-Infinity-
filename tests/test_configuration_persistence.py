"""
Test Configuration Persistence

Validates constraint serialization and file I/O.
"""

import sys
import json
from pathlib import Path
import logging

from constraints import ConstraintConstellation, ConstraintConjunction, ConstraintRetrograde
from config import ConfigurationManager, ConstraintSerializer

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def test_constraint_serialization():
    """Test individual constraint to_dict / from_dict."""
    print("="*80)
    print("TEST 1: Individual Constraint Serialization")
    print("="*80)
    
    # Test ConstraintConstellation
    c1 = ConstraintConstellation('mars_barycenter', 270.0, 300.0, sigma_deg=5.0)
    data1 = c1.to_dict()
    c1_restored = ConstraintConstellation.from_dict(data1)
    
    assert c1_restored.body == 'mars_barycenter'
    assert c1_restored.ra_min == 270.0
    assert c1_restored.ra_max == 300.0
    assert c1_restored.sigma == 5.0
    print(f"✅ ConstraintConstellation: {data1}")
    
    # Test ConstraintRetrograde
    c2 = ConstraintRetrograde('mars_barycenter')
    data2 = c2.to_dict()
    c2_restored = ConstraintRetrograde.from_dict(data2)
    
    assert c2_restored.body == 'mars_barycenter'
    print(f"✅ ConstraintRetrograde: {data2}")
    
    # Test ConstraintConjunction
    c3 = ConstraintConjunction('moon', 'jupiter', separation_deg=2.0)
    data3 = c3.to_dict()
    c3_restored = ConstraintConjunction.from_dict(data3)
    
    assert c3_restored.b1 == 'moon'
    assert c3_restored.b2 == 'jupiter'
    print(f"✅ ConstraintConjunction: {data3}")
    
    print("\n✅ All individual constraints pass round-trip serialization!\n")


def test_constraint_set_serialization():
    """Test full constraint set serialization."""
    print("="*80)
    print("TEST 2: Constraint Set Serialization")
    print("="*80)
    
    # Create a constraint set
    constraints = [
        ConstraintConstellation('mars_barycenter', 270.0, 300.0),
        ConstraintRetrograde('mars_barycenter')
    ]
    
    name = "Mars Retrograde in Sagittarius"
    description = "Find all Mars retrograde events in Sagittarius constellation"
    search_params = {
        'start_jd': 1348200.0,
        'end_jd': 2087200.0,
        'step_days': 5.0,
        'threshold': 0.8
    }
    
    # Serialize
    data = ConstraintSerializer.serialize_constraint_set(
        constraints=constraints,
        name=name,
        description=description,
        search_params=search_params
    )
    
    # Check structure
    assert data['version'] == '1.0'
    assert data['name'] == name
    assert data['description'] == description
    assert len(data['constraints']) == 2
    assert data['search_params'] == search_params
    
    print(f"✅ Serialized constraint set:\n{json.dumps(data, indent=2)}\n")
    
    # Deserialize
    constraints_restored, name_r, desc_r, params_r = (
        ConstraintSerializer.deserialize_constraint_set(data)
    )
    
    assert len(constraints_restored) == 2
    assert name_r == name
    assert desc_r == description
    assert params_r == search_params
    
    print(f"✅ Deserialized {len(constraints_restored)} constraints successfully!\n")


def test_file_persistence():
    """Test saving/loading from JSON files."""
    print("="*80)
    print("TEST 3: File Persistence")
    print("="*80)
    
    # Create a test config manager with temp directory
    test_dir = Path.home() / '.vector_infinity' / 'test_configs'
    manager = ConfigurationManager(config_dir=test_dir)
    
    print(f"Test config directory: {manager.config_dir}\n")
    
    # Create constraint set
    constraints = [
        ConstraintConstellation('mars_barycenter', 270.0, 300.0),
        ConstraintRetrograde('mars_barycenter')
    ]
    
    name = "Test Mars Retrograde"
    description = "Test configuration for Mars retrograde"
    search_params = {'start_jd': 1000000.0, 'end_jd': 2000000.0}
    
    # Save
    filepath = manager.save_constraint_set(
        name=name,
        constraints=constraints,
        description=description,
        search_params=search_params
    )
    
    print(f"✅ Saved to: {filepath}")
    assert filepath.exists()
    
    # Load
    constraints_loaded, name_l, desc_l, params_l = manager.load_constraint_set('test_mars_retrograde')
    
    assert len(constraints_loaded) == 2
    assert name_l == name
    assert desc_l == description
    assert params_l == search_params
    
    print(f"✅ Loaded '{name_l}' with {len(constraints_loaded)} constraints")
    
    # List
    saved = manager.list_saved_sets()
    assert len(saved) >= 1
    assert any(s['name'] == name for s in saved)
    
    print(f"✅ Found {len(saved)} saved configurations:")
    for cfg in saved:
        print(f"   - {cfg['name']} ({cfg['num_constraints']} constraints)")
    
    # Delete
    deleted = manager.delete_constraint_set('test_mars_retrograde')
    assert deleted
    assert not filepath.exists()
    
    print(f"✅ Deleted test configuration\n")


def test_special_characters():
    """Test filename sanitization."""
    print("="*80)
    print("TEST 4: Filename Sanitization")
    print("="*80)
    
    test_dir = Path.home() / '.vector_infinity' / 'test_configs'
    manager = ConfigurationManager(config_dir=test_dir)
    
    # Test special characters in name
    name = "Mars + Jupiter (2024) @ 15°!"
    constraints = [ConstraintConstellation('mars_barycenter', 0, 30)]
    
    filepath = manager.save_constraint_set(name, constraints)
    
    # Filename should be sanitized
    expected = 'mars_jupiter_2024_15.json'
    assert filepath.name == expected
    
    print(f"✅ '{name}' → '{filepath.name}'")
    
    # Clean up
    manager.delete_constraint_set(name)
    print()


def test_nonexistent_config():
    """Test loading non-existent configuration."""
    print("="*80)
    print("TEST 5: Error Handling")
    print("="*80)
    
    manager = ConfigurationManager()
    
    try:
        manager.load_constraint_set('this_does_not_exist')
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        print(f"✅ Correctly raised FileNotFoundError: {e}\n")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("CONFIGURATION PERSISTENCE TEST SUITE")
    print("="*80 + "\n")
    
    try:
        test_constraint_serialization()
        test_constraint_set_serialization()
        test_file_persistence()
        test_special_characters()
        test_nonexistent_config()
        
        print("="*80)
        print("ALL TESTS PASSED ✅")
        print("="*80)
        print("\nPhase 6 implementation complete!")
        print("Constraint sets can now be saved and loaded across sessions.\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
