from fastapi import Request
from slowapi import Limiter

def get_real_ip(request: Request) -> str:
    """Extract real IP from headers if behind proxy, else fallback to client host."""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    if not request.client or not request.client.host:
        return "127.0.0.1"
    return request.client.host

limiter = Limiter(key_func=get_real_ip, default_limits=["200/minute"])
