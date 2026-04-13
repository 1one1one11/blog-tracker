from blog_tracker.config import TelegramDestination, _parse_extra_destinations, _split_env_list, _unique_destinations, _unique_nonempty


def test_split_env_list_accepts_commas_and_newlines():
    assert _split_env_list("token-a, token-b\ntoken-c") == ["token-a", "token-b", "token-c"]


def test_unique_nonempty_preserves_order():
    assert _unique_nonempty(["", "token-a", "token-b", "token-a"]) == ["token-a", "token-b"]


def test_parse_extra_destinations_accepts_token_chat_pairs():
    assert _parse_extra_destinations("token-a|1382515939, token-b::-100123") == [
        TelegramDestination(bot_token="token-a", chat_id="1382515939"),
        TelegramDestination(bot_token="token-b", chat_id="-100123"),
    ]


def test_unique_destinations_deduplicates_token_chat_pairs():
    destinations = [
        TelegramDestination(bot_token="token-a", chat_id="1"),
        TelegramDestination(bot_token="token-a", chat_id="1"),
        TelegramDestination(bot_token="token-a", chat_id="2"),
    ]

    assert _unique_destinations(destinations) == [
        TelegramDestination(bot_token="token-a", chat_id="1"),
        TelegramDestination(bot_token="token-a", chat_id="2"),
    ]
