import google.generativeai as genai
from ai_analyzer import get_api_key

API_KEY = get_api_key()

if not API_KEY:
    print("Error: No Gemini API Key found. Please add it to your api_key.txt file in the project root.")
    exit(1)

print("Contacting Google Servers...")
genai.configure(api_key=API_KEY)

print("\nModels available for your API Key:")
try:
    # This is the "Call ListModels" command the error mentioned
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            print(f" - {model.name}")
except Exception as e:
    print(f"Failed to fetch models: {e}")
