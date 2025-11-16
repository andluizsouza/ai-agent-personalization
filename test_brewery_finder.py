"""
Unit tests for Tool 2: Brewery Finder

Tests the OpenBreweryDB API integration, filtering logic, and error handling.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.brewery_finder import BreweryFinder, search_breweries_by_location_and_type


class TestBreweryFinder:
    """Test suite for Brewery Finder tool."""
    
    @pytest.fixture
    def finder(self):
        """Create a BreweryFinder instance for testing."""
        return BreweryFinder()
    
    def test_initialization(self, finder):
        """Test that Brewery Finder initializes correctly."""
        assert finder is not None
        assert finder.API_BASE_URL == "https://api.openbrewerydb.org/v1/breweries"
        assert finder.REQUEST_TIMEOUT == 10
        assert finder.MAX_RESULTS == 50
    
    def test_normalize_brewery_name(self, finder):
        """Test brewery name normalization."""
        assert finder._normalize_brewery_name("Stone Brewing") == "stone brewing"
        assert finder._normalize_brewery_name("  BALLAST POINT  ") == "ballast point"
        assert finder._normalize_brewery_name("Modern Times") == "modern times"
    
    def test_is_brewery_new_true(self, finder):
        """Test that new breweries are correctly identified."""
        history = ["Stone Brewing", "Ballast Point Brewing", "Modern Times Beer"]
        
        assert finder._is_brewery_new("AleSmith Brewing", history) is True
        assert finder._is_brewery_new("Green Flash Brewing", history) is True
    
    def test_is_brewery_new_false(self, finder):
        """Test that existing breweries are correctly identified."""
        history = ["Stone Brewing", "Ballast Point Brewing", "Modern Times Beer"]
        
        # Exact match
        assert finder._is_brewery_new("Stone Brewing", history) is False
        
        # Case insensitive match
        assert finder._is_brewery_new("STONE BREWING", history) is False
        assert finder._is_brewery_new("ballast point brewing", history) is False
        
        # With extra whitespace
        assert finder._is_brewery_new("  Modern Times Beer  ", history) is False
    
    def test_filter_new_breweries(self, finder):
        """Test filtering of brewery list."""
        breweries = [
            {"name": "Stone Brewing", "type": "micro"},
            {"name": "AleSmith Brewing", "type": "micro"},
            {"name": "Ballast Point Brewing", "type": "micro"},
            {"name": "Green Flash Brewing", "type": "micro"}
        ]
        
        history = ["Stone Brewing", "Ballast Point Brewing"]
        
        new_breweries = finder._filter_new_breweries(breweries, history)
        
        assert len(new_breweries) == 2
        assert new_breweries[0]["name"] == "AleSmith Brewing"
        assert new_breweries[1]["name"] == "Green Flash Brewing"
    
    def test_format_brewery_result(self, finder):
        """Test brewery result formatting."""
        raw_brewery = {
            "id": "stone-brewing-san-diego",
            "name": "Stone Brewing",
            "brewery_type": "micro",
            "street": "1999 Citracado Pkwy",
            "city": "Escondido",
            "state": "California",
            "postal_code": "92029",
            "country": "United States",
            "phone": "7604715755",
            "website_url": "https://www.stonebrewing.com",
            "latitude": "33.1433",
            "longitude": "-117.1711"
        }
        
        formatted = finder._format_brewery_result(raw_brewery)
        
        assert formatted["brewery_id"] == "stone-brewing-san-diego"
        assert formatted["brewery_name"] == "Stone Brewing"
        assert formatted["brewery_type"] == "micro"
        assert formatted["city"] == "Escondido"
        assert formatted["state"] == "California"
        assert formatted["website_url"] == "https://www.stonebrewing.com"
    
    def test_search_breweries_success(self, finder):
        """
        Test successful brewery search with real API call.
        This test makes an actual API call to OpenBreweryDB.
        """
        result = finder.search_breweries(
            city="San Diego",
            state="CA",
            brewery_type="micro",
            brewery_history=["Stone Brewing"]
        )
        
        # Check result structure
        assert "status" in result
        assert "metadata" in result
        
        # If API is working, we should get success or NO_NEW_BREWERIES
        # (NO_NEW_BREWERIES means all breweries in SD are in history, which is unlikely)
        assert result["status"] in ["success", "NO_NEW_BREWERIES", "NO_BREWERIES"]
        
        # Check metadata
        assert "timestamp" in result["metadata"]
        assert "execution_time" in result["metadata"]
        assert "search_params" in result["metadata"]
        
        # If success, check data structure
        if result["status"] == "success":
            assert "data" in result
            assert isinstance(result["data"], list)
            assert len(result["data"]) > 0
            
            # Check first brewery structure
            first_brewery = result["data"][0]
            assert "brewery_name" in first_brewery
            assert "brewery_type" in first_brewery
            assert "city" in first_brewery
            assert "website_url" in first_brewery
    
    def test_search_breweries_no_history(self, finder):
        """Test search without brewery history (should return all results)."""
        result = finder.search_breweries(
            city="Portland",
            state="OR",
            brewery_type="micro"
        )
        
        assert result["status"] in ["success", "NO_BREWERIES"]
        
        if result["status"] == "success":
            assert len(result["data"]) > 0
    
    def test_search_breweries_invalid_city(self, finder):
        """Test search with invalid/non-existent city."""
        result = finder.search_breweries(
            city="NonExistentCityXYZ123",
            state="XX",
            brewery_type="micro"
        )
        
        # Should return NO_BREWERIES
        assert result["status"] == "NO_BREWERIES"
        assert "message" in result
        assert "metadata" in result
    
    def test_search_breweries_all_in_history(self, finder):
        """Test scenario where all breweries are in history."""
        # First, get actual breweries from a small city
        result1 = finder.search_breweries(
            city="Bend",
            state="OR",
            brewery_type="micro"
        )
        
        # If we got results, use them as history
        if result1["status"] == "success" and len(result1["data"]) > 0:
            # Get all brewery names
            all_names = [b["brewery_name"] for b in result1["data"]]
            
            # Search again with all names in history
            result2 = finder.search_breweries(
                city="Bend",
                state="OR",
                brewery_type="micro",
                brewery_history=all_names
            )
            
            # Should return NO_NEW_BREWERIES
            assert result2["status"] == "NO_NEW_BREWERIES"
            assert "message" in result2
            assert result2["metadata"]["new_breweries"] == 0
    
    def test_convenience_function(self):
        """Test the convenience function."""
        result = search_breweries_by_location_and_type(
            city="Denver",
            state="CO",
            brewery_type="brewpub"
        )
        
        assert "status" in result
        assert "metadata" in result
        assert result["status"] in ["success", "NO_BREWERIES", "API_ERROR"]
    
    def test_metadata_completeness(self, finder):
        """Test that metadata includes all required fields."""
        result = finder.search_breweries(
            city="Austin",
            state="TX",
            brewery_type="micro",
            brewery_history=["Austin Beerworks"]
        )
        
        metadata = result["metadata"]
        
        # Check all required metadata fields
        assert "timestamp" in metadata
        assert "execution_time" in metadata
        assert "search_params" in metadata
        
        # Check search params
        params = metadata["search_params"]
        assert params["city"] == "Austin"
        assert params["state"] == "TX"
        assert params["brewery_type"] == "micro"
        
        # If success, check additional metadata
        if result["status"] == "success":
            assert "total_found" in metadata
            assert "new_breweries" in metadata
            assert "filtered_out" in metadata


if __name__ == "__main__":
    # Run tests with pytest
    print("\nRunning Brewery Finder Tests\n")
    pytest.main([__file__, "-v", "--tb=short"])
