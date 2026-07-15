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
