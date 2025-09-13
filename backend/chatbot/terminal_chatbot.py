import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

class UrbanVitalsChatbot:
    def __init__(self):
        """Initialize the Urban Vitals web chatbot"""
        # Load environment variables
        load_dotenv()
        
        # Initialize conversation tracking
        self.conversation_history = []
        self.conversation_subject = None
        
        # Initialize Gemini model
        self.model = None
        self.chat = None
        self._initialize_gemini()
        
        # Load static data
        self.refined_data = None
        self.lewc_data = None
        self._load_data()
        
    def _initialize_gemini(self):
        """Initialize Google Gemini AI model"""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if not google_api_key:
            print("Warning: GOOGLE_API_KEY environment variable not set. Chatbot will use fallback responses.")
            return
        
        try:
            genai.configure(api_key=google_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            system_prompt = """
            You are an expert concierge for the city of Tempe, Arizona. Your tone should be friendly, professional, and natural, as if you're a human expert in a conversation.
            Avoid robotic phrases like "Of course" or "Certainly". If a user's query contains a likely typo, infer the correct intent based on the conversation's context.
            Your primary goal is to answer questions using the specific JSON data provided with each user query. Prioritize this data.
            If the provided data includes "live_aqi_data" or "live_weather_data" sections, seamlessly integrate that real-time information.
            NEVER mention that your knowledge is limited to the provided data or suggest checking other sources.
            You must hold a conversation and remember context from previous questions.
            If you cannot answer, simply say, "That's a great question, but I don't have that information right now."
            Keep responses concise and conversational for a web chat interface.
            
            When asked about which neighborhood has the highest/lowest scores, analyze ALL neighborhoods in the provided data and give specific names and values.
            When comparing neighborhoods, provide specific numerical comparisons.
            When explaining green scores, break down the components that contribute to the score.
            """
            
            self.chat = self.model.start_chat(history=[
                {'role': 'user', 'parts': [{'text': system_prompt}]},
                {'role': 'model', 'parts': [{'text': "Hello! I'm ready to help you explore Tempe. What would you like to know?"}]}
            ])
            
            print("Gemini model initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize Gemini: {e}")
            self.model = None
            self.chat = None
    
    def _load_data(self):
        """Load neighborhood data from JSON files"""
        refined_path = "backend/data-lib/Tempe-AZ-data.json"
        lewc_path = "backend/data-lib/Tempe-AZ-lewc-data.json"
        
        # Try alternative paths if the main ones don't work
        alternative_paths = [
            ("data-lib/Tempe-AZ-data.json", "data-lib/Tempe-AZ-lewc-data.json"),
            ("Tempe-AZ-data.json", "Tempe-AZ-lewc-data.json"),
        ]
        
        # Try main paths first
        try:
            with open(refined_path, 'r', encoding='utf-8') as f:
                self.refined_data = json.load(f)
        except FileNotFoundError:
            # Try alternative paths
            for alt_refined, _ in alternative_paths:
                try:
                    with open(alt_refined, 'r', encoding='utf-8') as f:
                        self.refined_data = json.load(f)
                    break
                except FileNotFoundError:
                    continue
            else:
                print(f"Warning: Could not find refined data file at any location")
                self.refined_data = {}
        except json.JSONDecodeError as e:
            print(f"Error parsing refined data: {e}")
            self.refined_data = {}
        
        try:
            with open(lewc_path, 'r', encoding='utf-8') as f:
                self.lewc_data = json.load(f)
        except FileNotFoundError:
            # Try alternative paths
            for _, alt_lewc in alternative_paths:
                try:
                    with open(alt_lewc, 'r', encoding='utf-8') as f:
                        self.lewc_data = json.load(f)
                    break
                except FileNotFoundError:
                    continue
            else:
                print(f"Warning: Could not find LEWC data file, using empty data")
                self.lewc_data = {}
        except json.JSONDecodeError as e:
            print(f"Error parsing LEWC data: {e}")
            self.lewc_data = {}
    
    def get_response(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Generate a response to the user's message
        
        Args:
            message (str): User's input message
            context (Dict): Context including neighborhoods and selected neighborhood
        
        Returns:
            str: Chatbot's response
        """
        try:
            # Add message to conversation history
            self.conversation_history.append({"user": message, "response": None})
            
            # Handle empty messages
            if not message.strip():
                return "I'm here to help! Ask me about neighborhood data, green scores, or sustainability metrics."
            
            # Use provided context or fall back to loaded data
            if context and context.get("neighborhoods"):
                # Convert web context to our data format
                neighborhoods_data = self._convert_web_context_to_data_format(context["neighborhoods"])
                selected_neighborhood = context.get("selected_neighborhood")
            else:
                neighborhoods_data = self.refined_data
                selected_neighborhood = None
            
            # Get relevant context for the query
            relevant_context = self._get_relevant_context(
                message, 
                neighborhoods_data, 
                self.lewc_data, 
                selected_neighborhood
            )
            
            # If Gemini is available, use it
            if self.chat:
                return self._get_gemini_response(message, relevant_context)
            else:
                # Enhanced fallback to rule-based responses
                return self._get_enhanced_fallback_response(message, neighborhoods_data, selected_neighborhood)
                
        except Exception as e:
            print(f"Error in get_response: {e}")
            return "I'm sorry, I encountered an error processing your request. Please try again."
    
    def _convert_web_context_to_data_format(self, neighborhoods: List[Dict]) -> Dict:
        """Convert web API format to our internal data format"""
        converted = {}
        for neighborhood in neighborhoods:
            name = neighborhood.get("name", "")
            converted[name] = {
                "id": neighborhood.get("id"),
                "name": name,
                "coordinates": neighborhood.get("coordinates"),
                "description": neighborhood.get("description"),
                "green_score": neighborhood.get("green_score"),
                "homeowners": {}
            }
            
            # Convert score_variables back to homeowners format
            score_vars = neighborhood.get("score_variables", {})
            for key, value in score_vars.items():
                if not key.endswith(("_exp", "_reason", "_explanation")) and isinstance(value, (int, float)):
                    converted[name]["homeowners"][key] = value
                elif key.endswith(("_exp", "_reason", "_explanation")):
                    converted[name]["homeowners"][key] = value
        
        return converted
    
    def _get_gemini_response(self, message: str, context: str) -> str:
        """Get response from Gemini AI model"""
        try:
            if context:
                prompt = f"""
Please answer the user's question based on the following JSON data about Tempe neighborhoods.
When asked about highest/lowest scores, analyze all neighborhoods and provide specific names and values.
When comparing neighborhoods, give specific numerical comparisons.

Relevant Data:
```json
{context}
```

User Question: {message}
"""
            else:
                prompt = message
            
            response = self.chat.send_message(prompt)
            
            # Update conversation history
            if self.conversation_history:
                self.conversation_history[-1]["response"] = response.text
            
            return response.text
            
        except Exception as e:
            print(f"Error getting Gemini response: {e}")
            return self._get_enhanced_fallback_response(message, {}, None)
    
    def _get_enhanced_fallback_response(self, message: str, neighborhoods_data: Dict, selected_neighborhood: Dict) -> str:
        """Enhanced fallback response system when Gemini is unavailable"""
        message_lower = message.lower().strip()
        
        # Handle greetings
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            if selected_neighborhood:
                return f"Hello! I see you're looking at {selected_neighborhood.get('name', 'this neighborhood')}. What would you like to know about it?"
            return "Hello! I'm your Urban Vitals assistant. What would you like to know about Tempe's neighborhoods?"
        
        # Handle highest/lowest green score questions
        if any(phrase in message_lower for phrase in ["highest green score", "best green score", "top green score"]):
            return self._find_highest_green_score(neighborhoods_data)
        
        if any(phrase in message_lower for phrase in ["lowest green score", "worst green score", "bottom green score"]):
            return self._find_lowest_green_score(neighborhoods_data)
        
        # Handle specific neighborhood queries
        if "green score" in message_lower:
            if selected_neighborhood:
                score = selected_neighborhood.get("green_score", "N/A")
                name = selected_neighborhood.get("name", "this neighborhood")
                return f"{name} has a Green Score of {score}/10. This score combines environmental quality, infrastructure, and livability factors."
            return "The Green Score is a comprehensive 1-10 rating that measures neighborhood sustainability, combining air quality, infrastructure, and livability metrics."
        
        # Handle air quality questions
        if any(term in message_lower for term in ["air quality", "aqi", "pollution"]):
            if selected_neighborhood:
                air_quality = selected_neighborhood.get("homeowners", {}).get("air_quality", "N/A")
                name = selected_neighborhood.get("name", "this neighborhood")
                return f"{name} has an air quality score of {air_quality}/10. Higher scores indicate cleaner air with fewer pollutants."
            return "Air quality measures pollution levels and environmental health. Higher scores indicate cleaner air with fewer pollutants."
        
        # Handle comparison questions
        if any(term in message_lower for term in ["compare", "versus", "vs", "better than", "worse than"]):
            return "I can help compare neighborhoods based on their Green Scores and individual sustainability metrics. Each area has unique strengths and challenges."
        
        # Default response for unhandled queries
        return "That's a great question, but I don't have that information right now."
    
    def _find_highest_green_score(self, neighborhoods_data: Dict) -> str:
        """Find neighborhood with highest green score"""
        if not neighborhoods_data:
            return "I don't have neighborhood data available right now."
        
        highest_score = 0
        highest_neighborhood = None
        
        for name, data in neighborhoods_data.items():
            score = data.get("green_score", 0)
            if score > highest_score:
                highest_score = score
                highest_neighborhood = name
        
        if highest_neighborhood:
            return f"{highest_neighborhood} has the highest Green Score at {highest_score}/10."
        else:
            return "I couldn't find green score data for the neighborhoods."
    
    def _find_lowest_green_score(self, neighborhoods_data: Dict) -> str:
        """Find neighborhood with lowest green score"""
        if not neighborhoods_data:
            return "I don't have neighborhood data available right now."
        
        lowest_score = 11  # Start higher than max possible score
        lowest_neighborhood = None
        
        for name, data in neighborhoods_data.items():
            score = data.get("green_score", 11)
            if score < lowest_score and score > 0:  # Exclude 0 scores as they might be missing data
                lowest_score = score
                lowest_neighborhood = name
        
        if lowest_neighborhood:
            return f"{lowest_neighborhood} has the lowest Green Score at {lowest_score}/10."
        else:
            return "I couldn't find green score data for the neighborhoods."
    
    def _get_fallback_response(self, message: str, context: str, selected_neighborhood: Dict) -> str:
        """Original fallback response system (kept for compatibility)"""
        return self._get_enhanced_fallback_response(message, {}, selected_neighborhood)
    
    def _get_relevant_context(self, query: str, neighborhoods_data: Dict, lewc_data: Dict, selected_neighborhood: Dict) -> str:
        """Get relevant context data for the query"""
        try:
            context_data = {}
            
            # For questions about highest/lowest scores, include all neighborhoods
            if any(phrase in query.lower() for phrase in ["highest", "lowest", "best", "worst", "top", "bottom", "compare"]):
                # Include all neighborhoods for comparison queries
                context_data = neighborhoods_data.copy()
            else:
                # For other queries, focus on selected neighborhood or find mentioned ones
                subject_neighborhood = None
                
                # If we have a selected neighborhood, use it as the subject
                if selected_neighborhood:
                    subject_name = selected_neighborhood.get("name")
                    if subject_name and subject_name in neighborhoods_data:
                        subject_neighborhood = subject_name
                
                # Find mentioned neighborhoods in the query
                if not subject_neighborhood:
                    mentioned_neighborhoods = self._find_mentioned_neighborhoods(query, neighborhoods_data.keys())
                    if mentioned_neighborhoods:
                        subject_neighborhood = mentioned_neighborhoods[0]
                
                # If we have a subject, fetch its data
                if subject_neighborhood:
                    context_data[subject_neighborhood] = neighborhoods_data[subject_neighborhood].copy()
                    
                    # Add environmental risk data if available
                    if subject_neighborhood in lewc_data:
                        context_data[subject_neighborhood]["environmental_risk_data"] = lewc_data[subject_neighborhood]
                    
                    # Get coordinates for live data
                    coords = neighborhoods_data.get(subject_neighborhood, {}).get("coordinates", {})
                    lat = coords.get("lat")
                    lng = coords.get("lng")
                    
                    # Add live AQI data if requested
                    if any(term in query.lower() for term in ["aqi", "air quality", "pollution"]):
                        live_aqi = self._get_live_aqi(lat, lng)
                        if live_aqi:
                            context_data[subject_neighborhood]["live_aqi_data"] = live_aqi
                    
                    # Add live weather data if requested
                    weather_keywords = ["weather", "temperature", "hot", "cold", "wind", "humidity"]
                    if any(term in query.lower() for term in weather_keywords):
                        live_weather = self._get_live_weather(lat, lng)
                        if live_weather:
                            context_data[subject_neighborhood]["live_weather_data"] = live_weather
                else:
                    # If no specific neighborhood, include a sample of all data for general queries
                    context_data = dict(list(neighborhoods_data.items())[:5])  # Sample of 5 neighborhoods
            
            return json.dumps(context_data, indent=2) if context_data else None
            
        except Exception as e:
            print(f"Error getting relevant context: {e}")
            return None
    
    def _find_mentioned_neighborhoods(self, query: str, neighborhood_names: List[str]) -> List[str]:
        """Find neighborhoods mentioned in the query"""
        mentioned = []
        lower_query = query.lower()
        
        for name in sorted(neighborhood_names, key=len, reverse=True):
            if name.lower() in lower_query:
                mentioned.append(name)
                lower_query = lower_query.replace(name.lower(), "")
        
        return mentioned
    
    def _get_live_aqi(self, lat: float, lng: float) -> Optional[Dict]:
        """Fetch live Air Quality Index data"""
        if lat is None or lng is None:
            return None
        
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&current=us_aqi"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            aqi_value = data.get('current', {}).get('us_aqi')
            
            return {
                "live_aqi_value": aqi_value,
                "live_aqi_quality": self._aqi_value_to_quality(aqi_value)
            }
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not fetch live AQI data. {e}")
            return None
    
    def _get_live_weather(self, lat: float, lng: float) -> Optional[Dict]:
        """Fetch live weather data"""
        if lat is None or lng is None:
            return None
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            current = data.get('current', {})
            
            return {
                "current_temp_f": current.get('temperature_2m'),
                "feels_like_f": current.get('apparent_temperature'),
                "humidity_percent": current.get('relative_humidity_2m'),
                "wind_speed_mph": current.get('wind_speed_10m'),
                "description": self._wmo_code_to_description(current.get('weather_code'))
            }
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not fetch live weather data. {e}")
            return None
    
    def _aqi_value_to_quality(self, aqi: int) -> str:
        """Convert AQI value to quality description"""
        if aqi is None:
            return "Unknown"
        if 0 <= aqi <= 50:
            return "Good"
        elif 51 <= aqi <= 100:
            return "Moderate"
        elif 101 <= aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif 151 <= aqi <= 200:
            return "Unhealthy"
        elif 201 <= aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    def _wmo_code_to_description(self, code: int) -> str:
        """Convert WMO weather code to description"""
        if code is None:
            return "unknown conditions"
        
        mapping = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle", 
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        return mapping.get(code, "unknown conditions")
    
    def reset(self):
        """Reset the conversation state"""
        self.conversation_history = []
        self.conversation_subject = None
        
        # Reset Gemini chat if available
        if self.model:
            try:
                system_prompt = """
                You are an expert concierge for the city of Tempe, Arizona. Your tone should be friendly, professional, and natural.
                Keep responses concise and conversational for a web chat interface.
                When asked about highest/lowest scores, analyze ALL neighborhoods in the provided data and give specific names and values.
                """
                
                self.chat = self.model.start_chat(history=[
                    {'role': 'user', 'parts': [{'text': system_prompt}]},
                    {'role': 'model', 'parts': [{'text': "Hello! I'm ready to help you explore Tempe. What would you like to know?"}]}
                ])
            except Exception as e:
                print(f"Error resetting Gemini chat: {e}")
    
    def __call__(self, message: str, context: Optional[Dict] = None) -> str:
        """Allow the chatbot to be called directly"""
        return self.get_response(message, context)