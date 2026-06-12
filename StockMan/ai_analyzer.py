import os
from google import genai
from google.genai import types

# Global flag to track API availability during runtime
AI_AVAILABLE = True


def get_api_key():
    """
    Retrieves the Gemini API Key from:
    1. A local 'api_key.txt' file in the project root folder.
    2. The 'GEMINI_API_KEY' environment variable.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    key_file_path = os.path.join(project_root, "api_key.txt")
    
    # 1. Try to read from api_key.txt
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str and not line_str.startswith("#"):
                        if line_str != "YOUR_API_KEY_HERE":
                            return line_str
        except Exception:
            pass

    # 2. Try to read from environment variable
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key

    return None


def get_market_insight(scrip_name, technical_signal, api_key=None):
    """
    Calls the Gemini API to analyze a stock using live Search grounding.
    Gracefully disables itself if billing/quota limits are hit.
    """
    global AI_AVAILABLE

    if not AI_AVAILABLE:
        return "[System] AI Analysis is disabled due to previous quota or API errors."

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create a file named 'api_key.txt' in the project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. You can get a free-of-cost API key (free version of Gemini) at: https://aistudio.google.com/"
        )

    try:
        # Initialize the modern GenAI client
        client = genai.Client(api_key=api_key)

        prompt = (
            f"You are a financial AI assisting a novice investor. "
            f"My local algorithmic scanner just flagged a '{technical_signal}' for the Indian stock {scrip_name}. "
            f"Using Google Search, find the latest news regarding this company and its sector. "
            f"Write a 3-paragraph plain-English explanation. Paragraph 1: What this technical signal generally means in simple terms. "
            f"Paragraph 2: A summary of the latest news/fundamentals for the company. "
            f"Paragraph 3: Any fundamental risks that might contradict the technical signal."
        )

        # Use the 2.5 Flash model explicitly listed in your terminal, with Google Search Grounding enabled
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[{"google_search": {}}]),
        )
        return response.text

    except Exception as e:
        # Generic error catching string-matching since the new SDK handles error classes differently
        error_msg = str(e).lower()
        if (
            "quota" in error_msg
            or "429" in error_msg
            or "exhausted" in error_msg
        ):
            AI_AVAILABLE = False
            return "[System] AI Analysis disabled: Free Tier Quota exhausted."
        elif (
            "permission" in error_msg
            or "400" in error_msg
            or "invalid api key" in error_msg
            or "403" in error_msg
        ):
            AI_AVAILABLE = False
            return "[System] AI Analysis disabled: API access denied or Invalid Key."
        else:
            return f"[System] Temporary network error while contacting AI: {e}"


def get_portfolio_sell_advice(scrip_list, api_key=None):
    """
    Calls the Gemini API to scan profitable portfolio holdings for institutional profit-booking advice using Google Search grounding.
    """
    global AI_AVAILABLE

    if not AI_AVAILABLE:
        return "[System] AI Analysis is disabled due to previous quota or API errors."

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create a file named 'api_key.txt' in the project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. You can get a free-of-cost API key (free version of Gemini) at: https://aistudio.google.com/"
        )

    try:
        client = genai.Client(api_key=api_key)

        scrip_details = ", ".join(
            [f"{ticker} ({gain:.2f}% gain)" for ticker, gain in scrip_list]
        )

        prompt = (
            f"Act as an aggregate equity research analyst. The user has an equity portfolio and is currently in the profit zone for the following Indian scrips: [{scrip_details}]. "
            f"Search recent institutional brokerage reports, market news, and consensus estimates (e.g., from major domestic and international research houses, "
            f"including Zee Business, Motilal Oswal Financial Services, ICICI Securities / ICICI Direct, HDFC Securities, and Axis Capital). "
            f"Identify if any broker houses have recently issued target-achieved alerts, downgrades, or specific advice recommending 'Profit Booking', 'Trimming 50%', or 'Exiting' these specific counters. "
            f"Generate a single, clean markdown table under the heading '**Table of Institutional Advice:**'. "
            f"The table must have the following columns: | Scrip | Broker House | Advice | Date of Report | "
            f"If no institutional sell/profit-booking advice exists for a scrip, list it in the table with 'N/A' for Broker House, 'Hold/Run Profits' for Advice, and 'N/A' for Date of Report. "
            f"Make sure to group the rows by Scrip. Do not output any other text or conversational filler, just the formatted markdown table."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[{"google_search": {}}]),
        )
        return response.text or "[System] Gemini returned an empty response. This can happen if safety filters blocked the output or if search grounding yielded no results."

    except Exception as e:
        error_msg = str(e).lower()
        if (
            "quota" in error_msg
            or "429" in error_msg
            or "exhausted" in error_msg
        ):
            AI_AVAILABLE = False
            return "[System] AI Analysis disabled: Free Tier Quota exhausted."
        elif (
            "permission" in error_msg
            or "400" in error_msg
            or "invalid api key" in error_msg
            or "403" in error_msg
        ):
            AI_AVAILABLE = False
            return "[System] AI Analysis disabled: API access denied or Invalid Key."
        else:
            return f"[System] Temporary network error while contacting AI: {e}"


def get_portfolio_buy_advice(scrip_list, api_key=None):
    """
    Calls the Gemini API to scan watchlist/active holdings for broker buy recommendations in the last 7 days using Google Search grounding.
    """
    global AI_AVAILABLE

    if not AI_AVAILABLE:
        return "[System] AI Analysis is disabled due to previous quota or API errors."

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create a file named 'api_key.txt' in the project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. You can get a free-of-cost API key (free version of Gemini) at: https://aistudio.google.com/"
        )

    try:
        client = genai.Client(api_key=api_key)

        scrip_details = ", ".join(scrip_list)

        prompt = (
            f"Act as an aggregate equity research analyst. The user tracks the following Indian scrips: [{scrip_details}]. "
            f"Search recent institutional brokerage reports, market news, and consensus estimates from the last seven days only (e.g., from major domestic and international research houses "
            f"like Motilal Oswal, Kotak Institutional Equities, ICICI Securities, Jefferies, Nomura, Morgan Stanley, etc.). "
            f"Identify if any broker houses have issued Buy / Buy Accumulate / Outperform recommendations for these specific counters in the last seven days. "
            f"Pick the top priority scrips (maximum 50 scrips) which are advised by the most number of broker houses in the last seven days. "
            f"Generate a single, clean markdown table under the heading '**Table of Institutional Buy Advice:**'. "
            f"The table must have the following columns: | Scrip | Buy Price Band | Target Price | Target Period | Broker House | Date of Report | "
            f"Do not include any scrip that has no buy recommendation or report in the last 7 days. "
            f"Sort the table rows by Scrip, or by the number of broker houses advising them. Do not output any other text or conversational filler, just the formatted markdown table."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[{"google_search": {}}]),
        )
        return response.text or "[System] Gemini returned an empty response. This can happen if safety filters blocked the output or if search grounding yielded no results."

    except Exception as e:
        error_msg = str(e).lower()
        if (
            "quota" in error_msg
            or "429" in error_msg
            or "exhausted" in error_msg
        ):
            AI_AVAILABLE = False
            return "[System] AI Analysis disabled: Free Tier Quota exhausted."
        elif (
            "permission" in error_msg
            or "400" in error_msg
            or "invalid api key" in error_msg
            or "403" in error_msg
        ):
            AI_AVAILABLE = False
            return "[System] AI Analysis disabled: API access denied or Invalid Key."
        else:
            return f"[System] Temporary network error while contacting AI: {e}"
