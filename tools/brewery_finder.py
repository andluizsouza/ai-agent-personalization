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
    
    def _simplify_brewery_name(self, name: str) -> str:
        """
        Simplify brewery name by removing common suffixes for better matching.
        Used for API searches to improve match rate.
        
        Args:
            name: Brewery name to simplify
            
        Returns:
            Simplified name with common suffixes removed
        """
        simplified = name.lower().strip()
        
        # Remove common brewery suffixes (in order of specificity)
        suffixes = [
            " brewing company",
            " brewing co",
            " brewery",
            " brewing", 
            " brewpub",
            " co"
        ]
        
        for suffix in suffixes:
            if simplified.endswith(suffix):
                simplified = simplified.replace(suffix, "").strip()
                break
        
        return simplified
    
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
        city: Optional[str] = None,
        state: Optional[str] = None,
        brewery_type: Optional[str] = None,
        brewery_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make API call to OpenBreweryDB.
        
        Args:
            city: City name to search (optional if brewery_name provided)
            state: Optional state/province code (e.g., 'CA', 'california')
            brewery_type: Optional brewery type filter
            brewery_name: Optional specific brewery name to search for
            
        Returns:
            Dictionary with 'status' and 'data' or 'error'
        """
        try:
            # Build query parameters
            params = {"per_page": self.MAX_RESULTS}
            
            # If searching by specific name, use by_name
            # Note: OpenBreweryDB API does substring search, so use main keywords only
            if brewery_name:
                # Simplify name (remove common suffixes) for better API matching
                search_name = self._simplify_brewery_name(brewery_name)
                # Replace spaces with underscores for API
                params["by_name"] = search_name.replace(" ", "_")
            
            if city:
                params["by_city"] = city.lower().replace(" ", "_")
            
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
        Format brewery data into a clean, structured result with ALL available fields.
        
        Args:
            brewery: Raw brewery data from API
            
        Returns:
            Formatted brewery dictionary with all API fields
        """
        return {
            # Core identification
            "brewery_id": brewery.get("id", ""),
            "brewery_name": brewery.get("name", ""),
            "brewery_type": brewery.get("brewery_type", ""),
            
            # Address information (structured)
            "address_1": brewery.get("address_1", None),
            "address_2": brewery.get("address_2", None),
            "address_3": brewery.get("address_3", None),
            "street": brewery.get("street", None),
            
            # Location
            "city": brewery.get("city", ""),
            "state": brewery.get("state", ""),
            "state_province": brewery.get("state_province", ""),
            "postal_code": brewery.get("postal_code", ""),
            "country": brewery.get("country", ""),
            
            # Coordinates
            "latitude": brewery.get("latitude", None),
            "longitude": brewery.get("longitude", None),
            
            # Contact information
            "phone": brewery.get("phone", None),
            "website_url": brewery.get("website_url", None)
        }
    
    def _format_brewery_info_response(self, brewery: Dict[str, Any], requested_info: str = "all") -> str:
        """
        Format brewery information into a human-readable response.
        
        Handles null/missing fields by indicating "Information unavailable".
        
        Args:
            brewery: Formatted brewery dictionary
            requested_info: Type of info requested (address, phone, website, coordinates, all)
            
        Returns:
            Formatted string response
        """
        name = brewery.get("brewery_name", "Unknown")
        
        if requested_info == "phone":
            phone = brewery.get("phone")
            if phone:
                return f"📞 {name}: {phone}"
            else:
                return f"❌ Phone number unavailable for {name}"
        
        elif requested_info == "website":
            website = brewery.get("website_url")
            if website:
                return f"🌐 {name}: {website}"
            else:
                return f"❌ Website unavailable for {name}"
        
        elif requested_info == "address":
            parts = []
            
            # Primary address
            if brewery.get("address_1"):
                parts.append(brewery["address_1"])
            elif brewery.get("street"):
                parts.append(brewery["street"])
            
            # Additional address lines
            if brewery.get("address_2"):
                parts.append(brewery["address_2"])
            if brewery.get("address_3"):
                parts.append(brewery["address_3"])
            
            # City, state, postal
            city = brewery.get("city", "")
            state = brewery.get("state", "") or brewery.get("state_province", "")
            postal = brewery.get("postal_code", "")
            country = brewery.get("country", "")
            
            if city or state:
                location = f"{city}, {state} {postal}".strip()
                parts.append(location)
            
            if country:
                parts.append(country)
            
            if parts:
                return f"📍 {name}:\n   " + "\n   ".join(parts)
            else:
                return f"❌ Address unavailable for {name}"
        
        elif requested_info == "coordinates":
            lat = brewery.get("latitude")
            lon = brewery.get("longitude")
            
            if lat and lon:
                return f"📍 {name}: ({lat}, {lon})"
            else:
                return f"❌ Coordinates unavailable for {name}"
        
        elif requested_info == "type":
            brewery_type = brewery.get("brewery_type", "")
            if brewery_type:
                return f"🍺 {name}: {brewery_type}"
            else:
                return f"❌ Brewery type unavailable for {name}"
        
        else:  # "all" or default
            lines = [f"🍺 {name}"]
            lines.append(f"   Type: {brewery.get('brewery_type', 'N/A')}")
            
            # Address
            if brewery.get("address_1") or brewery.get("street"):
                addr = brewery.get("address_1") or brewery.get("street")
                lines.append(f"   Address: {addr}")
                if brewery.get("address_2"):
                    lines.append(f"            {brewery['address_2']}")
            else:
                lines.append("   Address: Unavailable")
            
            # Location
            city = brewery.get("city", "N/A")
            state = brewery.get("state", "") or brewery.get("state_province", "N/A")
            postal = brewery.get("postal_code", "")
            lines.append(f"   Location: {city}, {state} {postal}")
            lines.append(f"   Country: {brewery.get('country', 'N/A')}")
            
            # Contact
            phone = brewery.get("phone", "Unavailable")
            website = brewery.get("website_url", "Unavailable")
            lines.append(f"   Phone: {phone}")
            lines.append(f"   Website: {website}")
            
            # Coordinates
            lat = brewery.get("latitude", "N/A")
            lon = brewery.get("longitude", "N/A")
            lines.append(f"   Coordinates: ({lat}, {lon})")
            
            return "\n".join(lines)
    
    def search_breweries(
        self,
        city: str = None,
        state: Optional[str] = None,
        brewery_type: Optional[str] = None,
        brewery_history: Optional[List[str]] = None,
        brewery_name: Optional[str] = None,
        filter_history: bool = True
    ) -> Dict[str, Any]:
        """
        Search for breweries based on location, type, or specific name.
        
        This is the main entry point for the Brewery Finder tool.
        
        Args:
            city: City name to search (optional if brewery_name provided)
            state: Optional state/province code (e.g., 'CA', 'OR')
            brewery_type: Optional brewery type (e.g., 'micro', 'brewpub', 'regional')
            brewery_history: List of brewery names the client has purchased from
            brewery_name: Optional specific brewery name to search for
            filter_history: Whether to filter out breweries from history (default: True)
            
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
        logger.info(f"   Brewery Name: {brewery_name or 'Not specified'}")
        logger.info(f"   City: {city or 'Not specified'}")
        logger.info(f"   State: {state or 'Not specified'}")
        logger.info(f"   Type: {brewery_type or 'Any'}")
        logger.info(f"   Filter History: {filter_history}")
        logger.info(f"   History: {len(brewery_history)} breweries to exclude" if filter_history else "   History: Not filtering")
        logger.info(f"{'='*60}\n")
        
        # Step 1: Call OpenBreweryDB API
        api_result = self._call_api(city, state, brewery_type, brewery_name)
        
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
            search_location = brewery_name if brewery_name else (city or "specified location")
            logger.warning(f"NO_BREWERIES: No breweries found for {search_location}")
            return {
                "status": "NO_BREWERIES",
                "message": f"No breweries found for '{search_location}'",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": round(execution_time, 2),
                    "total_found": 0,
                    "search_params": {
                        "city": city,
                        "state": state,
                        "brewery_type": brewery_type,
                        "brewery_name": brewery_name
                    }
                }
            }
        
        # Step 2.5: If searching by specific name, try to find best match
        if brewery_name:
            # Simplify the search term for comparison
            simplified_search = self._simplify_brewery_name(brewery_name)
            best_matches = []
            
            for brewery in breweries:
                brewery_name_from_api = brewery.get("name", "")
                simplified_api_name = self._simplify_brewery_name(brewery_name_from_api)
                
                # Check if simplified names match or if search term is in the brewery name
                if (simplified_search in simplified_api_name or 
                    simplified_api_name in simplified_search or
                    simplified_search == simplified_api_name):
                    best_matches.append(brewery)
            
            # If we found good matches, use only those
            if best_matches:
                breweries = best_matches
                logger.info(f"Filtered to {len(best_matches)} best matches for '{brewery_name}'")
        
        # Step 3: Filter out breweries from client's history (ONLY if filter_history is True)
        if filter_history:
            new_breweries = self._filter_new_breweries(breweries, brewery_history)
            
            # Step 4: Check if any new breweries remain after filtering
            if not new_breweries:
                execution_time = time.time() - start_time
                logger.warning(f"NO_NEW_BREWERIES: All {len(breweries)} breweries already in history")
                return {
                    "status": "NO_NEW_BREWERIES",
                    "message": f"All breweries found are already in purchase history",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "execution_time": round(execution_time, 2),
                        "total_found": len(breweries),
                        "new_breweries": 0,
                        "search_params": {
                            "city": city,
                            "state": state,
                            "brewery_type": brewery_type,
                            "brewery_name": brewery_name
                        }
                    }
                }
        else:
            # No filtering - return all results
            new_breweries = breweries
            logger.info(f"Filtering disabled - returning all {len(breweries)} results")
        
        # Step 5: Format and return results
        formatted_breweries = [self._format_brewery_result(b) for b in new_breweries]
        execution_time = time.time() - start_time
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BREWERY FINDER - Search completed successfully")
        logger.info(f"   Total found: {len(breweries)}")
        logger.info(f"   Returned: {len(formatted_breweries)}")
        logger.info(f"   Filtered: {filter_history}")
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
    city: Optional[str] = None,
    state: Optional[str] = None,
    brewery_type: Optional[str] = None,
    brewery_history: Optional[List[str]] = None,
    brewery_name: Optional[str] = None,
    filter_history: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to search for breweries.
    
    This is the function that will be registered as a LangChain tool.
    
    Args:
        city: City name to search (optional if brewery_name provided)
        state: Optional state code
        brewery_type: Optional brewery type filter
        brewery_history: List of brewery names to exclude (only used if filter_history=True)
        brewery_name: Specific brewery name to search for
        filter_history: Whether to filter out breweries from history (default: True)
        
    Returns:
        Search results dictionary
        
    Examples:
        >>> # Search for NEW breweries (with filtering)
        >>> result = search_breweries_by_location_and_type(
        ...     city="San Diego",
        ...     brewery_type="micro",
        ...     brewery_history=["Stone Brewing"],
        ...     filter_history=True
        ... )
        
        >>> # Search for SPECIFIC brewery (no filtering)
        >>> result = search_breweries_by_location_and_type(
        ...     brewery_name="Odell Brewing",
        ...     filter_history=False
        ... )
    """
    finder = BreweryFinder()
    return finder.search_breweries(city, state, brewery_type, brewery_history, brewery_name, filter_history)


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
