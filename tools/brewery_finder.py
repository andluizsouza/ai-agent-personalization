"""
Tool 2: Brewery Finder - OpenBreweryDB API Integration

This tool searches for breweries using the OpenBreweryDB API based on location and type,
filtering out breweries that the client has already purchased from (brewery_history).
It ensures recommendations are always novel and relevant to the client's preferences.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BreweryFinder:
    """
    Brewery Finder Tool for discovering new brewery opportunities.
    
    This tool integrates with OpenBreweryDB API to find breweries matching
    the client's location and preferred brewery types, while filtering out
    breweries from their purchase history.
    """
    
    # OpenBreweryDB API base URL (v1 API)
    API_BASE_URL = "https://api.openbrewerydb.org/v1/breweries"
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 10
    
    # Maximum number of results to fetch from API
    MAX_RESULTS = 50
    
    # State code to full name mapping (common US states)
    STATE_MAP = {
        "CA": "california", "NY": "new_york", "TX": "texas", "FL": "florida",
        "IL": "illinois", "PA": "pennsylvania", "OH": "ohio", "GA": "georgia",
        "NC": "north_carolina", "MI": "michigan", "NJ": "new_jersey",
        "VA": "virginia", "WA": "washington", "AZ": "arizona", "MA": "massachusetts",
        "TN": "tennessee", "IN": "indiana", "MO": "missouri", "MD": "maryland",
        "WI": "wisconsin", "CO": "colorado", "MN": "minnesota", "SC": "south_carolina",
        "AL": "alabama", "LA": "louisiana", "KY": "kentucky", "OR": "oregon",
        "OK": "oklahoma", "CT": "connecticut", "UT": "utah", "IA": "iowa",
        "NV": "nevada", "AR": "arkansas", "MS": "mississippi", "KS": "kansas",
        "NM": "new_mexico", "NE": "nebraska", "WV": "west_virginia", "ID": "idaho",
        "HI": "hawaii", "NH": "new_hampshire", "ME": "maine", "MT": "montana",
        "RI": "rhode_island", "DE": "delaware", "SD": "south_dakota",
        "ND": "north_dakota", "AK": "alaska", "VT": "vermont", "WY": "wyoming"
    }
    
    def __init__(self):
        """Initialize the Brewery Finder tool."""
        logger.info("Brewery Finder Tool initialized")
    
    def _normalize_brewery_name(self, name: str) -> str:
        """
        Normalize brewery name for comparison (lowercase, strip whitespace).
        
        Args:
            name: Brewery name to normalize
            
        Returns:
            Normalized brewery name
        """
        return name.lower().strip()
    
    def _is_brewery_new(self, brewery_name: str, brewery_history: List[str]) -> bool:
        """
        Check if a brewery is new (not in client's purchase history).
        
        Args:
            brewery_name: Name of the brewery to check
            brewery_history: List of brewery names from client's history
            
        Returns:
            True if brewery is new, False if already in history
        """
        normalized_name = self._normalize_brewery_name(brewery_name)
        normalized_history = [self._normalize_brewery_name(h) for h in brewery_history]
        
        return normalized_name not in normalized_history
    
    def _call_api(
        self,
        city: str,
        state: Optional[str] = None,
        brewery_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make API call to OpenBreweryDB.
        
        Args:
            city: City name to search
            state: Optional state/province code (e.g., 'CA', 'california')
            brewery_type: Optional brewery type filter
            
        Returns:
            Dictionary with 'status' and 'data' or 'error'
        """
        try:
            # Build query parameters
            params = {
                "by_city": city.lower().replace(" ", "_"),
                "per_page": self.MAX_RESULTS
            }
            
            if state:
                # Convert state code to full name if needed (e.g., CA -> california)
                state_upper = state.upper()
                if state_upper in self.STATE_MAP:
                    params["by_state"] = self.STATE_MAP[state_upper]
                else:
                    params["by_state"] = state.lower().replace(" ", "_")
            
            if brewery_type:
                params["by_type"] = brewery_type.lower()
            
            logger.info(f"Calling OpenBreweryDB API: {params}")
            
            # Make API request
            response = requests.get(
                self.API_BASE_URL,
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )
            
            # Check response status
            if response.status_code == 200:
                data = response.json()
                # API may return dict with message instead of list
                if isinstance(data, dict) and "message" in data:
                    # API returned a message (e.g., no results or API info)
                    logger.info(f"API returned message: {data['message']}")
                    return {"status": "success", "data": []}
                elif isinstance(data, list):
                    logger.info(f"API call successful: {len(data)} breweries found")
                    return {"status": "success", "data": data}
                else:
                    error_msg = f"Unexpected API response format: {type(data)}"
                    logger.error(f"{error_msg}")
                    return {"status": "API_ERROR", "error": error_msg}
            else:
                error_msg = f"API returned status code {response.status_code}"
                logger.error(f"{error_msg}")
                return {"status": "API_ERROR", "error": error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = f"API request timeout after {self.REQUEST_TIMEOUT}s"
            logger.error(f"{error_msg}")
            return {"status": "API_ERROR", "error": error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(f"{error_msg}")
            return {"status": "API_ERROR", "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{error_msg}")
            return {"status": "API_ERROR", "error": error_msg}
    
    def _filter_new_breweries(
        self,
        breweries: List[Dict[str, Any]],
        brewery_history: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter breweries to only include new ones (not in history).
        
        Args:
            breweries: List of brewery dictionaries from API
            brewery_history: List of brewery names from client's history
            
        Returns:
            Filtered list of new breweries
        """
        new_breweries = []
        
        for brewery in breweries:
            brewery_name = brewery.get("name", "")
            if brewery_name and self._is_brewery_new(brewery_name, brewery_history):
                new_breweries.append(brewery)
        
        logger.info(f"Filtered to {len(new_breweries)} new breweries (from {len(breweries)} total)")
        return new_breweries
    
    def _format_brewery_result(self, brewery: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format brewery data into a clean, structured result.
        
        Args:
            brewery: Raw brewery data from API
            
        Returns:
            Formatted brewery dictionary
        """
        return {
            "brewery_id": brewery.get("id", ""),
            "brewery_name": brewery.get("name", ""),
            "brewery_type": brewery.get("brewery_type", ""),
            "street": brewery.get("street", "") or brewery.get("address_1", ""),
            "city": brewery.get("city", ""),
            "state": brewery.get("state", "") or brewery.get("state_province", ""),
            "postal_code": brewery.get("postal_code", ""),
            "country": brewery.get("country", ""),
            "phone": brewery.get("phone", ""),
            "website_url": brewery.get("website_url", ""),
            "latitude": brewery.get("latitude", ""),
            "longitude": brewery.get("longitude", "")
        }
    
    def search_breweries(
        self,
        city: str,
        state: Optional[str] = None,
        brewery_type: Optional[str] = None,
        brewery_history: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for new breweries based on location and type preferences.
        
        This is the main entry point for the Brewery Finder tool.
        
        Args:
            city: City name to search (required)
            state: Optional state/province code (e.g., 'CA', 'OR')
            brewery_type: Optional brewery type (e.g., 'micro', 'brewpub', 'regional')
            brewery_history: List of brewery names the client has purchased from
            
        Returns:
            Dictionary with search results:
            - status: 'success', 'NO_BREWERIES', 'NO_NEW_BREWERIES', or 'API_ERROR'
            - data: List of brewery dictionaries (if success)
            - error: Error message (if error)
            - metadata: Search metadata (timestamp, filters, counts)
            
        Example:
            >>> finder = BreweryFinder()
            >>> result = finder.search_breweries(
            ...     city="San Diego",
            ...     state="CA",
            ...     brewery_type="micro",
            ...     brewery_history=["Stone Brewing", "Ballast Point"]
            ... )
            >>> if result['status'] == 'success':
            ...     print(f"Found {len(result['data'])} new breweries!")
        """
        start_time = time.time()
        
        if brewery_history is None:
            brewery_history = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BREWERY FINDER - Starting search")
        logger.info(f"   City: {city}")
        logger.info(f"   State: {state or 'Not specified'}")
        logger.info(f"   Type: {brewery_type or 'Any'}")
        logger.info(f"   History: {len(brewery_history)} breweries to exclude")
        logger.info(f"{'='*60}\n")
        
        # Step 1: Call OpenBreweryDB API
        api_result = self._call_api(city, state, brewery_type)
        
        if api_result["status"] != "success":
            execution_time = time.time() - start_time
            return {
                "status": "API_ERROR",
                "error": api_result.get("error", "Unknown API error"),
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": round(execution_time, 2),
                    "search_params": {
                        "city": city,
                        "state": state,
                        "brewery_type": brewery_type
                    }
                }
            }
        
        breweries = api_result["data"]
        
        # Step 2: Check if any breweries were found
        if not breweries:
            execution_time = time.time() - start_time
            logger.warning(f"NO_BREWERIES: No breweries found in {city}")
            return {
                "status": "NO_BREWERIES",
                "message": f"No breweries found in {city}" + (f", {state}" if state else ""),
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": round(execution_time, 2),
                    "total_found": 0,
                    "search_params": {
                        "city": city,
                        "state": state,
                        "brewery_type": brewery_type
                    }
                }
            }
        
        # Step 3: Filter out breweries from client's history
        new_breweries = self._filter_new_breweries(breweries, brewery_history)
        
        # Step 4: Check if any new breweries remain after filtering
        if not new_breweries:
            execution_time = time.time() - start_time
            logger.warning(f"NO_NEW_BREWERIES: All {len(breweries)} breweries already in history")
            return {
                "status": "NO_NEW_BREWERIES",
                "message": f"All breweries in {city} are already in purchase history",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": round(execution_time, 2),
                    "total_found": len(breweries),
                    "new_breweries": 0,
                    "search_params": {
                        "city": city,
                        "state": state,
                        "brewery_type": brewery_type
                    }
                }
            }
        
        # Step 5: Format and return results
        formatted_breweries = [self._format_brewery_result(b) for b in new_breweries]
        execution_time = time.time() - start_time
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BREWERY FINDER - Search completed successfully")
        logger.info(f"   Total found: {len(breweries)}")
        logger.info(f"   New breweries: {len(formatted_breweries)}")
        logger.info(f"   Execution time: {execution_time:.2f}s")
        logger.info(f"{'='*60}\n")
        
        return {
            "status": "success",
            "data": formatted_breweries,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "execution_time": round(execution_time, 2),
                "total_found": len(breweries),
                "new_breweries": len(formatted_breweries),
                "filtered_out": len(breweries) - len(formatted_breweries),
                "search_params": {
                    "city": city,
                    "state": state,
                    "brewery_type": brewery_type,
                    "history_size": len(brewery_history)
                }
            }
        }


# Convenience function for direct usage
def search_breweries_by_location_and_type(
    city: str,
    state: Optional[str] = None,
    brewery_type: Optional[str] = None,
    brewery_history: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to search for breweries.
    
    This is the function that will be registered as a LangChain tool.
    
    Args:
        city: City name to search
        state: Optional state code
        brewery_type: Optional brewery type filter
        brewery_history: List of brewery names to exclude
        
    Returns:
        Search results dictionary
        
    Example:
        >>> result = search_breweries_by_location_and_type(
        ...     city="San Diego",
        ...     brewery_type="micro",
        ...     brewery_history=["Stone Brewing"]
        ... )
    """
    finder = BreweryFinder()
    return finder.search_breweries(city, state, brewery_type, brewery_history)


if __name__ == "__main__":
    # Demo/test usage
    print("\nBrewery Finder Tool - Demo\n")
    
    # Example 1: Search with full parameters
    print("Example 1: Search for micro breweries in San Diego")
    result = search_breweries_by_location_and_type(
        city="San Diego",
        state="CA",
        brewery_type="micro",
        brewery_history=["Stone Brewing", "Ballast Point Brewing"]
    )
    
    if result["status"] == "success":
        print(f"Found {len(result['data'])} new breweries!")
        if result["data"]:
            print(f"\nFirst result: {result['data'][0]['brewery_name']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Message: {result.get('message', result.get('error', 'Unknown'))}")
    
    print(f"\nMetadata: {result['metadata']}")
