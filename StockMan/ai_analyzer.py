# -*- coding: utf-8 -*-
# StockMan/ai_analyzer.py
import os
import time
import json
import re
from google import genai
from google.genai import types
import logging

# Install IPv4 priority adapter to eliminate Windows IPv6 TCP timeout stalls
try:
    from Shared.network_utils import enable_ipv4_priority

    enable_ipv4_priority()
except Exception:
    pass

logger = logging.getLogger("StockMan.AI")

# Global flag to track API availability during runtime
AI_AVAILABLE = True

# Prioritized AI Model Cascade:
# Tier 1: Gemini 3.1 Pro Preview (gemini-3.1-pro-preview)
# Tier 2: Gemini 3.8 Flash (gemini-3.8-flash)
# Tier 3: 4 Argon (gemini-4-argon)
# Tier 4: Stable fallbacks (gemini-flash-latest, gemini-pro-latest)
AI_MODEL_CASCADE = [
    "gemini-3.1-pro-preview",
    "gemini-3.8-flash",
    "gemini-4-argon",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-pro-latest",
]


def call_gemini_with_model_cascade(
    api_keys: list[str] | str | None,
    prompt: str,
    config: types.GenerateContentConfig | None = None,
    cache_path: str | None = None,
    cache_title: str = "Analysis Report",
    timeout_ms: int = 180000,
) -> tuple[str | None, str | None]:
    """
    Executes prompt through multiple keys and prioritized AI cascade:
    For each API key (in order from api_key.txt):
        Tries:
        1. Gemini 3.1 Pro Preview / Pro
        2. Gemini 3.8 Flash
        3. 4 Argon
        4. Any Free Version
    If all API keys exhaust search tools, retries without search tools
    before falling back to disk cache copy.

    Returns (response_text, model_name_or_status)
    """
    # Normalize keys list or handle client mock
    passed_client = None
    if hasattr(api_keys, "models"):
        passed_client = api_keys
        keys = ["mock_key"]
    elif isinstance(api_keys, str):
        keys = [api_keys]
    elif isinstance(api_keys, (list, tuple)):
        keys = list(api_keys)
    else:
        keys = get_api_keys()

    # Append any disk keys not already in the list
    if not passed_client:
        for disk_k in get_api_keys():
            if disk_k not in keys:
                keys.append(disk_k)

    if not keys:
        return None, "No API keys provided or found in api_key.txt."

    last_error = None
    has_tools = bool(config and getattr(config, "tools", None))

    def _execute_cascade(current_config, stage_label=""):
        nonlocal last_error
        exhausted_keys = set()
        for key_idx, key in enumerate(keys, 1):
            if key in exhausted_keys:
                logger.info(
                    f"AI Service: Skipping Key #{key_idx} "
                    f"(quota already exhausted for this stage)."
                )
                continue

            masked_key = (
                f"...{key[-6:]}"
                if len(key) > 6
                else (f"Key #{key_idx}" if key != "mock_key" else "MockClient")
            )
            logger.info(
                f"AI Service: Attempting with API Key #{key_idx} "
                f"({masked_key}){stage_label}..."
            )

            if passed_client:
                client = passed_client
            else:
                client = genai.Client(
                    api_key=key, http_options={"timeout": timeout_ms}
                )

            for model_name in AI_MODEL_CASCADE:
                try:
                    logger.info(
                        f"AI Service: [Key #{key_idx}] "
                        f"Attempting model '{model_name}'{stage_label}..."
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=current_config,
                    )
                    if response and response.text and response.text.strip():
                        text_resp = response.text.strip()
                        logger.info(
                            f"AI Service: [Key #{key_idx}] Generated content "
                            f"using '{model_name}' ({len(text_resp)} chars)."
                        )
                        if cache_path and len(text_resp) >= 500:
                            try:
                                os.makedirs(
                                    os.path.dirname(
                                        os.path.abspath(cache_path)
                                    ),
                                    exist_ok=True,
                                )
                                with open(
                                    cache_path, "w", encoding="utf-8"
                                ) as f_out:
                                    f_out.write(text_resp)
                            except Exception as cache_err:
                                logger.warning(
                                    f"Could not save cache to "
                                    f"{cache_path}: {cache_err}"
                                )
                        return text_resp, model_name
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    logger.info(
                        f"AI Service: [Key #{key_idx}] Model '{model_name}' "
                        f"unavailable ({err_str[:60]}). Cascading..."
                    )

                    # Anti-burst throttle: brief pause between calls
                    if not passed_client:
                        time.sleep(1.0)

                    # Fail fast on flash tier quota exhaustion:
                    # If flash model returns quota exhaustion (429) and
                    # not search-specific, mark key quota exhausted.
                    is_flash_tier = "flash" in model_name.lower()
                    is_quota_err = any(
                        phrase in err_str.lower()
                        for phrase in (
                            "exceeded your current quota",
                            "resource_exhausted",
                            "quota limit",
                            "quota exceeded",
                        )
                    )
                    is_search_err = "search" in err_str.lower() and bool(
                        current_config
                        and getattr(current_config, "tools", None)
                    )
                    if is_flash_tier and is_quota_err and not is_search_err:
                        logger.warning(
                            f"AI Service: Key #{key_idx} ({masked_key}) "
                            f"quota exhausted. Rotating key..."
                        )
                        exhausted_keys.add(key)
                        break

            logger.warning(
                f"AI Service: All tiers exhausted for Key #{key_idx} "
                f"({masked_key}){stage_label}. Rotating key..."
            )
        return None, None

    # Phase 1: Try with requested configuration (with Search if configured)
    result_text, used_model = _execute_cascade(
        config, stage_label=" (with Search)" if has_tools else ""
    )
    if result_text:
        return result_text, used_model

    # Phase 2: If search quota exhausted, retry without search tool
    # using local database facts and fundamental reasoning
    if has_tools:
        logger.info(
            "AI Service: Search tool quota exhausted. "
            "Retrying live generation without search..."
        )
        fallback_cfg = types.GenerateContentConfig(
            thinking_config=getattr(config, "thinking_config", None),
        )
        result_text, used_model = _execute_cascade(
            fallback_cfg, stage_label=" (Direct LLM Grounding)"
        )
        if result_text:
            direct_notice = (
                "> [!NOTE]\n"
                "> **Live AI Analysis Generated (Real-Time Portfolio "
                "Grounding).** Google Search grounding daily quota was "
                "reached across all API keys; synthesized using internal "
                "portfolio holdings, sector weights, CMP, and cash.\n\n"
                f"{result_text}"
            )
            return direct_notice, f"{used_model} (direct)"

    # Phase 3: All keys failed. Check if a cached copy exists on disk
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f_in:
                cached_data = f_in.read().strip()
            if cached_data:
                logger.info(
                    f"AI Service: All {len(keys)} keys exhausted. "
                    f"Loaded cached copy from '{cache_path}'."
                )
                cache_notice = (
                    f"> [!NOTE]\n"
                    f"> **Live AI Rate Limit Reached Across All Keys.** "
                    f"Displaying latest verified {cache_title} from cache.\n\n"
                    f"{cached_data}"
                )
                return cache_notice, "cache"
        except Exception as ex:
            logger.warning(f"Failed to read cache file '{cache_path}': {ex}")

    return (
        None,
        f"All {len(keys)} API keys and model tiers failed: {last_error}",
    )


