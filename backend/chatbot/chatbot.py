import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

class UrbanVitalsChatbot:
    def __init__(self):
        """Initialize the Urban Vitals web chatbot with enhanced memory and CO2 tracking"""
        # Load environment variables
        load_dotenv()
        
        # Initialize conversation tracking with enhanced memory
        self.conversation_history = []
        self.conversation_context = {
            "current_neighborhood": None,
            "last_mentioned_neighborhoods": [],
            "last_discussed_topics": [],
            "user_preferences": {},
            "session_facts": {},  # Store key facts from the conversation
            "co2_stats": {
                "total_tokens": 0,
                "total_savings_kg": 0.0,
                "session_start": datetime.now()
            }
        }
        
        # Initialize Tandemn model
        self.model = None
        self.tandemn_api_key = None
        self.tandemn_endpoint = "https://api.tandemn.com/api/v1/chat/completions"
        self._initialize_tandemn()
        
        # Load static data
        self.refined_data = None
        self.lewc_data = None
        self.definitions_data = None
        self._load_data()
        
    def calculate_co2_savings(self, num_tokens: int, output_unit: str = 'kg') -> float:
        """
        Calculate CO2 savings from using Tandemn instead of commercial providers.
        Based on the formula from CO2-calculation.md
        
        Args:
            num_tokens (int): Number of tokens generated
            output_unit (str): 'kg' for kilograms, 'g' for grams, 'mg' for milligrams
        
        Returns:
            float: CO2 savings in specified unit
        """
        # Commercial provider parameters (using H100 GPUs)
        commercial_power = 2.8  # kW (4× H100 at 0.7 kW each)
        commercial_ci = 0.43    # kgCO2e/kWh (Azure data centers)
        commercial_tps = 100    # tokens/second
        embodied_co2 = 7000     # kgCO2e (4× H100 at 1750 kgCO2e each)
        lifetime_hours = 43800  # hours (5 years)
        
        # Tandemn parameters (using L40 GPUs)
        tandemn_power = 1.5     # kW (3× L40 at 0.5 kW each)
        tandemn_ci = 0.15       # kgCO2e/kWh (N. California grid)
        tandemn_tps = 30        # tokens/second
        
        # Calculate commercial emissions per token
        commercial_operational = (commercial_power * commercial_ci) / commercial_tps
        commercial_embodied = embodied_co2 / (commercial_tps * lifetime_hours)
        commercial_total = commercial_operational + commercial_embodied
        
        # Calculate Tandemn emissions per token (no embodied carbon)
        tandemn_total = (tandemn_power * tandemn_ci) / tandemn_tps
        
        # Convert to per token (divide by 3600 to convert seconds to hours)
        savings_per_token = (commercial_total - tandemn_total) / 3600
        
        # Calculate total savings
        total_savings = savings_per_token * num_tokens
        
        # Convert to requested unit
        if output_unit.lower() == 'g':
            total_savings *= 1000  # Convert kg to grams
        elif output_unit.lower() == 'mg':
            total_savings *= 1000000  # Convert kg to milligrams
        
        return total_savings

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        Rough approximation: 1 token ≈ 4 characters for English text
        """
        if not text:
            return 0
        # More sophisticated estimation considering word boundaries
        words = len(text.split())
        chars = len(text)
        # Average of character-based and word-based estimation
        char_based = chars / 4
        word_based = words * 1.3  # Average 1.3 tokens per word
        return int((char_based + word_based) / 2)

    def update_co2_stats(self, user_tokens: int, bot_tokens: int):
        """Update session CO2 statistics"""
        total_new_tokens = user_tokens + bot_tokens
        new_savings = self.calculate_co2_savings(total_new_tokens)
        
        self.conversation_context["co2_stats"]["total_tokens"] += total_new_tokens
        self.conversation_context["co2_stats"]["total_savings_kg"] += new_savings

    def get_co2_summary(self) -> Dict[str, Any]:
        """Get current session CO2 summary"""
        stats = self.conversation_context["co2_stats"]
        session_duration = datetime.now() - stats["session_start"]
        
        return {
            "total_tokens": stats["total_tokens"],
            "total_savings_kg": stats["total_savings_kg"],
            "session_duration_minutes": session_duration.total_seconds() / 60,
            "savings_formatted": self.format_co2_savings(stats["total_savings_kg"])
        }

    def format_co2_savings(self, savings_kg: float) -> str:
        """Format CO2 savings for display"""
        if savings_kg < 0.001:
            return f"{savings_kg * 1000000:.2f} mg"
        elif savings_kg < 1:
            return f"{savings_kg * 1000:.2f} g"
        else:
            return f"{savings_kg:.3f} kg"
        
    def _initialize_tandemn(self):
        """Initialize Tandemn AI model with enhanced memory instructions"""
        tandemn_api_key = os.getenv("TANDEMN_API_KEY")
        
        if not tandemn_api_key:
            print("Warning: TANDEMN_API_KEY environment variable not set. Chatbot will use fallback responses.")
            return
        
        try:
            self.tandemn_api_key = tandemn_api_key
            self.model = "casperhansen/deepseek-r1-distill-llama-70b-awq"
            
            # Test the connection with a simple request
            headers = {
                "Authorization": f"Bearer {self.tandemn_api_key}",
                "Content-Type": "application/json"
            }
            
            test_data = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_completion_tokens": 10
            }
            
            response = requests.post(self.tandemn_endpoint, headers=headers, json=test_data, timeout=10)
            
            if response.status_code == 200:
                print("Tandemn model configured successfully")
            else:
                print(f"Tandemn connection test failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                self.model = None
                self.tandemn_api_key = None
                
        except Exception as e:
            print(f"Failed to initialize Tandemn: {e}")
            self.model = None
            self.tandemn_api_key = None
    
    def _load_data(self):
        """Load neighborhood data from JSON files"""
        refined_path = "backend/data-lib/Tempe-AZ-data.json"
        lewc_path = "backend/data-lib/Tempe-AZ-lewc-data.json"
        definitions_path = "backend/data-lib/summary.json"
        
        # Try alternative paths if the main ones don't work
        alternative_paths = [
            ("data-lib/Tempe-AZ-data.json", "data-lib/Tempe-AZ-lewc-data.json", "data-lib/summary.json"),
            ("Tempe-AZ-data.json", "Tempe-AZ-lewc-data.json", "summary.json"),
        ]
        
        # Load refined data
        try:
            with open(refined_path, 'r', encoding='utf-8') as f:
                self.refined_data = json.load(f)
        except FileNotFoundError:
            for alt_refined, _, _ in alternative_paths:
                try:
                    with open(alt_refined, 'r', encoding='utf-8') as f:
                        self.refined_data = json.load(f)
                    break
                except FileNotFoundError:
                    continue
            else:
                print(f"Warning: Could not find refined data file")
                self.refined_data = {}
        except json.JSONDecodeError as e:
            print(f"Error parsing refined data: {e}")
            self.refined_data = {}
        
        # Load LEWC data
        try:
            with open(lewc_path, 'r', encoding='utf-8') as f:
                self.lewc_data = json.load(f)
        except FileNotFoundError:
            for _, alt_lewc, _ in alternative_paths:
                try:
                    with open(alt_lewc, 'r', encoding='utf-8') as f:
                        self.lewc_data = json.load(f)
                    break
                except FileNotFoundError:
                    continue
            else:
                print(f"Warning: Could not find LEWC data file")
                self.lewc_data = {}
        except json.JSONDecodeError as e:
            print(f"Error parsing LEWC data: {e}")
            self.lewc_data = {}
        
        # Load definitions data
        try:
            with open(definitions_path, 'r', encoding='utf-8') as f:
                self.definitions_data = json.load(f)
        except FileNotFoundError:
            for _, _, alt_definitions in alternative_paths:
                try:
                    with open(alt_definitions, 'r', encoding='utf-8') as f:
                        self.definitions_data = json.load(f)
                    break
                except FileNotFoundError:
                    continue
            else:
                print(f"Warning: Could not find definitions data file")
                self.definitions_data = []
        except json.JSONDecodeError as e:
            print(f"Error parsing definitions data: {e}")
            self.definitions_data = []

    def _update_conversation_context(self, user_message: str, bot_response: str):
        """Update conversation context based on the interaction"""
        user_lower = user_message.lower()
        response_lower = bot_response.lower()
        
        # Extract neighborhood mentions from the response
        mentioned_neighborhoods = []
        if self.refined_data:
            for neighborhood_name in self.refined_data.keys():
                if neighborhood_name.lower() in response_lower:
                    mentioned_neighborhoods.append(neighborhood_name)
        
        # Update current neighborhood if one was specifically mentioned
        if mentioned_neighborhoods:
            self.conversation_context["current_neighborhood"] = mentioned_neighborhoods[0]
            self.conversation_context["last_mentioned_neighborhoods"] = mentioned_neighborhoods[:3]  # Keep last 3
        
        # Track topics discussed
        topics = []
        if "green score" in user_lower or "green score" in response_lower:
            topics.append("green_score")
        if "air quality" in user_lower or "air quality" in response_lower:
            topics.append("air_quality")
        if "water quality" in user_lower or "water quality" in response_lower:
            topics.append("water_quality")
        if "walkability" in user_lower or "walkability" in response_lower:
            topics.append("walkability")
        if "lewc" in user_lower or "environmental risk" in user_lower:
            topics.append("lewc_score")
        if "co2" in user_lower or "carbon" in user_lower or "emissions" in user_lower:
            topics.append("co2_savings")
        
        if topics:
            self.conversation_context["last_discussed_topics"] = topics
        
        # Store important facts from responses
        if "highest" in response_lower and "score" in response_lower:
            # Extract the neighborhood with highest score
            for neighborhood in mentioned_neighborhoods:
                self.conversation_context["session_facts"][f"highest_score_neighborhood"] = neighborhood
        
        if "lowest" in response_lower and "score" in response_lower:
            for neighborhood in mentioned_neighborhoods:
                self.conversation_context["session_facts"][f"lowest_score_neighborhood"] = neighborhood

    def _resolve_pronouns_and_references(self, message: str) -> str:
        """Resolve pronouns and references in user messages"""
        message_lower = message.lower()
        resolved_message = message
        
        # Handle common pronoun references
        pronoun_patterns = ["it", "its", "that neighborhood", "there", "this place", "that place"]
        
        has_pronoun = any(pattern in message_lower for pattern in pronoun_patterns)
        
        if has_pronoun and self.conversation_context["current_neighborhood"]:
            current_neighborhood = self.conversation_context["current_neighborhood"]
            
            # Replace pronouns with the actual neighborhood name
            resolved_message = message.replace(" it ", f" {current_neighborhood} ")
            resolved_message = resolved_message.replace(" its ", f" {current_neighborhood}'s ")
            resolved_message = resolved_message.replace("that neighborhood", current_neighborhood)
            resolved_message = resolved_message.replace(" there", f" in {current_neighborhood}")
            resolved_message = resolved_message.replace("this place", current_neighborhood)
            resolved_message = resolved_message.replace("that place", current_neighborhood)
            
            # Handle sentence-starting pronouns
            if message_lower.startswith("it "):
                resolved_message = resolved_message.replace("It ", f"{current_neighborhood} ", 1)
            if message_lower.startswith("its "):
                resolved_message = resolved_message.replace("Its ", f"{current_neighborhood}'s ", 1)
        
        return resolved_message

    def _build_context_prompt(self, message: str, relevant_context: str) -> str:
        """Build a comprehensive context prompt including conversation history and CO2 info"""
        
        # Get recent conversation history
        recent_history = ""
        if len(self.conversation_history) > 0:
            recent_history = "Recent Conversation:\n"
            for i, exchange in enumerate(self.conversation_history[-3:]):  # Last 3 exchanges
                recent_history += f"User: {exchange['user']}\n"
                if exchange.get('response'):
                    recent_history += f"Assistant: {exchange['response']}\n"
            recent_history += "\n"
        
        # Build current context
        context_info = ""
        if self.conversation_context["current_neighborhood"]:
            context_info += f"Currently discussing: {self.conversation_context['current_neighborhood']}\n"
        
        if self.conversation_context["last_mentioned_neighborhoods"]:
            context_info += f"Recently mentioned neighborhoods: {', '.join(self.conversation_context['last_mentioned_neighborhoods'])}\n"
        
        if self.conversation_context["last_discussed_topics"]:
            topics = [topic.replace('_', ' ').title() for topic in self.conversation_context["last_discussed_topics"]]
            context_info += f"Recent topics: {', '.join(topics)}\n"
        
        if self.conversation_context["session_facts"]:
            context_info += f"Session facts: {json.dumps(self.conversation_context['session_facts'], indent=2)}\n"
        
        # Add CO2 context
        co2_summary = self.get_co2_summary()
        context_info += f"\nCO2 Session Stats:\n"
        context_info += f"- Total tokens processed: {co2_summary['total_tokens']}\n"
        context_info += f"- CO2 savings: {co2_summary['savings_formatted']}\n"
        context_info += f"- Session duration: {co2_summary['session_duration_minutes']:.1f} minutes\n"
        
        # Check if the message is asking for definitions or explanations
        definition_keywords = ['what is', 'what does', 'define', 'meaning of', 'explain', 'definition']
        is_definition_query = any(keyword in message.lower() for keyword in definition_keywords)
        
        # Check if asking about CO2/carbon/emissions
        co2_keywords = ['co2', 'carbon', 'emissions', 'footprint', 'savings', 'environment impact']
        is_co2_query = any(keyword in message.lower() for keyword in co2_keywords)
        
        definitions_context = ""
        if is_definition_query and self.definitions_data:
            definitions_context = f"""
