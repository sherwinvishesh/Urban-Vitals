import json
from geopy.geocoders import ArcGIS, Photon
import time
import argparse
import sys

def geocode_neighborhoods(input_filepath, output_filepath, city_context):
    """
    Reads a list of neighborhoods, finds their coordinates, and saves the result.
    """
    geolocators = [ArcGIS(timeout=10), Photon(timeout=10)]
    
    try:
        with open(input_filepath, 'r') as f:
            neighborhood_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filepath}' not found.")
        sys.exit(1)
        
    output_results = []
    print(f"Starting geocoding process for {len(neighborhood_data)} neighborhoods...")

    for item in neighborhood_data:
        neighborhood_name = item.get("neighbourhood_name")
        query = f"{neighborhood_name}, {city_context}"
        found_location = None

        for geocoder in geolocators:
            try:
                location = geocoder.geocode(query)
                time.sleep(1) # Respect API usage policies
                if location:
                    found_location = location
                    print(f"✅ Found '{neighborhood_name}' using {geocoder.__class__.__name__}.")
                    break
            except Exception as e:
                print(f"❌ Error with {geocoder.__class__.__name__} for '{neighborhood_name}': {e}.")
        
        item['latitude'] = found_location.latitude if found_location else None
        item['longitude'] = found_location.longitude if found_location else None
        output_results.append(item)

    with open(output_filepath, 'w') as f:
        json.dump(output_results, f, indent=2)

    print(f"\nGeocoding complete! Results saved to '{output_filepath}'")

def main():
    parser = argparse.ArgumentParser(description='Geocode neighborhood names.')
    parser.add_argument('--input-file', required=True, help='Input JSON file with neighborhood names.')
    parser.add_argument('--output-file', required=True, help='Output JSON file for results with coordinates.')
    parser.add_argument('--city-context', required=True, help='City and State for context (e.g., "Tempe, AZ").')
    args = parser.parse_args()
    
    geocode_neighborhoods(args.input_file, args.output_file, args.city_context)

if __name__ == "__main__":
    main()

