import os
import json
import time
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
import argparse
import sys
import logging
import re

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rewrite_explanation_with_cerebras(client, prompt, model="llama3.1-8b"):
    """
    Calls the Cerebras API to get the rewritten text.
    Includes error handling and exponential backoff for retries.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                max_tokens=200,
                temperature=0.7,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logging.warning(f"API Error (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff
            else:
                logging.error(f"Failed to get rewrite after {max_retries} attempts.")
                return None

def generate_rewrite_prompt(neighborhood_name, city_name, topic, score, original_text):
    """
    Creates a dynamic, high-quality prompt for the LLM.
    This version is now city-agnostic.
    """
    topic_map = {
        "aqi_reason": "Air Quality", "greenery_coverage_exp": "Greenery and Park Access",
        "water_quality_exp": "Water Quality", "cleanliness_exp": "Neighborhood Cleanliness",
        "power_grid_reliability_exp": "Power Grid Reliability", "road_quality_exp": "Road Quality",
        "public_safety_exp": "Public Safety", "walkability_explanation": "Walkability",
        "public_transit_access_explanation": "Public Transit Access", "renewable_energy_adoption_explanation": "Renewable Energy",
        "recycling_rate_explanation": "Recycling Program Effectiveness", "local_business_sustainability_practices_explanation": "Local Business Sustainability",
        "circular_economy_indicators_explanation": "Circular Economy Indicators"
    }

    prompt = f"""
    You are an urban planning analyst writing a sustainability report for {city_name}.
    Your task is to rewrite a data-driven explanation into a natural and personalized paragraph.

    **Neighborhood:** {neighborhood_name}
    **Topic:** {topic_map.get(topic, topic)}
    **Data-Driven Score:** {score}/10
    **Original Explanation (based on raw data):** "{original_text}"

    Please rewrite the explanation. Your new text must be a single, engaging paragraph that sounds like it was written for a resident. Directly reference the neighborhood name and incorporate the key facts from the original text, reflecting the tone of the score.

    **New Personalized Explanation:**
    """
    return prompt.strip()

def process_data_with_cerebras(input_filepath, output_filepath):
    """
    Main worker function to load data, process it with Cerebras, and save the result.
    """
    load_dotenv()
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        logging.critical("CEREBRAS_API_KEY not found in .env file. Please create the file and add your key.")
        sys.exit(1)
        
    client = Cerebras(api_key=api_key)
    
    try:
        with open(input_filepath, 'r') as f:
            all_neighborhood_data = json.load(f)
    except FileNotFoundError:
        logging.critical(f"Input file '{input_filepath}' not found.")
        sys.exit(1)

    # Dynamically get city name from the first neighborhood entry for the prompt
    try:
        first_entry = next(iter(all_neighborhood_data.values()))
        city_name_for_prompt = 'the city' # Default value
        
        # Try to find a description to extract the city name from
        description = first_entry.get('description', '')
        if description:
            # A simple regex to extract just the city name if it's complex
            match = re.search(r"A neighborhood within the city of (.*?)(,|$)", description)
            if match:
                 city_name_for_prompt = match.group(1)
        
    except StopIteration:
        logging.critical("Input file is empty. Cannot proceed.")
        sys.exit(1)


    explanation_keys = [
        "aqi_reason", "greenery_coverage_exp", "water_quality_exp", "cleanliness_exp",
        "power_grid_reliability_exp", "road_quality_exp", "public_safety_exp",
        "walkability_explanation", "public_transit_access_explanation",
        "renewable_energy_adoption_explanation", "recycling_rate_explanation",
        "local_business_sustainability_practices_explanation", "circular_economy_indicators_explanation"
    ]
    score_map = {key: key.replace("_exp", "").replace("_explanation", "") for key in explanation_keys}

    logging.info("--- Starting Personalized Explanation Generation ---")
    for name, data in all_neighborhood_data.items():
        logging.info(f"Processing Neighborhood: {name}")
        homeowners_data = data.get("homeowners", {})
        for key in explanation_keys:
            if key in homeowners_data:
                score_key = score_map[key]
                score = homeowners_data.get(score_key, "N/A")
                
                prompt = generate_rewrite_prompt(name, city_name_for_prompt, key, score, homeowners_data[key])
                new_text = rewrite_explanation_with_cerebras(client, prompt)
                
                if new_text:
                    homeowners_data[key] = new_text
                    logging.info(f"  - Successfully rewrote '{key}'.")
                else:
                    logging.warning(f"  - Failed to rewrite '{key}'. Keeping original text.")
                time.sleep(0.5) # Be respectful to the API

    with open(output_filepath, 'w') as f:
        json.dump(all_neighborhood_data, f, indent=4)
        
    logging.info(f"Personalized report saved to '{output_filepath}'.")

def main():
    """Parses command-line arguments and calls the main worker function."""
    parser = argparse.ArgumentParser(description='Rewrite sustainability explanations using the Cerebras AI API.')
    parser.add_argument('--input-file', required=True, help='Input JSON file with initial sustainability data.')
    parser.add_argument('--output-file', required=True, help='Output JSON file for personalized explanations.')
    args = parser.parse_args()
    process_data_with_cerebras(args.input_file, args.output_file)

if __name__ == '__main__':
    main()

