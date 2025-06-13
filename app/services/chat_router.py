# app/services/chat_router.py
import os
import json
import google.generativeai as genai
from typing import Dict, List
from app.schemas import ChatHistoryItem

# Configure the Gemini client
# Note: It's good practice to configure this once in main.py on startup,
# but having it here also works as long as the key is loaded.
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- FIXED ROUTER PROMPT ---
# We use f-string formatting and escape literal curly braces with double braces {{ }}
ROUTER_PROMPT = """
You are an expert intent router for a university's Tech Transfer Office chatbot.
Your task is to analyze the user's query and the conversation history to determine the user's intent(s).
Your response MUST be a valid JSON object.

The main intents are:
- "tech_query": The user is asking about specific technologies, a domain of technologies, or available innovations.
- "trl_assessment": The user wants to start or continue a Technology Readiness Level (TRL) assessment for a NEW idea.
- "general_inquiry": The user is asking a general question about OTMT, contacts, processes, or something not covered.

The user can have multiple intents. Your output should be a JSON object with a single key "intents", which is a list of intent objects.
For "tech_query", extract entities like "name", "genre", or "keywords".

**CRITICAL RULE: If the "Current User Query" is a follow-up question (e.g., uses "it", "its", "they", "what about...") you MUST look at the "Conversation History" to identify the primary subject (like a technology name) and include it in the entities of your response.**

Here is the schema of a technology in our database. Use this to help you identify what a user might be asking about.
Technology Schema:
{{
  "name": "string",
  "description": "string",
  "genre": "string (e.g., CV, AI, Health)",
  "innovators": ["list of names"],
  "advantages": ["list of strings"],
  "applications": ["list of strings"],
  "trl": "number (1-9)",
  "patent": "string"
}}

Example 1:
Query: "Tell me about Seek Suspect"
History: []
Output:
{{
  "intents": [
    {{"type": "tech_query", "entities": {{"name": "Seek Suspect"}}}}
  ]
}}

Example 2:
Query: "Who do I contact and what do you have in biotech?"
History: []
Output:
{{
  "intents": [
    {{"type": "general_inquiry", "entities": {{"keywords": "contact"}}}},
    {{"type": "tech_query", "entities": {{"genre": "biotech"}}}}
  ]
}}

Example 3:
Query: "What are its applications?"
History: [{{"role": "user", "parts": ["Tell me about Seek Suspect"]}}, {{"role": "model", "parts": ["Seek Suspect is a CV technology..."]}}]
Output:
{{
  "intents": [
    {{"type": "tech_query", "entities": {{"name": "Seek Suspect", "keywords": "applications"}}}}
  ]
}}

Conversation History:
{history}

Current User Query:
"{query}"

JSON Response:
"""


async def get_intent(query: str, history: List[ChatHistoryItem]) -> Dict:
    """Uses Gemini to classify the user's intent and extract entities."""
    router_model = genai.GenerativeModel('gemini-1.5-flash-latest')

    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")

    history_str = json.dumps([item.dict() for item in history])
    
    # --- FIXED FORMATTING ---
    # We now construct the prompt using an f-string
    prompt = f"""{ROUTER_PROMPT.format(history=history_str, query=query)}"""

    try:
        response = await router_model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        # A basic check to handle potential malformed text before the JSON
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            clean_json_str = response_text[json_start:json_end]
            return json.loads(clean_json_str)
        else:
            raise ValueError("No valid JSON object found in the response.")

    except Exception as e:
        print(f"Router Error: {e}. Falling back to general inquiry.")
        return {"intents": [{"type": "general_inquiry", "entities": {}}]}