from app.application.services.chat.chat_service import ChatService


def test_refund_question_matches_refund_policy() -> None:
    assert ChatService._has_lexical_relevance(
        "How can I get a refund?",
        "Refunds are available within 30 days.",
    )


def test_order_question_matches_plural_orders() -> None:
    assert ChatService._has_lexical_relevance(
        "Where is my order?",
        "Orders usually ship within two business days.",
    )


def test_unrelated_password_question_rejects_refund_content() -> None:
    assert not ChatService._has_lexical_relevance(
        "How do I reset my password?",
        "Refund requests are processed within five business days.",
    )


def test_query_without_meaningful_terms_is_rejected() -> None:
    assert not ChatService._has_lexical_relevance(
        "How can you help me?",
        "Our customer support team can assist with many questions.",
    )


def test_long_query_needs_multiple_matching_terms() -> None:
    assert not ChatService._has_lexical_relevance(
        "refund status for international purchase",
        "Refunds are available.",
    )
