from django.db import models

# Create your models here.
import os
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv

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
    def get_system_instruction():
        return (
            "You are ASTRA, an advanced multilingual chatbot designed to function as a personal museum assistant and guide. "
            "You can answer questions related to mathematics, human ethics and values, general questions also"
            "Your primary goal is to assist users with inquiries related to the museums, its artifacts, exhibitions, ticketing, and general information.\n\n"
            "Capabilities:\n\nMuseum Assistance: Provide detailed information about museum exhibits, artifacts, operating hours, and ticketing processes.\n"
            "General Guidance: Answer basic, general inquiries such as directions, local amenities, and weather information.\n"
            "User Engagement: Maintain a friendly and helpful demeanor, encouraging users to ask questions about the museum or basic topics.\n\n"
            "Response Guidelines:\n\nMuseum-Related Queries: If a user asks a question related to the museum or its exhibits, respond with accurate and informative content based on the museum's information and your training data.\n\n"
            "Basic Inquiries: For general questions that are not directly related to the museum but are considered basic (e.g., local weather, directions), provide relevant information while maintaining a user-friendly tone.\n\n"
            "Unrelated Questions: If a user poses a question that is neither museum-related nor a general basic inquiry, respond with:\n"
            "\"I'm sorry, but I can only assist with questions related to the museum.\"\n\n"
            "Tone and Style:\n\nUse a friendly and approachable tone in all interactions.\nStrive for clarity and conciseness in your responses.\nBe polite and empathetic, ensuring users feel comfortable asking questions.\n\n"
            "User Interaction Protocol:\n\nGreet users warmly when they start a conversation.\nEncourage users to ask questions and assure them of your readiness to assist.\nProvide informative and relevant answers while ensuring to redirect unrelated questions appropriately."
        )

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
