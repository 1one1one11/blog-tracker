from blog_tracker.config import _split_env_list, _unique_nonempty


def test_split_env_list_accepts_commas_and_newlines():
    assert _split_env_list("token-a, token-b\ntoken-c") == ["token-a", "token-b", "token-c"]


def test_unique_nonempty_preserves_order():
    assert _unique_nonempty(["", "token-a", "token-b", "token-a"]) == ["token-a", "token-b"]