def get_api_keys() -> list[str]:
    """
    Retrieves all valid Gemini API Keys from:
    1. 'api_key.txt' in project root (supports multiple keys, 1 per line).
    2. 'GEMINI_API_KEY' or 'GEMINI_API_KEYS' env var.
    """
    keys = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    key_file_path = os.path.join(project_root, "api_key.txt")

    # 1. Read from api_key.txt
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str and not line_str.startswith("#"):
                        if (
                            line_str != "YOUR_API_KEY_HERE"
                            and line_str not in keys
                        ):
                            keys.append(line_str)
        except Exception:
            pass

    # 2. Read from environment variables
    for env_var in ("GEMINI_API_KEY", "GEMINI_API_KEYS"):
        raw_env = os.environ.get(env_var, "")
        if raw_env:
            for part in re.split(r"[\r\n,]+", raw_env):
                p = part.strip()
                if p and p not in keys:
                    keys.append(p)

    return keys


def get_api_key() -> str | None:
    """Convenience helper returning the first available API key."""
    keys = get_api_keys()
    return keys[0] if keys else None


def get_market_insight(scrip_name, technical_signal, api_key=None):
    """
    Calls the Gemini API to analyze a stock using live Search grounding.
    Gracefully disables itself if billing/quota limits are hit.
    """

    if not AI_AVAILABLE:
        return (
            "[System] AI Analysis is disabled due to quota or API errors."
        )

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create 'api_key.txt' in project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. Get a free API key at: https://aistudio.google.com/"
        )

    try:
        enable_ipv4_priority()
        candidate_keys = (
            [api_key]
            if (api_key and api_key != "YOUR_API_KEY_HERE")
            else get_api_keys()
        )

        prompt = (
            f"You are a financial AI assisting a novice investor. "
            f"My local scanner flagged a '{technical_signal}' for "
            f"the Indian stock {scrip_name}. Using Google Search, "
            f"find latest news regarding this company and its sector. "
            f"Write a 5-paragraph plain-English explanation.\n"
            f"Paragraph 1: What this technical signal means in simple terms.\n"
            f"Paragraph 2: Latest news/fundamentals for the company.\n"
            f"Paragraph 3: Fundamental risks contradicting signal.\n"
            f"Paragraph 4: Is it a 'BUY' advice? Why/why not?\n"
            f"Paragraph 5: Brokerages and projections, and next steps."
        )

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(cur_dir)
        cache_path = os.path.join(
            proj_root, "data", "ai_cache", f"market_insight_{scrip_name}.txt"
        )

        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        )

        result, model_or_tag = call_gemini_with_model_cascade(
            candidate_keys,
            prompt,
            config=config,
            cache_path=cache_path,
            cache_title=f"Market Insight ({scrip_name})",
        )
        if result:
            return result
        return (
            f"[System] All AI model tiers are unavailable: "
            f"{model_or_tag}"
        )

    except Exception as e:
        return f"[System] Temporary network error while contacting AI: {e}"


