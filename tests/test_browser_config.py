from src.scraper import build_persistent_context_kwargs
from src import config


def test_context_kwargs_apply_stealth_config():
    kwargs = build_persistent_context_kwargs(headless=True, proxy=None)
    assert kwargs["locale"] == config.PLAYWRIGHT_LOCALE
    assert kwargs["timezone_id"] == config.PLAYWRIGHT_TIMEZONE
    assert kwargs["channel"] == config.BROWSER_CHANNEL
    assert kwargs["user_data_dir"] == config.USER_DATA_DIR
    # fingerprintable automation flags must NOT be present
    args = kwargs.get("args", [])
    assert "--disable-blink-features=AutomationControlled" not in args
    assert "--no-sandbox" not in args


def test_context_kwargs_include_proxy_when_given():
    kwargs = build_persistent_context_kwargs(headless=True,
                                             proxy="http://user:pass@host:8080")
    assert kwargs["proxy"]["server"] == "http://host:8080"
    assert kwargs["proxy"]["username"] == "user"
