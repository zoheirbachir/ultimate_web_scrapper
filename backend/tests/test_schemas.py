import pytest
from pydantic import ValidationError
from app.schemas import JobCreate


def test_auto_mode_defaults():
    j = JobCreate(urls=["http://a", "http://b"])
    assert j.mode == "auto"
    assert j.concurrency == 5
    assert j.use_browser_fallback is True


def test_custom_mode_requires_fields():
    with pytest.raises(ValidationError):
        JobCreate(urls=["http://a"], mode="custom")
    j = JobCreate(urls=["http://a"], mode="custom", fields={"t": {"selector": "h1"}})
    assert j.fields["t"].selector == "h1"


def test_rejects_empty_urls():
    with pytest.raises(ValidationError):
        JobCreate(urls=[])


def test_rejects_too_many_urls():
    with pytest.raises(ValidationError):
        JobCreate(urls=["http://a"] * 201)


def test_concurrency_bounds():
    with pytest.raises(ValidationError):
        JobCreate(urls=["http://a"], concurrency=0)
    with pytest.raises(ValidationError):
        JobCreate(urls=["http://a"], concurrency=99)
