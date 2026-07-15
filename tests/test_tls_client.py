import pytest
from src.scraper import TLSClient, ScraperResponse


class FakeResponse:
    def __init__(self, status_code=200, text="<html>ok</html>", url="http://x.com"):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = {"server": "nginx"}
        self.cookies = type("C", (), {"get_dict": lambda self: {}})()


class FakeSession:
    instances = 0

    def __init__(self, *args, **kwargs):
        FakeSession.instances += 1

    async def request(self, *args, **kwargs):
        return FakeResponse()

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_session_is_reused_across_fetches():
    FakeSession.instances = 0
    client = TLSClient(session_factory=lambda: FakeSession())
    r1 = await client.fetch("http://x.com/a")
    r2 = await client.fetch("http://x.com/b")
    await client.aclose()
    assert r1.success and r2.success
    assert FakeSession.instances == 1  # one session shared by both fetches


from src.scraper import ScraperBlockError


class RotatingFakeSession:
    """Blocks on the first proxy, succeeds on any other."""
    def __init__(self):
        pass

    async def request(self, *args, **kwargs):
        proxies = kwargs.get("proxies") or {}
        if proxies.get("https") == "http://bad:1@h:1":
            return FakeResponse(status_code=403,
                                text="<title>Just a moment...</title>",
                                url="http://x.com")
        return FakeResponse(status_code=200, text="<html>ok</html>")

    async def close(self):
        pass


class StubRotator:
    def __init__(self):
        self.calls = ["http://bad:1@h:1", "http://good:1@h:2"]
        self.i = -1
        self.failed = []

    def get_proxy(self):
        self.i += 1
        return self.calls[min(self.i, len(self.calls) - 1)]

    def mark_failed(self, p):
        self.failed.append(p)

    def mark_success(self, p):
        pass


@pytest.mark.asyncio
async def test_rotates_proxy_and_ua_on_block():
    from src import config
    config.MAX_RETRIES = 3
    config.BACKOFF_FACTOR = 0.01
    rotator = StubRotator()
    client = TLSClient(session_factory=lambda: RotatingFakeSession(), rotator=rotator)
    res = await client.fetch("http://x.com")
    await client.aclose()
    assert res.success is True                     # recovered after rotating
    assert "http://bad:1@h:1" in rotator.failed    # first proxy marked failed
