from src.utils import check_bot_challenges


def test_normal_page_mentioning_captcha_is_not_blocked():
    html = "<html><body><p>Please solve the captcha to post a comment.</p></body></html>"
    res = check_bot_challenges(html, "http://shop.example/item", status_code=200,
                               headers={"server": "nginx"})
    assert res["blocked"] is False


def test_cloudflare_title_challenge_blocked():
    html = "<html><head><title>Just a moment...</title></head></html>"
    res = check_bot_challenges(html, "http://x.com", status_code=403,
                               headers={"server": "cloudflare"})
    assert res["blocked"] is True
    assert res["system"] == "Cloudflare"


def test_cloudflare_mitigated_header_blocked():
    res = check_bot_challenges("<html></html>", "http://x.com", status_code=403,
                               headers={"cf-mitigated": "challenge"})
    assert res["blocked"] is True
    assert res["system"] == "Cloudflare"


def test_cloudflare_turnstile_script_blocked():
    html = "<html><body><script src='https://challenges.cloudflare.com/turnstile/v0/api.js'></script></body></html>"
    res = check_bot_challenges(html, "http://x.com", status_code=200, headers={})
    assert res["blocked"] is True
    assert res["system"] == "Cloudflare"


def test_datadome_marker_blocked():
    html = "<html><body><script src='https://geo.captcha-delivery.com/captcha/'></script></body></html>"
    res = check_bot_challenges(html, "http://x.com", status_code=403, headers={})
    assert res["blocked"] is True
    assert res["system"] == "DataDome"


def test_generic_recaptcha_only_on_challenge_status():
    html = "<html><body><div class='g-recaptcha'></div></body></html>"
    # 200 with a recaptcha widget (e.g. a normal login page) -> not a block
    assert check_bot_challenges(html, "http://x.com", status_code=200, headers={})["blocked"] is False
    # same widget behind a 403 wall -> block
    assert check_bot_challenges(html, "http://x.com", status_code=403, headers={})["blocked"] is True


def test_backward_compatible_two_arg_call():
    # old call sites pass only (html, url); CF title must still be detected
    old_cf = "<html><head><title>Attention Required! | Cloudflare</title></head></html>"
    assert check_bot_challenges(old_cf, "http://x.com")["blocked"] is True
