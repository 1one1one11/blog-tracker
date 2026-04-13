from blog_tracker.config import (
    TelegramDestination,
    _parse_extra_destinations,
    _split_env_list,
    _unique_destinations,
    _unique_nonempty,
    load_settings,
)


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


def test_load_settings_routes_extra_bot_tokens_to_extra_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "primary-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "primary-chat")
    monkeypatch.setenv("TELEGRAM_EXTRA_BOT_TOKENS", "extra-token")
    monkeypatch.setenv("TELEGRAM_EXTRA_CHAT_ID", "1382515939")
    monkeypatch.delenv("TELEGRAM_BOT_TOKENS", raising=False)
    monkeypatch.delenv("TELEGRAM_EXTRA_DESTINATIONS", raising=False)

    settings = load_settings()

    assert settings.telegram_destinations == [
        TelegramDestination(bot_token="primary-token", chat_id="primary-chat"),
        TelegramDestination(bot_token="extra-token", chat_id="1382515939"),
    ]
