from src.parser import ProductParser

HTML = """
<html><body>
  <h1 class="headline">Big News Today</h1>
  <span class="author">Jane Doe</span>
  <a class="src" href="https://example.com/full">read more</a>
  <img class="hero" src="/img/x.jpg">
</body></html>
"""


def test_parse_custom_extracts_text_and_attributes():
    parser = ProductParser()
    fields = {
        "title": {"selector": "h1.headline"},
        "author": {"selector": ".author"},
        "link": {"selector": "a.src", "attr": "href"},
        "image": {"selector": "img.hero", "attr": "src"},
        "missing": {"selector": ".nope"},
    }
    out = parser.parse_custom(HTML, "https://example.com/article", fields)
    assert out["url"] == "https://example.com/article"
    assert out["data"]["title"] == "Big News Today"
    assert out["data"]["author"] == "Jane Doe"
    assert out["data"]["link"] == "https://example.com/full"
    assert out["data"]["image"] == "https://example.com/img/x.jpg"  # resolved to absolute
    assert out["data"]["missing"] is None
