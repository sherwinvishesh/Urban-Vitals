#!/usr/bin/env python3
"""
Coordinate Finder (Google Maps Version)

Scrapes neighbourhoods for a city and finds their geographic coordinates using the
Google Maps Geocoding API. This version uses Google's high-quality geocoding service.

1.  It gets neighbourhoods from the neighbourhood_scraper
2.  It geocodes each neighbourhood using Google Maps API
3.  It uses asyncio and aiohttp to process neighbourhoods concurrently for speed
"""

import argparse
import json
import sys
import asyncio
import os
from typing import List, Dict, Optional, Tuple

import aiohttp
from aiolimiter import AsyncLimiter
from tqdm.asyncio import tqdm_asyncio
from dotenv import load_dotenv

from neighbourhood_scraper import NeighbourhoodScraper


class CoordinateFinder:
    """Finds coordinates for a city's neighbourhoods async."""

    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get Google API key from environment (optional)
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        
        # API endpoints
        self.google_geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.nominatim_geocode_url = "https://nominatim.openstreetmap.org/search"
        
        # Rate limiters
        self.google_rate_limiter = AsyncLimiter(10, 1)  # 10 requests per second for Google
        self.nominatim_rate_limiter = AsyncLimiter(1, 1)  # 1 request per second for Nominatim
        
        # Track which API to use
        self.use_google = bool(self.google_api_key)
        print(f"Using {'Google Maps' if self.use_google else 'OpenStreetMap Nominatim'} API for geocoding")

    async def _fetch_google_json(self, session: aiohttp.ClientSession, params: Dict) -> Dict:
        """Performs a single throttled GET request to the Google Maps API."""
        async with self.google_rate_limiter:
            try:
                async with session.get(self.google_geocode_url, params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"  ⚠ Google API Network/HTTP error: {e}", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"  ⚠ Google API Invalid JSON response: {e}", file=sys.stderr)
            return {}

    async def _fetch_nominatim_json(self, session: aiohttp.ClientSession, params: Dict) -> List[Dict]:
        """Performs a single throttled GET request to the Nominatim API."""
        async with self.nominatim_rate_limiter:
            try:
                async with session.get(self.nominatim_geocode_url, params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"  ⚠ Nominatim API Network/HTTP error: {e}", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"  ⚠ Nominatim API Invalid JSON response: {e}", file=sys.stderr)
            return []

    async def _geocode_city(self, session: aiohttp.ClientSession, city: str, state: str) -> bool:
        """
        Geocodes the city to verify it exists using the selected API.
        """
        print(f"Step 1: Verifying city location for {city}, {state}...")
        
        if self.use_google:
            params = {
                'address': f"{city}, {state}, USA",
                'key': self.google_api_key
            }
            data = await self._fetch_google_json(session, params)

            if data and data.get('status') == 'OK' and data.get('results'):
                result = data['results'][0]
                location = result['geometry']['location']
                print(f"  ✓ Found city at: ({location['lat']:.4f}, {location['lng']:.4f})")
                return True
            else:
                status = data.get('status', 'UNKNOWN_ERROR') if data else 'NO_RESPONSE'
                print(f"  ⚠ Google API failed. Status: {status}. Falling back to Nominatim...")
                self.use_google = False  # Fall back to Nominatim
        
        # Use Nominatim API (fallback or primary)
        params = {
            'q': f"{city}, {state}, USA",
            'format': 'json',
            'limit': 1
        }
        data = await self._fetch_nominatim_json(session, params)

        if data and len(data) > 0:
            result = data[0]
            lat = float(result.get('lat', 0))
            lon = float(result.get('lon', 0))
            print(f"  ✓ Found city at: ({lat:.4f}, {lon:.4f})")
            return True
        else:
            print(f"  ✗ Could not find {city}, {state} using any API", file=sys.stderr)
            return False

    async def _get_neighbourhood_coords(
        self, session: aiohttp.ClientSession, neighbourhood_data: Dict, city: str, state: str
    ) -> Dict:
        """Gets coordinates for a single neighbourhood using the selected API."""
        name = neighbourhood_data['neighbourhood_name']
        coords: Optional[Tuple[float, float]] = None
        
        if self.use_google:
            # Try Google Maps API first
            address_formats = [
                f"{name}, {city}, {state}, USA",
                f"{name} neighborhood, {city}, {state}, USA",
                f"{name}, {city}, {state}",
                f"{name} {city} {state}"
            ]
            
            for address in address_formats:
                params = {
                    'address': address,
                    'key': self.google_api_key
                }

                data = await self._fetch_google_json(session, params)
                
                if data and data.get('status') == 'OK' and data.get('results'):
                    result = data['results'][0]
                    location = result['geometry']['location']
                    coords = (location['lat'], location['lng'])
                    break
        
        # If Google failed or we're using Nominatim, try Nominatim
        if not coords:
            query_formats = [
                f"{name}, {city}, {state}, USA",
                f"{name}, {city}, {state}",
                f"{name} neighborhood, {city}, {state}",
                f"{name}, {city}"
            ]
            
            for query in query_formats:
                params = {
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'addressdetails': 1
                }

                data = await self._fetch_nominatim_json(session, params)
                
                if data and len(data) > 0:
                    result = data[0]
                    lat = float(result.get('lat', 0))
                    lon = float(result.get('lon', 0))
                    if lat != 0 and lon != 0:
                        coords = (lat, lon)
                        break

        return {
            "id": neighbourhood_data['id'],
            "neighbourhood_name": name,
            "latitude": coords[0] if coords else None,
            "longitude": coords[1] if coords else None,
        }

    async def find_coordinates_for_city(self, city: str, state: str) -> List[Dict]:
        """Main async orchestrator to find all neighbourhood coordinates for a city."""
        print(f"\nFinding coordinates for neighbourhoods in {city}, {state}")

        # Scraper can remain synchronous
        scraper = NeighbourhoodScraper()
        neighbourhoods = scraper.scrape_neighbourhoods(city, state)

        if not neighbourhoods:
            print("No neighbourhoods found to process!")
            return []
        print(f"Found {len(neighbourhoods)} neighbourhoods.")

        async with aiohttp.ClientSession() as session:
            # First, verify the city exists
            if not await self._geocode_city(session, city, state):
                return []

            # Create a list of concurrent tasks for all neighbourhoods
            print(f"\nStep 2: Geocoding {len(neighbourhoods)} neighbourhoods using Google Maps API...")
            tasks = [
                self._get_neighbourhood_coords(session, n, city, state) for n in neighbourhoods
            ]
            
            # Run tasks concurrently with a progress bar
            results = await tqdm_asyncio.gather(*tasks, desc="Processing Neighbourhoods")

        return results

    def save_results(self, results: List[Dict], city: str) -> str:
        """Saves the final results to a JSON file."""
        city_clean = city.lower().replace(' ', '_').replace(',', '')
        filename = f"{city_clean}_neighbourhoods_with_coordinates.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        return filename


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Find coordinates for neighbourhoods in a city.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('city_state', help='City and state (e.g., "Boston, MA")')
    args = parser.parse_args()

    try:
        city, state = [x.strip() for x in args.city_state.split(',')]
    except ValueError:
        print("Error: Please provide city and state in the format 'City, State'", file=sys.stderr)
        sys.exit(1)

    finder = CoordinateFinder()
    try:
        results = await finder.find_coordinates_for_city(city, state)

        if not results:
            print("\nNo results were generated.")
            sys.exit(1)

        filename = finder.save_results(results, city)

        # Final Summary
        successful = sum(1 for r in results if r['latitude'] is not None)
        total = len(results)
        success_rate = (successful / total * 100) if total > 0 else 0

        print(f"\n{'='*60}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"City:                 {city}, {state}")
        print(f"Total Neighbourhoods: {total}")
        print(f"Coordinates Found:    {successful}")
        print(f"Coordinates Failed:   {total - successful}")
        print(f"Success Rate:         {success_rate:.1f}%")
        print(f"\nResults saved to:     {filename}")

    except aiohttp.ClientError as e:
        print(f"\nA critical network error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure you are using Python 3.7+ for asyncio.run()
    asyncio.run(main())
