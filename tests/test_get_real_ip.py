from src.api.main import get_real_ip
from fastapi import Request

req = Request({'type': 'http', 'headers': [(b'x-forwarded-for', b'1.2.3.4')], 'client': ('testclient', 50000)})
print("with header:", get_real_ip(req))

req2 = Request({'type': 'http', 'headers': [], 'client': ('testclient', 50000)})
print("without header:", get_real_ip(req2))
