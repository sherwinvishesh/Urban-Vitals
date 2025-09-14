# Save this file as modal_pipeline.py
import modal
import re
import os
import json # Import json for file operations

# --- Environment Definition ---
image = (
    modal.Image.debian_slim()
    .pip_install(
        "requests",
        "geopy",
        "python-dotenv",
        "cerebras-cloud-sdk",
    )
    .add_local_dir(".", remote_path="/root")
)

# --- App Definition ---
app = modal.App(
    name="sustainability-pipeline",
    image=image,
)

app.secret = modal.Secret.from_name("cerebras-api-key")

# --- Pipeline Steps with Compatibility Wrappers ---

@app.function()
def scrape_neighbourhoods(city_state: str):
    """(Corresponds to neighbourhood_scraper.py) - No wrapper needed."""
    from neighbourhood_scraper import NeighbourhoodScraper
    
    city, state = [x.strip() for x in city_state.split(',')]
    scraper = NeighbourhoodScraper()
    results = scraper.scrape(city, state)
    if not results:
        raise ValueError("Scraping returned no results.")
    return results

@app.function()
def geocode_neighbourhoods(neighbourhood_data: list, city_context: str):
    """Wrapper for the file-based enhanced_geocoder.py script."""
    from enhanced_geocoder import geocode_neighborhoods as geocode_from_file
    
    temp_input_path = "/tmp/neighbourhood_data.json"
    temp_output_path = "/tmp/geocoded_data.json"

    with open(temp_input_path, 'w') as f:
        json.dump(neighbourhood_data, f)
    
    geocode_from_file(temp_input_path, temp_output_path, city_context)

    with open(temp_output_path, 'r') as f:
        result_data = json.load(f)
        
    return result_data

@app.function(timeout=1200)
def generate_sustainability_data(geocoded_data: list):
    """Wrapper for the file-based data_exp_2.py script."""
    from data_exp_2 import generate_sustainability_data as generate_from_file

    temp_input_path = "/tmp/geocoded_data.json"
    temp_output_path = "/tmp/sustainability_data.json"

    with open(temp_input_path, 'w') as f:
        json.dump(geocoded_data, f)

    generate_from_file(temp_input_path, temp_output_path)

    with open(temp_output_path, 'r') as f:
        result_data = json.load(f)
        
    return result_data

@app.function(timeout=1200)
def personalize_data_with_cerebras(sustainability_data: dict):
    """Wrapper for the file-based data_exp.py script."""
    from data_exp import process_data_with_cerebras as process_from_file
    
    temp_input_path = "/tmp/sustainability_data.json"
    temp_output_path = "/tmp/personalized_data.json"

    with open(temp_input_path, 'w') as f:
        json.dump(sustainability_data, f)
        
    process_from_file(temp_input_path, temp_output_path)

    with open(temp_output_path, 'r') as f:
        result_data = json.load(f)
        
    return result_data

@app.function()
def calculate_green_score(personalized_data: dict):
    """Wrapper for the file-based gs_converter.py script."""
    from gs_converter import calculate_and_finalize_data as finalize_from_file
    
    temp_input_path = "/tmp/personalized_data.json"
    temp_output_path = "/tmp/final_report.json"

    with open(temp_input_path, 'w') as f:
        json.dump(personalized_data, f)
        
    finalize_from_file(temp_input_path, temp_output_path)

    with open(temp_output_path, 'r') as f:
        result_data = json.load(f)
        
    return result_data

# --- Main Pipeline Orchestrator ---
@app.local_entrypoint()
def run_pipeline(city_state: str = "Boston, MA"):
    """
    This function runs on your local machine and calls the remote
    Modal functions in the correct order.
    """
    print(f"--- 🚀 Starting data pipeline for {city_state} on Modal ---")

    # Step 1: Scrape names
    print("\n[Step 1/5] Scraping neighborhood names...")
    scraped_data = scrape_neighbourhoods.remote(city_state)
    print(f"✅ Found {len(scraped_data)} neighborhoods.")

    # Step 2: Geocode coordinates
    print("\n[Step 2/5] Geocoding neighborhoods...")
    geocoded_data = geocode_neighbourhoods.remote(scraped_data, city_state)
    print("✅ Geocoding complete.")

    # Step 3: Generate sustainability scores from OSM/APIs
    print("\n[Step 3/5] Generating initial sustainability data...")
    sustainability_data = generate_sustainability_data.remote(geocoded_data)
    print("✅ Initial data generated.")

    # Step 4: Rewrite explanations with Cerebras AI
    print("\n[Step 4/5] Personalizing explanations with Cerebras AI...")
    personalized_data = personalize_data_with_cerebras.remote(sustainability_data)
    print("✅ Explanations personalized.")
    
    # Step 5: Calculate Green Score and finalize
    print("\n[Step 5/5] Calculating Green Scores and finalizing report...")
    final_report = calculate_green_score.remote(personalized_data)
    print("✅ Final report complete.")

    # --- Save Final Output ---
    city_slug = re.sub(r'[^\w\s-]', '', city_state.split(',')[0]).strip().replace(' ', '_').lower()
    final_output_file = f"{city_slug}_sustainability_report.json"
    
    with open(final_output_file, 'w') as f:
        json.dump(final_report, f, indent=4)

    print(f"\n--- 🎉 Pipeline completed successfully! ---")
    print(f"Final data saved locally to: {final_output_file}")