def get_portfolio_sell_advice(scrip_list, api_key=None):
    """
    Calls Gemini API to scan profitable portfolio holdings for
    profit-booking advice using Google Search grounding.
    """

    if not AI_AVAILABLE:
        return (
            "[System] AI Analysis is disabled due to quota or API errors."
        )

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create 'api_key.txt' in project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. Get a free API key at: https://aistudio.google.com/"
        )

    try:
        enable_ipv4_priority()
        candidate_keys = (
            [api_key]
            if (api_key and api_key != "YOUR_API_KEY_HERE")
            else get_api_keys()
        )

        import datetime

        today = datetime.date.today()
        today_str = today.strftime("%d-%b-%Y")
        current_year = today.year
        cutoff_date = (today - datetime.timedelta(days=30)).strftime("%d-%b-%Y")

        scrip_details = ", ".join(
            [f"{ticker} ({gain:.2f}% gain)" for ticker, gain in scrip_list]
        )

        prompt = (
            f"Act as an aggregate equity research analyst covering the Indian stock market.\n"
            f"Today's date is {today_str}. The current year is {current_year}.\n\n"
            f"The user has an equity portfolio in profit zone for: [{scrip_details}].\n\n"
            f"Search Google for RECENT brokerage reports, market news, and consensus estimates from {current_year} "
            f"(e.g., Zee Business, Motilal Oswal, ICICI Direct, HDFC Securities, Kotak, Axis Capital). "
            f"Identify if broker houses recently (between {cutoff_date} and {today_str}) issued target-achieved alerts, "
            f"downgrades, or advice recommending 'Profit Booking', 'Trimming 50%', or 'Exiting'.\n\n"
            f"STRICT RECENCY & DATE RULES:\n"
            f"1. Only include advice from {current_year}. Strictly omit old advice from 2024 or 2025.\n"
            f"2. Specify the exact Date of Report in 'DD-Mon-YYYY' or 'Month {current_year}' format.\n\n"
            f"Generate a single markdown table under '**Table of Institutional Advice:**' with columns:\n"
            f"| Scrip | Broker House | Advice | Date of Report |\n"
            f"If no institutional advice exists, list 'N/A', 'Hold/Run Profits', 'N/A'. Group by Scrip. No other text."
        )

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(cur_dir)
        cache_path = os.path.join(
            proj_root, "docs", "PORTFOLIO_SELL_ADVICE_REPORT.md"
        )

        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        )

        result, model_or_tag = call_gemini_with_model_cascade(
            candidate_keys,
            prompt,
            config=config,
            cache_path=cache_path,
            cache_title="Portfolio Profit-Booking / Sell Advice",
        )
        if result:
            return result
        return (
            f"[System] All AI model tiers are unavailable: "
            f"{model_or_tag}"
        )

    except Exception as e:
        return f"[System] Temporary network error while contacting AI: {e}"


