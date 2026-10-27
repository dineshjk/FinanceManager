# -*- coding: utf-8 -*-
# tests/test_ai_cascade.py
"""Tests for AI model cascade, multi-key pooling, auto-rotation, and disk cache fallback."""

import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from StockMan import ai_analyzer


def test_cascade_tier1_gemini_3_1_pro_preview():
    """Tier 1 (gemini-3.1-pro-preview) is called first and returns response on success."""
    mock_resp = MagicMock()
    mock_resp.text = "Analysis from 3.1 Pro Preview"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        result = ai_analyzer.get_market_insight("TCS", "Bullish", api_key="dummy_key")
        assert "Analysis from 3.1 Pro Preview" in result
        assert mock_client.models.generate_content.call_args_list[0].kwargs["model"] == "gemini-3.1-pro-preview"


def test_cascade_falls_back_to_gemini_3_8_flash():
    """When 3.1 Pro Preview fails, cascade tries 3.8 Flash."""
    mock_client = MagicMock()
    called_models = []

    def fake_generate(*args, **kwargs):
        m = kwargs.get("model")
        called_models.append(m)
        if m in ("gemini-3.1-pro-preview", "gemini-3.1-pro"):
            raise Exception("429 Resource has been exhausted")
        resp = MagicMock()
        resp.text = f"Analysis from {m}"
        return resp

    mock_client.models.generate_content.side_effect = fake_generate

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        result = ai_analyzer.get_market_insight("INFY", "Buy", api_key="dummy_key")
        assert "Analysis from gemini-3.8-flash" in result
        assert "gemini-3.1-pro-preview" in called_models
        assert "gemini-3.8-flash" in called_models


def test_cascade_falls_back_to_gemini_4_argon():
    """When 3.1 Pro and 3.8 Flash fail, cascade tries 4 Argon."""
    mock_client = MagicMock()
    called_models = []

    def fake_generate(*args, **kwargs):
        m = kwargs.get("model")
        called_models.append(m)
        if m in ("gemini-3.1-pro-preview", "gemini-3.1-pro", "gemini-3.8-flash"):
            raise Exception("503 Service Unavailable")
        resp = MagicMock()
        resp.text = f"Analysis from {m}"
        return resp

    mock_client.models.generate_content.side_effect = fake_generate

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        result = ai_analyzer.get_market_insight("WIPRO", "Neutral", api_key="dummy_key")
        assert "Analysis from gemini-4-argon" in result
        assert called_models.index("gemini-3.8-flash") < called_models.index("gemini-4-argon")


def test_cascade_falls_back_to_cache_when_all_fail():
    """When all models in the cascade fail, disk cache is returned."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("All models exhausted")

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".md", encoding="utf-8") as tmp:
        tmp.write("# Cached Verified Report\nDetailed investment advice.")
        tmp_path = tmp.name

    try:
        text, tag = ai_analyzer.call_gemini_with_model_cascade(
            mock_client,
            "Prompt",
            cache_path=tmp_path,
            cache_title="Portfolio Report",
        )
        assert tag == "cache"
        assert "> [!NOTE]" in text
        assert "# Cached Verified Report" in text
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_multi_key_rotation_on_quota():
    """When Key 1 hits quota limits on all models, engine rotates to Key 2."""
    clients_created = []

    mock_client1 = MagicMock()
    mock_client1.models.generate_content.side_effect = Exception("429 Quota exhausted for Key 1")

    mock_client2 = MagicMock()
    mock_resp2 = MagicMock()
    mock_resp2.text = "Success from Key 2 via Gemini 3.8 Flash"
    mock_client2.models.generate_content.return_value = mock_resp2

    def client_factory(api_key, **kwargs):
        clients_created.append(api_key)
        if api_key == "KEY_ALPHA":
            return mock_client1
        return mock_client2

    with patch.object(ai_analyzer.genai, "Client", side_effect=client_factory):
        text, model = ai_analyzer.call_gemini_with_model_cascade(
            ["KEY_ALPHA", "KEY_BETA"],
            "Analyze portfolio",
        )
        assert "Success from Key 2" in text
        assert "KEY_ALPHA" in clients_created
        assert "KEY_BETA" in clients_created


def test_get_api_keys_multi_line_parsing():
    """Verifies that multiple keys with comments and empty lines are cleanly parsed."""
    fake_content = (
        "# Account 1\n"
        "KEY_1111111111\n\n"
        "# Account 2 (Work)\n"
        "KEY_2222222222\n"
        "# Empty comment\n"
        "KEY_3333333333\n"
    )
    with patch("builtins.open", mock_open(read_data=fake_content)):
        with patch("os.path.exists", return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                keys = ai_analyzer.get_api_keys()
                assert "KEY_1111111111" in keys
                assert "KEY_2222222222" in keys
                assert "KEY_3333333333" in keys
                assert len(keys) == 3


def test_search_grounding_quota_fallback_to_direct_generation():
    """When search grounding hits quota on all keys, fallback generates directly without search."""
    calls = []

    def fake_generate(model, contents, config=None):
        calls.append(config)
        # If search tool was passed, raise 429 quota exhausted
        if config and getattr(config, "tools", None):
            raise Exception("429 RESOURCE_EXHAUSTED: Search quota exceeded")
        resp = MagicMock()
        resp.text = "Direct Institutional Analysis without Search Grounding"
        return resp

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = fake_generate

    search_cfg = ai_analyzer.types.GenerateContentConfig(tools=[{"google_search": {}}])

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        text, model = ai_analyzer.call_gemini_with_model_cascade(
            ["KEY_1"],
            "Analyze portfolio",
            config=search_cfg,
        )
        assert "Direct Institutional Analysis without Search Grounding" in text
        assert "(direct)" in model
        assert "Google Search grounding daily quota was reached" in text


def test_get_portfolio_buy_advice_prompt_recency():
    """Verify that get_portfolio_buy_advice includes current year, date anchors, and excludes 2024."""
    import datetime

    captured_prompt = []
    mock_resp = MagicMock()
    mock_resp.text = (
        "**Table of Institutional Buy Advice:**\n\n"
        "| Scrip | Buy Price Band | Target Price | Target Period | Broker House | Date of Report |\n"
        "| TCS.NS | 4100-4200 | 4800 | 12M | Motilal Oswal | 20-Oct-2026 |"
    )

    mock_client = MagicMock()

    def fake_generate(model, contents, config=None):
        captured_prompt.append(contents)
        return mock_resp

    mock_client.models.generate_content.side_effect = fake_generate

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        res = ai_analyzer.get_portfolio_buy_advice(
            ["TCS.NS", "INFY.NS"], api_key="dummy_key"
        )
        assert "Table of Institutional Buy Advice" in res
        assert len(captured_prompt) > 0
        prompt_text = captured_prompt[0]

        today = datetime.date.today()
        current_year = str(today.year)
        today_str = today.strftime("%d-%b-%Y")

        assert today_str in prompt_text
        assert current_year in prompt_text
        assert "STRICTLY FORBIDDEN: Do NOT include any outdated reports from 2024" in prompt_text
        assert "Table of Institutional Buy Advice" in prompt_text
        assert "Date of Report" in prompt_text

