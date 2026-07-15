from app.core.apikeys import generate_api_key, verify_api_key, hash_api_key


def test_generate_returns_raw_prefix_hash():
    raw, prefix, h = generate_api_key()
    assert raw.startswith("sk_")
    assert prefix == raw[:12]
    assert len(prefix) == 12
    assert h == hash_api_key(raw)


def test_verify_matches_only_correct_key():
    raw, prefix, h = generate_api_key()
    assert verify_api_key(raw, h) is True
    assert verify_api_key("sk_wrongkey", h) is False
    assert verify_api_key("", h) is False


def test_keys_are_unique():
    a, _, _ = generate_api_key()
    b, _, _ = generate_api_key()
    assert a != b
