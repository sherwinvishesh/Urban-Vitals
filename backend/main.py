from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import json
import os
import sys
from pathlib import Path

# Add import for the chatbot
sys.path.append(str(Path(__file__).parent / "chatbot"))

try:
    from terminal_chatbot import UrbanVitalsChatbot  # Adjust import based on your chatbot class name
except ImportError:
    print("Warning: Chatbot module not found. Chatbot functionality will be disabled.")
    UrbanVitalsChatbot = None

app = FastAPI(title="Urban Vitals API", description="API for Urban Vitals neighborhood data")

# Configure CORS - more permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
chatbot_instance = None
if UrbanVitalsChatbot:
    try:
        chatbot_instance = UrbanVitalsChatbot()
        print("Chatbot initialized successfully")
    except Exception as e:
        print(f"Failed to initialize chatbot: {e}")

# Load data from JSON file
def load_neighborhoods():
    # Try multiple possible locations for the data file
    possible_paths = [
        Path(__file__).parent / "data-lib" / "Tempe-AZ-data.json",
        Path(__file__).parent / "Tempe-AZ-data.json",
        Path(__file__).parent / "data.json",
    ]
    
    data_path = None
    for path in possible_paths:
        if path.exists():
            data_path = path
            break
    
    if not data_path:
        raise FileNotFoundError(f"Could not find data file. Looked in: {[str(p) for p in possible_paths]}")
    
    print(f"Loading data from: {data_path}")
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in data file: {e}")
    except Exception as e:
        raise Exception(f"Error reading data file: {e}")
    
    # Transform the data structure to match frontend expectations
    neighborhoods = []
    for neighborhood_name, data in raw_data.items():
        try:
            # Extract homeowners data for score variables
            homeowners = data.get("homeowners", {})
            score_variables = {}
            
            # Map the homeowners data to score variables
            score_variables["air_quality"] = homeowners.get("air_quality", 0)
            score_variables["greenery_coverage"] = homeowners.get("greenery_coverage", 0)
            score_variables["water_quality"] = homeowners.get("water_quality", 0)
            score_variables["cleanliness"] = homeowners.get("cleanliness", 0)
            score_variables["power_grid_reliability"] = homeowners.get("power_grid_reliability", 0)
            score_variables["road_quality"] = homeowners.get("road_quality", 0)
            score_variables["public_safety"] = homeowners.get("public_safety", 0)
            score_variables["walkability"] = homeowners.get("walkability", 0)
            score_variables["public_transit_access"] = homeowners.get("public_transit_access", 0)
            score_variables["renewable_energy_adoption"] = homeowners.get("renewable_energy_adoption", 0)
            score_variables["recycling_rate"] = homeowners.get("recycling_rate", 0)
            score_variables["local_business_sustainability_practices"] = homeowners.get("local_business_sustainability_practices", 0)
            score_variables["circular_economy_indicators"] = homeowners.get("circular_economy_indicators", 0)
            
            # Add explanations
            score_variables["air_quality_reason"] = homeowners.get("aqi_reason", "")
            score_variables["greenery_coverage_exp"] = homeowners.get("greenery_coverage_exp", "")
            score_variables["water_quality_exp"] = homeowners.get("water_quality_exp", "")
            score_variables["cleanliness_exp"] = homeowners.get("cleanliness_exp", "")
            score_variables["power_grid_reliability_exp"] = homeowners.get("power_grid_reliability_exp", "")
            score_variables["road_quality_exp"] = homeowners.get("road_quality_exp", "")
            score_variables["public_safety_exp"] = homeowners.get("public_safety_exp", "")
            score_variables["walkability_exp"] = homeowners.get("walkability_explanation", "")
            score_variables["public_transit_access_exp"] = homeowners.get("public_transit_access_explanation", "")
            score_variables["renewable_energy_adoption_exp"] = homeowners.get("renewable_energy_adoption_explanation", "")
            score_variables["recycling_rate_exp"] = homeowners.get("recycling_rate_explanation", "")
            score_variables["local_business_sustainability_practices_exp"] = homeowners.get("local_business_sustainability_practices_explanation", "")
            score_variables["circular_economy_indicators_exp"] = homeowners.get("circular_economy_indicators_explanation", "")
            
            neighborhood = {
                "id": data.get("id"),
                "name": data.get("name", neighborhood_name),
                "coordinates": data.get("coordinates"),
                "description": data.get("description", ""),
                "green_score": data.get("green_score", 0),
                "score_variables": score_variables
            }
            
            neighborhoods.append(neighborhood)
            
        except Exception as e:
            print(f"Error processing neighborhood {neighborhood_name}: {e}")
            continue
    
    print(f"Successfully loaded {len(neighborhoods)} neighborhoods")
    return neighborhoods

