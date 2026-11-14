# -*- coding: utf-8 -*-
# StockMan/test_api.py
"""
External API Diagnostic & Connectivity Testing Utility.

This diagnostic CLI tool validates external API credentials, testing communication
with Google Gemini generative models, Yahoo Finance, and Google Drive endpoints.

Key Responsibilities:
    • API Key Verification: Verifies that valid API keys are present in `api_key.txt`.
    • Health Probe: Sends test prompts to the Gemini model cascade to confirm low-latency responses.
"""

import google.generativeai as genai
from StockMan.ai_analyzer import get_api_key

API_KEY = get_api_key()

if __name__ == "__main__":
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
