"""
Test script for SQL Runner Tool (Tool 1)
Run this after installing dependencies and setting GOOGLE_API_KEY
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.sql_runner import get_client_profile

def test_sql_runner():
    """Run comprehensive tests for SQL Runner"""
    
    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not found in environment")
        print("Please set it with: export GOOGLE_API_KEY='your-api-key'")
        return False
    
    # Check if database exists
    if not Path("data/customers.db").exists():
        print("ERROR: data/customers.db not found")
        print("Please run: python create_database.py")
        return False
    
    # Get a sample client from database for testing
    import sqlite3
    conn = sqlite3.connect("data/customers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT client_id, client_name, postal_code FROM customers LIMIT 1")
    sample_row = cursor.fetchone()
    conn.close()
    
    if not sample_row:
        print("ERROR: No data in data/customers.db")
        print("Please run: python create_database.py")
        return False
    
    test_client_id = sample_row[0]
    test_client_name = sample_row[1]
    test_postal_code = sample_row[2]
    
    print("=" * 80)
    print(" Testing SQL Runner Tool (Tool 1)")
    print("=" * 80)
    print(f"\nUsing test data:")
    print(f"  Client ID: {test_client_id}")
    print(f"  Client Name: {test_client_name}")
    print(f"  Postal Code: {test_postal_code}")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Search by client_id
    print(f"\n[Test 1]  Search by client_id='{test_client_id}'")
    print("-" * 80)
    try:
        result = get_client_profile(client_id=test_client_id)
        
        if result["search_method"] == "client_id" and result["result"]:
            print("PASSED")
            print(f"   Found: {result['result']['client_name']}")
            print(f"   Location: {result['result']['client_location_city_state']}")
            print(f"   Execution time: {result['execution_time_ms']}ms")
            tests_passed += 1
        else:
            print("FAILED - Client not found")
            tests_failed += 1
    except Exception as e:
        print(f"FAILED - Error: {e}")
        tests_failed += 1
    
    # Test 2: Search by postal_code AND client_name (combined)
    test_name_partial = test_client_name.split()[0]
    print(f"\n[Test 2]  Search by postal_code='{test_postal_code}' AND client_name='{test_name_partial}'")
    print("-" * 80)
    try:
        result = get_client_profile(postal_code=test_postal_code, client_name=test_name_partial)
        
        if result["search_method"] == "postal_code_and_name" and result["result"]:
            print("PASSED")
            print(f"   Found: {result['result']['client_name']}")
            print(f"   Client ID: {result['result']['client_id']}")
            print(f"   Execution time: {result['execution_time_ms']}ms")
            tests_passed += 1
        else:
            print("FAILED - Client not found")
            tests_failed += 1
    except Exception as e:
        print(f"FAILED - Error: {e}")
        tests_failed += 1
    
    # Test 3: Search with only postal_code (should fail - needs both)
    print(f"\n[Test 3] Search by postal_code only (should NOT find - needs client_name too)")
    print("-" * 80)
    try:
        result = get_client_profile(postal_code=test_postal_code)
        
        if result["search_method"] == "not_found" and not result["result"]:
            print("PASSED")
            print(f"   Correctly returned 'not_found' (postal_code alone is insufficient)")
            print(f"   Execution time: {result['execution_time_ms']}ms")
            tests_passed += 1
        else:
            print("FAILED - Should have returned 'not_found'")
            tests_failed += 1
    except Exception as e:
        print(f"FAILED - Error: {e}")
        tests_failed += 1
    
    # Test 4: Fallback logic (invalid client_id → postal_code AND client_name)
    print("\n[Test 4]  Fallback test (invalid client_id → postal_code AND client_name)")
    print("-" * 80)
    try:
        result = get_client_profile(
            client_id="INVALID", 
            postal_code=test_postal_code, 
            client_name=test_name_partial
        )
        
        if result["search_method"] == "postal_code_and_name" and result["result"]:
            print("PASSED")
            print(f"   Fallback successful: Found via postal_code AND client_name")
            print(f"   Found: {result['result']['client_name']}")
            print(f"   Execution time: {result['execution_time_ms']}ms")
            tests_passed += 1
        else:
            print("FAILED - Fallback did not work")
            tests_failed += 1
    except Exception as e:
        print(f"FAILED - Error: {e}")
        tests_failed += 1
    
    # Test 5: Not found scenario
    print("\n[Test 5] Not found test (all invalid)")
    print("-" * 80)
    try:
        result = get_client_profile(
            client_id="INVALID",
            postal_code="00000",
            client_name="NonExistent"
        )
        
        if result["search_method"] == "not_found" and not result["result"]:
            print("PASSED")
            print(f"   Correctly returned 'not_found'")
            print(f"   Execution time: {result['execution_time_ms']}ms")
            tests_passed += 1
        else:
            print("FAILED - Should have returned 'not_found'")
            tests_failed += 1
    except Exception as e:
        print(f"FAILED - Error: {e}")
        tests_failed += 1
    
    # Test 6: Validate JSON parsing
    print("\n[Test 6]  JSON parsing validation")
    print("-" * 80)
    try:
        result = get_client_profile(client_id=test_client_id)
        
        if result["result"]:
            profile = result["result"]
            
            # Check if JSON fields are properly parsed as lists
            is_valid = (
                isinstance(profile.get("top3_brewery_types"), list) and
                isinstance(profile.get("top5_beers_recently"), list) and
                isinstance(profile.get("top3_breweries_recently"), list)
            )
            
            if is_valid:
                print("PASSED")
                print(f"   Top 3 brewery types: {profile['top3_brewery_types']}")
                print(f"   Number of beers: {len(profile['top5_beers_recently'])}")
                print(f"   Number of breweries in history: {len(profile['top3_breweries_recently'])}")
                tests_passed += 1
            else:
                print("FAILED - JSON fields not properly parsed as lists")
                tests_failed += 1
        else:
            print("FAILED - Could not retrieve profile")
            tests_failed += 1
    except Exception as e:
        print(f"FAILED - Error: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print(" Test Summary")
    print("=" * 80)
    print(f"Passed: {tests_passed}/6")
    print(f"Failed: {tests_failed}/6")
    
    if tests_failed == 0:
        print("\n All tests passed! SQL Runner is working correctly.")
        return True
    else:
        print(f"\n{tests_failed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = test_sql_runner()
    sys.exit(0 if success else 1)
