from django.db import models

# Create your models here.
import os
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv
import geocoder

class ASTRAChatbot:
    def __init__(self, userid):
        # Load environment variables from a .env file
        load_dotenv()
        
        # Set up API keys and MongoDB connection
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.mongo_uri = os.getenv("MONGO_URI")
        ID =userid
        
        genai.configure(api_key=self.api_key)
        
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[ID]
        self.collection = self.db['chat_history']
        self.history_db = self.db['history']
        
        # Create the model configuration
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-002",
            generation_config=generation_config,
            system_instruction=self.get_system_instruction(),
        )
        
        # Start the chat session with initial context
        self.chat_session = self.model.start_chat(history=list(self.history_db.find()))

    @staticmethod
    def get_system_instruction(loc):
        print(loc)
        return (
            f"You are ASTRA, an advanced multilingual chatbot designed to function as a personal tourism assistant and guide. You can answer questions related to travel planning, destination recommendations, local attractions, accommodations, transportation, and all tourism-related queries. Your primary goal is to assist users with inquiries related to travel and tourism, including popular tourist spots, events, cultural experiences, and essential travel information in and around {loc['city']}.\n\n"

            """    
            Capabilities:

                Destination Assistance: Provide detailed information about popular tourist attractions, landmarks, museums, parks, and cultural sites.
                Travel Planning: Help users plan their trips with suggested itineraries, routes, and personalized travel recommendations.
                Local Information: Share relevant details about local weather, transportation options, nearby restaurants, accommodations, and events happening in {loc['city']}.
                Personalized Suggestions: Offer tailored advice for travelers based on their interests, such as adventure, relaxation, family outings, or budget-friendly trips.
                Ticketing Support: Assist users with the ticket booking process for attractions, events, public transportation, and guided tours.
                Emergency Assistance: Provide quick access to contact information for local emergency services, such as hospitals, police, and embassies.
                Cultural Guidance: Help users understand local traditions, etiquette, language phrases, and currency-related tips.
                Response Guidelines:

                Tourism-Related Queries: If a user asks a question about destinations, itineraries, or local attractions, respond with accurate and informative suggestions to enhance their travel experience.
                General Travel Assistance: For general queries such as local amenities, transportation, or packing tips, provide practical and relevant advice in a friendly tone.
                Unrelated Questions: If a user poses a question unrelated to tourism or travel, respond with:
                "I'm sorry, but I specialize in assisting with travel and tourism-related questions. Let me know how I can help you with your journey!"
                Tone and Style:

                Use a warm, enthusiastic, and approachable tone in all interactions.
                Provide clear, concise, and actionable advice while maintaining a friendly demeanor.
                Be empathetic and polite, ensuring users feel comfortable and supported throughout their planning.
                User Interaction Protocol:

                Greet users warmly and ask about their travel goals or current plans.
                Encourage users to share their preferences, such as travel style, budget, or interests.
                Provide well-structured responses that are easy to follow and implement.
                Maintain a positive and supportive tone to inspire confidence in users' travel decisions.""")
    @staticmethod
    def get_location_by_ip():
        location = geocoder.ip('me')
        if location and location.latlng and location.city:
            return {
                "city": location.city,
                "country": location.country,
                "latitude": location.latlng[0],
                "longitude": location.latlng[1]
            }
        else:
            return {
                "city": "unknown",
                "country": "unknown",
                "latitude": "0",
                "longitude": "0"
            }

    def query_mongodb(self, user_input):
        result = self.history_db.find_one({"query": user_input})
        return result["response"] if result else None

    def get_response(self, user_input):
        # Check MongoDB first
        db_response = self.query_mongodb(user_input)
        if db_response:
            return db_response
        else:
            # Classify the query first
            #query_class = PredictClass(user_input).predict_class()
            
            # Conditional response for ticketing and reservations
            """ if query_class == "Ticketing and Reservations":
                return (
                    "If you would like to book a ticket, please click on the following link or type `/tickets` to proceed with the booking process:\n"
                    "[Book Tickets](https://example.com/book-tickets)"
                ) """
            
            # Get response from Gemini if not in MongoDB
            response = self.chat_session.send_message(user_input)
            self.collection.insert_one({"query": user_input, "response": response.text})
            return response.text

    def interact(self):
        print("ASTRA: How can I assist you today?")
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    self.client.close()
                    break
                
                bot_response = self.get_response(user_input)
                print("ASTRA:", bot_response)
            except Exception as e:
                print("An error occurred:", e)


class PredictClass:
    def __init__(self, query):
        self.query = query
        
        # Load environment variables from a .env file
        load_dotenv()
        
        # Set up API keys
        self.api_key = os.getenv("GEMINI_API_KEY_2")
        genai.configure(api_key=self.api_key)
        
        # Define possible query classes
        self.possible_classes = [
            "Museum Information", "Exhibits and Artifacts", "Ticketing and Reservations", 
            "Visitor Information and Amenities", "Events and Programs", "Navigation and Directions", 
            "Basic General Inquiry", "User Account and Previous Visits", "Ticket Verification",
            "Feedback and Support", "Unhandled or Out-of-Scope Queries"
        ]
        
        # Model configuration
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 128,
            "response_mime_type": "text/plain",
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-002",
            generation_config=self.generation_config,
        )
        
        # Start a separate chat session for classification
        self.chat_session = self.model.start_chat()

    def predict_class(self):
        # Generate a classification prompt for the query
        prompt = f"Classify the following query into one of these categories: {', '.join(self.possible_classes)}\n\nQuery: {self.query}"
        
        # Get the predicted class from Gemini API
        response = self.chat_session.send_message(prompt)
        return response.text.strip()


if __name__ == "__main__":
    pass
