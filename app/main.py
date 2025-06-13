# app/main.py
import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

# Load environment variables from .env file
load_dotenv()

from app.schemas import ChatRequest
from app.services.data_loader import load_technology_data
from app.services.chat_router import get_intent
from app.services.context_builder import build_context_and_prompt
import google.generativeai as genai

# --- FastAPI App Initialization ---
app = FastAPI(title="Tech-Transfer Pal API")

# Global state to hold cached data
app_state = {}

# --- CORS Configuration ---
# Allows your React frontend to communicate with this backend
origins = [
    "http://localhost:3000",  # Default React dev server
    # Add your production frontend URL here later
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Server Startup Event ---
@app.on_event("startup")
async def startup_event():
    # Configure the Gemini client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    genai.configure(api_key=api_key)
    
    # Load technology data into the app_state
    await load_technology_data(app_state)


# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"Hello": "Welcome to the Tech-Transfer Pal API"}


@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    """
    Main chat endpoint that orchestrates the two-LLM call process.
    """
    # 1. ROUTER: Get the user's intent
    intent_data = await get_intent(request.message, request.history)
    print(f"Detected Intent: {intent_data}")
    
    # 2. CONTEXT BUILDER: Prepare context and the final system prompt
    all_technologies = app_state.get("technologies", [])
    prompt_details = build_context_and_prompt(intent_data, all_technologies)
    
    # 3. SYNTHESIZER: Generate the final, streamed response
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    # Construct chat history for the final call
    # The system prompt is now dynamic based on intent
    final_history = [{'role': 'user', 'parts': [prompt_details['system_prompt']]}]
    final_history.append({'role': 'model', 'parts': ["Hello! I'm Tech-Transfer Pal. I'm ready to assist you."]})
    
    # Add the conversation history from the client
    for item in request.history:
        final_history.append(item.dict())
        
    # Add the RAG context as a separate message for the model to process
    if prompt_details['context']:
       final_history.append({'role': 'user', 'parts': [prompt_details['context']]})
       final_history.append({'role': 'model', 'parts': ["Okay, I have the context. I will use it to answer the next question."]})

    chat = model.start_chat(history=final_history)
    
    async def event_stream():
        try:
            # Send the user's actual message to get the final response
            response = chat.send_message(request.message, stream=True)
            for chunk in response:
                if chunk.text:
                    # Format as Server-Sent Event (SSE) for the frontend
                    data = {"content": chunk.text}
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01) # Small delay
        except Exception as e:
            print(f"Streaming Error: {e}")
            error_data = {"content": "Sorry, an unexpected error occurred."}
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            # Signal that the stream is complete
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")