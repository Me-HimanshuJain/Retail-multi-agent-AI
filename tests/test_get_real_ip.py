from fastapi import Request
from src.api.limiter import get_real_ip


def test_get_real_ip_forwarded():
    req = Request(
        {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
            "client": ("testclient", 50000),
        }
    )

    assert get_real_ip(req) == "1.2.3.4"


def test_get_real_ip_client():
    req = Request(
        {
            "type": "http",
            "headers": [],
            "client": ("127.0.0.1", 50000),
        }
    )

    assert get_real_ip(req) == "127.0.0.1"