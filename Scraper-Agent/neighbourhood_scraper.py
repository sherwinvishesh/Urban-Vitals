import argparse
import json
import requests
import re
import sys
import logging
from typing import List, Dict

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
TOOLHOUSE_API_URL = "https://agents.toolhouse.ai/c5498324-050e-4bd1-a4c1-dbe8e6271806"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

class NeighbourhoodScraper:
    def __init__(self):
        self.session = requests.Session()
        # Set headers once on the session for all subsequent requests
        self.session.headers.update({
            'User-Agent': 'GreenCityScraper/1.0 (https://example.com; contact@example.com)'
        })

    def _query_overpass(self, city: str, state: str) -> List[str]:
        """
        Primary method: Queries OpenStreetMap via Overpass API for neighborhoods.
        """
        logging.info(f"Querying Overpass API for neighborhoods in {city}, {state}.")
        
        area_query = f"""
        [out:json][timeout:25];
        area["name"="{city}"]["admin_level"="8"];
        out;
        """
        try:
            area_response = self.session.post(OVERPASS_API_URL, data=area_query)
            area_response.raise_for_status()
            area_data = area_response.json()
            
            if not area_data.get('elements'):
                logging.warning("Overpass could not find an administrative area for this city.")
                return []
            
            area_id = area_data['elements'][0]['id'] + 3600000000

            neighborhood_query = f"""
            [out:json][timeout:25];
            area({area_id})->.searchArea;
            (
              node["place"="neighbourhood"](area.searchArea);
              way["place"="neighbourhood"](area.searchArea);
              relation["place"="neighbourhood"](area.searchArea);
            );
            out;
            """
            response = self.session.post(OVERPASS_API_URL, data=neighborhood_query)
            response.raise_for_status()
            data = response.json()
            
            neighborhoods = [elem['tags']['name'] for elem in data.get('elements', []) if 'name' in elem.get('tags', {})]
            logging.info(f"Overpass API found {len(neighborhoods)} neighborhoods.")
            return neighborhoods
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Overpass API request failed: {e}")
            return []
        except (KeyError, IndexError):
            logging.error("Failed to parse Overpass API response for area ID.")
            return []

    def _get_from_toolhouse(self, city: str, state: str) -> List[str]:
        """
        Secondary method: Calls the Toolhouse API.
        This method is now tweaked to send the query exactly as requested.
        """
        logging.info(f"Querying Toolhouse API for {city}, {state}.")
        
        # This payload matches the required format: --json '{ "message": "City, State" }'
        payload = {"message": f"{city}, {state}"}
        
        try:
            # Use the class's session object for consistent headers and connection pooling.
            # The `json` parameter automatically serializes the payload and sets the
            # 'Content-Type' header to 'application/json'.
            response = self.session.post(TOOLHOUSE_API_URL, json=payload, timeout=60)
            response.raise_for_status()
            
            logging.info(f"Toolhouse API raw response: {response.text[:500]}...")
            
            data = response.json()
            neighborhoods = []
            
            if isinstance(data, dict):
                for key in ['neighborhoods', 'districts', 'areas', 'result', 'data', 'message', 'content']:
                    if key in data:
                        value = data[key]
                        if isinstance(value, list):
                            neighborhoods.extend([str(item) for item in value if item])
                        elif isinstance(value, str):
                            neighborhoods.extend(self._parse_neighborhoods_from_text(value))
            elif isinstance(data, list):
                neighborhoods = [str(item) for item in data if item]
            elif isinstance(data, str):
                neighborhoods = self._parse_neighborhoods_from_text(data)
                
            if neighborhoods:
                logging.info(f"Toolhouse API found {len(neighborhoods)} neighborhoods.")
                return neighborhoods
            else:
                logging.warning("Toolhouse API returned data but no neighborhoods could be extracted.")
                return []
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Toolhouse API request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse Toolhouse API JSON response: {e}")
            return []

    def _parse_neighborhoods_from_text(self, text: str) -> List[str]:
        """A simple helper to extract neighborhood names from a plain text string."""
        # Splits the string by commas, newlines, or semicolons.
        candidates = re.split(r'[,\n;]+', text)
        # Cleans up whitespace and removes any empty strings.
        return [name.strip() for name in candidates if name.strip()]

    def _get_from_fallback_list(self, city: str) -> List[str]:
        """Tertiary method: Uses a hardcoded list for common cities."""
        logging.info(f"Using curated fallback list for {city}.")
        fallback_data = {
            'tempe': ['Maple-Ash', 'Mitchell Park West', 'Kiwanis Park', 'Broadmor', 'Warner Ranch'],
            'phoenix': ['Arcadia', 'Biltmore', 'Camelback East', 'Central City', 'Deer Valley'],
            'boston': ['Back Bay', 'Beacon Hill', 'North End', 'South End', 'Cambridge', 'Charlestown'],
            'chicago': ['Loop', 'Lincoln Park', 'Wicker Park', 'River North', 'Gold Coast', 'Lakeview'],
        }
        return fallback_data.get(city.lower().replace(' ', ''), [])

    def scrape(self, city: str, state: str) -> List[Dict]:
        """
        Executes the scraping process using a robust fallback chain.
        """
        logging.info(f"--- Starting scrape for {city}, {state} ---")
        
        areas = self._query_overpass(city, state)
        
        if not areas:
            logging.warning("Overpass failed, trying Toolhouse API.")
            areas = self._get_from_toolhouse(city, state)

        if not areas:
            logging.warning("Toolhouse failed, trying curated fallback list.")
            areas = self._get_from_fallback_list(city)

        if not areas:
            logging.critical(f"All data sources failed for {city}, {state}. Cannot proceed.")
            return []

        unique_areas = sorted(list(set(
            area.strip().title() for area in areas if isinstance(area, str) and area.strip()
        )))
        
        logging.info(f"Found {len(unique_areas)} unique neighborhoods.")
        
        return [{"id": i, "neighbourhood_name": area} for i, area in enumerate(unique_areas, 1)]

def main():
    parser = argparse.ArgumentParser(
        description='Scrape neighbourhoods for a city using a robust, multi-source pipeline.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('city_state', help='City and state (e.g., "Boston, MA")')
    parser.add_argument('--output-file', required=True, help='Path to save the output JSON file.')
    args = parser.parse_args()
    
    try:
        city, state = [x.strip() for x in args.city_state.split(',')]
    except ValueError:
        logging.critical("Invalid format. Please use: 'City, State'")
        sys.exit(1)
        
    scraper = NeighbourhoodScraper()
    results = scraper.scrape(city, state)
    
    if not results:
        logging.error("Scraping returned no results. Exiting.")
        sys.exit(1)
        
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    logging.info(f"Successfully saved {len(results)} neighborhoods to {args.output_file}")

if __name__ == "__main__":
    main()
