import subprocess
import sys
import os
import re

def run_command(command):
    """Runs a command in a subprocess and checks for errors."""
    print(f"\n{'='*20}\n[RUNNING]: {' '.join(command)}\n{'='*20}")
    try:
        # Using capture_output=True to get stdout/stderr
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        print("[STDOUT]:")
        print(result.stdout)
        if result.stderr:
            print("[STDERR]:")
            print(result.stderr)
        print(f"[SUCCESS]: Command '{' '.join(command)}' finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR]: Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}.")
        print("[ERROR STDOUT]:")
        print(e.stdout)
        print("[ERROR STDERR]:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"[ERROR]: The command '{command[0]}' was not found.")
        print("Please ensure all script files are in the same directory.")
        return False


def main():
    """
    Main function to orchestrate the entire data processing pipeline.
    """
    if len(sys.argv) != 2:
        print("Usage: python run_pipeline.py \"City, State\"")
        sys.exit(1)

    city_state_input = sys.argv[1]
    try:
        city, state = [x.strip() for x in city_state_input.split(',')]
    except ValueError:
        print("Error: Please provide input in the format \"City, State\"")
        sys.exit(1)

    # --- Define filenames for the pipeline ---
    city_slug = re.sub(r'[^\w\s-]', '', city).strip().replace(' ', '_').lower()
    
    # Intermediate files
    step1_output_names = f"_{city_slug}_step1_names.json"
    step2_output_coords = f"_{city_slug}_step2_coords.json"
    step3_output_sustainability = f"_{city_slug}_step3_sustainability.json" # Assumed new script for this
    step4_output_personalized = f"_{city_slug}_step4_personalized.json"
    
    # Final output file
    final_output_file = f"{city_slug}_data_f.json"
    
    intermediate_files = [
        step1_output_names,
        step2_output_coords,
        step3_output_sustainability,
        step4_output_personalized
    ]

    print(f"--- Starting data pipeline for {city}, {state} ---")

    # --- Pipeline Steps ---
    pipeline_steps = [
        # Step 1: Scrape neighborhood names
        ["python", "neighbourhood_scraper.py", city_state_input, "--output-file", step1_output_names],
        
        # Step 2: Geocode the neighborhoods
        ["python", "enhanced_geocoder.py", "--input-file", step1_output_names, "--output-file", step2_output_coords, "--city-context", city_state_input],
        
        # Step 3: Generate initial sustainability data (using a placeholder for data_exp_2.py)
        # NOTE: This step assumes 'data_exp_2.py' generates the initial data scores.
        # Based on our previous work, this is the OpenStreetMap data generator.
        ["python", "data_exp_2.py", "--input-file", step2_output_coords, "--output-file", step3_output_sustainability],

        # Step 4: Rewrite explanations with Cerebras AI
        ["python", "data_exp.py", "--input-file", step3_output_sustainability, "--output-file", step4_output_personalized],
        
        # Step 5: Calculate Green Score and finalize
        ["python", "gs_converter.py", "--input-file", step4_output_personalized, "--output-file", final_output_file],
    ]

    # Execute all steps
    for step in pipeline_steps:
        if not run_command(step):
            print("\n--- Pipeline failed at a critical step. Aborting. ---")
            sys.exit(1)

    # --- Cleanup ---
    print("\n--- Cleaning up intermediate files ---")
    for f in intermediate_files:
        if os.path.exists(f):
            os.remove(f)
            print(f"Removed: {f}")

    print(f"\n--- Pipeline completed successfully! ---")
    print(f"Final data saved to: {final_output_file}")

if __name__ == "__main__":
    main()
