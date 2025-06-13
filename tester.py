import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Make sure it's set in your .env file.")

# Configure the API client
genai.configure(api_key=GOOGLE_API_KEY)

# List available models
def list_models():
    models = genai.list_models()
    print("Available models:")
    for model in models:
        print(model.name)

# Run the function
list_models()