Available Term Definitions:
{json.dumps(self.definitions_data, indent=2)}
"""
        
        co2_context = ""
        if is_co2_query:
            co2_context = f"""
CO2 Calculation Information:
- This chatbot uses Tandemn's eco-friendly AI infrastructure
- Savings come from: refurbished hardware (avoiding embodied carbon) + green energy
- Current session has saved: {co2_summary['savings_formatted']} of CO2 emissions
- Formula: Commercial providers use new H100 GPUs with high embodied carbon, Tandemn uses refurbished L40 GPUs with negligible embodied carbon
"""
        
        prompt = f"""
CONTEXT INSTRUCTIONS:
- Maintain conversation continuity and remember what has been discussed
- Use the conversation history and context to understand references like "it", "that neighborhood", etc.
- The user's question may reference previously discussed neighborhoods or topics
- If asked about CO2 savings or environmental impact, explain the benefits of using eco-friendly AI

{recent_history}
{context_info}
{definitions_context}
{co2_context}

Current Neighborhood Data:
{relevant_context if relevant_context else "General query - no specific neighborhood data"}

IMPORTANT: If the user is asking about a specific metric (like "how is its water quality") and we previously discussed a neighborhood, provide the specific data for that neighborhood.

User Question: {message}

Please provide a helpful, contextual response that considers the entire conversation.
"""
        
        return prompt

    def get_response(self, message: str, context: Optional[Dict] = None) -> str:
        """Generate a response with enhanced memory and context tracking including CO2 calculations"""
        try:
            # Estimate tokens for user message
            user_tokens = self.estimate_tokens(message)
            
            # Resolve pronouns before processing
            resolved_message = self._resolve_pronouns_and_references(message)
            
            # Add message to conversation history
            self.conversation_history.append({
                "user": message,
                "resolved_user": resolved_message,
                "response": None,
                "timestamp": datetime.now().isoformat(),
                "user_tokens": user_tokens
            })
            
            # Handle empty messages
            if not message.strip():
                return "I'm here to help! Ask me about neighborhood data, green scores, or sustainability metrics."
            
            # Use provided context or fall back to loaded data
            if context and context.get("neighborhoods"):
                neighborhoods_data = self._convert_web_context_to_data_format(context["neighborhoods"])
                selected_neighborhood = context.get("selected_neighborhood")
            else:
                neighborhoods_data = self.refined_data
                selected_neighborhood = None
            
            # Update current neighborhood from context if provided
            if selected_neighborhood and selected_neighborhood.get("name"):
                self.conversation_context["current_neighborhood"] = selected_neighborhood["name"]
            
            # Get relevant context for the query (use resolved message)
            relevant_context = self._get_relevant_context(
                resolved_message, 
                neighborhoods_data, 
                self.lewc_data, 
                selected_neighborhood
            )
            
            # Generate response
            if self.tandemn_api_key and self.model:
                response = self._get_tandemn_response(resolved_message, relevant_context)
            else:
                response = self._get_enhanced_fallback_response(resolved_message, neighborhoods_data, selected_neighborhood)
            
            # Estimate tokens for bot response
            bot_tokens = self.estimate_tokens(response)
            
            # Update CO2 statistics
            self.update_co2_stats(user_tokens, bot_tokens)
            
            # Update conversation context
            self._update_conversation_context(resolved_message, response)
            
            # Update conversation history with response and token counts
            if self.conversation_history:
                self.conversation_history[-1]["response"] = response
                self.conversation_history[-1]["bot_tokens"] = bot_tokens
                self.conversation_history[-1]["co2_savings"] = self.calculate_co2_savings(user_tokens + bot_tokens)
            
            return response
                
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

    def _get_tandemn_response(self, message: str, relevant_context: str) -> str:
        """Get response from Tandemn API with full context"""
        try:
            # Build comprehensive context prompt
            context_prompt = self._build_context_prompt(message, relevant_context)
            
            # Prepare the request for Tandemn API
            headers = {
                "Authorization": f"Bearer {self.tandemn_api_key}",
                "Content-Type": "application/json"
            }
            
            # Format messages for Tandemn API - simplified to avoid potential issues
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert concierge for the city of Tempe, Arizona. Your tone should be friendly, professional, and natural.

You MUST remember and maintain context throughout the conversation.
When a user refers to "it", "that neighborhood", "there", etc., use the conversation context to understand what they're referring to.
If you mention a neighborhood or answer a question about one, remember that for follow-up questions.
Always consider the full conversation history when responding.

You are powered by Tandemn's eco-friendly AI infrastructure that uses refurbished hardware and green energy.
If asked about environmental impact, CO2 savings, or sustainability, mention how this conversation is helping save carbon emissions.

Your primary goal is to answer questions using the specific JSON data provided with each user query.
When asked about highest/lowest scores, analyze ALL neighborhoods and provide specific names and values.
When comparing neighborhoods, provide specific numerical comparisons.
When explaining scores, break down the components that contribute to the score.

Keep responses concise and conversational for a web chat interface."""
                },
                {
                    "role": "user",
                    "content": f"Context: {relevant_context}\n\nUser Question: {message}"
                }
            ]
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_completion_tokens": 1000,
                "stream": False
            }
            
            # Send to Tandemn with timeout
            response = requests.post(self.tandemn_endpoint, headers=headers, json=data, timeout=30)
            
            # Check for successful response
            if response.status_code == 200:
                response_data = response.json()
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    return response_data['choices'][0]['message']['content']
                else:
                    print(f"Unexpected response format: {response_data}")
                    return self._get_enhanced_fallback_response(message, {}, None)
            else:
                print(f"Tandemn API error: {response.status_code} - {response.text}")
                return self._get_enhanced_fallback_response(message, {}, None)
            
        except requests.exceptions.Timeout:
            print("Tandemn API request timed out")
            return self._get_enhanced_fallback_response(message, {}, None)
        except requests.exceptions.RequestException as e:
            print(f"Tandemn API request error: {e}")
            return self._get_enhanced_fallback_response(message, {}, None)
        except Exception as e:
            print(f"Error getting Tandemn response: {e}")
            return self._get_enhanced_fallback_response(message, {}, None)

    def _get_enhanced_fallback_response(self, message: str, neighborhoods_data: Dict, selected_neighborhood: Dict) -> str:
        """Enhanced fallback with context awareness and CO2 info"""
        message_lower = message.lower().strip()
        
        # Handle CO2/carbon/emissions queries
        if any(keyword in message_lower for keyword in ['co2', 'carbon', 'emissions', 'footprint', 'savings', 'environmental impact']):
            co2_summary = self.get_co2_summary()
            return f"🌱 Great question about environmental impact! This conversation has already saved {co2_summary['savings_formatted']} of CO2 emissions by using Tandemn's eco-friendly AI infrastructure instead of traditional commercial providers. We achieve this through refurbished hardware (avoiding embodied carbon from manufacturing) and green energy sources. Every token we process together helps reduce the carbon footprint of AI!"
        
        # Handle greetings
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            if self.conversation_context["current_neighborhood"]:
                return f"Hello! We were just discussing {self.conversation_context['current_neighborhood']}. What else would you like to know?"
            return "Hello! I'm your Urban Vitals assistant powered by eco-friendly AI. What would you like to know about Tempe's neighborhoods?"
        
        # Handle contextual queries about current neighborhood
        current_neighborhood = self.conversation_context.get("current_neighborhood")
        if current_neighborhood and current_neighborhood in self.refined_data:
            neighborhood_data = self.refined_data[current_neighborhood]
            
            # Water quality question
            if "water quality" in message_lower:
                water_quality = neighborhood_data.get("homeowners", {}).get("water_quality", "N/A")
                water_exp = neighborhood_data.get("homeowners", {}).get("water_quality_exp", "")
                response = f"{current_neighborhood} has a water quality score of {water_quality}/10."
                if water_exp:
                    response += f" {water_exp}"
                return response
            
            # Air quality question
            if "air quality" in message_lower:
                air_quality = neighborhood_data.get("homeowners", {}).get("air_quality", "N/A")
                air_exp = neighborhood_data.get("homeowners", {}).get("aqi_reason", "")
                response = f"{current_neighborhood} has an air quality score of {air_quality}/10."
                if air_exp:
                    response += f" {air_exp}"
                return response
            
            # Other metrics
            metrics = {
                "walkability": "walkability",
                "safety": "public_safety",
                "cleanliness": "cleanliness",
                "green": "greenery_coverage"
            }
            
            for keyword, metric in metrics.items():
                if keyword in message_lower:
                    score = neighborhood_data.get("homeowners", {}).get(metric, "N/A")
                    return f"{current_neighborhood} has a {keyword} score of {score}/10."
        
        # Handle definition queries
        definition_keywords = ['what is', 'what does', 'define', 'meaning of', 'explain']
        if any(keyword in message_lower for keyword in definition_keywords):
            return self._handle_definition_query(message_lower)
        
        # Handle highest/lowest queries
        if any(phrase in message_lower for phrase in ["highest green score", "best green score", "top green score"]):
            return self._find_highest_green_score(neighborhoods_data)
        
        if any(phrase in message_lower for phrase in ["lowest green score", "worst green score", "bottom green score"]):
            return self._find_lowest_green_score(neighborhoods_data)
        
        return "That's a great question, but I don't have that information right now. Feel free to ask about neighborhoods, green scores, or our eco-friendly AI system!"

    def _handle_definition_query(self, message_lower: str) -> str:
        """Handle definition queries using the definitions data"""
        for definition in self.definitions_data:
            if isinstance(definition, dict) and 'term' in definition:
                term = definition['term'].lower()
                term_words = term.replace('_', ' ').replace('-', ' ').split()
                
                if any(word in message_lower for word in term_words if len(word) > 3):
                    return f"**{definition['term'].replace('_', ' ').title()}**: {definition['description']}"
        
        return "I can help explain Urban Vitals terms like green_score, air_quality, walkability, lewc_score, and many others. What specific term would you like me to explain?"

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
            # Update context
            self.conversation_context["current_neighborhood"] = highest_neighborhood
            return f"{highest_neighborhood} has the highest Green Score at {highest_score}/10."
        else:
            return "I couldn't find green score data for the neighborhoods."

    def _find_lowest_green_score(self, neighborhoods_data: Dict) -> str:
        """Find neighborhood with lowest green score"""
        if not neighborhoods_data:
            return "I don't have neighborhood data available right now."
        
        lowest_score = 11
        lowest_neighborhood = None
        
        for name, data in neighborhoods_data.items():
            score = data.get("green_score", 11)
            if score < lowest_score and score > 0:
                lowest_score = score
                lowest_neighborhood = name
        
        if lowest_neighborhood:
            # Update context
            self.conversation_context["current_neighborhood"] = lowest_neighborhood
            return f"{lowest_neighborhood} has the lowest Green Score at {lowest_score}/10."
        else:
            return "I couldn't find green score data for the neighborhoods."

    def _get_relevant_context(self, query: str, neighborhoods_data: Dict, lewc_data: Dict, selected_neighborhood: Dict) -> str:
        """Get relevant context data for the query with conversation awareness"""
        try:
            context_data = {}
            
            # For questions about highest/lowest scores, include all neighborhoods
            if any(phrase in query.lower() for phrase in ["highest", "lowest", "best", "worst", "top", "bottom", "compare"]):
                context_data = neighborhoods_data.copy()
            else:
                # Determine subject neighborhood
                subject_neighborhood = None
                
                # First check if we have a current neighborhood in context
                if self.conversation_context.get("current_neighborhood"):
                    subject_neighborhood = self.conversation_context["current_neighborhood"]
                
                # Override with selected neighborhood if provided
                if selected_neighborhood and selected_neighborhood.get("name"):
                    subject_neighborhood = selected_neighborhood["name"]
                
                # Look for mentioned neighborhoods in query
                if not subject_neighborhood:
                    mentioned_neighborhoods = self._find_mentioned_neighborhoods(query, neighborhoods_data.keys())
                    if mentioned_neighborhoods:
                        subject_neighborhood = mentioned_neighborhoods[0]
                
                # If we have a subject, fetch its data
                if subject_neighborhood and subject_neighborhood in neighborhoods_data:
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
                    # If no specific neighborhood, include a sample for general queries
                    context_data = dict(list(neighborhoods_data.items())[:5])
            
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
        """Reset the conversation state and CO2 tracking"""
        self.conversation_history = []
        self.conversation_context = {
            "current_neighborhood": None,
            "last_mentioned_neighborhoods": [],
            "last_discussed_topics": [],
            "user_preferences": {},
            "session_facts": {},
            "co2_stats": {
                "total_tokens": 0,
                "total_savings_kg": 0.0,
                "session_start": datetime.now()
            }
        }
        
        print("Conversation state and CO2 tracking reset")

    def __call__(self, message: str, context: Optional[Dict] = None) -> str:
        """Allow the chatbot to be called directly"""
        return self.get_response(message, context)