# app/services/data_loader.py
import httpx
from typing import Dict, Any

TECHNOLOGY_API_URL = "https://otmt.iiitd.edu.in/data/technologies"

async def load_technology_data(app_state: Dict[str, Any]):
    """
    Fetches technology data from the API on server startup and caches it.
    """
    print("Fetching technology data...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(TECHNOLOGY_API_URL)
            response.raise_for_status()  # Raises an exception for 4xx/5xx errors
            app_state["technologies"] = response.json()
            print(f"Successfully cached {len(app_state['technologies'])} technologies.")
    except httpx.RequestError as e:
        print(f"FATAL: Error fetching technology data: {e}")
        print("The chatbot will not be able to answer questions about technologies.")
        app_state["technologies"] = []
    except Exception as e:
        print(f"An unexpected error occurred during data fetching: {e}")
        app_state["technologies"] = []