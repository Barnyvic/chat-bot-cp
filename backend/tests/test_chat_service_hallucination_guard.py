from app.chat_service import ChatService


def test_requires_tool_evidence_for_order_lookup():
    assert ChatService._requires_tool_evidence("Can you check my last order status?") is True


def test_requires_tool_evidence_for_auth_lookup():
    assert ChatService._requires_tool_evidence("My email is donaldgarcia@example.net and pin is 7912") is True


def test_no_tool_evidence_needed_for_greeting():
    assert ChatService._requires_tool_evidence("Hi there") is False


def test_no_evidence_response_is_safe_and_explicit():
    response = ChatService._no_evidence_response()
    assert "verified backend data" in response
    assert "query Meridian systems" in response
