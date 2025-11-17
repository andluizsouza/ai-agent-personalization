# OpenBreweryDB API Schema Documentation

**API Reference**: https://www.openbrewerydb.org/documentation

## Brewery Object Schema

Complete field specification for brewery data returned by OpenBreweryDB API.

### Available Fields

| Field Name | Type | Description | Nullable |
|------------|------|-------------|----------|
| `id` | string | Unique identifier for the brewery | No |
| `name` | string | Brewery name | No |
| `brewery_type` | string | Type of brewery (micro, brewpub, regional, large, planning, bar, contract, proprietor, closed) | No |
| `address_1` | string | Primary street address | Yes |
| `address_2` | string | Secondary address line (suite, apt, etc.) | Yes |
| `address_3` | string | Third address line | Yes |
| `city` | string | City name | No |
| `state_province` | string | State or province (full name) | No |
| `state` | string | State abbreviation or name | No |
| `postal_code` | string | Postal or ZIP code | No |
| `country` | string | Country name | No |
| `longitude` | number | Longitude coordinate (decimal degrees) | Yes |
| `latitude` | number | Latitude coordinate (decimal degrees) | Yes |
| `phone` | string | Contact phone number | Yes |
| `website_url` | string | Brewery website URL | Yes |
| `street` | string | Street address (alternative to address_1) | Yes |

### Brewery Types

The `brewery_type` field can have the following values:

- **micro**: Most craft breweries. Generally distributes within a limited area.
- **brewpub**: Brewery combined with a restaurant.
- **regional**: Regional craft brewery.
- **large**: A very large brewery. Think Budweiser, Coors, etc.
- **planning**: A brewery in planning or not yet opened.
- **bar**: A bar that brews beer.
- **contract**: A brewery that uses another brewery's equipment.
- **proprietor**: Smaller brewery contracted to a larger company.
- **closed**: A location that has been closed.

### API Endpoints

#### Search Breweries
```
GET https://api.openbrewerydb.org/v1/breweries
```

**Query Parameters:**

- `by_city` (string): Filter by city name (use underscores for spaces)
- `by_state` (string): Filter by state name (use underscores for spaces)
- `by_type` (string): Filter by brewery type
- `by_name` (string): Search by brewery name (partial match, use underscores for spaces)
- `by_postal` (string): Filter by postal code
- `per_page` (number): Number of results per page (default: 20, max: 50)
- `page` (number): Page number for pagination

**Example Requests:**

```bash
# Search by city
GET https://api.openbrewerydb.org/v1/breweries?by_city=san_diego

# Search by city and type
GET https://api.openbrewerydb.org/v1/breweries?by_city=san_diego&by_type=micro

# Search by name
GET https://api.openbrewerydb.org/v1/breweries?by_name=stone

# Multiple filters
GET https://api.openbrewerydb.org/v1/breweries?by_city=fort_collins&by_state=colorado&by_type=micro
```

### Response Format

The API returns a JSON array of brewery objects:

```json
[
  {
    "id": "5494",
    "name": "Odell Brewing Co",
    "brewery_type": "regional",
    "address_1": "800 E Lincoln Ave",
    "address_2": null,
    "address_3": null,
    "city": "Fort Collins",
    "state_province": "Colorado",
    "postal_code": "80524-2221",
    "country": "United States",
    "longitude": "-105.0594",
    "latitude": "40.5875",
    "phone": "9704989070",
    "website_url": "http://www.odellbrewing.com",
    "state": "Colorado",
    "street": "800 E Lincoln Ave"
  }
]
```

### Field Usage Guidelines

1. **Address Fields**: Use `address_1` + `address_2` + `address_3` for structured address, or `street` for simple address
2. **State Fields**: Both `state` and `state_province` may be present - `state` is abbreviated, `state_province` is full name
3. **Coordinates**: `latitude` and `longitude` are decimal degrees, suitable for mapping applications
4. **Null Values**: Many fields can be null - always check before using
5. **Phone Format**: Phone numbers may not be formatted consistently
6. **Website URLs**: May not include protocol - add "https://" if needed

### Error Handling

- **Empty Results**: API returns empty array `[]` if no breweries match criteria
- **Invalid Parameters**: API typically ignores invalid parameters rather than returning error
- **Rate Limiting**: No authentication required, reasonable rate limits apply
- **Timeout**: Recommend 10-second timeout for API calls

### Data Quality Notes

- Not all breweries have complete information (especially phone, website, address_2/3)
- Coordinates may be missing for some breweries
- Phone numbers are stored without formatting
- Website URLs may be outdated or invalid
- Some breweries may have type "closed" if no longer operating

### Tool 2 Integration

Tool 2 (BreweryFinder) can now provide any of these fields when answering questions about a brewery:

**Supported Queries:**
- "What's the phone number of [brewery]?"
- "What's the website of [brewery]?"
- "Where is [brewery] located?" (full address)
- "What are the coordinates of [brewery]?"
- "What type of brewery is [brewery]?"
- "Give me all information about [brewery]"

**Response Behavior:**
- If a field is null/missing in API, Tool 2 will communicate "Information unavailable"
- All available fields are returned in structured format
- Coordinates are provided in decimal degrees format suitable for maps