def load_definitions():
    """Load definitions/summary data from JSON file"""
    possible_paths = [
        Path(__file__).parent / "data-lib" / "summary.json",
        Path(__file__).parent / "summary.json",
        Path(__file__).parent / "definitions.json",
    ]
    
    data_path = None
    for path in possible_paths:
        if path.exists():
            data_path = path
            break
    
    if not data_path:
        print(f"Warning: Could not find definitions file. Looked in: {[str(p) for p in possible_paths]}")
        return []
    
    print(f"Loading definitions from: {data_path}")
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            definitions_data = json.load(f)
        return definitions_data
    except json.JSONDecodeError as e:
        print(f"Error parsing definitions data: {e}")
        return []
    except Exception as e:
        print(f"Error reading definitions file: {e}")
        return []
def load_lewc_data():
    """Load LEWC disaster data from JSON file"""
    possible_paths = [
        Path(__file__).parent / "data-lib" / "Tempe-AZ-lewc.json",  # This should be the disaster file
        Path(__file__).parent / "Tempe-AZ-lewc.json",
        Path(__file__).parent / "lewc.json",
    ]
    
    data_path = None
    for path in possible_paths:
        if path.exists():
            data_path = path
            break
    
    if not data_path:
        print(f"Warning: Could not find LEWC disaster data file. Looked in: {[str(p) for p in possible_paths]}")
        return {}
    
    print(f"Loading LEWC disaster data from: {data_path}")
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            lewc_data = json.load(f)
        return lewc_data
    except json.JSONDecodeError as e:
        print(f"Error parsing LEWC disaster data: {e}")
        return {}
    except Exception as e:
        print(f"Error reading LEWC disaster file: {e}")
        return {}

@app.get("/")
def read_root():
    return {"message": "Urban Vitals API", "status": "running", "version": "1.0"}

