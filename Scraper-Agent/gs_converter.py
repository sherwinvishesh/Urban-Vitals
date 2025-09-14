import json
import argparse
import sys
import logging

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_and_finalize_data(input_filepath, output_filepath):
    """
    Loads the personalized neighborhood data, calculates the average 'Green Score'
    for each neighborhood, and formats the output as specified.
    """
    try:
        with open(input_filepath, 'r') as f:
            personalized_data = json.load(f)
    except FileNotFoundError:
        logging.critical(f"Input file '{input_filepath}' not found. Please ensure the previous pipeline step completed successfully.")
        sys.exit(1)

    score_keys = [
        "air_quality", "greenery_coverage", "water_quality", "cleanliness",
        "power_grid_reliability", "road_quality", "public_safety", "walkability",
        "public_transit_access", "renewable_energy_adoption", "recycling_rate",
        "local_business_sustainability_practices", "circular_economy_indicators"
    ]
    finalized_report = {}

    logging.info("--- Calculating Green Scores and Finalizing Report ---")

    for name, data in personalized_data.items():
        homeowners_data = data.get("homeowners", {})
        scores = [homeowners_data[key] for key in score_keys if key in homeowners_data and isinstance(homeowners_data[key], (int, float))]
        
        green_score = sum(scores) / len(scores) if scores else 0.0

        finalized_report[name] = {
            "id": data.get("id"),
            "name": data.get("name"),
            "coordinates": data.get("coordinates"),
            "description": data.get("description"),
            "green_score": round(green_score, 2),
            "homeowners": homeowners_data
        }
    logging.info(f"Calculated Green Score for {len(finalized_report)} neighborhoods.")

    with open(output_filepath, 'w') as f:
        json.dump(finalized_report, f, indent=4)

    logging.info(f"Final report with Green Scores saved to '{output_filepath}'.")

def main():
    """Parses command-line arguments and calls the main worker function."""
    parser = argparse.ArgumentParser(description='Calculate Green Score and finalize data.')
    # --- CORRECTED LINES ---
    parser.add_argument('--input-file', required=True, help='Input JSON file with personalized data.')
    parser.add_argument('--output-file', required=True, help='Final output JSON file.')
    # --- END CORRECTION ---
    args = parser.parse_args()
    calculate_and_finalize_data(args.input_file, args.output_file)

if __name__ == '__main__':
    main()

