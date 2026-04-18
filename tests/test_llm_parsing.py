from unittest.mock import patch, MagicMock

def test_parse_purchase_with_llm_success():
    """LLM returns amount|description → parsed correctly."""
    with patch("services.llm._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(type="text", text="1500|билет на концерт")]
        mock_client.messages.create.return_value = mock_message
        mock_get_client.return_value = mock_client

        import asyncio
        from services.llm import parse_purchase_with_llm
        result = asyncio.run(parse_purchase_with_llm("билет на концерт 26 апреля за 1500"))
        assert result == (1500.0, "билет на концерт")

def test_parse_purchase_with_llm_error():
    """LLM unavailable → raises LLMError."""
    with patch("services.llm._get_client") as mock_get_client:
        mock_get_client.side_effect = Exception("connection refused")
        import asyncio
        from services.llm import parse_purchase_with_llm, LLMError
        try:
            asyncio.run(parse_purchase_with_llm("test"))
            assert False, "Should have raised LLMError"
        except LLMError:
            pass