@app.get("/api/neighborhoods")
def get_neighborhoods():
    """Get all neighborhoods with their data"""
    try:
        neighborhoods = load_neighborhoods()
        return {"success": True, "data": neighborhoods, "count": len(neighborhoods)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Data file not found: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/neighborhoods/{neighborhood_id}")
def get_neighborhood(neighborhood_id: int):
    """Get a specific neighborhood by ID"""
    try:
        neighborhoods = load_neighborhoods()
        neighborhood = next((n for n in neighborhoods if n["id"] == neighborhood_id), None)
        if neighborhood:
            return {"success": True, "data": neighborhood}
        raise HTTPException(status_code=404, detail="Neighborhood not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/neighborhoods/stats/summary")
def get_stats_summary():
    """Get summary statistics of all neighborhoods"""
    try:
        neighborhoods = load_neighborhoods()
        
        # Calculate statistics
        green_scores = [n["green_score"] for n in neighborhoods if n["green_score"] is not None and n["green_score"] > 0]
        
        if not green_scores:
            return {"success": False, "error": "No valid green scores found"}
        
        stats = {
            "total_neighborhoods": len(neighborhoods),
            "average_green_score": sum(green_scores) / len(green_scores),
            "highest_green_score": max(green_scores),
            "lowest_green_score": min(green_scores),
            "neighborhoods_with_data": len(green_scores)
        }
        
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/definitions")
def get_definitions():
    """Get all term definitions"""
    try:
        definitions = load_definitions()
        return {"success": True, "data": definitions, "count": len(definitions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/definitions/{term}")
def get_definition(term: str):
    """Get definition for a specific term"""
    try:
        definitions = load_definitions()
        
        # Search for the term (case-insensitive)
        term_lower = term.lower().replace('_', ' ').replace('-', ' ')
        
        for definition in definitions:
            if isinstance(definition, dict) and 'term' in definition:
                def_term = definition['term'].lower().replace('_', ' ').replace('-', ' ')
                if term_lower == def_term or term_lower in def_term:
                    return {"success": True, "data": definition}
        
        raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/lewc")
def get_lewc_data():
    """Get all LEWC (environmental risk) data"""
    try:
        lewc_data = load_lewc_data()
        return {"success": True, "data": lewc_data, "count": len(lewc_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/lewc/{neighborhood_name}")
def get_lewc_neighborhood(neighborhood_name: str):
    """Get LEWC data for a specific neighborhood"""
    try:
        lewc_data = load_lewc_data()
        
        # Search for the neighborhood (case-insensitive)
        for name, data in lewc_data.items():
            if name.lower() == neighborhood_name.lower():
                return {"success": True, "data": {name: data}}
        
        raise HTTPException(status_code=404, detail=f"LEWC data for '{neighborhood_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Chatbot endpoints
@app.post("/api/chatbot/message")
async def chat_message(request_data: dict):
    """Send a message to the chatbot and get a response"""
    try:
        if not chatbot_instance:
            return {
                "response": "I'm sorry, but the chatbot service is currently unavailable. Please try again later.",
                "success": False,
                "error": "Chatbot service unavailable"
            }
        
        # Extract message and context from request
        message = request_data.get("message", "")
        neighborhood_context = request_data.get("neighborhood_context")
        
        if not message:
            return {
                "response": "I didn't receive a message. Please try again.",
                "success": False,
                "error": "Empty message"
            }
        
        # Get neighborhoods data for context
        neighborhoods = load_neighborhoods()
        
        # Prepare context for the chatbot
        context = {
            "neighborhoods": neighborhoods,
            "selected_neighborhood": neighborhood_context,
            "total_neighborhoods": len(neighborhoods)
        }
        
        # Get chatbot response (adjust method name based on your chatbot implementation)
        if hasattr(chatbot_instance, 'get_response'):
            response = chatbot_instance.get_response(message, context)
        elif hasattr(chatbot_instance, 'chat'):
            response = chatbot_instance.chat(message, context)
        elif hasattr(chatbot_instance, 'process_message'):
            response = chatbot_instance.process_message(message, context)
        else:
            # Fallback - try calling the instance directly
            response = chatbot_instance(message, context)
        
        return {
            "response": str(response),
            "success": True
        }
        
    except Exception as e:
        print(f"Chatbot error: {e}")
        return {
            "response": "I'm sorry, I'm having trouble processing your request right now. Please try again later.",
            "success": False,
            "error": str(e)
        }

@app.get("/api/chatbot/status")
def chatbot_status():
    """Check if chatbot is available"""
    return {
        "available": chatbot_instance is not None,
        "status": "ready" if chatbot_instance else "unavailable"
    }

@app.post("/api/chatbot/reset")
def reset_chatbot():
    """Reset chatbot conversation state"""
    try:
        if chatbot_instance and hasattr(chatbot_instance, 'reset'):
            chatbot_instance.reset()
        return {"success": True, "message": "Chatbot conversation reset"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Health check endpoint
@app.get("/health")
def health_check():
    try:
        neighborhoods = load_neighborhoods()
        definitions = load_definitions()
        lewc_data = load_lewc_data()
        
        return {
            "status": "healthy",
            "neighborhoods_loaded": len(neighborhoods),
            "definitions_loaded": len(definitions),
            "lewc_data_loaded": len(lewc_data),
            "data_file_exists": True,
            "chatbot_available": chatbot_instance is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "data_file_exists": False,
            "chatbot_available": chatbot_instance is not None
        }

if __name__ == "__main__":
    import uvicorn
    print("Starting Urban Vitals API...")
    print("Available endpoints:")
    print("- GET /")
    print("- GET /api/neighborhoods")
    print("- GET /api/neighborhoods/{id}")
    print("- GET /api/neighborhoods/stats/summary")
    print("- GET /api/definitions")
    print("- GET /api/definitions/{term}")
    print("- GET /api/lewc")
    print("- GET /api/lewc/{neighborhood_name}")
    print("- POST /api/chatbot/message")
    print("- GET /api/chatbot/status")
    print("- POST /api/chatbot/reset")
    print("- GET /health")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)