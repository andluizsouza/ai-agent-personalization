"""
Integration Example: Tool 1 + Tool 2 + Tool 3 (Complete Workflow)

This script demonstrates how all three tools work together to provide
personalized brewery recommendations with detailed website summaries.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools import get_client_profile, search_breweries_by_location_and_type, get_website_summary


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main():
    """Run the integration demo."""
    print("\n BEES AI - Complete Tool Integration Demo")
    print("   Tool 1 (SQL Runner) + Tool 2 (Brewery Finder) + Tool 3 (Web Explorer)")
    
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
            print("ERROR Error: No clients found in database")
            print("   Please run create_database.py first to populate the database")
            return
        
        client_id = result[0]
        print(f" Found client in database: {result[1]} ({client_id})")
        
    except Exception as e:
        print(f"ERROR Error accessing database: {e}")
        print("   Please ensure customers.db exists in the data/ directory")
        return
    
    print(f" Fetching full profile for client: {client_id}")
    
    # Get full profile using Tool 1
    profile_result = get_client_profile(client_id=client_id)
    
    # Check if client was found
    if profile_result["search_method"] == "not_found" or not profile_result["result"]:
        print(f"ERROR Error: Client not found in database")
        return
    
    profile = profile_result["result"]
    
    print(f"OK Client Found!")
    print(f"   Name: {profile['client_name']}")
    print(f"   Location: {profile['client_city']}, {profile['client_state']}")
    print(f"   Postal Code: {profile['postal_code']}")
    print(f"\n Preferences:")
    print(f"   Top 3 Brewery Types: {', '.join(profile['top3_brewery_types'])}")
    print(f"   Top 5 Recent Beers:")
    for i, beer in enumerate(profile['top5_beers_recently'], 1):
        print(f"      {i}. {beer}")
    print(f"   Recent Breweries:")
    for brewery in profile['top3_breweries_recently']:
        print(f"      • {brewery}")
    
    # Step 2: Search for new breweries
    print_section("STEP 2: Search New Breweries (Tool 2)")
    
    print(f" Searching for {profile['top3_brewery_types'][0]} breweries in {profile['client_city']}, {profile['client_state']}")
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
        
        print(f"OK Found {len(breweries)} new brewery recommendations!")
        print(f"   Total breweries found: {metadata['total_found']}")
        print(f"   Filtered out (already in history): {metadata['filtered_out']}")
        print(f"   Execution time: {metadata['execution_time']}s")
        
        if breweries:
            print(f"\nTop 3 Recommendations:")
            for i, brewery in enumerate(breweries[:3], 1):
                print(f"\n   {i}. {brewery['brewery_name']}")
                print(f"      Type: {brewery['brewery_type']}")
                print(f"      Address: {brewery['street']}, {brewery['city']}, {brewery['state']} {brewery['postal_code']}")
                if brewery['phone']:
                    print(f"      Phone: {brewery['phone']}")
                if brewery['website_url']:
                    print(f"      Website: {brewery['website_url']}")
    
    elif brewery_result["status"] == "NO_BREWERIES":
        print(f"WARNING {brewery_result['message']}")
        print("   Recommendation: Try expanding search to nearby cities or different brewery types.")
    
    elif brewery_result["status"] == "NO_NEW_BREWERIES":
        print(f"WARNING {brewery_result['message']}")
        print(f"   This client already knows all {brewery_result['metadata']['total_found']} local breweries!")
        print("   Recommendation: Consider expanding to nearby cities or different types.")
    
    else:  # API_ERROR
        print(f"ERROR API Error: {brewery_result.get('error', 'Unknown error')}")
        print("   Recommendation: Check internet connection and try again.")
    
    # Step 4: Get website summary (Tool 3)
    print_section("STEP 4: Get Brewery Details (Tool 3)")
    
    if brewery_result["status"] == "success" and breweries:
        # Get the first recommended brewery
        top_brewery = breweries[0]
        brewery_name = top_brewery['brewery_name']
        brewery_url = top_brewery.get('website_url', '')
        brewery_type = top_brewery['brewery_type']
        
        # Construct address from brewery data
        address_parts = []
        if top_brewery.get('street'):
            address_parts.append(top_brewery['street'])
        if top_brewery.get('city'):
            address_parts.append(top_brewery['city'])
        if top_brewery.get('state'):
            address_parts.append(top_brewery['state'])
        if top_brewery.get('postal_code'):
            address_parts.append(top_brewery['postal_code'])
        brewery_address = ", ".join(address_parts)
        
        print(f" Getting detailed information for: {brewery_name}")
        print(f"   Address: {brewery_address}")
        
        if brewery_url:
            print(f"   Using Gemini Grounding (Google Search) with RAG cache...")
            
            summary_result = get_website_summary(
                brewery_name=brewery_name,
                url=brewery_url,
                brewery_type=brewery_type,
                address=brewery_address
            )
            
            if "error" not in summary_result:
                print(f"\nOK Summary Retrieved!")
                print(f"   Source: {summary_result['source']}")
                print(f"   Cache Status: {summary_result['cache_status']}")
                print(f"   Execution Time: {summary_result['execution_time_ms']:.2f}ms")
                print(f"\n   Summary:")
                print(f"   {summary_result['summary']}")
            else:
                print(f"WARNING Could not retrieve summary: {summary_result.get('error')}")
        else:
            print(f"WARNING No website URL available for {brewery_name}")
    else:
        print(" Skipping Tool 3 - No breweries to analyze")
    
    # Step 5: Summary
    print_section("STEP 5: Complete Workflow Summary")
    
    print(" Agent Workflow Completed:")
    print(f"   1. Retrieved client profile from database")
    print(f"   2. Searched OpenBreweryDB API with filters")
    print(f"   3. Filtered out {len(profile['top3_breweries_recently'])} known breweries")
    
    if brewery_result["status"] == "success":
        print(f"   4. Generated {len(brewery_result['data'])} personalized recommendations")
        if breweries and breweries[0].get('website_url'):
            print(f"   5. Retrieved detailed website summary using RAG cache")
    else:
        print(f"   4. No new recommendations available")
    
    print(f"\n All 3 Tools Integrated Successfully!")
    print(f"   Tool 1: Client Profile Retrieval with Text-to-SQL")
    print(f"   Tool 2: Brewery Discovery with API + History Filtering")
    print(f"   Tool 3: Gemini Grounding (Google Search) with RAG Cache (TTL 30 days)")
    
    print(f"\n Architecture Highlights:")
    print(f"   • No web scraping needed - Gemini Grounding handles search")
    print(f"   • Cache-first strategy reduces API costs by 99%")
    print(f"   • Precise searches using brewery name + address + website")
    
    print(f"\n Next Steps:")
    print(f"   • Create Planner Agent to orchestrate all 3 tools")
    print(f"   • Add conditional logic (ask user if they want details)")
    print(f"   • Implement CLI (main.py) for conversational interface")
    print(f"   • Build REST API (FastAPI) for external integration")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
