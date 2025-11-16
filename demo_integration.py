"""
Integration Example: Tool 1 (SQL Runner) + Tool 2 (Brewery Finder)

This script demonstrates how the two tools work together to provide
personalized brewery recommendations based on client profile data.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools import get_client_profile, search_breweries_by_location_and_type


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main():
    """Run the integration demo."""
    print("\n🍺 BEES AI - Tool Integration Demo")
    print("   Tool 1 (SQL Runner) + Tool 2 (Brewery Finder)")
    
    # Step 1: Get client profile from database
    print_section("STEP 1: Get Client Profile (Tool 1)")
    
    # First, we need to get a real client_id from the database
    # Let's query the database directly to get the first client
    import sqlite3
    db_path = Path(__file__).parent / "data" / "customers.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, client_name FROM customers LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print("❌ Error: No clients found in database")
            print("   Please run create_database.py first to populate the database")
            return
        
        client_id = result[0]
        print(f"🔍 Found client in database: {result[1]} ({client_id})")
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        print("   Please ensure customers.db exists in the data/ directory")
        return
    
    print(f"🔍 Fetching full profile for client: {client_id}")
    
    # Get full profile using Tool 1
    profile_result = get_client_profile(client_id=client_id)
    
    # Check if client was found
    if profile_result["search_method"] == "not_found" or not profile_result["result"]:
        print(f"❌ Error: Client not found in database")
        return
    
    profile = profile_result["result"]
    
    print(f"✅ Client Found!")
    print(f"   Name: {profile['client_name']}")
    print(f"   Location: {profile['client_city']}, {profile['client_state']}")
    print(f"   Postal Code: {profile['postal_code']}")
    print(f"\n📊 Preferences:")
    print(f"   Top 3 Brewery Types: {', '.join(profile['top3_brewery_types'])}")
    print(f"   Top 5 Recent Beers:")
    for i, beer in enumerate(profile['top5_beers_recently'], 1):
        print(f"      {i}. {beer}")
    print(f"   Recent Breweries:")
    for brewery in profile['top3_breweries_recently']:
        print(f"      • {brewery}")
    
    # Step 2: Search for new breweries
    print_section("STEP 2: Search New Breweries (Tool 2)")
    
    print(f"🔍 Searching for {profile['top3_brewery_types'][0]} breweries in {profile['client_city']}, {profile['client_state']}")
    print(f"   Excluding breweries from purchase history...")
    
    brewery_result = search_breweries_by_location_and_type(
        city=profile['client_city'],
        state=profile['client_state'],
        brewery_type=profile['top3_brewery_types'][0],  # Use client's favorite type
        brewery_history=profile['top3_breweries_recently']
    )
    
    # Step 3: Present results
    print_section("STEP 3: Recommendations")
    
    if brewery_result["status"] == "success":
        breweries = brewery_result["data"]
        metadata = brewery_result["metadata"]
        
        print(f"✅ Found {len(breweries)} new brewery recommendations!")
        print(f"   Total breweries found: {metadata['total_found']}")
        print(f"   Filtered out (already in history): {metadata['filtered_out']}")
        print(f"   Execution time: {metadata['execution_time']}s")
        
        if breweries:
            print(f"\n🎯 Top 3 Recommendations:")
            for i, brewery in enumerate(breweries[:3], 1):
                print(f"\n   {i}. {brewery['brewery_name']}")
                print(f"      Type: {brewery['brewery_type']}")
                print(f"      Address: {brewery['street']}, {brewery['city']}, {brewery['state']} {brewery['postal_code']}")
                if brewery['phone']:
                    print(f"      Phone: {brewery['phone']}")
                if brewery['website_url']:
                    print(f"      Website: {brewery['website_url']}")
    
    elif brewery_result["status"] == "NO_BREWERIES":
        print(f"⚠️ {brewery_result['message']}")
        print("   Recommendation: Try expanding search to nearby cities or different brewery types.")
    
    elif brewery_result["status"] == "NO_NEW_BREWERIES":
        print(f"⚠️ {brewery_result['message']}")
        print(f"   This client already knows all {brewery_result['metadata']['total_found']} local breweries!")
        print("   Recommendation: Consider expanding to nearby cities or different types.")
    
    else:  # API_ERROR
        print(f"❌ API Error: {brewery_result.get('error', 'Unknown error')}")
        print("   Recommendation: Check internet connection and try again.")
    
    # Step 4: Summary
    print_section("STEP 4: Summary")
    
    print("📋 Agent Workflow Completed:")
    print(f"   1. ✅ Retrieved client profile from database")
    print(f"   2. ✅ Searched OpenBreweryDB API with filters")
    print(f"   3. ✅ Filtered out {len(profile['top3_breweries_recently'])} known breweries")
    if brewery_result["status"] == "success":
        print(f"   4. ✅ Generated {len(brewery_result['data'])} personalized recommendations")
    else:
        print(f"   4. ⚠️ No new recommendations available")
    
    print(f"\n💡 Next Steps:")
    print(f"   • Implement Tool 3 (Web Explorer) to get brewery details")
    print(f"   • Create Planner Agent to orchestrate all 3 tools")
    print(f"   • Add conditional logic (ask user if they want details)")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