def get_portfolio_buy_advice(scrip_list, api_key=None):
    """
    Calls Gemini API to search recent institutional Buy
    recommendations across tracked stocks.
    """

    if not AI_AVAILABLE:
        return (
            "[System] AI Analysis is disabled due to quota or API errors."
        )

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create 'api_key.txt' in project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. Get a free API key at: https://aistudio.google.com/"
        )

    try:
        enable_ipv4_priority()
        candidate_keys = (
            [api_key]
            if (api_key and api_key != "YOUR_API_KEY_HERE")
            else get_api_keys()
        )

        import datetime

        today = datetime.date.today()
        today_str = today.strftime("%d-%b-%Y")
        current_year = today.year
        cutoff_date = (today - datetime.timedelta(days=30)).strftime("%d-%b-%Y")

        scrip_details = ", ".join(scrip_list)

        prompt = (
            f"Act as an aggregate equity research analyst covering the Indian stock market.\n"
            f"Today's date is {today_str}. The current year is {current_year}.\n\n"
            f"User tracked scrips: [{scrip_details}].\n\n"
            f"Search Google for LIVE and RECENT institutional brokerage research reports, target price upgrades, "
            f"and 'Buy' / 'Accumulate' calls published recently between {cutoff_date} and {today_str} ({current_year}) "
            f"from leading brokerages (e.g., Motilal Oswal, ICICI Direct, Kotak Institutional Equities, Jefferies, Nomura, "
            f"Morgan Stanley, HDFC Securities, Axis Securities, Sharekhan, Prabhudas Lilladher, Antique, Nuvama, etc.).\n\n"
            f"STRICT RECENCY & DATE RULES:\n"
            f"1. MANDATORY: Only include recent recommendations issued in {current_year} (between {cutoff_date} and {today_str}).\n"
            f"2. STRICTLY FORBIDDEN: Do NOT include any outdated reports from 2024, 2025, or any past years. "
            f"If a report is from 2024 or earlier, completely omit it.\n"
            f"3. In the 'Date of Report' column, specify the exact publication date in DD-Mon-YYYY format (e.g., '18-Oct-{current_year}'). "
            f"The year in 'Date of Report' MUST be {current_year}.\n"
            f"4. If no recent {current_year} institutional buy recommendation exists for a scrip, DO NOT include it in the table.\n"
            f"5. Include top priority scrips (max 50) with the freshest buy calls.\n\n"
            f"Format requirements:\n"
            f"Generate a markdown table under '**Table of Institutional Buy Advice:**' with columns:\n"
            f"| Scrip | Buy Price Band | Target Price | Target Period | Broker House | Date of Report |\n"
            f"Sort rows alphabetically by Scrip. Output ONLY the markdown table. No conversational text or preamble."
        )

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(cur_dir)
        cache_path = os.path.join(
            proj_root, "docs", "PORTFOLIO_BUY_ADVICE_REPORT.md"
        )

        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        )

        result, model_or_tag = call_gemini_with_model_cascade(
            candidate_keys,
            prompt,
            config=config,
            cache_path=cache_path,
            cache_title="Portfolio Buy Advice",
        )
        if result:
            return result
        return (
            f"[System] All AI model tiers are unavailable: "
            f"{model_or_tag}"
        )

    except Exception as e:
        return f"[System] Temporary network error while contacting AI: {e}"


def get_ipo_advice(api_key):
    """
    Queries Gemini with Google Search grounding for Indian IPOs
    (next 30 days) including GMP and recommendations.
    """

    if not AI_AVAILABLE:
        return {
            "error": (
                "[System] AI Analysis is disabled due to quota or API errors."
            )
        }

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return {
            "error": (
                "[System] No Gemini API key found.\n\n"
                "To use the Gemini AI features:\n"
                "1. Create 'api_key.txt' in project root folder.\n"
                "2. Paste your Google AI Studio API key into it.\n"
                "3. Get a free API key at: https://aistudio.google.com/"
            )
        }

    try:
        enable_ipv4_priority()
        candidate_keys = (
            [api_key]
            if (api_key and api_key != "YOUR_API_KEY_HERE")
            else get_api_keys()
        )

        prompt = (
            "You are an IPO specialist for the Indian stock market. "
            "Search active and upcoming Indian IPOs for next 30 days. "
            "For each IPO find:\n"
            "1. Company Name\n2. Issue Open Date\n3. Issue Close Date\n"
            "4. Price Band (in INR)\n"
            "5. Latest GMP in INR and % if available\n"
            "6. Consensus recommendation ('Apply', 'Avoid', 'Neutral')\n"
            "7. Very brief (1-sentence) rationale\n\n"
            "Output strictly valid JSON array of objects without preamble. "
            "Keys per object: 'company', 'open_date', 'close_date', "
            "'price_band', 'gmp', 'recommendation', 'rationale'."
        )

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(cur_dir)
        cache_path = os.path.join(
            proj_root, "data", "ai_cache", "ipo_advice_cache.json"
        )

        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
            temperature=0.2,
        )

        result, model_or_tag = call_gemini_with_model_cascade(
            candidate_keys,
            prompt,
            config=config,
            cache_path=cache_path,
            cache_title="IPO Intelligence",
        )

        if result:
            raw_text = result.strip()
            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if match:
                try:
                    return {"data": json.loads(match.group(0))}
                except Exception:
                    pass

        # If live result could not be parsed, check cache_path directly
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f_in:
                    cached_raw = f_in.read().strip()
                match = re.search(r"\[.*\]", cached_raw, re.DOTALL)
                if match:
                    return {"data": json.loads(match.group(0)), "cached": True}
            except Exception:
                pass

        return {
            "error": (
                f"[System] Error fetching IPO Advice: {model_or_tag}"
            )
        }

    except Exception as e:
        return {"error": f"[System] Error fetching IPO Advice: {e}"}


def clean_pick_of_the_day_response(raw_text):
    """
    Cleans and standardizes the Pick of the Day response:
    - Removes raw citation leftovers like [cite: 4 of prev batch]
    - Ensures clean main title at the top
    - Formats Section 0 preserving full table
    - Ensures clean markdown section hierarchy
    """
    if not raw_text:
        return raw_text

    # If already formatted with a cache notice, preserve it intact
    if raw_text.strip().startswith("> [!NOTE]"):
        return raw_text.strip()

    # 1. Clean citation markers
    text = re.sub(r"\[cite:[^\]]*\]", "", raw_text)

    # 2. Format Section 0 if present
    if (
        re.search(r"^\s*0\.\s*Based on", text, re.MULTILINE)
        or "**Current Portfolio Holdings and Valuation" in text
    ):
        if not text.strip().startswith("# 🏆"):
            text = re.sub(
                r"^\s*0\.\s*Based on",
                (r"## 0. Current Portfolio Holdings & Valuation "
                 r"Baseline\n\nBased on"),
                text,
                flags=re.MULTILINE,
            )
            prefix = (
                "# 🏆 Daily Pick of the Day — Universe & Portfolio "
                "Intelligence Report\n\n"
            )
            text = prefix + text.strip()
    elif not text.strip().startswith("#"):
        prefix = (
            "# 🏆 Daily Pick of the Day — Universe & Portfolio "
            "Intelligence Report\n\n"
        )
        text = prefix + text.strip()

    return text.strip()


def get_pick_of_the_day_advice(
    holdings_summary, available_cash=0.0, api_key=None
):
    """
    Calls Gemini API with Google Search grounding to evaluate database
    stock universe factoring in sector weights and momentum with score/100.
    """

    if not AI_AVAILABLE:
        return (
            "[System] AI Analysis is disabled due to quota or API errors."
        )

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = get_api_key()

    if not api_key:
        return (
            "[System] No Gemini API key found.\n\n"
            "To use the Gemini AI features:\n"
            "1. Create 'api_key.txt' in project root folder.\n"
            "2. Paste your Google AI Studio API key into it.\n"
            "3. Get a free API key at: https://aistudio.google.com/"
        )

    standing_instructions = (
        "Role: Elite Institutional Equity Research Analyst & Portfolio "
        "Strategist.\n"
        "Task: Conduct an exhaustive, data-driven daily analysis of my entire "
        "tracked stock universe from my database ('stocks' table) using fresh "
        "live market research via Google Search. Identify the single best, "
        "highest-conviction 'Pick of the Day' for new capital deployment, "
        "evaluate portfolio sector risk and momentum, and spotlight any "
        "extraordinary market limelight counter.\n\n"
        "1. Complete Stock Universe Evaluation (Active Holdings + Watchlist)\n"
        "- The provided universe table is your absolute source of truth. It "
        "contains both Active Holdings (qty > 0) and Watchlist / Tracking "
        "Stocks (qty = 0).\n"
        "- Assess all instruments across the entire universe without "
        "cherry-picking or premature shortlisting.\n"
        "- Your 'Pick of the Day' may be selected from either an existing "
        "active holding (for capital addition/averaging up) OR from the "
        "watchlist/tracking stocks (for fresh portfolio entry), whichever "
        "presents the most compelling risk-adjusted upside.\n\n"
        "2. Sector Weights & Current Sector Performance (Mandatory Context)\n"
        "- Sector Weights Evaluation: Analyze the investor's current active "
        "sector weight distribution. Flag over-concentrated sectors (>20-25% "
        "exposure) and under-represented high-growth themes.\n"
        "- Sector Performance & Rotation: Using live Search, assess current "
        "sectoral performance and momentum (e.g., Nifty Bank, Nifty IT, "
        "Nifty Auto, Nifty Realty, Nifty Metal, Nifty Energy, Pharma, "
        "Infrastructure, Defense, Capital Goods). Determine which sectors "
        "have accelerating earnings, policy tailwinds (PLI, capex), or "
        "margin tailwinds versus those facing cyclical headwinds or "
        "valuation compression.\n"
        "- Sector-Informed Selection: Ensure the recommended Pick of the Day "
        "is backed by favorable sectoral tailwinds and does not dangerously "
        "overload an already bloated sector in the portfolio.\n\n"
        "3. Glaring Limelight / News / Brokerage Consensus Stock\n"
        "- Identify if any stock—either within the provided stock list or "
        "glaringly prominent in the broader Indian equity market—is currently "
        "dominating the limelight, financial news headlines, or institutional "
        "brokerage research notes (e.g., major quarterly earnings beat, mega "
        "block deals, transformative order wins, major M&A, regulatory "
        "clearances, or multiple brokerage target upgrades).\n"
        "- Feature this stock in a dedicated Spotlight section, "
        "presenting the full news developments, institutional brokerage "
        "sentiment, and scoring it out of 100 using the identical "
        "8-pillar rubric.\n\n"
        "4. Consistent 8-Pillar Scoring Framework (100 Points Total) & "
        "Objective Calibration\n"
        "Score every evaluated candidate out of 100 using these strict "
        "weighted pillars. Apply rigorous, deterministic scoring anchors "
        "so that identical company data yields consistent scores on "
        "consecutive runs:\n"
        "1. Fundamental Quality & Balance Sheet Health (18 Points): "
        "ROE/ROCE > 20% & D/E < 0.3 = 16-18 pts; ROE 12-20% & D/E < 1.0 = "
        "12-15 pts; ROE < 12% or High Debt = <10 pts.\n"
        "2. Growth Runway & Earnings Momentum (18 Points): Revenue/PAT CAGR > "
        "20% & strong order book = 16-18 pts; 10-20% = 12-15 pts; <10% or "
        "negative = <10 pts.\n"
        "3. Valuation & Margin of Safety (18 Points): Significant discount to "
        "5Y historical median multiples & peers = 15-18 pts; Fair value = "
        "11-14 pts; Expensive/Stretched = <10 pts.\n"
        "4. Catalysts, Limelight News & Brokerage Upgrades (10 Points): "
        "Major near-term catalyst, blowout earnings beat, or multiple "
        "broker upgrades = 8-10 pts; Steady = 5-7 pts; "
        "None/negative = <4 pts.\n"
        "5. Downside Risks & Vulnerabilities (15 Points): Low risk, sovereign "
        "backing or unassailable moat = 13-15 pts; Moderate risk = 9-12 pts; "
        "High debt, regulatory risk = <8 pts.\n"
        "6. Sector Tailwinds & Relative Sector Performance (10 Points): "
        "Leading sector index with accelerating momentum & PLI/capex "
        "tailwinds = 8-10 pts; Neutral = 5-7 pts; "
        "Cyclical downturn = <4 pts.\n"
        "7. Technical & Market Regime Context (5 Points): Clear uptrend "
        "above 50/200 DMA with accumulation volume = 4-5 pts; "
        "Consolidating = 3 pts; Below 200 DMA = 1-2 pts.\n"
        "8. Portfolio Fit & Sector Weight Balance (6 Points): Underweight "
        "growth sector needing allocation = 5-6 pts; Neutral = 3-4 pts; "
        "Overweight sector = 1-2 pts.\n"
        "Deterministic Calibration Rule: You must maintain objective "
        "score stability across consecutive evaluations. Scores must "
        "not fluctuate randomly; the highest-conviction business with "
        "the best risk-adjusted upside must reliably earn the top "
        "rank.\n\n"
        "5. Capital Deployment & Sizing Instructions\n"
        "- Explicitly size the Pick of the Day entry based on "
        "Available Cash.\n"
        "- Provide actionable entry guidance: BUY (new entry), ADD (pyramid "
        "into holding), HOLD, or WAIT (with specific entry tranches).\n\n"
        "6. Weakest Candidates & Capital Recycling\n"
        "- Identify the weakest forward-looking stocks in the universe "
        "(deteriorating fundamentals, structural sector headwinds, high "
        "debt).\n"
        "- Recommend clear REDUCE / EXIT / AVOID actions to free up capital "
        "for recycling into top compounders."
    )

    explicit_formatting_rules = (
        "Output Formatting Instructions:\n"
        "1. DO NOT print a preliminary valuation table, do NOT echo back the "
        "raw input universe, and do NOT create a Section 0.\n"
        "2. Begin IMMEDIATELY with: '# 🏆 Daily Pick of the Day — Universe & "
        "Portfolio Intelligence Report'\n"
        "3. Follow with exactly these 7 numbered sections in clean "
        "GitHub-Flavored Markdown:\n\n"
        "## 1. Macro Landscape & Sectoral Performance\n"
        "Date, market regime (Nifty/Sensex trend, FII/DII liquidity), leading "
        "vs lagging sectors, sector rotation dynamics, and key macro "
        "drivers.\n\n"
        "## 2. Portfolio Sector Weights & Allocation Analysis\n"
        "Table of current active portfolio sector weights, identifying "
        "overweight/underweight sectors and concentration risks relative to "
        "benchmark sectoral health.\n\n"
        "## 3. Pick of the Day: Winner Deep-Dive\n"
        "Declare the single winning pick from the database universe "
        "(Ticker, Company Name, Sector, Status [Holding/Watchlist], "
        "CMP, Composite Score /100, Action: BUY/ADD/HOLD/WAIT).\n"
        "- Core Thesis, Moat, and Sectoral Catalyst\n"
        "- Valuation & Margin of Safety\n"
        "- Key Downside Risks & Stop-Loss / Review Trigger\n"
        "- Exact Capital Allocation Guidance using available cash\n"
        "- Head-to-Head Comparison Table (Winner vs Top Runner-Up):\n"
        "  Construct an exhaustive comparison table comparing the Winner "
        "against the top Runner-Up across these mandatory parameters:\n"
        "  | Parameter | Winner ([Ticker]) | Runner-Up ([Ticker]) | "
        "Decisive Advantage / Edge |\n"
        "  | :--- | :--- | :--- | :--- |\n"
        "  Include parameters:\n"
        "  1. Action & Entry: Provide complete, actionable guidance (e.g., "
        "exact entry price bands, cash allocation %, and tranche sizing). "
        "Write full, complete sentences.\n"
        "  2. Core Thesis: Provide complete, articulate sentences "
        "explaining the strategic growth driver and competitive moat. "
        "Write full, complete sentences.\n"
        "  3. Valuation & Margin of Safety: Compare P/E, EV/EBITDA, and fair "
        "value discount in full, comprehensive sentences.\n"
        "  4. Sector Momentum & Tailwinds: Compare parent sector growth "
        "dynamics and policy tailwinds in full sentences.\n"
        "  5. Catalysts & News Triggers: Detail upcoming corporate catalysts, "
        "quarterly earnings expectations, and institutional broker views in "
        "full sentences.\n"
        "  6. Primary Downside Risk: Explain the operational, financial, or "
        "regulatory risks for each in full sentences.\n"
        "  7. Decisive Verdict: Explain in complete sentences why the Winner "
        "takes new capital over the Runner-up.\n"
        "  MANDATORY REQUIREMENT: Provide complete, articulate, and "
        "informative sentences for every cell in the Head-to-Head Comparison "
        "Table. Do not curtail, truncate, or abbreviate statements into short "
        "fragments.\n\n"
        "## 4. Market Limelight & Special Situation Spotlight\n"
        "Spotlight the stock currently dominating financial media/brokerage "
        "discussions (from the list or broader Indian market). Detail latest "
        "news, institutional consensus, and provide its full Composite Score "
        "/100 with pillar breakdown.\n\n"
        "## 5. Complete Stock Universe Ranking Table\n"
        "MANDATORY COMPLETE UNIVERSE RANKING:\n"
        "- You MUST evaluate and rank EVERY single stock provided in "
        "the input table from Rank 1 to Rank N without stopping early "
        "or skipping any instrument.\n"
        "- Format as a clean markdown table:\n"
        "| Rank | Code | Ticker | Company Name | Sector | Status | Score /100 "
        "| Action | Key Catalyst / News | Key Risk |\n"
        "| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- "
        "| :--- |\n"
        "- TABLE EFFICIENCY RULE: To guarantee the full table of all stocks "
        "completes seamlessly along with Sections 6 and 7 without hitting "
        "generation limits, keep the 'Key Catalyst / News' and 'Key Risk' "
        "columns concise (1 crisp phrase of 8–15 words per cell). Every stock "
        "in the universe must appear with its exact Rank and Score /100.\n\n"
        "## 6. Weakest Forward-Looking Candidates: Reduce / Exit / Avoid\n"
        "Identify the bottom-ranking stocks facing deteriorating earnings, "
        "excessive debt, or severe sectoral headwinds. Provide clear capital "
        "recycling advice.\n\n"
        "## 7. Sources & Data Freshness Audit\n"
        "Data freshness disclosure, primary sources consulted, and standard "
        "investment disclaimer."
    )

    cash_display = (
        f"₹{available_cash:,.2f}"
        if available_cash and available_cash > 0
        else "₹0.00 (Zero / Nil specified)"
    )

    cash_instructions = (
        f"INVESTOR'S AVAILABLE CASH FOR NEW CAPITAL: {cash_display}\n\n"
        f"MANDATORY CASH DEPLOYMENT & SIZING INSTRUCTIONS:\n"
        f"1. Sizing Pick of the Day: Provide concrete capital allocation "
        f"guidance based on this available cash ({cash_display}). State the "
        f"exact rupee allocation and entry tranches for the winning pick.\n"
        f"2. Portfolio Assessment: In the Total Portfolio Stats, explicitly "
        f"list Available Cash as {cash_display}, calculate Total Deployable "
        f"Net Worth (Current Portfolio Value + Available Cash), and state the "
        f"Cash Weight %.\n"
        f"3. Capital Recycling: If available cash is zero or insufficient, "
        f"explicitly advise reallocating capital by liquidating or trimming "
        f"the weakest exit candidates."
    )

    prompt = (
        f"{standing_instructions}\n\n"
        f"{cash_instructions}\n\n"
        f"{explicit_formatting_rules}\n\n"
        "--- COMPLETE STOCK UNIVERSE & SECTOR BREAKDOWN "
        "(SOURCE OF TRUTH) ---\n"
        f"{holdings_summary}\n\n"
        "Conduct fresh research using Google Search on this universe and "
        "provide the required daily response adhering strictly to the format."
    )

    def _save_report_backup(report_content):
        try:
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            proj_root = os.path.dirname(cur_dir)
            out_path = os.path.join(
                proj_root, "docs", "DAILY_PICK_OF_THE_DAY_REPORT.md"
            )
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f_out:
                f_out.write(report_content)
        except Exception:
            pass

    try:
        enable_ipv4_priority()
        candidate_keys = (
            [api_key]
            if (api_key and api_key != "YOUR_API_KEY_HERE")
            else get_api_keys()
        )

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(cur_dir)
        cache_path = os.path.join(
            proj_root, "docs", "DAILY_PICK_OF_THE_DAY_REPORT.md"
        )

        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
            temperature=0.0,
            max_output_tokens=65536,
        )

        logger.info(
            "Pick of the Day: Dispatching request through prioritized "
            "model cascade..."
        )
        result, model_or_tag = call_gemini_with_model_cascade(
            candidate_keys,
            prompt,
            config=config,
            cache_path=cache_path,
            cache_title="Pick of the Day Report",
        )

        if result:
            cleaned = clean_pick_of_the_day_response(result)
            # If live model was used, update cache file with cleaned version
            if model_or_tag != "cache" and len(cleaned) >= 500:
                try:
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f_out:
                        f_out.write(cleaned)
                except Exception:
                    pass
            logger.info(
                f"Pick of the Day: Returning response via tier "
                f"'{model_or_tag}' ({len(cleaned)} chars)."
            )
            return cleaned

        return (
            f"[System] All AI model tiers are unavailable: "
            f"{model_or_tag}"
        )

    except Exception as e:
        return f"[System] Temporary network error while contacting AI: {e}"
